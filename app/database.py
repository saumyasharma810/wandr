from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlmodel import SQLModel
from app.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False
    )

async def create_db_and_tables():
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with AsyncSession(engine, expire_on_commit=False) as session:
        yield session
