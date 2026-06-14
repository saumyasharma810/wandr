from typing import Annotated
from fastapi import FastAPI, Depends, Request
from fastapi.responses import JSONResponse
from app.models import User, UserPublic
from app.database import create_db_and_tables, AsyncSession, get_session
from contextlib import asynccontextmanager
from app.auth import router as auth_router, get_current_active_user
from app.chat import router as chat_router
from app.trips import router as trip_router
from app.tips import router as tips_router
from app.config import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from loguru import logger
import time
from fastapi.middleware.cors import CORSMiddleware

limiter = Limiter(key_func=get_remote_address)

SessionDep = Annotated[AsyncSession, Depends(get_session)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]

@asynccontextmanager
async def lifespan(app: FastAPI):
   await create_db_and_tables()
   logger.info("Wandr API started — DB tables ready")
   yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(chat_router, prefix="/chat", tags=["chat"])
app.include_router(trip_router,prefix="", tags=["trip"])
app.include_router(tips_router, prefix="", tags=["tips"])

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 1. request logging middleware — logs every request
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start
    logger.info(
        f"{request.method} {request.url.path} "
        f"→ {response.status_code} ({duration:.2f}s)"
    )
    return response


# 2. global error handler — catches unhandled exceptions
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url.path}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )



@app.get("/")
def home():
    return {"message": "hello"}

@app.get("/users/me", response_model=UserPublic)
def read_users_me(current_user: CurrentUser):
    return current_user

