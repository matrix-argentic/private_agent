"""Knowledge base group schemas."""

from pydantic import BaseModel


class Knowledge(BaseModel):
    """知识库分组"""

    id: str
    name: str
    description: str = ""
    created_at: str = ""
    document_count: int = 0

    model_config = {"from_attributes": True}


class CreateKnowledgeRequest(BaseModel):
    name: str
    description: str = ""


class UpdateKnowledgeRequest(BaseModel):
    name: str | None = None
    description: str | None = None
