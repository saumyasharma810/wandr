from sqlmodel import SQLModel, Field
from datetime import datetime

class TripBase(SQLModel):
    country: str = Field(default=None)
    duration_days: int = Field(default=None)

class Trip(TripBase, table=True):
    id: int | None = Field(default = None, primary_key=True)
    is_public: bool = Field(default=False)

class TripPublic(TripBase):
    id: int

class TripCreate(TripBase):
    is_public: bool | None

class TripUpdate(SQLModel):       
    country: str | None = None
    duration_days: int | None = None
    is_public: bool | None = None

class UserBase(SQLModel):
    username: str = Field(unique=True, index=True)
    email: str = Field(unique=True, index=True)

class User(UserBase, table=True):
    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str
    is_active: bool = Field(default=True)

class UserCreate(SQLModel):
    username: str
    email: str
    password: str          # plain text — will be hashed before saving

class UserPublic(UserBase):
    id: int

class RefreshToken(SQLModel, table=True):
    tokenHash: str = Field(default=None, primary_key=True)
    user_id: int
    expires_at: datetime
    is_revoked: bool = Field(default=False)