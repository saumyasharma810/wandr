from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Depends, Request
from sqlmodel import select
from app.models import Trip, TripCreate, TripPublic, TripUpdate, User, UserPublic
from app.database import create_db_and_tables, Session, get_session
from contextlib import asynccontextmanager
from app.auth import router as auth_router, get_current_active_user
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from datetime import datetime, timezone

limiter = Limiter(key_func=get_remote_address)

SessionDep = Annotated[Session, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

@asynccontextmanager
async def lifespan(app: FastAPI):
   create_db_and_tables()
   yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.get("/")
def home():
    return {"message": "hello"}

@app.get("/users/me", response_model=UserPublic)
def read_users_me(current_user: CurrentUser):
    return current_user

@app.get("/trips", response_model=list[TripPublic])
def get_all_trips(current_user: CurrentUser, session: SessionDep, offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    trips = session.execute(
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return trips

@app.get("/trips/{id}", response_model=TripPublic)
@limiter.limit("1/minute")
def get_trip(id: int, current_user: CurrentUser, session: SessionDep, request: Request) -> Trip:
    trip = session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    return trip

@app.post("/trips", response_model=TripPublic)
def add_trip(trip: TripCreate, current_user: CurrentUser, session: SessionDep) -> Trip:
    db_trp = Trip.model_validate(trip.model_dump() | {"user_id": current_user.id})
    session.add(db_trp)
    session.commit()
    session.refresh(db_trp)
    return db_trp

@app.delete("/trips/{id}")
def delete_trip(id: int, current_user: CurrentUser, session: SessionDep):
    trip = session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    session.delete(trip)
    session.commit()
    return {"status": "ok"}

@app.patch("/trips/{id}", response_model=TripPublic)
def update_trip(id: int, trip: TripUpdate, current_user: CurrentUser, session: SessionDep):
    trip_db = session.get(Trip, id)
    if not trip_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip_db.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    trip_data = trip.model_dump(exclude_unset=True)
    trip_data["updated_at"] = datetime.now(timezone.utc)
    trip_db.sqlmodel_update(trip_data)
    session.add(trip_db)
    session.commit()
    session.refresh(trip_db)
    return trip_db
