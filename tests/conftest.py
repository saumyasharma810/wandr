import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_session


@pytest_asyncio.fixture(name="session")
async def session_fixture():
    engine = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool)
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session


@pytest_asyncio.fixture(name="client")
async def client_fixture(session: AsyncSession):
    async def override():
        yield session

    app.dependency_overrides[get_session] = override
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def reset_rate_limits():
    yield
    import app.main as main_module
    import app.auth as auth_module
    for lim in [main_module.limiter, auth_module.limiter]:
        try:
            lim._storage.reset()
        except Exception:
            pass


async def register(client, username="alice", email="alice@test.com", password="secret123"):
    return await client.post("/auth/register", json={
        "username": username, "email": email, "password": password,
    })

async def login(client, username="alice", password="secret123"):
    return await client.post("/auth/login", data={"username": username, "password": password})

async def get_tokens(client, username="alice", password="secret123") -> dict:
    r = await login(client, username, password)
    assert r.status_code == 200, r.text
    return r.json()

async def auth_headers(client, username="alice", password="secret123") -> dict:
    tokens = await get_tokens(client, username, password)
    return {"Authorization": f"Bearer {tokens['access_token']}"}
