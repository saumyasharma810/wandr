from tests.conftest import register, auth_headers

TIP = {"country": "Japan", "city": "Tokyo", "content": "Amazing ramen in Shibuya!", "is_public": True}


async def _setup(client, username="alice", email="alice@test.com") -> dict:
    await register(client, username=username, email=email)
    return await auth_headers(client, username=username)


async def _create_tip(client, headers=None, payload=None) -> dict:
    r = await client.post("/tips", json=payload or TIP, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ── create ─────────────────────────────────────────────────────────────────────

async def test_add_tip_authenticated(client):
    headers = await _setup(client)
    r = await client.post("/tips", json=TIP, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["country"] == "Japan"
    assert data["city"] == "Tokyo"
    assert data["content"] == "Amazing ramen in Shibuya!"
    assert data["username"] == "alice"
    assert "id" in data
    assert "helpful_count" in data


async def test_add_tip_anonymous_flag(client):
    headers = await _setup(client)
    r = await client.post("/tips", json={**TIP, "is_anonymous": True}, headers=headers)
    assert r.status_code == 200
    assert r.json()["username"] is None


async def test_add_tip_no_auth(client):
    r = await client.post("/tips", json=TIP)
    assert r.status_code == 200
    data = r.json()
    assert data["username"] is None


# ── list ───────────────────────────────────────────────────────────────────────

async def test_get_tips_no_filter(client):
    headers = await _setup(client)
    await _create_tip(client, headers)
    r = await client.get("/tips")
    assert r.status_code == 200
    assert len(r.json()) == 1


async def test_get_tips_filter_by_city(client):
    headers = await _setup(client)
    await _create_tip(client, headers, {**TIP, "city": "Tokyo"})
    await _create_tip(client, headers, {**TIP, "city": "Osaka"})
    r = await client.get("/tips?city=Tokyo")
    assert r.status_code == 200
    tips = r.json()
    assert len(tips) == 1
    assert tips[0]["city"] == "Tokyo"


async def test_get_tips_filter_by_country(client):
    headers = await _setup(client)
    await _create_tip(client, headers, {**TIP, "country": "Japan"})
    await _create_tip(client, headers, {**TIP, "country": "France", "city": "Paris"})
    r = await client.get("/tips?country=Japan")
    assert r.status_code == 200
    assert all(t["country"] == "Japan" for t in r.json())


async def test_get_tips_excludes_private(client):
    headers = await _setup(client)
    await _create_tip(client, headers, {**TIP, "is_public": False})
    r = await client.get("/tips")
    assert r.status_code == 200
    assert r.json() == []


async def test_get_tips_includes_username(client):
    headers = await _setup(client)
    await _create_tip(client, headers)
    tips = (await client.get("/tips")).json()
    assert tips[0]["username"] == "alice"


async def test_get_tips_anonymous_username_is_none(client):
    await _create_tip(client)
    tips = (await client.get("/tips")).json()
    assert tips[0]["username"] is None


# ── update ─────────────────────────────────────────────────────────────────────

async def test_update_tip_success(client):
    headers = await _setup(client)
    tip = await _create_tip(client, headers)
    r = await client.patch(f"/tips/{tip['id']}", json={"city": "Osaka"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "Osaka"
    assert data["country"] == "Japan"  # unchanged


async def test_update_tip_not_found(client):
    headers = await _setup(client)
    r = await client.patch("/tips/99999", json={"city": "X"}, headers=headers)
    assert r.status_code == 404


async def test_update_tip_another_users_tip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    tip = await _create_tip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.patch(f"/tips/{tip['id']}", json={"city": "X"}, headers=bob_headers)
    assert r.status_code == 403


async def test_update_tip_no_auth(client):
    r = await client.patch("/tips/1", json={"city": "X"})
    assert r.status_code == 401


async def test_update_anonymous_tip_forbidden(client):
    tip = await _create_tip(client)  # no auth → anonymous
    headers = await _setup(client)
    r = await client.patch(f"/tips/{tip['id']}", json={"city": "X"}, headers=headers)
    assert r.status_code == 403


# ── upvote ─────────────────────────────────────────────────────────────────────

async def test_upvote_tip_success(client):
    headers = await _setup(client)
    tip = await _create_tip(client, headers)
    r = await client.patch(f"/tips/{tip['id']}/helpful", headers=headers)
    assert r.status_code == 200
    assert r.json()["helpful_count"] == 1


async def test_upvote_increments(client):
    headers = await _setup(client)
    tip = await _create_tip(client, headers)
    await client.patch(f"/tips/{tip['id']}/helpful", headers=headers)
    r = await client.patch(f"/tips/{tip['id']}/helpful", headers=headers)
    assert r.json()["helpful_count"] == 2


async def test_upvote_tip_not_found(client):
    headers = await _setup(client)
    r = await client.patch("/tips/99999/helpful", headers=headers)
    assert r.status_code == 404


async def test_upvote_tip_no_auth(client):
    r = await client.patch("/tips/1/helpful")
    assert r.status_code == 401


# ── delete ─────────────────────────────────────────────────────────────────────

async def test_delete_tip_success(client):
    headers = await _setup(client)
    tip = await _create_tip(client, headers)
    r = await client.delete(f"/tips/{tip['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


async def test_delete_tip_not_found(client):
    headers = await _setup(client)
    r = await client.delete("/tips/99999", headers=headers)
    assert r.status_code == 404


async def test_delete_tip_another_users_tip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    tip = await _create_tip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.delete(f"/tips/{tip['id']}", headers=bob_headers)
    assert r.status_code == 403


async def test_delete_tip_no_auth(client):
    r = await client.delete("/tips/1")
    assert r.status_code == 401


async def test_delete_anonymous_tip_forbidden(client):
    tip = await _create_tip(client)  # no auth → anonymous
    headers = await _setup(client)
    r = await client.delete(f"/tips/{tip['id']}", headers=headers)
    assert r.status_code == 403
