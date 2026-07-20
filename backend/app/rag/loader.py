"""文档加载模块 — 支持中文编码 + 扫描版 PDF OCR 回退"""
import os
from langchain_community.document_loaders import (
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain.schema import Document
from pathlib import Path


def _load_pdf_with_ocr_fallback(file_path: str) -> list[Document]:
    """加载 PDF：先尝试提取文本层，如果全部为空则 OCR 回退"""
    # ── 第一步：用 pypdf 提取文本层 ──
    from langchain_community.document_loaders import PyPDFLoader
    loader = PyPDFLoader(file_path)
    docs = loader.load()

    # 检查是否有有效文本内容
    # 只有全部页面都没有文字时才触发较慢的 OCR 路径。
    has_text = any(doc.page_content.strip() for doc in docs)
    if has_text:
        return docs

    # ── 第二步：文本层为空 → 扫描版/图片 PDF，尝试 OCR ──
    print(f"[Loader] PDF 文本层为空，尝试 OCR: {file_path}")
    try:
        return _ocr_pdf(file_path)
    except ImportError:
        raise ValueError(
            "该 PDF 为扫描版/图片格式（无文本层），无法直接提取文字。\n"
            "请安装 OCR 支持后重试：pip install pymupdf rapidocr-onnxruntime\n"
            "或将 PDF 转为文字版后上传。"
        )
    except Exception as e:
        raise ValueError(
            f"扫描版 PDF OCR 处理失败: {e}\n"
            "建议将 PDF 转为文字版后重新上传。"
        )


def _ocr_pdf(file_path: str) -> list[Document]:
    """对扫描版 PDF 执行 OCR 提取文字（依赖 pymupdf + rapidocr-onnxruntime）"""
    import fitz  # pymupdf

    try:
        from rapidocr_onnxruntime import RapidOCR
    except ImportError:
        raise ImportError("rapidocr-onnxruntime 未安装")

    ocr_engine = RapidOCR()
    doc = fitz.open(file_path)
    documents = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        # 将 PDF 页面渲染为图片（dpi=200 平衡速度和精度）
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        # OCR 提取文字
        result, _ = ocr_engine(img_bytes)
        if result:
            # result 是 [[box, text, confidence], ...] 的列表
            text = "\n".join(item[1] for item in result)
        else:
            text = ""

        if text.strip():
            documents.append(Document(
                page_content=text,
                metadata={"source": file_path, "page": page_num + 1},
            ))

    doc.close()
    return documents


def load_document(file_path: str) -> list[Document]:
    """根据文件类型加载文档（PDF 支持扫描版 OCR 回退）"""
    suffix = Path(file_path).suffix.lower()

    # TextLoader 必须指定 encoding，Windows 默认 GBK 会导致中文文件乱码/报错
    loader_map = {
        ".pdf": _load_pdf_with_ocr_fallback,  # 自定义 PDF 加载（含 OCR 回退）
        ".docx": lambda fp: Docx2txtLoader(fp).load(),
        ".txt": lambda fp: TextLoader(fp, encoding="utf-8").load(),
        ".md": lambda fp: UnstructuredMarkdownLoader(fp).load(),
    }

    loader_factory = loader_map.get(suffix)
    if not loader_factory:
        raise ValueError(f"不支持的文件类型: {suffix}")

    return loader_factory(file_path)
