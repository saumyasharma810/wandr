from tests.conftest import register, login, get_tokens, auth_headers


# ── register ───────────────────────────────────────────────────────────────────

async def test_register_success(client):
    r = await register(client)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@test.com"
    assert "password" not in data
    assert "hashed_password" not in data


async def test_register_duplicate_username(client):
    await register(client)
    r = await client.post("/auth/register", json={
        "username": "alice", "email": "other@test.com", "password": "secret123",
    })
    assert r.status_code == 409
    assert "Username" in r.json()["detail"]


async def test_register_duplicate_email(client):
    await register(client)
    r = await client.post("/auth/register", json={
        "username": "alice2", "email": "alice@test.com", "password": "secret123",
    })
    assert r.status_code == 409
    assert "Email" in r.json()["detail"]


# ── login ──────────────────────────────────────────────────────────────────────

async def test_login_success(client):
    await register(client)
    r = await login(client)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await register(client)
    r = await client.post("/auth/login", data={"username": "alice", "password": "wrong"})
    assert r.status_code == 401


async def test_login_wrong_username(client):
    r = await client.post("/auth/login", data={"username": "nobody", "password": "secret123"})
    assert r.status_code == 401


# ── protected route ────────────────────────────────────────────────────────────

async def test_get_me_success(client):
    await register(client)
    r = await client.get("/users/me", headers=await auth_headers(client))
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


async def test_get_me_no_token(client):
    r = await client.get("/users/me")
    assert r.status_code == 401


async def test_get_me_invalid_token(client):
    r = await client.get("/users/me", headers={"Authorization": "Bearer totallyinvalid"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"


# ── refresh ────────────────────────────────────────────────────────────────────

async def test_refresh_success(client):
    await register(client)
    tokens = await get_tokens(client)
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # refresh token must always rotate (jti guarantees uniqueness)
    assert data["refresh_token"] != tokens["refresh_token"]
    # new access token must be usable
    me = await client.get("/users/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200


async def test_refresh_invalid_token(client):
    r = await client.post("/auth/refresh", json={"refresh_token": "notavalidtoken"})
    assert r.status_code == 401


async def test_refresh_revoked_token_rejected(client):
    await register(client)
    tokens = await get_tokens(client)
    await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    # reuse the same (now rotated/revoked) token
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid refresh token"


# ── logout ─────────────────────────────────────────────────────────────────────

async def test_logout_success(client):
    await register(client)
    tokens = await get_tokens(client)
    r = await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_logout_then_refresh_fails(client):
    await register(client)
    tokens = await get_tokens(client)
    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    r = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


async def test_logout_invalid_token(client):
    r = await client.post("/auth/logout", json={"refresh_token": "notavalidtoken"})
    assert r.status_code == 401
