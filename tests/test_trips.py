from tests.conftest import register, auth_headers

TRIP = {"country": "Japan", "city": "Tokyo", "duration_days": 7}


async def _setup(client, username="alice", email="alice@test.com") -> dict:
    await register(client, username=username, email=email)
    return await auth_headers(client, username=username)


async def _create_trip(client, headers, payload=None) -> dict:
    r = await client.post("/trips", json=payload or TRIP, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ── create ─────────────────────────────────────────────────────────────────────

async def test_add_trip_success(client):
    headers = await _setup(client)
    r = await client.post("/trips", json=TRIP, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["country"] == "Japan"
    assert data["city"] == "Tokyo"
    assert data["duration_days"] == 7
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


async def test_add_trip_no_auth(client):
    r = await client.post("/trips", json=TRIP)
    assert r.status_code == 401


# ── list ───────────────────────────────────────────────────────────────────────

async def test_get_trips_returns_own_only(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    await _create_trip(client, alice_headers, {"country": "Japan"})

    bob_headers = await _setup(client, "bob", "bob@test.com")
    await _create_trip(client, bob_headers, {"country": "France"})

    r = await client.get("/trips", headers=alice_headers)
    assert r.status_code == 200
    trips = r.json()
    assert len(trips) == 1
    assert trips[0]["country"] == "Japan"


async def test_get_trips_empty(client):
    headers = await _setup(client)
    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_get_trips_no_auth(client):
    r = await client.get("/trips")
    assert r.status_code == 401


# ── get by id ──────────────────────────────────────────────────────────────────

async def test_get_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["country"] == "Japan"


async def test_get_trip_not_found(client):
    headers = await _setup(client)
    r = await client.get("/trips/99999", headers=headers)
    assert r.status_code == 404


async def test_get_trip_another_users_trip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.get(f"/trips/{trip['id']}", headers=bob_headers)
    assert r.status_code == 403


async def test_get_trip_no_auth(client):
    r = await client.get("/trips/1")
    assert r.status_code == 401


# ── update ─────────────────────────────────────────────────────────────────────

async def test_update_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.patch(f"/trips/{trip['id']}", json={"country": "South Korea"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["country"] == "South Korea"


async def test_update_trip_partial(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.patch(f"/trips/{trip['id']}", json={"city": "Osaka"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "Osaka"
    assert data["country"] == "Japan"  # unchanged


async def test_update_trip_not_found(client):
    headers = await _setup(client)
    r = await client.patch("/trips/99999", json={"country": "X"}, headers=headers)
    assert r.status_code == 404


async def test_update_trip_another_users_trip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.patch(f"/trips/{trip['id']}", json={"country": "X"}, headers=bob_headers)
    assert r.status_code == 403


async def test_update_trip_no_auth(client):
    r = await client.patch("/trips/1", json={"country": "X"})
    assert r.status_code == 401


# ── delete ─────────────────────────────────────────────────────────────────────

async def test_delete_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.delete(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    # confirm gone via list (avoids calling rate-limited GET /trips/{id} twice)
    remaining = (await client.get("/trips", headers=headers)).json()
    assert all(t["id"] != trip["id"] for t in remaining)


async def test_delete_trip_not_found(client):
    headers = await _setup(client)
    r = await client.delete("/trips/99999", headers=headers)
    assert r.status_code == 404


async def test_delete_trip_another_users_trip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.delete(f"/trips/{trip['id']}", headers=bob_headers)
    assert r.status_code == 403


async def test_delete_trip_no_auth(client):
    r = await client.delete("/trips/1")
    assert r.status_code == 401
