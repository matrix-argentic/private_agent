import asyncio

from langchain_core.documents import Document
from loguru import logger

from app.repository.vector_store import VectorStoreRepository


class SearchService:

    def __init__(self, vector_store_repo: VectorStoreRepository):
        self._repo = vector_store_repo

    async def search(
        self,
        query: str,
        top_k: int = 5,
        kb_ids: list[str] | None = None,
    ) -> list[Document]:
        """多路召回：同时进行带 kb_ids 筛选和不带筛选的搜索，然后去重和重排。"""
        logger.info("search query={} top_k={} kb_ids={}", query, top_k, kb_ids)

        # 两路召回：全局搜索 + kb_ids 限定搜索
        tasks = [self._repo.asearch(query=query, top_k=top_k * 2)]
        if kb_ids:
            tasks.append(
                self._repo.asearch(query=query, top_k=top_k * 2, kb_ids=kb_ids)
            )

        results = await asyncio.gather(*tasks)

        # 合并所有召回结果
        all_docs = [doc for result in results for doc in result]

        # 按 document_id 去重（保留 score 最高的）
        seen: dict[str, Document] = {}
        for doc in all_docs:
            doc_id = doc.metadata.get("document_id", "")
            score = doc.metadata.get("score", 0.0)
            if doc_id not in seen or score > seen[doc_id].metadata.get("score", 0.0):
                seen[doc_id] = doc

        deduped = list(seen.values())

        # 按 score 降序重排
        deduped.sort(key=lambda d: d.metadata.get("score", 0.0), reverse=True)

        return deduped[:top_k]
