"""Document SQLAlchemy model."""

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.client.database import Base


class DocumentModel(Base):
    """Document ORM model.

    ⚠️ The DB column is named ``metadata``, but the Python attribute is
    ``_metadata`` to avoid conflicting with ``Base.metadata`` (SQLAlchemy's
    ``MetaData`` instance).  The service layer handles the mapping between
    ``_metadata`` (ORM) and ``metadata`` (Pydantic).
    """

    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    file_id: Mapped[str] = mapped_column(String, default="")
    file_name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, default="")
    knowledge_id: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[str] = mapped_column(String, default="")
    file_path: Mapped[str] = mapped_column(String, default="")
    status: Mapped[str] = mapped_column(String, default="uploaded")
    _metadata: Mapped[list] = mapped_column("metadata", JSON, default=list)
