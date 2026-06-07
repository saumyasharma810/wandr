from typing import Annotated
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sqlmodel import select, delete, func
from app.models import ChatMessage, ChatRequest, User
from app.database import AsyncSession, get_session
from app.auth import get_current_active_user
from app.config import settings
from anthropic import AsyncAnthropic
from datetime import datetime, timezone
from loguru import logger

router = APIRouter()
client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

# ── helper: get conversation history ──────────────────

async def get_history(
    user_id: int,
    conversation_id: int,
    session: SessionDep,
    limit: int = 10
) -> list[dict]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == user_id)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    messages = result.scalars().all()
    # reverse to get chronological order
    messages = list(reversed(messages))
    return [{"role": m.role, "content": m.content} for m in messages]

# ── helper: check daily rate limit ────────────────────

async def check_daily_limit(user_id: int, session: SessionDep):
    today = datetime.now(timezone.utc).date()
    result = await session.execute(
        select(func.count(ChatMessage.id))
        .where(ChatMessage.user_id == user_id)
        .where(ChatMessage.role == "user")
        .where(ChatMessage.created_at >= datetime(today.year, today.month, today.day))
    )
    count = result.scalar()

    if count >= 20:
        logger.warning(f"Rate limit hit: user_id={user_id} exceeded 20 msgs/day")
        raise HTTPException(
            status_code=429,
            detail="Daily limit of 20 messages reached"
        )
    

async def get_next_conversation_id(user_id: int, session: AsyncSession) -> int:
    result = await session.execute(
        select(func.max(ChatMessage.conversation_id))
        .where(ChatMessage.user_id == user_id)
    )
    max_id = result.scalar()
    return (max_id or 0) + 1

# ── 1. POST /chat — send message, get streaming response

@router.post("")
async def chat(
    request: ChatRequest,
    current_user: CurrentUser,
    session: SessionDep,
):
     # if no conversation_id provided, start a new one
    if request.conversation_id is None:
        conversation_id = await get_next_conversation_id(current_user.id, session)
    else:
        conversation_id = request.conversation_id

    # rate limit check
    await check_daily_limit(current_user.id, session)

    # save user message
    user_msg = ChatMessage(
        user_id=current_user.id,
        conversation_id=conversation_id,
        role="user",
        content=request.message,
    )
    session.add(user_msg)
    await session.commit()

    # get conversation history (last 10 messages)
    history = await get_history(
        current_user.id, conversation_id, session, limit=10
    )

    # system prompt (simple for now, will be replaced in week 6)
    system_prompt = "You are a helpful travel advisor."

    # messages for Claude = history + current message
    messages = history  # user message already in history after commit

    async def generate():

        # first event tells client which conversation this is
        yield f"data: {{\"conversation_id\": {conversation_id}}}\n\n"

        try:
            logger.info(f"Claude stream started: user_id={current_user.id} conv={conversation_id}")
            async with client.messages.stream(
                system=system_prompt,
                max_tokens=100,
                messages=messages,
                model="claude-haiku-4-5-20251001",
            ) as stream:
                async for text in stream.text_stream:
                    yield f"data: {text}\n\n"

                # get full response after stream ends
                final = await stream.get_final_message()
                full_text = final.content[0].text
                logger.info(f"Claude stream done: user_id={current_user.id} conv={conversation_id} tokens={final.usage.output_tokens}")

                # save assistant message
                assistant_msg = ChatMessage(
                    user_id=current_user.id,
                    conversation_id=conversation_id,
                    role="assistant",
                    content=full_text,
                )
                session.add(assistant_msg)
                await session.commit()
        except Exception as e:
            logger.error(f"Stream error: user_id={current_user.id} conv={conversation_id} {e}")
            yield "data: [ERROR]\n\n"
            return

        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")

# ── 2. GET /chat/history — all conversations list ─────

@router.get("/history")
async def get_conversations(
    current_user: CurrentUser,
    session: SessionDep,
):
    result = await session.execute(
        select(ChatMessage.conversation_id)
        .where(ChatMessage.user_id == current_user.id)
        .distinct()
    )
    conversation_ids = result.scalars().all()

    conversations = []
    for conv_id in conversation_ids:
        # get first message of each conversation as preview
        first_msg = await session.execute(
            select(ChatMessage)
            .where(ChatMessage.user_id == current_user.id)
            .where(ChatMessage.conversation_id == conv_id)
            .where(ChatMessage.role == "user")
            .order_by(ChatMessage.created_at.asc())
            .limit(1)
        )
        first = first_msg.scalars().first()
        if first:
            conversations.append({
                "conversation_id": conv_id,
                "preview": first.content[:80],
                "created_at": first.created_at,
            })

    return conversations

# ── 3. GET /chat/{conversation_id} — messages in a convo

@router.get("/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: CurrentUser,
    session: SessionDep,
):
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where(ChatMessage.conversation_id == conversation_id)
        .order_by(ChatMessage.created_at.asc())
    )
    messages = result.scalars().all()

    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return messages

# ── 4. DELETE /chat/{conversation_id} — delete a convo ─

@router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    current_user: CurrentUser,
    session: SessionDep,
):
    # verify it belongs to this user first
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where(ChatMessage.conversation_id == conversation_id)
        .limit(1)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Conversation not found")

    await session.execute(
        delete(ChatMessage)
        .where(ChatMessage.user_id == current_user.id)
        .where(ChatMessage.conversation_id == conversation_id)
    )
    await session.commit()
    return {"status": "deleted"}