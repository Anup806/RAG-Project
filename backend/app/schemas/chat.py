import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.models.chat import MessageRole


class Citation(BaseModel):
    filename: str
    document_id: str
    page_number: int
    chunk_id: str
    text: str


class ChatSessionCreate(BaseModel):
    title: str | None = None
    document_ids: list[uuid.UUID] = Field(default_factory=list)


class ChatSessionUpdate(BaseModel):
    title: str | None = None
    document_ids: list[uuid.UUID] | None = None


class ChatSessionRead(BaseModel):
    id: uuid.UUID
    title: str
    selected_document_ids: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageCreate(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    document_ids: list[uuid.UUID] | None = None


class MessageRead(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: MessageRole
    content: str
    citations: list[Citation] = Field(default_factory=list)
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatAnswer(BaseModel):
    message: MessageRead
    sources: list[Citation]


class ChatSessionList(BaseModel):
    sessions: list[ChatSessionRead]


class MessageList(BaseModel):
    messages: list[MessageRead]

