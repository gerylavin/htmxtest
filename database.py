from typing import Annotated
from fastapi import Depends
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.ext.asyncio import create_async_engine,async_sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_FILENAME = "database.db"
DATABASE_URL = f"sqlite+aiosqlite:///{DATABASE_FILENAME}"

connect_args = {"check_same_thread": False}

engine = create_async_engine(
    DATABASE_URL, 
    connect_args=connect_args, 
    echo=True
)

async_session_maker = async_sessionmaker(
    bind=engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)

    
async def create_db_and_tables():
    """Asynchronously create the database tables."""
    async with engine.begin() as conn:
        # metadata.create_all is a synchronous method, so we use conn.run_sync
        # to execute the schema generation safely in an async context.
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session():
    async with async_session_maker() as session:
        yield session

SessionDep = Annotated[AsyncSession, Depends(get_session)]