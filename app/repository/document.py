"""Document repository — wraps raw SQLAlchemy CRUD."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.server.models.document import DocumentModel


class DocumentRepository:
    """Data-access layer for documents table."""

    def __init__(self, db: Session):
        self._db = db

    def list(self) -> list[DocumentModel]:
        return self._db.query(DocumentModel).all()

    def list_filtered(
        self,
        knowledge_id: str | None = None,
        search: str | None = None,
        status: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> list[DocumentModel]:
        query = self._db.query(DocumentModel)
        if knowledge_id:
            query = query.filter(DocumentModel.knowledge_id == knowledge_id)
        if search:
            query = query.filter(DocumentModel.file_name.ilike(f"%{search}%"))
        if status:
            query = query.filter(DocumentModel.status == status)
        if date_from:
            query = query.filter(DocumentModel.created_at >= date_from)
        if date_to:
            query = query.filter(DocumentModel.created_at <= date_to)
        return query.all()

    def get(self, doc_id: str) -> DocumentModel | None:
        return self._db.query(DocumentModel).filter(DocumentModel.id == doc_id).first()

    def create(self, model: DocumentModel) -> DocumentModel:
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model

    def update(self, doc_id: str, **kwargs) -> DocumentModel | None:
        model = self.get(doc_id)
        if not model:
            return None
        for key, value in kwargs.items():
            if value is not None:
                setattr(model, key, value)
        self._db.commit()
        self._db.refresh(model)
        return model

    def delete(self, doc_id: str) -> bool:
        model = self.get(doc_id)
        if not model:
            return False
        self._db.delete(model)
        self._db.commit()
        return True
