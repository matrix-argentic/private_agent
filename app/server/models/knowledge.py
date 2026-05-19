"""Knowledge SQLAlchemy model."""

from sqlalchemy import Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.client.database import Base


class KnowledgeModel(Base):
    __tablename__ = "knowledges"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[str] = mapped_column(String, default="")
    document_count: Mapped[int] = mapped_column(Integer, default=0)
