from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from langfuse import get_client
from langfuse.langchain import CallbackHandler

from app.agent.graph import get_agent
from app.pkg.embedding.silicon_flow import SiliconFlowEmbedding
from app.client.milvus import milvus_manager
from app.core.config import AppConfig, get_app_config
from app.repository.chat_message import ChatMessageRepository
from app.repository.document import DocumentRepository
from app.repository.knowledge import KnowledgeRepository
from app.repository.user import UserRepository
from app.repository.vector_store import VectorStoreRepository
from app.client.database import db_manager
from app.server.schema.auth import UserResponse
from app.service.auth import AuthService
from app.service.chat import ChatService
from app.service.document import DocumentService
from app.service.ingest import IngestService
from app.service.knowledge import KnowledgeService
from app.service.search import SearchService


def get_embedding(config: AppConfig = Depends(get_app_config)):
    return SiliconFlowEmbedding(
        api_key=config.embedding.siliconflow_api_key,
        model=config.embedding.embedding_model,
    )


def get_ingest_service(
    embedding: SiliconFlowEmbedding = Depends(get_embedding),
):
    repo = VectorStoreRepository(
        embedding=embedding,
        client=milvus_manager.client,
        aclient=milvus_manager.aclient,
    )
    return IngestService(vector_store_repo=repo)


def get_knowledge_service():
    """Yields a KnowledgeBaseService with a scoped DB session."""
    db = db_manager.get_session()
    try:
        repo = KnowledgeRepository(db)
        yield KnowledgeService(repo)
    finally:
        db.close()


def get_document_service():
    """Yields a DocumentService with a scoped DB session."""
    db = db_manager.get_session()
    try:
        repo = DocumentRepository(db)
        yield DocumentService(repo)
    finally:
        db.close()


def get_vector_store_repo(
    embedding: SiliconFlowEmbedding = Depends(get_embedding),
):
    """Returns a VectorStoreRepository with pre-initialized Milvus clients."""
    return VectorStoreRepository(
        embedding=embedding,
        client=milvus_manager.client,
        aclient=milvus_manager.aclient,
    )


def get_search_service(
    embedding: SiliconFlowEmbedding = Depends(get_embedding),
):
    repo = VectorStoreRepository(
        embedding=embedding,
        client=milvus_manager.client,
        aclient=milvus_manager.aclient,
    )
    return SearchService(vector_store_repo=repo)


langfuse = get_client()
langfuse_handler = CallbackHandler()


def get_document_repo():
    """Yields a DocumentRepository with a scoped DB session."""
    db = db_manager.get_session()
    try:
        yield DocumentRepository(db)
    finally:
        db.close()


def get_knowledge_repo():
    """Yields a KnowledgeRepository with a scoped DB session."""
    db = db_manager.get_session()
    try:
        yield KnowledgeRepository(db)
    finally:
        db.close()


def get_chat_message_repo():
    """Yields a ChatMessageRepository with a scoped DB session."""
    db = db_manager.get_session()
    try:
        yield ChatMessageRepository(db)
    finally:
        db.close()


async def get_chat_service(
    document_repo: DocumentRepository = Depends(get_document_repo),
    knowledge_repo: KnowledgeRepository = Depends(get_knowledge_repo),
    search_service: SearchService = Depends(get_search_service),
    chat_message_repo: ChatMessageRepository = Depends(get_chat_message_repo),
):
    agent = await get_agent()
    return ChatService(
        agent=agent,
        langfuse=langfuse,
        langfuse_handler=langfuse_handler,
        document_repo=document_repo,
        knowledge_repo=knowledge_repo,
        search_service=search_service,
        chat_message_repo=chat_message_repo,
    )


# ── Auth ──────────────────────────────────────────────────────────


def get_user_repo():
    """Yields a UserRepository with a scoped DB session."""
    db = db_manager.get_session()
    try:
        yield UserRepository(db)
    finally:
        db.close()


def get_auth_service(
    user_repo: UserRepository = Depends(get_user_repo),
    config: AppConfig = Depends(get_app_config),
) -> AuthService:
    return AuthService(user_repo, config.auth)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    return auth_service.get_current_user(token)
