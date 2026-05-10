from tests.conftest import register, login, get_tokens, auth_headers


# ── register ───────────────────────────────────────────────────────────────────

def test_register_success(client):
    r = register(client)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] == "alice"
    assert data["email"] == "alice@test.com"
    assert "password" not in data
    assert "hashed_password" not in data


def test_register_duplicate_username(client):
    register(client)
    r = client.post("/auth/register", json={
        "username": "alice", "email": "other@test.com", "password": "secret123",
    })
    assert r.status_code == 409
    assert "Username" in r.json()["detail"]


def test_register_duplicate_email(client):
    register(client)
    r = client.post("/auth/register", json={
        "username": "alice2", "email": "alice@test.com", "password": "secret123",
    })
    assert r.status_code == 409
    assert "Email" in r.json()["detail"]


# ── login ──────────────────────────────────────────────────────────────────────

def test_login_success(client):
    register(client)
    r = login(client)
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    register(client)
    r = client.post("/auth/login", data={"username": "alice", "password": "wrong"})
    assert r.status_code == 401


def test_login_wrong_username(client):
    r = client.post("/auth/login", data={"username": "nobody", "password": "secret123"})
    assert r.status_code == 401


# ── protected route ────────────────────────────────────────────────────────────

def test_get_me_success(client):
    register(client)
    r = client.get("/users/me", headers=auth_headers(client))
    assert r.status_code == 200
    assert r.json()["username"] == "alice"


def test_get_me_no_token(client):
    r = client.get("/users/me")
    assert r.status_code == 401


def test_get_me_invalid_token(client):
    r = client.get("/users/me", headers={"Authorization": "Bearer totallyinvalid"})
    assert r.status_code == 401
    assert r.json()["detail"] == "Could not validate credentials"


# ── refresh ────────────────────────────────────────────────────────────────────

def test_refresh_success(client):
    register(client)
    tokens = get_tokens(client)
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert "refresh_token" in data
    # refresh token must always rotate (jti guarantees uniqueness)
    assert data["refresh_token"] != tokens["refresh_token"]
    # new access token must be usable
    me = client.get("/users/me", headers={"Authorization": f"Bearer {data['access_token']}"})
    assert me.status_code == 200


def test_refresh_invalid_token(client):
    r = client.post("/auth/refresh", json={"refresh_token": "notavalidtoken"})
    assert r.status_code == 401


def test_refresh_revoked_token_rejected(client):
    register(client)
    tokens = get_tokens(client)
    client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    # reuse the same (now rotated/revoked) token
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid refresh token"


# ── logout ─────────────────────────────────────────────────────────────────────

def test_logout_success(client):
    register(client)
    tokens = get_tokens(client)
    r = client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_logout_then_refresh_fails(client):
    register(client)
    tokens = get_tokens(client)
    client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})
    r = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r.status_code == 401


def test_logout_invalid_token(client):
    r = client.post("/auth/logout", json={"refresh_token": "notavalidtoken"})
    assert r.status_code == 401
