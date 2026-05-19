import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Body, Depends, File, UploadFile
from fastapi.exceptions import HTTPException

from loguru import logger

from fastapi import Depends

from app.server.dependency.dependency import (
    get_current_user,
    get_document_service,
    get_ingest_service,
    get_knowledge_service,
    get_vector_store_repo,
)
from app.server.schema.document import (
    CreateDocumentRequest,
    DocumentContentUpdate,
    DocumentUpdate,
)
from app.server.schema.ingest import DocMetadata, IngestRequest
from app.server.schema.knowledge import CreateKnowledgeRequest
from app.repository.vector_store import VectorStoreRepository
from app.service.document import DocumentService
from app.service.ingest import IngestService
from app.service.knowledge import KnowledgeService

api_router = APIRouter(prefix="/api")

# All data routes require authentication
protected_router = APIRouter(
    prefix="/api",
    dependencies=[Depends(get_current_user)],
)

_UPLOAD_DIR = Path(__file__).resolve().parents[3] / "data" / "uploads"
_DOCUMENTS_DIR = Path(__file__).resolve().parents[3] / "data" / "documents"

__all__ = ["api_router", "protected_router"]


@api_router.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


# ── Upload & Ingest ────────────────────────────────────────────


@protected_router.post("/upload")
async def upload(
    file: UploadFile = File(...),
    doc_service: DocumentService = Depends(get_document_service),
):
    """上传文件，并保存到磁盘.

    Returns 返回 ``file_id`` 可以在 ``POST /api/ingest`` 接口中使用.
    """
    _UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    dest = _UPLOAD_DIR / file_id

    total = 0
    with open(dest, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            f.write(chunk)
            total += len(chunk)

    doc_service.create(
        file_id=file_id,
        file_name=file.filename or file_id,
        file_path=dest,
    )

    logger.info("File saved: {} ({} bytes, id={})", file.filename, total, file_id)
    return {"file_id": file_id, "filename": file.filename}


@protected_router.post("/ingest")
async def ingest(
    req: IngestRequest,
    ingest_service: IngestService = Depends(get_ingest_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    doc_service: DocumentService = Depends(get_document_service),
):
    """为上传的文件附加元数据并提取到向量存储中。

    JSON 请求体：

    .. code-block:: json

        {
            "file_id": "abc...",
            "filename": "doc.pdf",
            "title": "xx...",
            "description": "desc...",
            "knowledge_id": "knowxxx.."
        }
    """
    file_path = _UPLOAD_DIR / req.file_id
    if not file_path.exists():
        raise HTTPException(
            status_code=404, detail=f"file_id '{req.file_id}' not found"
        )

    doc = doc_service.get(req.file_id)
    if not doc:
        raise HTTPException(
            status_code=404, detail=f"document record '{req.file_id}' not found"
        )

    doc_meta = DocMetadata(
        knowledge_id=req.knowledge_id,
        title=req.title,
        description=req.description,
        create_time=datetime.now(timezone.utc).isoformat(),
        document_id=doc.id,
    )
    filename: str = ""

    filename = req.filename or req.file_id

    # Build metadata with document_id for chunk→doc linkage
    ingest_metadata = doc_meta.model_dump()

    inserted = ingest_service.ingest_file(
        file_path=file_path,
        filename=filename,
        metadata=ingest_metadata,
    )

    # Move file to permanent storage instead of deleting
    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    permanent_path = _DOCUMENTS_DIR / req.file_id
    file_path.rename(permanent_path)

    # Update document record
    doc_service.patch(
        doc.id,
        DocumentUpdate(
            knowledge_id=req.knowledge_id,
            description=req.description,
            file_path=str(permanent_path),
            status="ingested",
        ),
    )
    # doc_service.update_status(doc.id, "ingested")

    # Update KB document count (one document, not chunks)
    if req.knowledge_id:
        knowledge_service.increment_document_count(req.knowledge_id, 1)

    return {
        "message": "ok",
        "filename": filename,
        "chunks_inserted": inserted,
        "metadata": doc_meta.model_dump(),
        "knowledge_id": req.knowledge_id,
    }


# ── Document CRUD ─────────────────────────────────────────────


@protected_router.post("/documents/create", status_code=201)
def create_document(
    req: CreateDocumentRequest,
    doc_service: DocumentService = Depends(get_document_service),
):
    """创建新的空 Markdown 文档记录和文件。"""
    file_id = uuid.uuid4().hex

    _DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    file_path = _DOCUMENTS_DIR / file_id
    file_path.write_text("", encoding="utf-8")

    doc = doc_service.create(
        file_id=file_id,
        file_name=req.filename,
        file_path=file_path,
        knowledge_id=req.knowledge_id,
        description=req.description,
    )

    logger.info("New document created: {} ({})", req.filename, file_id)
    return doc


@protected_router.get("/documents")
def list_documents(
    knowledge_id: str | None = None,
    search: str | None = None,
    status: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    doc_service: DocumentService = Depends(get_document_service),
):
    """获取文档列表，支持按知识库、文件名、状态、时间范围筛选."""
    return doc_service.list_filtered(
        knowledge_id=knowledge_id,
        search=search,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )


@protected_router.patch("/documents/{doc_id}")
def update_document(
    doc_id: str,
    body: DocumentUpdate,
    doc_service: DocumentService = Depends(get_document_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
):
    """更新文档的元数据（描述、关联知识库等）。"""
    current = doc_service.get(doc_id)
    if not current:
        raise HTTPException(404, "Document not found")

    # Adjust KB counts if KB changed
    if body.knowledge_id is not None and body.knowledge_id != current.knowledge_id:
        if current.knowledge_id:
            knowledge_service.increment_document_count(current.knowledge_id, -1)
        if body.knowledge_id:
            knowledge_service.increment_document_count(body.knowledge_id, 1)

    updated = doc_service.patch(doc_id, body)
    if not updated:
        raise HTTPException(404, "Document not found")
    return updated


@protected_router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
    vector_store_repo: VectorStoreRepository = Depends(get_vector_store_repo),
):
    """删除文档及其文件、Milvus 向量和知识库计数。"""
    doc = doc_service.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Decrement KB count
    if doc.knowledge_id:
        knowledge_service.increment_document_count(doc.knowledge_id, -1)

    # Delete chunks from Milvus
    vector_store_repo.delete_by_expression(f"document_id == '{doc_id}'")

    # Delete file from disk
    file_path = Path(doc.file_path)
    if file_path.exists():
        file_path.unlink()

    doc_service.delete(doc_id)
    logger.info("Document deleted: {} ({})", doc.file_name, doc_id)
    return {"message": "ok"}


@protected_router.get("/documents/{doc_id}/content")
def get_document_content(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
):
    """读取文档的原始内容（用于编辑器）。"""
    doc = doc_service.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(404, "Document file not found on disk")

    content = file_path.read_text(encoding="utf-8")
    return {"content": content, "file_name": doc.file_name}


@protected_router.put("/documents/{doc_id}/content")
async def update_document_content(
    doc_id: str,
    body: DocumentContentUpdate,
    doc_service: DocumentService = Depends(get_document_service),
    ingest_service: IngestService = Depends(get_ingest_service),
    vector_store_repo: VectorStoreRepository = Depends(get_vector_store_repo),
):
    """保存编辑后的文档内容并重新同步到向量数据库。"""
    doc = doc_service.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Write new content to disk
    file_path = Path(doc.file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(body.content, encoding="utf-8")

    # Delete old Milvus chunks for this document
    vector_store_repo.delete_by_expression(f"document_id == '{doc_id}'")

    # Re-ingest
    ingest_metadata = {"document_id": doc_id}
    if doc.knowledge_id:
        ingest_metadata["knowledge_id"] = doc.knowledge_id
    inserted = ingest_service.ingest_file(
        file_path=file_path,
        filename=doc.file_name,
        metadata=ingest_metadata,
    )

    doc_service.update_status(doc_id, "ingested")
    logger.info("Document re-synced after edit: {} ({})", doc.file_name, doc_id)
    return {"message": "ok", "chunks_inserted": inserted}


@protected_router.post("/documents/{doc_id}/resync")
async def resync_document(
    doc_id: str,
    doc_service: DocumentService = Depends(get_document_service),
    ingest_service: IngestService = Depends(get_ingest_service),
    vector_store_repo: VectorStoreRepository = Depends(get_vector_store_repo),
):
    """重新同步文档到向量数据库（不修改内容）。"""
    doc = doc_service.get(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    file_path = Path(doc.file_path)
    if not file_path.exists():
        raise HTTPException(404, "Document file not found on disk")

    # Delete old chunks
    vector_store_repo.delete_by_expression(f"document_id == '{doc_id}'")

    # Re-ingest with current metadata
    ingest_metadata = {"document_id": doc_id}
    if doc.knowledge_id:
        ingest_metadata["knowledge_id"] = doc.knowledge_id
    inserted = ingest_service.ingest_file(
        file_path=file_path,
        filename=doc.file_name,
        metadata=ingest_metadata,
    )

    doc_service.update_status(doc_id, "ingested")
    logger.info("Document re-synced: {} ({})", doc.file_name, doc_id)
    return {"message": "ok", "chunks_inserted": inserted}
