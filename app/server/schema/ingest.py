"""File ingest schemas — metadata model consistent with existing Lenovo ingest."""

from pydantic import BaseModel, Field


class DocMetadata(BaseModel):
    """Metadata stored per chunk in the vector store."""

    knowledge_id: str = ""
    title: str = ""
    description: str = ""
    document_id: str = ""
    create_time: str = ""


class IngestRequest(BaseModel):
    """JSON body for the ingest endpoint."""

    file_id: str
    filename: str = ""
    title: str = ""
    description: str = ""
    knowledge_id: str = ""
