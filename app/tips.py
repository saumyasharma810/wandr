from typing import Annotated
from fastapi import HTTPException, Query, Depends, APIRouter
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import select
from app.models import User, StrangerTipCreate, StrangerTipUpdate, StrangerTipBase, StrangerTip, StrangerTipPublic
from app.database import AsyncSession, get_session
from app.auth import get_current_active_user, get_current_user



router = APIRouter()

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

_oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

async def _get_optional_user(
    token: str | None = Depends(_oauth2_optional),
    session: AsyncSession = Depends(get_session),
) -> User | None:
    if token is None:
        return None
    try:
        user = await get_current_user(token, session)
        return user if user.is_active else None
    except HTTPException:
        return None

OptionalUser = Annotated[User | None, Depends(_get_optional_user)]

@router.get("/tips", response_model=list[StrangerTipPublic])
async def get_tips(session: SessionDep, city: str | None = None, country: str | None = None, offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 15,):
    query = (
        select(StrangerTip, User.username)
        .outerjoin(User, StrangerTip.user_id == User.id)
        .where(StrangerTip.is_public == True)
    )
    if city:
        query = query.where(StrangerTip.city == city)
    if country:
        query = query.where(StrangerTip.country == country)
    result = await session.execute(query.offset(offset).limit(limit))
    return [
        StrangerTipPublic(**tip.model_dump(), username=username)
        for tip, username in result.all()
    ]

@router.post("/tips", response_model=StrangerTipPublic)
async def add_tip(tip: StrangerTipCreate, session: SessionDep, current_user: OptionalUser):
    user_id = current_user.id if (current_user and not tip.is_anonymous) else None
    db_tip = StrangerTip.model_validate(tip.model_dump(exclude={"is_anonymous"}) | {"user_id": user_id})
    session.add(db_tip)
    await session.commit()
    await session.refresh(db_tip)
    username = current_user.username if user_id else None
    return StrangerTipPublic(**db_tip.model_dump(), username=username)

@router.patch("/tips/{id}", response_model=StrangerTipBase)
async def update_tip(id: int, tip: StrangerTipUpdate, session: SessionDep, current_user: CurrentUser):
    db_tip = await session.get(StrangerTip, id)
    if not db_tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if db_tip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    tip_data = tip.model_dump(exclude_unset=True)
    db_tip.sqlmodel_update(tip_data)
    session.add(db_tip)
    await session.commit()
    await session.refresh(db_tip)
    return db_tip

@router.patch("/tips/{id}/helpful", response_model=StrangerTipPublic)
async def upvote_tip(id: int, session: SessionDep, current_user: CurrentUser):
    db_tip = await session.get(StrangerTip, id)
    if not db_tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    db_tip.helpful_count += 1
    session.add(db_tip)
    await session.commit()
    await session.refresh(db_tip)
    username = None
    if db_tip.user_id:
        user = await session.get(User, db_tip.user_id)
        username = user.username if user else None
    return StrangerTipPublic(**db_tip.model_dump(), username=username)
    

@router.delete("/tips/{id}")
async def delete_tip(id: int, session: SessionDep, current_user: CurrentUser):
    db_tip = await session.get(StrangerTip, id)
    if not db_tip:
        raise HTTPException(status_code=404, detail="Tip not found")
    if db_tip.user_id is None or db_tip.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not your trip")
    await session.delete(db_tip)
    await session.commit()
    return {"status": "ok"}