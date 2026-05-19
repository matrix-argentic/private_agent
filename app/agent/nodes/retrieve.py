from loguru import logger

from app.agent.state import ChatContext, ChatState
from langgraph.runtime import Runtime


async def retrieve_node(
    state: ChatState, runtime: Runtime[ChatContext]
) -> ChatState:
    query = state.get("re_query", "") or state.get("query", "")
    kb_ids = state.get("matched_kb_ids", [])

    search_service = runtime.context.get("search_service")
    if not search_service or not query:
        logger.warning("search_service unavailable or empty query, skipping retrieval")
        return {}

    logger.info("retrieving for query={} kb_ids={}", query, kb_ids)
    docs = await search_service.search(query=query, kb_ids=kb_ids or None)

    retrieved = [
        {"content": doc.page_content, "metadata": doc.metadata} for doc in docs
    ]
    logger.info("retrieved {} documents", len(retrieved))
    return {"retrieved_docs": retrieved}
