from sqlmodel import SQLModel, Field

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