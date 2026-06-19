import json
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.database.session import AsyncSessionLocal, get_session
from app.models.chat import ChatSession, Message, MessageRole
from app.models.document import Document, DocumentStatus
from app.models.user import User
from app.rag.prompt import build_rag_prompt, format_sources
from app.schemas.chat import (
    ChatAnswer,
    ChatSessionCreate,
    ChatSessionList,
    ChatSessionRead,
    ChatSessionUpdate,
    MessageCreate,
    MessageList,
    MessageRead,
)
from app.services.dependencies import get_rag_pipeline

router = APIRouter()


@router.post("/sessions", response_model=ChatSessionRead, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: ChatSessionCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    document_ids = await _resolve_document_ids(db, user.id, payload.document_ids)
    session = ChatSession(
        user_id=user.id,
        title=payload.title or "New chat",
        selected_document_ids=document_ids,
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@router.get("/sessions", response_model=ChatSessionList)
async def list_sessions(
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatSessionList:
    result = await db.execute(
        select(ChatSession)
        .where(ChatSession.user_id == user.id)
        .order_by(ChatSession.updated_at.desc())
    )
    return ChatSessionList(sessions=list(result.scalars().all()))


@router.patch("/sessions/{session_id}", response_model=ChatSessionRead)
async def update_session(
    session_id: uuid.UUID,
    payload: ChatSessionUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatSession:
    session = await _get_session_or_404(db, session_id, user.id)
    if payload.title is not None:
        session.title = payload.title
    if payload.document_ids is not None:
        session.selected_document_ids = await _resolve_document_ids(db, user.id, payload.document_ids)
    await db.commit()
    await db.refresh(session)
    return session


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> None:
    session = await _get_session_or_404(db, session_id, user.id)
    await db.delete(session)
    await db.commit()


@router.get("/sessions/{session_id}/messages", response_model=MessageList)
async def list_messages(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> MessageList:
    await _get_session_or_404(db, session_id, user.id)
    result = await db.execute(
        select(Message)
        .where(Message.session_id == session_id)
        .order_by(Message.created_at.asc())
    )
    return MessageList(messages=list(result.scalars().all()))


@router.post("/sessions/{session_id}/messages", response_model=ChatAnswer)
async def create_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> ChatAnswer:
    session = await _get_session_or_404(db, session_id, user.id)
    document_ids = await _document_scope(db, user.id, session, payload.document_ids)

    user_message = Message(session_id=session.id, role=MessageRole.user, content=payload.question)
    db.add(user_message)
    await db.commit()

    pipeline = get_rag_pipeline()
    answer, sources = await pipeline.answer(payload.question, document_ids=document_ids)
    assistant_message = Message(
        session_id=session.id,
        role=MessageRole.assistant,
        content=answer,
        citations=sources,
    )
    if session.title == "New chat":
        session.title = _title_from_question(payload.question)
    db.add(assistant_message)
    await db.commit()
    await db.refresh(assistant_message)
    return ChatAnswer(message=MessageRead.model_validate(assistant_message), sources=sources)


@router.post("/sessions/{session_id}/messages/stream")
async def stream_message(
    session_id: uuid.UUID,
    payload: MessageCreate,
    db: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    session = await _get_session_or_404(db, session_id, user.id)
    document_ids = await _document_scope(db, user.id, session, payload.document_ids)

    user_message = Message(session_id=session.id, role=MessageRole.user, content=payload.question)
    db.add(user_message)
    if session.title == "New chat":
        session.title = _title_from_question(payload.question)
    await db.commit()

    async def event_generator():
        pipeline = get_rag_pipeline()
        answer_parts: list[str] = []
        sources: list[dict[str, str | int]] = []
        try:
            chunks = await pipeline.retrieve_context(payload.question, document_ids=document_ids)
            sources = [chunk.citation() for chunk in chunks]
            yield _sse("sources", {"sources": sources})

            if chunks:
                prompt = build_rag_prompt(payload.question, chunks)
                async for token in pipeline.llm.stream(prompt):
                    answer_parts.append(token)
                    yield _sse("token", {"token": token})
                footer = f"\n\n{format_sources(sources)}"
                answer_parts.append(footer)
                yield _sse("token", {"token": footer})
            else:
                token = (
                    "The uploaded documents do not contain enough information to answer that question.\n\n"
                    f"{format_sources(sources)}"
                )
                answer_parts.append(token)
                yield _sse("token", {"token": token})

            content = "".join(answer_parts)
            async with AsyncSessionLocal() as write_session:
                assistant_message = Message(
                    session_id=session_id,
                    role=MessageRole.assistant,
                    content=content,
                    citations=sources,
                )
                write_session.add(assistant_message)
                await write_session.commit()
                await write_session.refresh(assistant_message)
                payload_done = {
                    "message": MessageRead.model_validate(assistant_message).model_dump(mode="json"),
                    "sources": sources,
                }
            yield _sse("done", payload_done)
        except Exception as exc:
            yield _sse("error", {"detail": str(exc)})

    return StreamingResponse(event_generator(), media_type="text/event-stream")


async def _get_session_or_404(db: AsyncSession, session_id: uuid.UUID, user_id: uuid.UUID) -> ChatSession:
    session = await db.get(ChatSession, session_id)
    if not session or session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat session not found.")
    return session


async def _resolve_document_ids(
    db: AsyncSession,
    user_id: uuid.UUID,
    requested: list[uuid.UUID] | None,
) -> list[str]:
    if not requested:
        return []
    result = await db.execute(
        select(Document.id)
        .where(Document.user_id == user_id)
        .where(Document.status == DocumentStatus.processed)
        .where(Document.id.in_(requested))
    )
    ids = [str(item) for item in result.scalars().all()]
    if len(ids) != len(set(requested)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="One or more selected documents are unavailable or still processing.",
        )
    return ids


async def _document_scope(
    db: AsyncSession,
    user_id: uuid.UUID,
    session: ChatSession,
    requested: list[uuid.UUID] | None,
) -> list[str]:
    if requested:
        return await _resolve_document_ids(db, user_id, requested)
    if session.selected_document_ids:
        return await _resolve_document_ids(db, user_id, [uuid.UUID(item) for item in session.selected_document_ids])

    result = await db.execute(
        select(Document.id)
        .where(Document.user_id == user_id)
        .where(Document.status == DocumentStatus.processed)
    )
    return [str(item) for item in result.scalars().all()]


def _title_from_question(question: str) -> str:
    normalized = " ".join(question.split())
    return normalized[:80] or "New chat"


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

