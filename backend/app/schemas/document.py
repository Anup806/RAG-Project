import uuid
from datetime import datetime

from pydantic import BaseModel

from app.models.document import DocumentStatus


class DocumentRead(BaseModel):
    id: uuid.UUID
    filename: str
    content_type: str
    file_size: int
    status: DocumentStatus
    page_count: int
    chunk_count: int
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UploadBatchRead(BaseModel):
    id: uuid.UUID
    original_count: int
    accepted_count: int
    status: str
    documents: list[DocumentRead]

    model_config = {"from_attributes": True}


class UploadAccepted(BaseModel):
    upload_id: uuid.UUID
    documents: list[DocumentRead]


class DocumentList(BaseModel):
    documents: list[DocumentRead]

