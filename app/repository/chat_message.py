"""Chat message repository — wraps raw SQLAlchemy CRUD."""

from sqlalchemy.orm import Session

from app.server.models.chat_message import ChatMessageModel


class ChatMessageRepository:
    """Data-access layer for chat_messages table."""

    def __init__(self, db: Session):
        self._db = db

    def create(self, model: ChatMessageModel) -> ChatMessageModel:
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return model

    def list_by_session(
        self, session_id: str, limit: int = 100
    ) -> list[ChatMessageModel]:
        return (
            self._db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
            .order_by(ChatMessageModel.created_at)
            .limit(limit)
            .all()
        )

    def list_before(
        self, session_id: str, before_id: str | None = None, limit: int = 20
    ) -> list[ChatMessageModel]:
        """Cursor-based pagination: returns messages older than ``before_id``.

        Results are ordered by ``created_at`` descending so the caller
        gets the most recent chunk first.  Pass ``before_id=None`` to
        fetch the latest page.
        """
        query = (
            self._db.query(ChatMessageModel)
            .filter(ChatMessageModel.session_id == session_id)
        )
        if before_id:
            before = self.get(before_id)
            if before:
                query = query.filter(ChatMessageModel.created_at < before.created_at)

        return (
            query
            .order_by(ChatMessageModel.created_at.desc())
            .limit(limit + 1)
            .all()
        )

    def get(self, msg_id: str) -> ChatMessageModel | None:
        return (
            self._db.query(ChatMessageModel)
            .filter(ChatMessageModel.id == msg_id)
            .first()
        )
