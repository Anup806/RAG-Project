from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_session
from app.schemas.health import HealthRead
from app.services.dependencies import get_vector_store

router = APIRouter()


@router.get("", response_model=HealthRead)
async def health(db: Annotated[AsyncSession, Depends(get_session)]) -> HealthRead:
    database_status = "ok"
    vector_status = "ok"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        database_status = "error"

    vector_store = get_vector_store()
    if not await vector_store.heartbeat():
        vector_status = "error"

    status = "ok" if database_status == "ok" and vector_status == "ok" else "degraded"
    return HealthRead(status=status, database=database_status, vector_store=vector_status)

