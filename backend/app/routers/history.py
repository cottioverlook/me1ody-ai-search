import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.db import Conversation, Message, create_engine, create_sessionmaker
from app.models.schemas import ConversationListItem, ConversationResponse, FavoriteRequest, HistoryMessage, Source
from app.utils.user_context import get_user_id

router = APIRouter(prefix="/api", tags=["history"])

engine = create_engine(settings.database_url)
session_factory = create_sessionmaker(engine)


async def get_db():
    async with session_factory() as session:
        yield session


@router.get("/history", response_model=list[ConversationListItem])
async def list_conversations(request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(request)
    result = await db.execute(
        select(Conversation)
        .where(Conversation.user_id == user_id)
        .order_by(Conversation.is_favorite.desc(), Conversation.created_at.desc())
        .limit(50)
    )
    return [
        ConversationListItem(
            id=conv.id,
            share_id=conv.share_id,
            title=conv.title,
            created_at=conv.created_at.isoformat(),
            is_favorite=conv.is_favorite,
        )
        for conv in result.scalars()
    ]


@router.get("/history/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(conversation_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(request)
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return await conversation_response(conv, db)


@router.get("/share/{share_id}", response_model=ConversationResponse)
async def get_shared_conversation(share_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Conversation).where(Conversation.share_id == share_id))
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Shared conversation not found")
    return await conversation_response(conv, db)


@router.patch("/history/{conversation_id}/favorite", response_model=ConversationListItem)
async def update_favorite(
    conversation_id: str,
    payload: FavoriteRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    user_id = get_user_id(request)
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    conv.is_favorite = payload.is_favorite
    await db.commit()
    return ConversationListItem(
        id=conv.id,
        share_id=conv.share_id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        is_favorite=conv.is_favorite,
    )


@router.delete("/history/{conversation_id}")
async def delete_conversation(conversation_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    user_id = get_user_id(request)
    conv = await db.get(Conversation, conversation_id)
    if not conv or conv.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")

    await db.delete(conv)
    await db.commit()
    return {"status": "deleted"}


async def conversation_response(conv: Conversation, db: AsyncSession) -> ConversationResponse:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .order_by(Message.created_at)
    )

    messages = []
    for msg in result.scalars():
        sources = None
        if msg.sources:
            try:
                sources = [Source(**s) for s in json.loads(msg.sources)]
            except (json.JSONDecodeError, TypeError):
                pass
        messages.append(
            HistoryMessage(role=msg.role, content=msg.content, sources=sources)
        )

    return ConversationResponse(
        id=conv.id,
        share_id=conv.share_id,
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        is_favorite=conv.is_favorite,
        messages=messages,
    )
