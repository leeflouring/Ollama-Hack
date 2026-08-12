import asyncio
import datetime
import importlib
import sys
from pathlib import Path

from sqlalchemy import DateTime, event, inspect, select

sys.path.insert(0, str(Path(__file__).parents[1]))

import src.database as database
from src.ai_model.models import AIModelDB, AIModelStatusEnum, EndpointAIModelDB
from src.ai_model.service import get_endpoint_counts
from src.apikey.models import ApiKeyDB, ApiKeyUsageLogDB
from src.apikey.service import get_api_key_usage_stats
from src.config import DatabaseConfig, DatabaseEngine
from src.database import DatabaseSessionManager, SQLModel, get_engine_kwargs, get_engine_schema
from src.endpoint.models import (
    EndpointDB,
    EndpointPerformanceDB,
    EndpointStatusEnum,
    EndpointTestTask,
    TaskStatus,
)
from src.endpoint.schemas import EndpointFilterParams
from src.endpoint.service import get_endpoints_with_ai_model_counts
from src.ollama import ollama_router
from src.setting.models import SystemSettings
from src.setting.service import init_settings
from src.user.models import UserDB
from src.utils import now

importlib.import_module("src.routes")


def test_database_urls_and_engine_kwargs():
    credentials = {
        "host": "db.example",
        "username": "user@example.com",
        "password": "p@ss:/?#[]",
        "db": "ollama_hack",
    }

    mysql = get_engine_schema(DatabaseConfig(engine=DatabaseEngine.MYSQL, **credentials))
    postgres = get_engine_schema(DatabaseConfig(engine=DatabaseEngine.POSTGRESQL, **credentials))
    sqlite_config = DatabaseConfig(engine=DatabaseEngine.SQLITE, db="/data/ollama-hack.db")
    sqlite = get_engine_schema(sqlite_config)

    assert mysql.drivername == "mysql+aiomysql"
    assert mysql.port == 3306
    assert mysql.username == credentials["username"]
    assert mysql.password == credentials["password"]
    assert postgres.drivername == "postgresql+asyncpg"
    assert postgres.port == 5432
    assert postgres.password == credentials["password"]
    assert sqlite.drivername == "sqlite+aiosqlite"
    assert sqlite.database == "/data/ollama-hack.db"
    assert "pool_size" not in get_engine_kwargs(sqlite_config)
    assert get_engine_kwargs(DatabaseConfig()).get("pool_size") == 5
    assert all(
        column.type.timezone
        for table in SQLModel.metadata.sorted_tables
        for column in table.columns
        if isinstance(column.type, DateTime)
    )
    paths = {route.path for route in ollama_router.routes}
    assert "/api/{proxy_path:path}" in paths
    assert "/v1/{proxy_path:path}" in paths


def test_sqlite_schema_indexes_pragmas_and_initial_settings(tmp_path):
    async def run():
        sqlite_config = DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            db=str(tmp_path / "ollama-hack.db"),
        )
        manager = DatabaseSessionManager(
            get_engine_schema(sqlite_config),
            get_engine_kwargs(sqlite_config),
        )
        original_manager = database.sessionmanager
        database.sessionmanager = manager
        try:
            await database.create_db_and_tables()
            await database.create_db_and_tables()

            async with manager.session() as session:
                await init_settings(session)
                settings = (await session.execute(select(SystemSettings))).scalars().all()
                assert settings

            async with manager.connect() as connection:
                foreign_keys = (
                    await connection.exec_driver_sql("PRAGMA foreign_keys")
                ).scalar_one()
                journal_mode = (
                    await connection.exec_driver_sql("PRAGMA journal_mode")
                ).scalar_one()

                def read_indexes(sync_connection):
                    inspector = inspect(sync_connection)
                    return {
                        index["name"]
                        for table in inspector.get_table_names()
                        for index in inspector.get_indexes(table)
                    }

                actual_indexes = await connection.run_sync(read_indexes)

            declared_indexes = {
                index.name
                for table in SQLModel.metadata.sorted_tables
                for index in table.indexes
                if index.name
            }
            assert foreign_keys == 1
            assert journal_mode == "wal"
            assert declared_indexes <= actual_indexes
        finally:
            database.sessionmanager = original_manager
            await manager.close()

    asyncio.run(run())


