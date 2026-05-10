import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool
from app.main import app
from app.database import get_session


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def override():
        yield session

    app.dependency_overrides[get_session] = override
    with TestClient(app) as c:
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


# ── helpers ────────────────────────────────────────────────────────────────────

def register(client: TestClient, username="alice", email="alice@test.com", password="secret123"):
    return client.post("/auth/register", json={
        "username": username, "email": email, "password": password,
    })


def login(client: TestClient, username="alice", password="secret123"):
    return client.post("/auth/login", data={"username": username, "password": password})


def get_tokens(client: TestClient, username="alice", password="secret123") -> dict:
    r = login(client, username, password)
    assert r.status_code == 200, r.text
    return r.json()


def auth_headers(client: TestClient, username="alice", password="secret123") -> dict:
    return {"Authorization": f"Bearer {get_tokens(client, username, password)['access_token']}"}
