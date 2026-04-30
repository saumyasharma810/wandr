from typing import Annotated
from fastapi import FastAPI, HTTPException, Query, Depends
from sqlmodel import select
from app.models import Trip, TripCreate, TripPublic, TripUpdate, User, UserPublic
from app.database import create_db_and_tables,Session, get_session
from contextlib import asynccontextmanager
from app.auth import router as auth_router, get_current_active_user

# define SessionDep locally in main.py
SessionDep = Annotated[Session, Depends(get_session)]

CurrentUser = Annotated[User, Depends(get_current_active_user)]

@asynccontextmanager
async def lifespan(app: FastAPI):
   create_db_and_tables()
   yield

app = FastAPI(lifespan=lifespan)

app.include_router(auth_router, prefix="/auth", tags=["auth"])

@app.get("/")
def home():
    return {"message": "hello"}

@app.get("/users/me", response_model=UserPublic)
def read_users_me(current_user: Annotated[User, Depends(get_current_active_user)]):
    return current_user

@app.get("/trips", response_model=list[TripPublic])
def get_all_trips(session: SessionDep, offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    trips = session.execute(select(Trip).offset(offset).limit(limit)).scalars().all()
    return trips

@app.get("/trips/{id}", response_model=TripPublic)
def get_trip(id:int, session: SessionDep) -> Trip:
    trip = session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    return trip

@app.post("/trips", response_model=TripPublic)
def add_trip(trip: TripCreate, session: SessionDep) -> Trip:
    db_trp = Trip.model_validate(trip)
    session.add(db_trp)
    session.commit()
    session.refresh(db_trp)
    return db_trp

@app.delete("/trips/{id}")
def delete_trip(id:int, session: SessionDep):
    trip = session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    session.delete(trip)
    session.commit()
    return {"Status":"Ok"}

@app.patch("/trips/{id}", response_model=TripPublic)
def update_trip(id: int, trip: TripUpdate ,session: SessionDep):
    trip_db = session.get(Trip, id)
    if not trip_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    trip_data = trip.model_dump(exclude_defaults=True)
    trip_db.sqlmodel_update(trip_data)
    session.add(trip_db)
    session.commit()
    session.refresh(trip_db)
    return trip_db





