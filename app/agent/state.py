from typing import Annotated, List, TypedDict

from langchain.messages import AnyMessage
from langfuse import Langfuse
from langgraph.graph import add_messages

from app.repository.document import DocumentRepository
from app.repository.knowledge import KnowledgeRepository
from app.service.search import SearchService


class ChatState(TypedDict):
    query: str
    re_query: str  # 重写的问题
    summary: str  # 短期记忆总结
    intent: str  # 用户意图
    matched_tool_ids: List[str]  # 匹配的工具ID列表
    matched_kb_ids: List[str]  # 匹配的知识库ID列表
    retrieved_docs: List[dict]  # 检索到的文档列表
    messages: Annotated[list[AnyMessage], add_messages]


class ChatContext(TypedDict):
    langfuse: Langfuse
    knowledge_repo: KnowledgeRepository
    document_repo: DocumentRepository
    search_service: SearchService
