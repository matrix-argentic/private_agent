"""Chat message Pydantic schemas."""

from pydantic import BaseModel


class ChatMessage(BaseModel):
    id: str
    session_id: str
    user_id: str
    query: str
    response: str = ""
    created_at: str = ""
    rating: int | None = None
    comment: str | None = None
    error: str | None = None

    model_config = {"from_attributes": True}


class SaveChatMessageRequest(BaseModel):
    session_id: str
    user_id: str
    query: str
    response: str = ""
    rating: int | None = None
    comment: str | None = None
    error: str | None = None
