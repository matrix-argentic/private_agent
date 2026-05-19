from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores.utils import filter_complex_metadata


from app.pkg.loader.file_loader import FileLoader
from app.pkg.loader.lenovo import LenovoDocumentLoader
from app.repository.vector_store import VectorStoreRepository


class IngestService:
    """
    文档载入的服务：load -> split -> save
    """

    def __init__(
        self,
        vector_store_repo: VectorStoreRepository,
    ):
        # self.text_spliter = MarkdownHeaderTextSplitter(
        #     headers_to_split_on=[
        #         ("#", "section"),
        #         ("##", "subsection"),
        #         ("###", "subsubsection"),
        #     ]
        # )
        self.text_spliter = RecursiveCharacterTextSplitter(
            separators=["\n##", "\n**", "\n\n", "\n", " ", ""],
            chunk_size=1500,
            chunk_overlap=200,
        )
        self.vector_store_repo = vector_store_repo

    def ingest(self, knowledge_no_list: list[int]):
        loader = LenovoDocumentLoader(knowledge_no_list=knowledge_no_list)
        documents = loader.load()
        documents = self.text_spliter.split_documents(documents=documents)
        documents = filter_complex_metadata(documents=documents)
        documents = [
            document for document in documents if document.page_content.strip()
        ]
        if len(documents) > 0:
            self.vector_store_repo.add_documents(documents=documents)

    def ingest_file(
        self,
        file_path: Path,
        filename: str,
        metadata: dict | None = None,
    ) -> int:
        """提取单个上传的文件.

        Pipeline: load → split → filter → store (和
        :meth:`ingest` 一样).

        Args:
            file_path: 文件路径.
            filename: 原始文件名 (用来做类型判断).
            metadata: 元数据.

        Returns:
            Number of chunks inserted.
        """
        if metadata is None:
            metadata = {}

        loader = FileLoader(file_path=file_path, filename=filename, metadata=metadata)
        documents = list(loader.lazy_load())
        if not documents:
            return 0

        documents = self.text_spliter.split_documents(documents=documents)
        documents = [doc for doc in documents if doc.page_content.strip()]
        for doc in documents:
            doc.metadata = metadata
        documents = filter_complex_metadata(documents=documents)
        if not documents:
            return 0

        return self.vector_store_repo.add_documents(documents=documents)


# uv run -m rag.service.ingest
if __name__ == "__main__":
    from app.pkg.embedding.silicon_flow import SiliconFlowEmbedding
    from app.client.milvus import MilvusManager
    from app.core.config import get_app_config
    from tqdm import tqdm

    config = get_app_config()
    embedding = SiliconFlowEmbedding(
        api_key=config.embedding.siliconflow_api_key,
        model=config.embedding.embedding_model,
    )
    mgr = MilvusManager(milvus_config=config.milvus)
    repo = VectorStoreRepository(
        embedding=embedding,
        client=mgr.client,
        aclient=mgr.aclient,
    )

    ingest = IngestService(vector_store_repo=repo)

    batch_size = 50
    total = 500
    for start in tqdm(
        range(1, total + 1, batch_size), desc="知识库上传进度", unit="batch"
    ):
        end = min(start + batch_size, total + 1)
        knowledge_no_list = list(range(start, end))
        ingest.ingest(knowledge_no_list=knowledge_no_list)
