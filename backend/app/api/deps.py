import uuid
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.database.session import get_session
from app.models.user import User


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_session)],
    x_user_id: Annotated[str | None, Header(alias="X-User-Id")] = None,
) -> User:
    if x_user_id:
        try:
            user_id = uuid.UUID(x_user_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid X-User-Id header.") from exc
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    result = await db.execute(select(User).where(User.email == settings.DEFAULT_USER_EMAIL))
    user = result.scalar_one_or_none()
    if user:
        return user

    user = User(email=settings.DEFAULT_USER_EMAIL, display_name=settings.DEFAULT_USER_NAME)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

