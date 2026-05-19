"""KnowledgeBase repository — wraps raw SQLAlchemy CRUD."""

from sqlalchemy.orm import Session

from app.server.models.knowledge import KnowledgeModel


class KnowledgeRepository:
    """Data-access layer for knowledges table."""

    def __init__(self, db: Session):
        self._db = db

    def list(self) -> list[KnowledgeModel]:
        return self._db.query(KnowledgeModel).all()

    def get(self, kb_id: str) -> KnowledgeModel | None:
        return self._db.query(KnowledgeModel).filter(KnowledgeModel.id == kb_id).first()

    def create(self, model: KnowledgeModel) -> KnowledgeModel:
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model

    def delete(self, model: KnowledgeModel) -> None:
        self._db.delete(model)
        self._db.commit()

    def update(self, kb_id: str, **kwargs) -> KnowledgeModel | None:
        model = self.get(kb_id)
        if not model:
            return None
        for key, value in kwargs.items():
            if hasattr(model, key):
                setattr(model, key, value)
        self._db.commit()
        self._db.refresh(model)
        return model

    def increment_document_count(self, kb_id: str, delta: int = 1) -> None:
        model = self.get(kb_id)
        if model:
            model.document_count += delta
            self._db.commit()
