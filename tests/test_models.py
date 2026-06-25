from datetime import datetime, date, timezone
from app.models import (
    Trip, TripCreate, TripUpdate, TripPublic,
    TripStop, TripStopCreate, TripStopPublic,
    User, UserCreate,
    VibeTag, TravelStyle, BudgetLevel,
)

STOP_FIELDS = dict(
    city="Tokyo", country="Japan",
    arrival_date=date(2024, 3, 1), departure_date=date(2024, 3, 7),
    vibe=VibeTag.loved_it, would_return=True,
)

TRIP_FIELDS = dict(
    start_date=date(2024, 3, 1), end_date=date(2024, 3, 7),
    travel_style=TravelStyle.solo, budget_level=BudgetLevel.mid,
)


def test_trip_model_creation():
    trip = Trip(**TRIP_FIELDS, user_id=1, is_public=True)
    assert trip.travel_style == TravelStyle.solo
    assert trip.budget_level == BudgetLevel.mid
    assert trip.is_public is True
    assert trip.id is None
    assert trip.title is None


def test_trip_optional_fields_default_to_none():
    trip = Trip(**TRIP_FIELDS, user_id=1)
    assert trip.title is None
    assert trip.ai_summary is None
    assert trip.is_public is True  # new default is True


def test_trip_stop_model():
    stop = TripStop(**STOP_FIELDS, trip_id=1)
    assert stop.city == "Tokyo"
    assert stop.country == "Japan"
    assert stop.order == 0
    assert stop.id is None


def test_trip_create_model():
    stop = TripStopCreate(**STOP_FIELDS)
    trip = TripCreate(**TRIP_FIELDS, stops=[stop])
    assert trip.travel_style == TravelStyle.solo
    assert len(trip.stops) == 1
    assert trip.stops[0].city == "Tokyo"
    assert trip.is_public is True


def test_trip_update_partial():
    update = TripUpdate(is_public=False)
    assert update.is_public is False
    assert update.title is None
    assert update.start_date is None


def test_trip_public_model():
    now = datetime.now(timezone.utc)
    stop = TripStopPublic(
        id=1, trip_id=1, **STOP_FIELDS, order=0,
        created_at=now,
    )
    trip = TripPublic(id=1, user_id=42, **TRIP_FIELDS, is_public=True, created_at=now, stops=[stop], countries=["Japan"])
    assert trip.id == 1
    assert trip.user_id == 42
    assert trip.countries == ["Japan"]
    assert len(trip.stops) == 1


def test_enum_values():
    assert VibeTag.loved_it == "loved_it"
    assert TravelStyle.solo == "solo"
    assert BudgetLevel.luxury == "luxury"


def test_user_model_creation():
    user = User(username="alice", email="alice@test.com", hashed_password="hash")
    assert user.username == "alice"
    assert user.is_active is True
    assert user.id is None


def test_user_create_model():
    u = UserCreate(username="alice", email="alice@test.com", password="plaintext")
    assert u.password == "plaintext"
