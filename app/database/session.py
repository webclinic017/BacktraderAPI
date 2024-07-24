import contextlib
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    create_async_engine,
    async_sessionmaker,
    AsyncConnection
)
from typing import AsyncGenerator

from ..utils.errors import InternalServiceError
from ..utils.config import app_settings


class DatabaseSessionManager:
    def __init__(self, host: str):
        print('host', host)
        self.engine: AsyncEngine = create_async_engine(host)
        self._sessionmaker: async_sessionmaker[AsyncSession] = async_sessionmaker(
            autocommit=False, bind=self.engine
        )

    async def close(self):
        if self.engine is None:
            raise InternalServiceError
        
        await self.engine.dispose()
        self.engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncGenerator[AsyncConnection, None]:
        if self.engine is None:
            raise InternalServiceError
        
        async with self.engine.begin() as connection:
            try:
                yield connection
            except SQLAlchemyError:
                await connection.rollback()
                raise InternalServiceError
            
    @contextlib.asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncConnection, None]:
        if not self._sessionmaker:
            raise InternalServiceError
        
        session = self._sessionmaker
        try:
            yield session
        except SQLAlchemyError:
            await session.rollback()
            raise InternalServiceError
        finally:
            await session.close()


session_manager = DatabaseSessionManager(host=app_settings.db_dsn)


async def get_db():
    async with session_manager.session() as session:
        yield session