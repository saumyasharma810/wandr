import json
import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from sqlmodel import select

from app.models import ChatMessage, User
from tests.conftest import register, auth_headers


# ── mock Anthropic streaming ──────────────────────────────────────────────────

class MockStream:
    def __init__(self, texts=("Hi there",), full_text="Hi there"):
        self._texts = texts
        self._full_text = full_text

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    @property
    def text_stream(self):
        async def _gen():
            for t in self._texts:
                yield t
        return _gen()

    async def get_final_message(self):
        msg = MagicMock()
        msg.content = [MagicMock(text=self._full_text)]
        msg.usage.output_tokens = 5
        return msg


@pytest.fixture(autouse=True)
def mock_claude():
    with patch("app.chat.client") as mock_client:
        mock_client.messages.stream.return_value = MockStream()
        yield mock_client


# ── helpers ───────────────────────────────────────────────────────────────────

async def _setup(client, username="alice", email="alice@test.com") -> dict:
    await register(client, username=username, email=email)
    return await auth_headers(client, username=username)


async def _send(client, headers, message="What to do in Tokyo?", conversation_id=None):
    payload = {"message": message}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    r = await client.post("/chat", json=payload, headers=headers)
    assert r.status_code == 200, r.text
    return r


def _parse_conversation_id(response_text: str) -> int:
    for line in response_text.splitlines():
        if line.startswith("data: {"):
            return json.loads(line[6:])["conversation_id"]
    raise AssertionError("No conversation_id event found in SSE response")


# ── POST /chat ────────────────────────────────────────────────────────────────

async def test_chat_new_conversation(client):
    headers = await _setup(client)
    r = await _send(client, headers)
    assert "conversation_id" in r.text
    assert "[DONE]" in r.text


async def test_chat_assigns_sequential_conversation_ids(client):
    headers = await _setup(client)
    r1 = await _send(client, headers, "First question")
    r2 = await _send(client, headers, "Second question")
    assert _parse_conversation_id(r2.text) == _parse_conversation_id(r1.text) + 1


async def test_chat_continue_conversation(client):
    headers = await _setup(client)
    r1 = await _send(client, headers)
    conv_id = _parse_conversation_id(r1.text)

    r2 = await _send(client, headers, "Follow-up", conversation_id=conv_id)
    assert _parse_conversation_id(r2.text) == conv_id


async def test_chat_saves_both_messages_to_db(client, session):
    headers = await _setup(client)
    r = await _send(client, headers, "Tell me about Kyoto")
    conv_id = _parse_conversation_id(r.text)

    result = await session.execute(
        select(ChatMessage).where(ChatMessage.conversation_id == conv_id)
    )
    messages = result.scalars().all()
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[0].content == "Tell me about Kyoto"
    assert messages[1].role == "assistant"


async def test_chat_no_auth(client):
    r = await client.post("/chat", json={"message": "hello"})
    assert r.status_code == 401


async def test_chat_invalid_conversation_id(client):
    headers = await _setup(client)
    r = await client.post("/chat", json={"message": "hello", "conversation_id": 0}, headers=headers)
    assert r.status_code == 422  # pydantic rejects non-positive id


# ── rate limit ────────────────────────────────────────────────────────────────

async def test_chat_rate_limit(client, session):
    headers = await _setup(client)

    result = await session.execute(select(User).where(User.username == "alice"))
    user = result.scalars().first()

    for _ in range(20):
        session.add(ChatMessage(
            user_id=user.id,
            conversation_id=1,
            role="user",
            content="x",
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        ))
    await session.commit()

    r = await client.post("/chat", json={"message": "one more"}, headers=headers)
    assert r.status_code == 429


# ── GET /chat/history ─────────────────────────────────────────────────────────

async def test_get_history_empty(client):
    headers = await _setup(client)
    r = await client.get("/chat/history", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_get_history_lists_all_conversations(client):
    headers = await _setup(client)
    await _send(client, headers, "First convo")
    await _send(client, headers, "Second convo")

    r = await client.get("/chat/history", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert len(data) == 2
    assert all("conversation_id" in c and "preview" in c and "created_at" in c for c in data)


async def test_get_history_preview_truncated_at_80(client):
    headers = await _setup(client)
    long_msg = "A" * 100
    await _send(client, headers, long_msg)

    r = await client.get("/chat/history", headers=headers)
    assert len(r.json()[0]["preview"]) <= 80


async def test_get_history_no_auth(client):
    r = await client.get("/chat/history")
    assert r.status_code == 401


# ── GET /chat/{conversation_id} ───────────────────────────────────────────────

async def test_get_conversation_returns_messages(client):
    headers = await _setup(client)
    r = await _send(client, headers)
    conv_id = _parse_conversation_id(r.text)

    r2 = await client.get(f"/chat/{conv_id}", headers=headers)
    assert r2.status_code == 200
    messages = r2.json()
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"


async def test_get_conversation_not_found(client):
    headers = await _setup(client)
    r = await client.get("/chat/99999", headers=headers)
    assert r.status_code == 404


async def test_get_conversation_another_users(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    r = await _send(client, alice_headers)
    conv_id = _parse_conversation_id(r.text)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r2 = await client.get(f"/chat/{conv_id}", headers=bob_headers)
    assert r2.status_code == 404  # 404, not 403 — don't reveal existence


async def test_get_conversation_no_auth(client):
    r = await client.get("/chat/1")
    assert r.status_code == 401


# ── DELETE /chat/{conversation_id} ────────────────────────────────────────────

async def test_delete_conversation_success(client):
    headers = await _setup(client)
    r = await _send(client, headers)
    conv_id = _parse_conversation_id(r.text)

    r2 = await client.delete(f"/chat/{conv_id}", headers=headers)
    assert r2.status_code == 200
    assert r2.json() == {"status": "deleted"}

    r3 = await client.get(f"/chat/{conv_id}", headers=headers)
    assert r3.status_code == 404


async def test_delete_conversation_not_found(client):
    headers = await _setup(client)
    r = await client.delete("/chat/99999", headers=headers)
    assert r.status_code == 404


async def test_delete_conversation_another_users(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    r = await _send(client, alice_headers)
    conv_id = _parse_conversation_id(r.text)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r2 = await client.delete(f"/chat/{conv_id}", headers=bob_headers)
    assert r2.status_code == 404


async def test_delete_conversation_no_auth(client):
    r = await client.delete("/chat/1")
    assert r.status_code == 401
