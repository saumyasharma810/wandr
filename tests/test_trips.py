from tests.conftest import register, auth_headers

TRIP = {"country": "Japan", "city": "Tokyo", "duration_days": 7}


def _setup(client, username="alice", email="alice@test.com") -> dict:
    register(client, username=username, email=email)
    return auth_headers(client, username=username)


def _create_trip(client, headers, payload=None) -> dict:
    r = client.post("/trips", json=payload or TRIP, headers=headers)
    assert r.status_code == 200, r.text
    return r.json()


# ── create ─────────────────────────────────────────────────────────────────────

def test_add_trip_success(client):
    headers = _setup(client)
    r = client.post("/trips", json=TRIP, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["country"] == "Japan"
    assert data["city"] == "Tokyo"
    assert data["duration_days"] == 7
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data


def test_add_trip_no_auth(client):
    r = client.post("/trips", json=TRIP)
    assert r.status_code == 401


# ── list ───────────────────────────────────────────────────────────────────────

def test_get_trips_returns_own_only(client):
    alice_headers = _setup(client, "alice", "alice@test.com")
    _create_trip(client, alice_headers, {"country": "Japan"})

    bob_headers = _setup(client, "bob", "bob@test.com")
    _create_trip(client, bob_headers, {"country": "France"})

    r = client.get("/trips", headers=alice_headers)
    assert r.status_code == 200
    trips = r.json()
    assert len(trips) == 1
    assert trips[0]["country"] == "Japan"


def test_get_trips_empty(client):
    headers = _setup(client)
    r = client.get("/trips", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


def test_get_trips_no_auth(client):
    r = client.get("/trips")
    assert r.status_code == 401


# ── get by id ──────────────────────────────────────────────────────────────────

def test_get_trip_success(client):
    headers = _setup(client)
    trip = _create_trip(client, headers)
    r = client.get(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    assert r.json()["country"] == "Japan"


def test_get_trip_not_found(client):
    headers = _setup(client)
    r = client.get("/trips/99999", headers=headers)
    assert r.status_code == 404


def test_get_trip_another_users_trip(client):
    alice_headers = _setup(client, "alice", "alice@test.com")
    trip = _create_trip(client, alice_headers)

    bob_headers = _setup(client, "bob", "bob@test.com")
    r = client.get(f"/trips/{trip['id']}", headers=bob_headers)
    assert r.status_code == 403


def test_get_trip_no_auth(client):
    r = client.get("/trips/1")
    assert r.status_code == 401


# ── update ─────────────────────────────────────────────────────────────────────

def test_update_trip_success(client):
    headers = _setup(client)
    trip = _create_trip(client, headers)
    r = client.patch(f"/trips/{trip['id']}", json={"country": "South Korea"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["country"] == "South Korea"


def test_update_trip_partial(client):
    headers = _setup(client)
    trip = _create_trip(client, headers)
    r = client.patch(f"/trips/{trip['id']}", json={"city": "Osaka"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["city"] == "Osaka"
    assert data["country"] == "Japan"  # unchanged


def test_update_trip_not_found(client):
    headers = _setup(client)
    r = client.patch("/trips/99999", json={"country": "X"}, headers=headers)
    assert r.status_code == 404


def test_update_trip_another_users_trip(client):
    alice_headers = _setup(client, "alice", "alice@test.com")
    trip = _create_trip(client, alice_headers)

    bob_headers = _setup(client, "bob", "bob@test.com")
    r = client.patch(f"/trips/{trip['id']}", json={"country": "X"}, headers=bob_headers)
    assert r.status_code == 403


def test_update_trip_no_auth(client):
    r = client.patch("/trips/1", json={"country": "X"})
    assert r.status_code == 401


# ── delete ─────────────────────────────────────────────────────────────────────

def test_delete_trip_success(client):
    headers = _setup(client)
    trip = _create_trip(client, headers)
    r = client.delete(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    # confirm gone via list (avoids calling rate-limited GET /trips/{id} twice)
    remaining = client.get("/trips", headers=headers).json()
    assert all(t["id"] != trip["id"] for t in remaining)


def test_delete_trip_not_found(client):
    headers = _setup(client)
    r = client.delete("/trips/99999", headers=headers)
    assert r.status_code == 404


def test_delete_trip_another_users_trip(client):
    alice_headers = _setup(client, "alice", "alice@test.com")
    trip = _create_trip(client, alice_headers)

    bob_headers = _setup(client, "bob", "bob@test.com")
    r = client.delete(f"/trips/{trip['id']}", headers=bob_headers)
    assert r.status_code == 403


def test_delete_trip_no_auth(client):
    r = client.delete("/trips/1")
    assert r.status_code == 401
