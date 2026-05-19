from pymilvus import DataType, MilvusClient, AsyncMilvusClient
from langchain_core.embeddings import Embeddings
from langchain_core.documents import Document


class VectorStoreRepository:

    def __init__(
        self,
        embedding: Embeddings,
        client: MilvusClient,
        aclient: AsyncMilvusClient,
        collection_name="it_collection",
        *,
        index_type: str = "HNSW",
        metric_type: str = "COSINE",
        index_params: dict | None = None,
    ):
        self.embedding = embedding
        self.collection_name = collection_name
        self._index_type = index_type
        self._metric_type = metric_type
        self._index_params = index_params or (
            {"M": 16, "efConstruction": 200}
            if index_type == "HNSW"
            else {"nlist": 1024}
        )
        self.milvus_client = client
        self.async_milvus_client = aclient

    # ── Collection lifecycle ──────────────────────────────────────────────────

    def _ensure_collection(self, dimension: int) -> None:
        """Create the collection with proper schema if it doesn't exist."""
        if self.milvus_client.has_collection(self.collection_name):
            return

        schema = self.milvus_client.create_schema(
            auto_id=True,
            enable_dynamic_field=True,
        )
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("vector", DataType.FLOAT_VECTOR, dim=dimension)
        schema.add_field("text", DataType.VARCHAR, max_length=65_535)

        index_params = self.milvus_client.prepare_index_params()
        index_params.add_index(
            field_name="vector",
            index_type=self._index_type,
            metric_type=self._metric_type,
            params=self._index_params,
        )

        self.milvus_client.create_collection(
            collection_name=self.collection_name,
            schema=schema,
            index_params=index_params,
        )

    # ── Core operations ───────────────────────────────────────────────────────

    def add_documents(self, documents: list[Document], batch_size: int = 50) -> int:
        """Embed and store documents into Milvus.

        Each document's ``page_content`` is both vectorised (stored as
        ``vector``) and stored verbatim as ``text``; ``metadata`` is
        stored as dynamic fields for filtering.
        """
        if not documents:
            return 0

        texts = [doc.page_content for doc in documents]
        vectors = self.embedding.embed_documents(texts)
        if not vectors:
            return 0

        self._ensure_collection(len(vectors[0]))

        total = 0
        for start in range(0, len(documents), batch_size):
            batch_docs = documents[start : start + batch_size]
            batch_vecs = vectors[start : start + batch_size]

            data: list[dict] = []
            for doc, vec in zip(batch_docs, batch_vecs):
                entity = {"vector": vec, "text": doc.page_content}
                entity.update(doc.metadata)
                data.append(entity)

            res = self.milvus_client.insert(
                collection_name=self.collection_name,
                data=data,
            )
            total += res.get("insert_count", 0)

        return total

    async def aadd_documents(
        self, documents: list[Document], batch_size: int = 32
    ) -> int:
        """Async variant of add_documents."""
        if not documents:
            return 0

        texts = [doc.page_content for doc in documents]
        vectors = await self.embedding.aembed_documents(texts)
        if not vectors:
            return 0

        self._ensure_collection(len(vectors[0]))

        total = 0
        for start in range(0, len(documents), batch_size):
            batch_docs = documents[start : start + batch_size]
            batch_vecs = vectors[start : start + batch_size]

            data: list[dict] = []
            for doc, vec in zip(batch_docs, batch_vecs):
                entity = {"vector": vec, "text": doc.page_content}
                entity.update(doc.metadata)
                data.append(entity)

            res = await self.async_milvus_client.insert(
                collection_name=self.collection_name,
                data=data,
            )
            total += res.get("insert_count", 0)

        return total

    def delete_by_expression(self, expression: str) -> int:
        """Delete entities matching a Milvus filter expression.

        Example: ``delete_by_expression("document_id == 'abc123'")``
        """
        res = self.milvus_client.delete(
            collection_name=self.collection_name,
            filter=expression,
        )
        return res.get("delete_count", 0)

    def search(
        self,
        query: str,
        top_k: int = 5,
        kb_ids: list[str] | None = None,
    ) -> list[Document]:
        """Search for semantically similar documents in Milvus."""
        query_vector = self.embedding.embed_query(query)
        filter_expr = f"knowledge_id in {kb_ids}" if kb_ids else None
        results = self.milvus_client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["text", "document_id", "knowledge_id"],
            filter=filter_expr,
        )
        docs: list[Document] = []
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {})
                metadata = {
                    "document_id": entity.get("document_id", ""),
                    "knowledge_id": entity.get("knowledge_id", ""),
                }
                docs.append(
                    Document(
                        page_content=entity.get("text", ""),
                        metadata=metadata,
                    )
                )
        return docs

    async def asearch(
        self,
        query: str,
        top_k: int = 5,
        kb_ids: list[str] | None = None,
    ) -> list[Document]:
        """Async search with optional kb_ids filtering."""
        query_vector = await self.embedding.aembed_query(query)
        filter_expr = f"knowledge_id in {kb_ids}" if kb_ids else None
        results = await self.async_milvus_client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["text", "document_id", "knowledge_id"],
            filter=filter_expr,
        )

        docs: list[Document] = []
        for hits in results:
            for hit in hits:
                entity = hit.get("entity", {})
                metadata = {
                    "document_id": entity.get("document_id", ""),
                    "knowledge_id": entity.get("knowledge_id", ""),
                    "score": hit.get("distance", 0.0),
                }
                docs.append(
                    Document(
                        page_content=entity.get("text", ""),
                        metadata=metadata,
                    )
                )
        return docs


# uv run -m rag.repository.vector_store
if __name__ == "__main__":
    from app.pkg.embedding.silicon_flow import SiliconFlowEmbedding
    from app.client.milvus import MilvusManager
    from app.core.config import get_app_config

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
