from typing import Annotated
from fastapi import HTTPException, Query, Request, Depends, APIRouter
from sqlmodel import select
from app.models import Trip, TripCreate, TripPublic, TripUpdate, User
from app.database import AsyncSession, get_session
from app.auth import get_current_active_user
from datetime import datetime, timezone



router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]



@router.get("/trips", response_model=list[TripPublic])
async def get_all_trips(current_user: CurrentUser, session: SessionDep, offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    trips = await session.execute(
        select(Trip)
        .where(Trip.user_id == current_user.id)
        .offset(offset)
        .limit(limit)
    )
    trips = trips.scalars().all()
    return trips

@router.get("/trips/{id}", response_model=TripPublic)
async def get_trip(id: int, current_user: CurrentUser, session: SessionDep, request: Request) -> Trip:
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id and not trip.is_public:
        raise HTTPException(status_code=403, detail="Not your trip")
    return trip

@router.post("/trips", response_model=TripPublic)
async def add_trip(trip: TripCreate, current_user: CurrentUser, session: SessionDep) -> Trip:
    db_trp = Trip.model_validate(trip.model_dump() | {"user_id": current_user.id})
    session.add(db_trp)
    await session.commit()
    await session.refresh(db_trp)
    return db_trp

@router.delete("/trips/{id}")
async def delete_trip(id: int, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    await session.delete(trip)
    await session.commit()
    return {"status": "ok"}

@router.patch("/trips/{id}", response_model=TripPublic)
async def update_trip(id: int, trip: TripUpdate, current_user: CurrentUser, session: SessionDep):
    trip_db = await session.get(Trip, id)
    if not trip_db:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip_db.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    trip_data = trip.model_dump(exclude_unset=True)
    trip_data["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    trip_db.sqlmodel_update(trip_data)
    session.add(trip_db)
    await session.commit()
    await session.refresh(trip_db)
    return trip_db
