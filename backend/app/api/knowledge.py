"""知识库 API — 文档上传/列表/删除，全链路异步"""
import os
import uuid
import traceback
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from sqlalchemy import select
from app.database import get_sessionmaker
from app.models.document import Document as DocumentModel
from app.rag.loader import load_document
from app.rag.splitter import split_documents
from app.rag.retriever import add_documents, get_vector_store

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

# 使用绝对路径，避免工作目录变化导致文件路径不一致
UPLOAD_DIR = str(Path(__file__).resolve().parent.parent.parent / "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    allowed_types = {".pdf", ".docx", ".txt", ".md"}
    suffix = os.path.splitext(file.filename)[1].lower()

    if suffix not in allowed_types:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}")

    file_id = str(uuid.uuid4())
    save_path = os.path.join(UPLOAD_DIR, f"{file_id}_{file.filename}")

    content = await file.read()
    with open(save_path, "wb") as f:
        f.write(content)

    async with get_sessionmaker()() as db:
        doc = DocumentModel(
            filename=file.filename,
            file_path=save_path,
            file_type=suffix.lstrip("."),
            vector_status="pending",
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        try:
            doc.vector_status = "indexing"
            await db.commit()

            # 检查文件是否为空（0 bytes）
            if os.path.getsize(save_path) == 0:
                raise ValueError("上传文件为空（0 字节），无法建立索引")

            # 1. 加载文档（PDF 自动处理扫描版 OCR 回退）
            documents = load_document(save_path)
            if not documents:
                raise ValueError("文档内容为空，无法建立索引")

            # 2. 分块
            chunks = split_documents(documents)
            if not chunks:
                raise ValueError(
                    "文档分块后无有效内容，无法建立索引。"
                    "可能原因：1) 扫描版/图片 PDF 无法识别文字（需 OCR 支持）；"
                    "2) 文档内容纯为图片/表格，无可提取文字。"
                )

            # 3. 写入向量库（异步）
            await add_documents(chunks)

            doc.vector_status = "completed"
        except Exception as e:
            doc.vector_status = "failed"
            # 对用户友好的错误信息，不暴露原始 trace
            detail = f"索引失败: {str(e)[:200]}"
            if isinstance(e, ValueError):
                detail = str(e)  # ValueError 的信息已经是用户友好的
            raise HTTPException(status_code=500, detail=detail)
        finally:
            await db.commit()

    return {
        "id": str(doc.id),
        "filename": file.filename,
        "status": doc.vector_status,
    }


@router.get("/documents")
async def list_documents():
    async with get_sessionmaker()() as db:
        result = await db.execute(select(DocumentModel).order_by(DocumentModel.created_at.desc()))
        docs = result.scalars().all()
        return [
            {
                "id": str(d.id),
                "filename": d.filename,
                "file_type": d.file_type,
                "vector_status": d.vector_status,
                "created_at": str(d.created_at),
            }
            for d in docs
        ]


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    async with get_sessionmaker()() as db:
        result = await db.execute(select(DocumentModel).where(DocumentModel.id == doc_id))
        doc = result.scalar_one_or_none()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除本地文件
        if os.path.exists(doc.file_path):
            os.remove(doc.file_path)

        # 删除向量库中的索引（关键：不能只删文件不删向量）
        try:
            vector_store = get_vector_store()
            # 获取该文档对应的向量 ID（通过 metadata 过滤）
            collection = vector_store._collection
            existing = collection.get(
                where={"source": doc.file_path},
                include=["embeddings"],
            )
            if existing and existing["ids"]:
                from app.rag.retriever import delete_documents
                await delete_documents(existing["ids"])
        except Exception:
            # 向量库清理失败不应阻止删除操作，记录日志即可
            print(f"[Knowledge] 向量清理失败 for doc {doc_id}: {traceback.format_exc()}")

        await db.delete(doc)
        await db.commit()

    return {"status": "ok"}
