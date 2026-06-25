from typing import Annotated
from collections import defaultdict
from fastapi import HTTPException, Query, Depends, APIRouter
from sqlmodel import select, func
from sqlalchemy import delete
from app.models import (
    Trip, TripCreate, TripPublic, TripUpdate,
    TripStop, TripStopCreate, TripStopUpdate, TripStopPublic,
    User,
)
from app.database import AsyncSession, get_session
from app.auth import get_current_active_user
from datetime import datetime, timezone


router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


def _build_trip_public(trip: Trip, stops: list[TripStop]) -> TripPublic:
    stops_sorted = sorted(stops, key=lambda s: s.arrival_date)
    seen: dict[str, bool] = {}
    countries: list[str] = []
    for stop in stops_sorted:
        if stop.country not in seen:
            seen[stop.country] = True
            countries.append(stop.country)
    return TripPublic(
        id=trip.id,
        user_id=trip.user_id,
        title=trip.title,
        start_date=trip.start_date,
        end_date=trip.end_date,
        travel_style=trip.travel_style,
        budget_level=trip.budget_level,
        is_public=trip.is_public,
        ai_summary=trip.ai_summary,
        created_at=trip.created_at,
        stops=[TripStopPublic.model_validate(s, from_attributes=True) for s in stops],
        countries=countries,
    )


async def _fetch_stops(session: AsyncSession, trip_id: int) -> list[TripStop]:
    result = await session.execute(
        select(TripStop).where(TripStop.trip_id == trip_id).order_by(TripStop.order)
    )
    return list(result.scalars().all())


@router.get("/trips", response_model=list[TripPublic])
async def get_all_trips(
    current_user: CurrentUser,
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
):
    result = await session.execute(
        select(Trip).where(Trip.user_id == current_user.id).offset(offset).limit(limit)
    )
    trips = list(result.scalars().all())

    if not trips:
        return []

    trip_ids = [t.id for t in trips]
    stops_result = await session.execute(
        select(TripStop).where(TripStop.trip_id.in_(trip_ids)).order_by(TripStop.order)
    )
    all_stops = list(stops_result.scalars().all())

    stops_by_trip: dict[int, list[TripStop]] = defaultdict(list)
    for stop in all_stops:
        stops_by_trip[stop.trip_id].append(stop)

    return [_build_trip_public(trip, stops_by_trip[trip.id]) for trip in trips]


@router.get("/trips/{id}", response_model=TripPublic)
async def get_trip(id: int, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id and not trip.is_public:
        raise HTTPException(status_code=403, detail="Not your trip")
    stops = await _fetch_stops(session, id)
    return _build_trip_public(trip, stops)


@router.post("/trips", response_model=TripPublic, status_code=201)
async def add_trip(trip_in: TripCreate, current_user: CurrentUser, session: SessionDep):
    if not trip_in.stops:
        raise HTTPException(status_code=422, detail="At least one stop is required")

    trip_data = trip_in.model_dump(exclude={"stops"})
    db_trip = Trip(**trip_data | {"user_id": current_user.id})
    session.add(db_trip)
    await session.flush()  # get id before committing

    db_stops: list[TripStop] = []
    for i, stop_in in enumerate(trip_in.stops):
        stop_data = stop_in.model_dump()
        if stop_data["order"] is None:
            stop_data["order"] = i
        db_stop = TripStop(**stop_data | {"trip_id": db_trip.id})
        session.add(db_stop)
        db_stops.append(db_stop)

    await session.commit()
    await session.refresh(db_trip)
    for stop in db_stops:
        await session.refresh(stop)

    return _build_trip_public(db_trip, db_stops)


@router.patch("/trips/{id}", response_model=TripPublic)
async def update_trip(id: int, trip_in: TripUpdate, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    trip_data = trip_in.model_dump(exclude_unset=True)
    trip_data["updated_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
    trip.sqlmodel_update(trip_data)
    session.add(trip)
    await session.commit()
    await session.refresh(trip)
    stops = await _fetch_stops(session, id)
    return _build_trip_public(trip, stops)


@router.delete("/trips/{id}")
async def delete_trip(id: int, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    await session.execute(delete(TripStop).where(TripStop.trip_id == id))
    await session.delete(trip)
    await session.commit()
    return {"status": "ok"}


# ── stop endpoints ─────────────────────────────────────────────────────────────

@router.post("/trips/{id}/stops", response_model=TripStopPublic, status_code=201)
async def add_stop(id: int, stop_in: TripStopCreate, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")

    stop_data = stop_in.model_dump()
    if stop_data["order"] is None:
        result = await session.execute(
            select(func.max(TripStop.order)).where(TripStop.trip_id == id)
        )
        max_order = result.scalar()
        stop_data["order"] = (max_order + 1) if max_order is not None else 0

    db_stop = TripStop(**stop_data | {"trip_id": id})
    session.add(db_stop)
    await session.commit()
    await session.refresh(db_stop)
    return db_stop


@router.patch("/trips/{id}/stops/{stop_id}", response_model=TripStopPublic)
async def update_stop(
    id: int, stop_id: int, stop_in: TripStopUpdate, current_user: CurrentUser, session: SessionDep
):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")

    stop = await session.get(TripStop, stop_id)
    if not stop or stop.trip_id != id:
        raise HTTPException(status_code=404, detail="Stop not found")

    stop.sqlmodel_update(stop_in.model_dump(exclude_unset=True))
    session.add(stop)
    await session.commit()
    await session.refresh(stop)
    return stop


@router.delete("/trips/{id}/stops/{stop_id}")
async def delete_stop(id: int, stop_id: int, current_user: CurrentUser, session: SessionDep):
    trip = await session.get(Trip, id)
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    if trip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")

    stop = await session.get(TripStop, stop_id)
    if not stop or stop.trip_id != id:
        raise HTTPException(status_code=404, detail="Stop not found")

    count_result = await session.execute(
        select(func.count()).select_from(TripStop).where(TripStop.trip_id == id)
    )
    if count_result.scalar() <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the last stop of a trip")

    await session.delete(stop)
    await session.commit()
    return {"status": "ok"}
