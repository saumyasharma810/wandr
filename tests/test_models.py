# tests/test_models.py

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlmodel import SQLModel
from app.models import Trip, TripCreate, TripUpdate, TripPublic


@pytest.fixture(scope="function")
def test_engine():
    """Create a fresh in-memory database for each test"""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    yield engine
    # No cleanup needed for in-memory DB


def test_trip_model_creation():
    """Test creating a Trip instance"""
    trip = Trip(country="Japan", duration_days=10, is_public=True)
    assert trip.country == "Japan"
    assert trip.duration_days == 10
    assert trip.is_public == True
    assert trip.id is None  # Not set until saved


def test_trip_create_model():
    """Test TripCreate model validation"""
    trip_data = {"country": "France", "duration_days": 7, "is_public": False}
    trip_create = TripCreate(**trip_data)
    assert trip_create.country == "France"
    assert trip_create.duration_days == 7
    assert trip_create.is_public == False


def test_trip_update_model():
    """Test TripUpdate model with partial data"""
    update_data = {"country": "Germany", "is_public": True}
    trip_update = TripUpdate(**update_data)
    assert trip_update.country == "Germany"
    assert trip_update.duration_days is None  # Not provided
    assert trip_update.is_public == True


def test_trip_public_model():
    """Test TripPublic model"""
    trip_data = {"id": 1, "country": "Italy", "duration_days": 5}
    trip_public = TripPublic(**trip_data)
    assert trip_public.id == 1
    assert trip_public.country == "Italy"
    assert trip_public.duration_days == 5


def test_trip_model_validation():
    """Test model creation with None values (nullable fields)"""
    trip = Trip()  # Should work with None defaults
    assert trip.country is None
    assert trip.duration_days is None
    assert trip.is_public == False  # Default value



def test_session_management(test_engine):
    """Test that sessions work correctly"""
    # Test that we can create a session and use it
    with Session(test_engine) as session:
        trip = Trip(country="Test", duration_days=1, is_public=False)
        session.add(trip)
        session.commit()
        session.refresh(trip)
        assert trip.id is not None

        # Clean up
        session.delete(trip)
        session.commit()