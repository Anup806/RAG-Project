import uuid
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.config import settings
from app.database.session import get_session
from app.models.document import Document, DocumentStatus, UploadBatch
from app.models.user import User
from app.schemas.document import DocumentList, DocumentRead, UploadAccepted
from app.services.dependencies import get_vector_store
from app.services.document_service import process_document_job
from app.utils.files import make_storage_path, save_upload, validate_upload

router = APIRouter()


@router.post("/upload", response_model=UploadAccepted, status_code=status.HTTP_202_ACCEPTED)
async def upload_documents(
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
    files: Annotated[list[UploadFile], File(description="One or more PDF files.")],
) -> UploadAccepted:
    if not files:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files were uploaded.")
    if len(files) > settings.MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Upload at most {settings.MAX_FILES_PER_UPLOAD} PDFs at a time.",
        )

    for file in files:
        validate_upload(file)

    upload = UploadBatch(user_id=user.id, original_count=len(files), accepted_count=0)
    db.add(upload)
    await db.flush()

    documents: list[Document] = []
    saved_paths: list[Path] = []
    try:
        for file in files:
            destination = make_storage_path(file.filename or "document.pdf")
            size = await save_upload(file, destination)
            saved_paths.append(destination)
            document = Document(
                user_id=user.id,
                upload_batch_id=upload.id,
                filename=file.filename or destination.name,
                content_type=file.content_type or "application/pdf",
                file_size=size,
                storage_path=str(destination),
                status=DocumentStatus.pending,
            )
            db.add(document)
            documents.append(document)

        upload.accepted_count = len(documents)
        await db.commit()
        for document in documents:
            await db.refresh(document)
            background_tasks.add_task(process_document_job, document.id)
    except Exception:
        await db.rollback()
        for path in saved_paths:
            path.unlink(missing_ok=True)
        raise

    return UploadAccepted(upload_id=upload.id, documents=[DocumentRead.model_validate(doc) for doc in documents])


@router.get("", response_model=DocumentList)
async def list_documents(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> DocumentList:
    result = await db.execute(
        select(Document)
        .where(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
    )
    return DocumentList(documents=list(result.scalars().all()))


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Document:
    document = await db.get(Document, document_id)
    if not document or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    document = await db.get(Document, document_id)
    if not document or document.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    vector_store = get_vector_store()
    await vector_store.delete_document(str(document.id))
    Path(document.storage_path).unlink(missing_ok=True)
    await db.delete(document)
    await db.commit()

