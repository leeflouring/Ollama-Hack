import contextlib
from typing import Annotated, Any, AsyncIterator

from fastapi import Depends
from sqlalchemy import TEXT, DateTime, event
from sqlalchemy.dialects.mysql import LONGTEXT as MYSQL_LONGTEXT
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declared_attr
from sqlmodel import SQLModel as _SQLModel

from .config import DatabaseConfig, DatabaseEngine, LogLevels, get_config
from .logging import get_logger
from .utils import snake_case

config = get_config()
logger = get_logger(__name__)

LONGTEXT = TEXT().with_variant(MYSQL_LONGTEXT(), "mysql")
UTC_DATETIME = DateTime(timezone=True)


class SQLModel(_SQLModel):
    @declared_attr.directive
    def __tablename__(cls) -> str:
        return snake_case(cls.__name__)


class DatabaseSessionManager:
    def __init__(self, host: str | URL, engine_kwargs: dict[str, Any] | None = None):
        if engine_kwargs is None:
            engine_kwargs = {}

        self._engine = create_async_engine(host, **engine_kwargs)
        self._sessionmaker = async_sessionmaker(autocommit=False, bind=self._engine)

        if self._engine.url.get_backend_name() == "sqlite":

            @event.listens_for(self._engine.sync_engine, "connect")
            def set_sqlite_pragmas(dbapi_connection, _):
                cursor = dbapi_connection.cursor()
                try:
                    cursor.execute("PRAGMA foreign_keys=ON")
                    cursor.execute("PRAGMA journal_mode=WAL")
                    cursor.execute("PRAGMA busy_timeout=5000")
                finally:
                    cursor.close()

    async def close(self):
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()

        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:
            raise Exception("DatabaseSessionManager is not initialized")

        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:
            raise Exception("DatabaseSessionManager is not initialized")

        session = self._sessionmaker()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_engine_schema(database: DatabaseConfig | None = None) -> URL:
    database = database or config.database

    match database.engine:
        case DatabaseEngine.MYSQL:
            return URL.create(
                "mysql+aiomysql",
                username=database.username,
                password=database.password,
                host=database.host,
                port=database.port or 3306,
                database=database.db,
                query={"charset": "utf8mb4"},
            )
        case DatabaseEngine.POSTGRESQL:
            return URL.create(
                "postgresql+asyncpg",
                username=database.username,
                password=database.password,
                host=database.host,
                port=database.port or 5432,
                database=database.db,
            )
        case DatabaseEngine.SQLITE:
            return URL.create("sqlite+aiosqlite", database=database.db)
        case _:
            raise ValueError(f"Unsupported database engine: {database.engine}")


def get_engine_kwargs(database: DatabaseConfig | None = None) -> dict[str, Any]:
    database = database or config.database
    kwargs: dict[str, Any] = {"echo": config.app.log_level == LogLevels.DEBUG}
    if database.engine == DatabaseEngine.SQLITE:
        kwargs["connect_args"] = {"timeout": database.pool_timeout}
    else:
        kwargs.update(
            pool_size=database.pool_size,
            max_overflow=database.max_overflow,
            pool_timeout=database.pool_timeout,
            pool_recycle=database.pool_recycle,
            pool_pre_ping=True,
        )
    return kwargs


sessionmanager = DatabaseSessionManager(
    get_engine_schema(),
    get_engine_kwargs(),
)


async def create_db_and_tables():
    async with sessionmanager.connect() as connection:

        def create_schema(sync_connection):
            SQLModel.metadata.create_all(sync_connection)
            for table in SQLModel.metadata.sorted_tables:
                for index in table.indexes:
                    index.create(sync_connection, checkfirst=True)

        await connection.run_sync(create_schema)


async def get_db_session():
    async with sessionmanager.session() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
