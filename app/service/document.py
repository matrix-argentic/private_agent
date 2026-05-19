"""Document service — business logic for uploaded document records."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from loguru import logger

from app.repository.document import DocumentRepository
from app.server.models.document import DocumentModel
from app.server.schema.document import Document, DocumentUpdate


class DocumentService:
    """Business logic layer for document record management."""

    def __init__(self, repo: DocumentRepository):
        self._repo = repo

    @staticmethod
    def _orm_to_dict(orm: DocumentModel) -> dict:
        """Convert ORM instance to dict, renaming ``_metadata`` → ``metadata``."""
        return {
            "id": orm.id,
            "file_id": orm.file_id,
            "file_name": orm.file_name,
            "description": orm.description,
            "knowledge_id": orm.knowledge_id,
            "created_at": orm.created_at,
            "file_path": orm.file_path,
            "status": orm.status,
            "metadata": orm._metadata if isinstance(orm._metadata, list) else [],
        }

    def create(
        self,
        file_id: str,
        file_name: str,
        file_path: Path,
        knowledge_id: str = "",
        description: str = "",
    ) -> Document:
        orm = DocumentModel(
            id=file_id,
            file_id=file_id,
            file_name=file_name,
            description=description,
            knowledge_id=knowledge_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            file_path=str(file_path),
            status="uploaded",
        )
        self._repo.create(orm)
        logger.info("Document record created: {} ({})", file_name, file_id)
        return Document.model_validate(self._orm_to_dict(orm))

    def get(self, doc_id: str) -> Document | None:
        orm = self._repo.get(doc_id)
        return Document.model_validate(self._orm_to_dict(orm)) if orm else None

    def list(self) -> list[Document]:
        return [Document.model_validate(self._orm_to_dict(m)) for m in self._repo.list()]

    def list_filtered(
        self,
        knowledge_id: str | None = None,
        search: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[Document]:
        orms = self._repo.list_filtered(
            knowledge_id=knowledge_id,
            search=search,
            status=status,
            date_from=date_from,
            date_to=date_to,
        )
        return [Document.model_validate(self._orm_to_dict(m)) for m in orms]

    def patch(self, doc_id: str, updates: DocumentUpdate) -> Document | None:
        update_data = updates.model_dump(exclude_none=True)
        # Map Pydantic field name → ORM attribute name
        if "metadata" in update_data:
            update_data["_metadata"] = update_data.pop("metadata")
        orm = self._repo.update(doc_id, **update_data)
        return Document.model_validate(self._orm_to_dict(orm)) if orm else None

    def update_status(self, doc_id: str, status: str) -> Document | None:
        orm = self._repo.update(doc_id, status=status)
        return Document.model_validate(self._orm_to_dict(orm)) if orm else None

    def delete(self, doc_id: str) -> bool:
        return self._repo.delete(doc_id)
