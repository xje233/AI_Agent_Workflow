"""文档分块：将加载后的长文本切为适合向量化和检索的片段。"""
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document


def split_documents(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    # 重叠区保留跨段语义，分隔符顺序优先尊重自然段和中文句号。
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_documents(documents)
