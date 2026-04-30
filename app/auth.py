from typing import Annotated
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from sqlmodel import select
from app.models import UserCreate, User, UserPublic
from app.database import Session, get_session
from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from app.config import settings
from app.schemas import Token, TokenData
import jwt
from jwt.exceptions import InvalidTokenError


# create hasher (recommended config → uses Argon2)
password_hash = PasswordHash.recommended()

router = APIRouter()

SessionDep = Annotated[Session, Depends(get_session)]

DUMMY_HASH = password_hash.hash("dummypassword")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# Hash a password
def get_password_hash(password:str) -> bool:
    return password_hash.hash(password=password)

# Verify password
def verify_password(password:str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)

# get user from db
def get_user(username: str, session: Session):
    return session.execute(select(User).where(User.username == username)).scalars().first()

# authenticate is user in db and verify password
def authenticate_user(username: str, password: str, session: Session):
    user = get_user(username=username, session=session)
    if not user:
        verify_password(password, DUMMY_HASH)
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

# create access token
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

# get current user from jwt
def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], session: SessionDep):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(username=token_data.username, session=session)
    if user is None:
        raise credentials_exception
    return user

# check if the current user is active or not
def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


@router.post("/register", response_model=UserPublic)
def register(user: UserCreate, session: SessionDep):
    existing_user = session.execute(select(User).where(User.username == user.username)).scalars().first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already present")
    existing_email = session.execute(select(User).where(User.email == user.email)).scalars().first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already present")
    db_user = User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
    )
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user

@router.post("/login")
def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], session: SessionDep) -> Token:
    user = authenticate_user(form_data.username, form_data.password, session)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

