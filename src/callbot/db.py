from collections.abc import AsyncIterator

from loguru import logger as log
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlmodel import SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession

from callbot.misc.singleton import Singleton
from callbot.settings import Settings


class Session(AsyncSession):
    async def close(self) -> None:
        await super().close()
        if isinstance(self.bind, AsyncEngine) and self.bind.echo:
            log.debug("DB session closed")


class EngineWrapper(metaclass=Singleton):
    engine: AsyncEngine

    def __init__(self) -> None:
        settings = Settings()
        self.engine = create_async_engine(settings.db.url)

    async def create_tables(self, drop_first: bool = False) -> None:
        async with self.engine.begin() as conn:
            if drop_first:
                await conn.run_sync(SQLModel.metadata.drop_all)
            await conn.run_sync(SQLModel.metadata.create_all)

    def get_session(self) -> Session:
        return Session(self.engine)

    @classmethod
    async def yield_session(cls) -> AsyncIterator[Session]:
        async with Session(cls().engine) as session:
            yield session
