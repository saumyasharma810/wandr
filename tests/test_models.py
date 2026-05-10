from datetime import datetime, timezone
from app.models import (
    Trip, TripCreate, TripUpdate, TripPublic,
    User, UserCreate,
    VibeTag, TravelStyle, BudgetLevel,
)


def test_trip_model_creation():
    trip = Trip(country="Japan", duration_days=10, is_public=True, user_id=1)
    assert trip.country == "Japan"
    assert trip.duration_days == 10
    assert trip.is_public is True
    assert trip.id is None


def test_trip_optional_fields_default_to_none():
    trip = Trip(country="Japan", user_id=1)
    assert trip.city is None
    assert trip.start_date is None
    assert trip.vibe is None
    assert trip.travel_style is None
    assert trip.budget_level is None
    assert trip.is_public is False


def test_trip_create_model():
    trip = TripCreate(country="France", duration_days=7, is_public=False)
    assert trip.country == "France"
    assert trip.duration_days == 7
    assert trip.is_public is False


def test_trip_update_partial():
    update = TripUpdate(country="Germany", is_public=True)
    assert update.country == "Germany"
    assert update.duration_days is None
    assert update.is_public is True


def test_trip_public_model():
    now = datetime.now(timezone.utc)
    trip = TripPublic(id=1, country="Italy", duration_days=5, user_id=42, created_at=now)
    assert trip.id == 1
    assert trip.user_id == 42
    assert trip.country == "Italy"


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
