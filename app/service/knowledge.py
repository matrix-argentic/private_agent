"""KnowledgeBase service — business logic for KB management."""

import uuid
from datetime import datetime, timezone

from loguru import logger

from app.repository.knowledge import KnowledgeRepository
from app.server.models.knowledge import KnowledgeModel
from app.server.schema.knowledge import CreateKnowledgeRequest, Knowledge


class KnowledgeService:
    """Business logic layer for knowledge base CRUD."""

    def __init__(self, repo: KnowledgeRepository):
        self._repo = repo

    def list(self) -> list[Knowledge]:
        return [Knowledge.model_validate(m) for m in self._repo.list()]

    def create(self, req: CreateKnowledgeRequest) -> Knowledge:
        kb_id = uuid.uuid4().hex[:12]
        orm = KnowledgeModel(
            id=kb_id,
            name=req.name,
            description=req.description,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._repo.create(orm)
        logger.info("Knowledge base created: {} ({})", req.name, kb_id)
        return Knowledge.model_validate(orm)

    def update(self, kb_id: str, name: str | None = None, description: str | None = None) -> Knowledge | None:
        updates = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if not updates:
            return None
        orm = self._repo.update(kb_id, **updates)
        if not orm:
            return None
        logger.info("Knowledge base updated: {} ({})", orm.name, kb_id)
        return Knowledge.model_validate(orm)

    def delete(self, kb_id: str) -> None:
        orm = self._repo.get(kb_id)
        if not orm:
            from fastapi.exceptions import HTTPException

            raise HTTPException(
                status_code=404, detail=f"knowledge base '{kb_id}' not found"
            )
        self._repo.delete(orm)
        logger.info("Knowledge base deleted: {} ({})", orm.name, kb_id)

    def increment_document_count(self, kb_id: str, delta: int = 1) -> None:
        self._repo.increment_document_count(kb_id, delta)