def test_sqlite_query_optimizations_use_fixed_query_counts(tmp_path):
    async def run():
        sqlite_config = DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            db=str(tmp_path / "query-counts.db"),
        )
        manager = DatabaseSessionManager(
            get_engine_schema(sqlite_config),
            get_engine_kwargs(sqlite_config),
        )
        original_manager = database.sessionmanager
        database.sessionmanager = manager
        try:
            await database.create_db_and_tables()
            async with manager.session() as session:
                endpoints = [
                    EndpointDB(
                        url="http://one.example",
                        name="one",
                        status=EndpointStatusEnum.AVAILABLE,
                    ),
                    EndpointDB(
                        url="http://two.example",
                        name="two",
                        status=EndpointStatusEnum.UNAVAILABLE,
                    ),
                ]
                models = [
                    AIModelDB(name="model-one", tag="latest"),
                    AIModelDB(name="model-two", tag="latest"),
                ]
                user = UserDB(username="admin", password="hash", is_admin=True)
                session.add_all([*endpoints, *models, user])
                await session.commit()
                for item in [*endpoints, *models, user]:
                    await session.refresh(item)

                session.add_all(
                    [
                        EndpointAIModelDB(
                            endpoint_id=endpoints[0].id,
                            ai_model_id=models[0].id,
                            status=AIModelStatusEnum.AVAILABLE,
                        ),
                        EndpointAIModelDB(
                            endpoint_id=endpoints[0].id,
                            ai_model_id=models[1].id,
                            status=AIModelStatusEnum.UNAVAILABLE,
                        ),
                        EndpointAIModelDB(
                            endpoint_id=endpoints[1].id,
                            ai_model_id=models[0].id,
                            status=AIModelStatusEnum.AVAILABLE,
                        ),
                        EndpointPerformanceDB(
                            endpoint_id=endpoints[0].id,
                            status=EndpointStatusEnum.AVAILABLE,
                        ),
                        EndpointTestTask(
                            endpoint_id=endpoints[0].id,
                            status=TaskStatus.DONE,
                        ),
                    ]
                )
                api_key = ApiKeyDB(key="test-key", name="test", user_id=user.id)
                session.add(api_key)
                await session.commit()
                await session.refresh(api_key)
                session.add_all(
                    [
                        ApiKeyUsageLogDB(
                            api_key_id=api_key.id,
                            endpoint="/v1/chat/completions",
                            method="POST",
                            status_code=200,
                        ),
                        ApiKeyUsageLogDB(
                            api_key_id=api_key.id,
                            endpoint="/v1/chat/completions",
                            method="POST",
                            status_code=500,
                            timestamp=now() - datetime.timedelta(days=1),
                        ),
                        ApiKeyUsageLogDB(
                            api_key_id=api_key.id,
                            endpoint="/v1/chat/completions",
                            method="POST",
                            status_code=200,
                            timestamp=now() - datetime.timedelta(days=31),
                        ),
                    ]
                )
                await session.commit()
                for item in [*models, user, api_key]:
                    await session.refresh(item)
                model_ids = [models[0].id, models[1].id]
                api_key_id = api_key.id

                statements = 0

                def count_statements(*_):
                    nonlocal statements
                    statements += 1

                event.listen(manager._engine.sync_engine, "before_cursor_execute", count_statements)
                page = await get_endpoints_with_ai_model_counts(
                    session,
                    EndpointFilterParams(page=1, size=10),
                )
                event.remove(
                    manager._engine.sync_engine,
                    "before_cursor_execute",
                    count_statements,
                )
                assert statements <= 5
                assert page.items[0].total_ai_model_count == 2
                assert page.items[0].avaliable_ai_model_count == 1
                assert page.items[0].task_status == TaskStatus.DONE

                statements = 0
                event.listen(manager._engine.sync_engine, "before_cursor_execute", count_statements)
                counts = await get_endpoint_counts(session, model_ids)
                event.remove(
                    manager._engine.sync_engine,
                    "before_cursor_execute",
                    count_statements,
                )
                assert statements == 1
                assert counts == {model_ids[0]: (2, 1), model_ids[1]: (1, 0)}

                statements = 0
                event.listen(manager._engine.sync_engine, "before_cursor_execute", count_statements)
                stats = await get_api_key_usage_stats(session, api_key_id, user)
                event.remove(
                    manager._engine.sync_engine,
                    "before_cursor_execute",
                    count_statements,
                )
                assert statements <= 4
                assert stats.total_requests == 3
                assert stats.last_30_days_requests == 2
                assert stats.requests_today == 1
                assert stats.successful_requests == 2
                assert stats.failed_requests == 1
                assert stats.requests_per_day[0]["count"] == 1
        finally:
            database.sessionmanager = original_manager
            await manager.close()

    asyncio.run(run())
