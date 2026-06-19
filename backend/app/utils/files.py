import re
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

PDF_MIME_TYPES = {"application/pdf", "application/x-pdf"}


def sanitize_filename(filename: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._")
    return safe or "document.pdf"


def make_storage_path(filename: str) -> Path:
    safe_name = sanitize_filename(filename)
    return settings.upload_path / f"{uuid.uuid4()}_{safe_name}"


def validate_upload(file: UploadFile) -> None:
    content_type = file.content_type or ""
    filename = file.filename or ""
    if content_type not in PDF_MIME_TYPES and not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"{filename or 'Uploaded file'} is not a PDF.",
        )


async def save_upload(file: UploadFile, destination: Path) -> int:
    size = 0
    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > settings.max_file_size_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"{file.filename} exceeds {settings.MAX_FILE_SIZE_MB} MB.",
                )
            output.write(chunk)
    return size

