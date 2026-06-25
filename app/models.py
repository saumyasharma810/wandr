from sqlmodel import SQLModel, Field
from sqlalchemy import Column, Integer, ForeignKey
from datetime import datetime, date, timezone
from enum import Enum
from pydantic import field_validator

# ── enums ──────────────────────────────────────────

class VibeTag(str, Enum):
    loved_it = "loved_it"
    mixed = "mixed"
    never_again = "never_again"
    neutral = "neutral"

class TravelStyle(str, Enum):
    solo = "solo"
    couple = "couple"
    group = "group"
    family = "family"

class BudgetLevel(str, Enum):
    backpacker = "backpacker"
    mid = "mid"
    luxury = "luxury"

# ── user ───────────────────────────────────────────

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class UserCreate(SQLModel):
    username: str
    email: str
    password: str

class UserPublic(UserBase):
    id: int

# ── trip stop (defined before Trip so TripStopCreate can be used in TripCreate) ──

class TripStopCreate(SQLModel):
    city: str
    country: str
    arrival_date: date
    departure_date: date
    vibe: VibeTag
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool
    order: int | None = None  # auto-assigned if omitted

class TripStopUpdate(SQLModel):
    city: str | None = None
    country: str | None = None
    arrival_date: date | None = None
    departure_date: date | None = None
    vibe: VibeTag | None = None
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool | None = None
    order: int | None = None

class TripStopPublic(SQLModel):
    id: int
    trip_id: int
    city: str
    country: str
    arrival_date: date
    departure_date: date
    vibe: VibeTag
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool
    order: int
    created_at: datetime

class TripStop(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    trip_id: int = Field(
        sa_column=Column(
            Integer,
            ForeignKey("trip.id", ondelete="CASCADE"),
            index=True,
            nullable=False,
        )
    )
    city: str
    country: str
    arrival_date: date
    departure_date: date
    vibe: VibeTag
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool
    order: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

# ── trip ───────────────────────────────────────────

class Trip(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str | None = None
    start_date: date
    end_date: date
    travel_style: TravelStyle
    budget_level: BudgetLevel
    is_public: bool = Field(default=True)
    ai_summary: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TripCreate(SQLModel):
    title: str | None = None
    start_date: date
    end_date: date
    travel_style: TravelStyle
    budget_level: BudgetLevel
    is_public: bool = True
    stops: list[TripStopCreate]

class TripPublic(SQLModel):
    id: int
    user_id: int
    title: str | None = None
    start_date: date
    end_date: date
    travel_style: TravelStyle
    budget_level: BudgetLevel
    is_public: bool
    ai_summary: str | None = None
    created_at: datetime
    stops: list[TripStopPublic] = []
    countries: list[str] = []  # derived: distinct countries ordered by earliest arrival_date

class TripUpdate(SQLModel):
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    travel_style: TravelStyle | None = None
    budget_level: BudgetLevel | None = None
    is_public: bool | None = None

# ── stranger tip ───────────────────────────────────

class StrangerTipBase(SQLModel):
    country: str
    city: str
    content: str
    is_public: bool = Field(default=True)

class StrangerTip(StrangerTipBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int | None = Field(
        default=None,
        foreign_key="user.id",
        index=True
    )  # nullable — anonymous tips allowed
    helpful_count: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class StrangerTipCreate(StrangerTipBase):
    is_anonymous: bool = False

class StrangerTipUpdate(SQLModel):
    country: str | None = None
    city: str | None = None
    content: str | None = None
    is_public: bool | None = None

class StrangerTipPublic(StrangerTipBase):
    id: int
    helpful_count: int
    created_at: datetime
    username: str | None  # None if anonymous

# ── refresh token ──────────────────────────────────

class RefreshToken(SQLModel, table=True):
    tokenHash: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    expires_at: datetime
    is_revoked: bool = Field(default=False)  # add this for logout support


# chat

class ChatRequest(SQLModel):
    message: str
    conversation_id: int | None = None

    @field_validator("conversation_id")
    @classmethod
    def must_be_positive(cls, v):
        if v is not None and v < 1:
            raise ValueError("conversation_id must be a positive integer")
        return v

class ChatMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    conversation_id: int = Field(index=True)
    role: str
    content: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None)
    )
