from tests.conftest import register, auth_headers

STOP = {
    "city": "Tokyo",
    "country": "Japan",
    "arrival_date": "2024-03-01",
    "departure_date": "2024-03-07",
    "vibe": "loved_it",
    "would_return": True,
}

TRIP = {
    "title": "Japan adventure",
    "start_date": "2024-03-01",
    "end_date": "2024-03-07",
    "travel_style": "solo",
    "budget_level": "mid",
    "is_public": False,
    "stops": [STOP],
}


async def _setup(client, username="alice", email="alice@test.com") -> dict:
    await register(client, username=username, email=email)
    return await auth_headers(client, username=username)


async def _create_trip(client, headers, payload=None) -> dict:
    r = await client.post("/trips", json=payload or TRIP, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── create ─────────────────────────────────────────────────────────────────────

async def test_add_trip_success(client):
    headers = await _setup(client)
    r = await client.post("/trips", json=TRIP, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["title"] == "Japan adventure"
    assert data["travel_style"] == "solo"
    assert data["budget_level"] == "mid"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data
    assert len(data["stops"]) == 1
    assert data["stops"][0]["city"] == "Tokyo"
    assert data["stops"][0]["country"] == "Japan"
    assert data["countries"] == ["Japan"]


async def test_add_trip_multiple_stops(client):
    headers = await _setup(client)
    payload = {**TRIP, "stops": [
        STOP,
        {"city": "Kyoto", "country": "Japan", "arrival_date": "2024-03-08",
         "departure_date": "2024-03-12", "vibe": "loved_it", "would_return": True},
    ]}
    r = await client.post("/trips", json=payload, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert len(data["stops"]) == 2
    assert data["countries"] == ["Japan"]


async def test_add_trip_no_auth(client):
    r = await client.post("/trips", json=TRIP)
    assert r.status_code == 401


async def test_add_trip_no_stops_rejected(client):
    headers = await _setup(client)
    payload = {**TRIP, "stops": []}
    r = await client.post("/trips", json=payload, headers=headers)
    assert r.status_code == 422


# ── list ───────────────────────────────────────────────────────────────────────

async def test_get_trips_returns_own_only(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    await _create_trip(client, alice_headers, {**TRIP, "stops": [{**STOP, "country": "Japan"}]})

    bob_headers = await _setup(client, "bob", "bob@test.com")
    await _create_trip(client, bob_headers, {**TRIP, "stops": [{**STOP, "country": "France", "city": "Paris"}]})

    r = await client.get("/trips", headers=alice_headers)
    assert r.status_code == 200
    trips = r.json()
    assert len(trips) == 1
    assert trips[0]["countries"] == ["Japan"]


async def test_get_trips_empty(client):
    headers = await _setup(client)
    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200
    assert r.json() == []


async def test_get_trips_no_auth(client):
    r = await client.get("/trips")
    assert r.status_code == 401


async def test_get_trips_countries_derived(client):
    headers = await _setup(client)
    payload = {
        **TRIP,
        "stops": [
            {"city": "Tokyo", "country": "Japan", "arrival_date": "2024-03-01",
             "departure_date": "2024-03-07", "vibe": "loved_it", "would_return": True},
            {"city": "Bangkok", "country": "Thailand", "arrival_date": "2024-02-20",
             "departure_date": "2024-02-28", "vibe": "mixed", "would_return": False},
        ],
    }
    r = await client.post("/trips", json=payload, headers=headers)
    assert r.status_code == 201

    r = await client.get("/trips", headers=headers)
    assert r.status_code == 200
    trips = r.json()
    # Thailand stop has earlier arrival_date, so it comes first
    assert trips[0]["countries"] == ["Thailand", "Japan"]


# ── get by id ──────────────────────────────────────────────────────────────────

async def test_get_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == trip["id"]
    assert len(data["stops"]) == 1
    assert data["stops"][0]["city"] == "Tokyo"
    assert data["countries"] == ["Japan"]


async def test_get_trip_not_found(client):
    headers = await _setup(client)
    r = await client.get("/trips/99999", headers=headers)
    assert r.status_code == 404


async def test_get_trip_another_users_trip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)  # is_public=False

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.get(f"/trips/{trip['id']}", headers=bob_headers)
    assert r.status_code == 403


async def test_get_trip_no_auth(client):
    r = await client.get("/trips/1")
    assert r.status_code == 401


# ── update trip (trip-level fields only) ───────────────────────────────────────

async def test_update_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.patch(f"/trips/{trip['id']}", json={"title": "Updated title"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["title"] == "Updated title"


async def test_update_trip_partial(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.patch(f"/trips/{trip['id']}", json={"is_public": True}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["is_public"] is True
    assert data["travel_style"] == "solo"  # unchanged


async def test_update_trip_does_not_affect_stops(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    original_stop_id = trip["stops"][0]["id"]

    await client.patch(f"/trips/{trip['id']}", json={"title": "New title"}, headers=headers)

    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    data = r.json()
    assert len(data["stops"]) == 1
    assert data["stops"][0]["id"] == original_stop_id
    assert data["stops"][0]["city"] == "Tokyo"


async def test_update_trip_not_found(client):
    headers = await _setup(client)
    r = await client.patch("/trips/99999", json={"title": "X"}, headers=headers)
    assert r.status_code == 404


async def test_update_trip_another_users_trip(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.patch(f"/trips/{trip['id']}", json={"title": "X"}, headers=bob_headers)
    assert r.status_code == 403


async def test_update_trip_no_auth(client):
    r = await client.patch("/trips/1", json={"title": "X"})
    assert r.status_code == 401


# ── delete trip ────────────────────────────────────────────────────────────────

async def test_delete_trip_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.delete(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 200
    remaining = (await client.get("/trips", headers=headers)).json()
    assert all(t["id"] != trip["id"] for t in remaining)


async def test_delete_trip_cascades_stops(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    stop_id = trip["stops"][0]["id"]

    await client.delete(f"/trips/{trip['id']}", headers=headers)

    # Trip is gone — 404
    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    assert r.status_code == 404

    # Stop endpoint should 404 too (trip doesn't exist)
    r = await client.patch(
        f"/trips/{trip['id']}/stops/{stop_id}", json={"city": "Osaka"}, headers=headers
    )
    assert r.status_code == 404


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


# ── add stop ───────────────────────────────────────────────────────────────────

async def test_add_stop_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    new_stop = {"city": "Osaka", "country": "Japan", "arrival_date": "2024-03-08",
                "departure_date": "2024-03-12", "vibe": "loved_it", "would_return": True}
    r = await client.post(f"/trips/{trip['id']}/stops", json=new_stop, headers=headers)
    assert r.status_code == 201
    data = r.json()
    assert data["city"] == "Osaka"
    assert data["trip_id"] == trip["id"]


async def test_add_stop_auto_order(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    first_order = trip["stops"][0]["order"]

    new_stop = {"city": "Kyoto", "country": "Japan", "arrival_date": "2024-03-08",
                "departure_date": "2024-03-10", "vibe": "loved_it", "would_return": True}
    r = await client.post(f"/trips/{trip['id']}/stops", json=new_stop, headers=headers)
    assert r.status_code == 201
    assert r.json()["order"] == first_order + 1


async def test_add_stop_not_owner(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)

    bob_headers = await _setup(client, "bob", "bob@test.com")
    new_stop = {"city": "Kyoto", "country": "Japan", "arrival_date": "2024-03-08",
                "departure_date": "2024-03-10", "vibe": "loved_it", "would_return": True}
    r = await client.post(f"/trips/{trip['id']}/stops", json=new_stop, headers=bob_headers)
    assert r.status_code == 403


async def test_add_stop_trip_not_found(client):
    headers = await _setup(client)
    new_stop = {"city": "Tokyo", "country": "Japan", "arrival_date": "2024-03-01",
                "departure_date": "2024-03-07", "vibe": "loved_it", "would_return": True}
    r = await client.post("/trips/99999/stops", json=new_stop, headers=headers)
    assert r.status_code == 404


# ── update stop ────────────────────────────────────────────────────────────────

async def test_update_stop_success(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    stop_id = trip["stops"][0]["id"]

    r = await client.patch(f"/trips/{trip['id']}/stops/{stop_id}", json={"city": "Osaka"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["city"] == "Osaka"


async def test_update_stop_partial(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    stop_id = trip["stops"][0]["id"]

    r = await client.patch(f"/trips/{trip['id']}/stops/{stop_id}", json={"vibe": "mixed"}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["vibe"] == "mixed"
    assert data["city"] == "Tokyo"  # unchanged


async def test_update_stop_does_not_affect_other_stops(client):
    headers = await _setup(client)
    payload = {**TRIP, "stops": [
        STOP,
        {"city": "Kyoto", "country": "Japan", "arrival_date": "2024-03-08",
         "departure_date": "2024-03-12", "vibe": "neutral", "would_return": False},
    ]}
    trip = await _create_trip(client, headers, payload)
    stop_0_id = trip["stops"][0]["id"]
    stop_1_id = trip["stops"][1]["id"]

    await client.patch(f"/trips/{trip['id']}/stops/{stop_0_id}", json={"city": "Osaka"}, headers=headers)

    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    stops = {s["id"]: s for s in r.json()["stops"]}
    assert stops[stop_0_id]["city"] == "Osaka"
    assert stops[stop_1_id]["city"] == "Kyoto"  # unchanged


async def test_update_stop_not_owner(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    trip = await _create_trip(client, alice_headers)
    stop_id = trip["stops"][0]["id"]

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.patch(f"/trips/{trip['id']}/stops/{stop_id}", json={"city": "Osaka"}, headers=bob_headers)
    assert r.status_code == 403


async def test_update_stop_not_found(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.patch(f"/trips/{trip['id']}/stops/99999", json={"city": "X"}, headers=headers)
    assert r.status_code == 404


# ── delete stop ────────────────────────────────────────────────────────────────

async def test_delete_stop_success(client):
    headers = await _setup(client)
    payload = {**TRIP, "stops": [
        STOP,
        {"city": "Kyoto", "country": "Japan", "arrival_date": "2024-03-08",
         "departure_date": "2024-03-12", "vibe": "loved_it", "would_return": True},
    ]}
    trip = await _create_trip(client, headers, payload)
    stop_0_id = trip["stops"][0]["id"]

    r = await client.delete(f"/trips/{trip['id']}/stops/{stop_0_id}", headers=headers)
    assert r.status_code == 200

    r = await client.get(f"/trips/{trip['id']}", headers=headers)
    assert len(r.json()["stops"]) == 1


async def test_delete_stop_last_stop_blocked(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    stop_id = trip["stops"][0]["id"]

    r = await client.delete(f"/trips/{trip['id']}/stops/{stop_id}", headers=headers)
    assert r.status_code == 400


async def test_delete_stop_not_owner(client):
    alice_headers = await _setup(client, "alice", "alice@test.com")
    payload = {**TRIP, "stops": [STOP, {**STOP, "city": "Kyoto", "arrival_date": "2024-03-08", "departure_date": "2024-03-12"}]}
    trip = await _create_trip(client, alice_headers, payload)
    stop_id = trip["stops"][0]["id"]

    bob_headers = await _setup(client, "bob", "bob@test.com")
    r = await client.delete(f"/trips/{trip['id']}/stops/{stop_id}", headers=bob_headers)
    assert r.status_code == 403


async def test_delete_stop_not_found(client):
    headers = await _setup(client)
    trip = await _create_trip(client, headers)
    r = await client.delete(f"/trips/{trip['id']}/stops/99999", headers=headers)
    assert r.status_code == 404
