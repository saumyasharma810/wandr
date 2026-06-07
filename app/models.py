from sqlmodel import SQLModel, Field
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

# ── trip ───────────────────────────────────────────

class TripBase(SQLModel):
    country: str
    city: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    vibe: VibeTag | None = None
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool | None = None
    is_public: bool = Field(default=False)
    travel_style: TravelStyle | None = None
    budget_level: BudgetLevel | None = None

class Trip(TripBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

class TripCreate(TripBase):
    pass  # user_id auto-set from JWT token in endpoint

class TripPublic(TripBase):
    id: int
    user_id: int
    created_at: datetime

class TripUpdate(SQLModel):
    country: str | None = None
    city: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    duration_days: int | None = None
    vibe: VibeTag | None = None
    notes: str | None = None
    highlight: str | None = None
    lowlight: str | None = None
    would_return: bool | None = None
    is_public: bool | None = None
    travel_style: TravelStyle | None = None
    budget_level: BudgetLevel | None = None

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
    pass

class StrangerTipPublic(StrangerTipBase):
    id: int
    helpful_count: int
    created_at: datetime

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
