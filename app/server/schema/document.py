"""Document schemas."""

from pydantic import BaseModel


class MetadataItem(BaseModel):
    """A single metadata key-value pair."""
    key: str
    value: str


class Document(BaseModel):
    """上传的文档记录"""

    id: str
    file_id: str
    file_name: str
    description: str = ""
    knowledge_id: str = ""
    created_at: str = ""
    file_path: str = ""
    status: str = "uploaded"
    metadata: list[MetadataItem] = []

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    """Partial update payload for a document record."""

    description: str | None = None
    knowledge_id: str | None = None
    file_path: str | None = None
    status: str | None = None
    metadata: list[MetadataItem] | None = None


class DocumentContentUpdate(BaseModel):
    """New content for a document."""

    content: str


class CreateDocumentRequest(BaseModel):
    """Payload for creating a new empty markdown document."""

    filename: str
    description: str = ""
    knowledge_id: str = ""
