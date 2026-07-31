import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError
from sqlalchemy import select

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.config import AppConfig, DatabaseConfig, DatabaseEngine
from src.database import DatabaseSessionManager, SQLModel, get_engine_kwargs, get_engine_schema
from src.endpoint import external_feed
from src.endpoint import scheduler as scheduler_module
from src.endpoint.models import EndpointDB
from src.endpoint.schemas import EndpointBatchCreate, EndpointCreate
from src.endpoint.service import batch_create_or_update_endpoints


async def create_sqlite_manager(path: Path) -> DatabaseSessionManager:
    config = DatabaseConfig(engine=DatabaseEngine.SQLITE, db=str(path))
    manager = DatabaseSessionManager(get_engine_schema(config), get_engine_kwargs(config))
    async with manager.connect() as connection:
        await connection.run_sync(SQLModel.metadata.create_all)
    return manager


class FakeScheduler:
    def __init__(self) -> None:
        self.endpoint_ids: list[int] = []

    async def schedule_endpoint_test(self, endpoint_id: int, *_args) -> None:
        self.endpoint_ids.append(endpoint_id)


def test_external_feed_config_and_scheduler_are_opt_in(monkeypatch):
    defaults = AppConfig()
    assert defaults.external_feed_enabled is False
    assert defaults.external_feed_interval_hours == 10
    assert defaults.external_feed_url.endswith("/public/data.json")
    assert AppConfig(
        external_feed_enabled=False,
        external_feed_interval_hours=0,
    ).external_feed_interval_hours == 0

    with pytest.raises(ValidationError):
        AppConfig(external_feed_enabled=True, external_feed_interval_hours=0)

    service = scheduler_module.SchedulerService()
    monkeypatch.setattr(
        scheduler_module,
        "get_config",
        lambda: SimpleNamespace(app=AppConfig(external_feed_enabled=False)),
    )
    service.schedule_external_feed_sync(immediate=True)
    assert service.scheduler.get_job("external_feed_sync") is None

    monkeypatch.setattr(
        scheduler_module,
        "get_config",
        lambda: SimpleNamespace(
            app=AppConfig(external_feed_enabled=True, external_feed_interval_hours=7)
        ),
    )
    service.schedule_external_feed_sync(immediate=True)
    service.schedule_external_feed_sync(immediate=True)
    job = service.scheduler.get_job("external_feed_sync")
    assert job is not None
    assert job.max_instances == 1
    assert job.trigger.interval.total_seconds() == 7 * 60 * 60
    assert len(service.scheduler.get_jobs()) == 1


def test_parse_external_feed_filters_normalizes_and_bounds_records():
    payload = [
        {"server": " https://public.example/ "},
        {"server": "https://public.example"},
        {"server": "http://8.8.8.8:11434/"},
        {"server": "ftp://public.example"},
        {"server": "http://user:pass@public.example"},
        {"server": "http://public.example?token=secret"},
        {"server": "http://public.example#fragment"},
        {"server": "http://localhost:11434"},
        {"server": "http://api.localhost"},
        {"server": "http://127.0.0.1:11434"},
        {"server": "http://127.1:11434"},
        {"server": "http://2130706433:11434"},
        {"server": "http://0x7f000001:11434"},
        {"server": "http://%31%32%37.0.0.1:11434"},
        {"server": "http://10.0.0.1"},
        {"server": "http://2852039166"},
        {"server": "http://224.0.0.1"},
        {"server": "http://[::1]:11434"},
        {"server": "http://[ff02::1]:11434"},
        {"server": "http://[fec0::1]:11434"},
        {"server": "http://public.example:not-a-port"},
        {"server": "http://public example"},
        {"models": ["ignored"]},
        "not-an-object",
    ]

    assert external_feed.parse_external_feed(payload) == [
        "https://public.example",
        "http://8.8.8.8:11434",
    ]

    with pytest.raises(ValueError, match="JSON array"):
        external_feed.parse_external_feed({"server": "https://public.example"})
    with pytest.raises(ValueError, match="record limit"):
        external_feed.parse_external_feed([{}] * (external_feed.MAX_RECORDS + 1))


def test_manual_batch_import_handles_existing_and_new_urls(tmp_path, monkeypatch):
    async def run():
        manager = await create_sqlite_manager(tmp_path / "manual.db")
        fake_scheduler = FakeScheduler()
        monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: fake_scheduler)
        try:
            async with manager.session() as session:
                existing = EndpointDB(url="http://existing.example", name="Custom name")
                session.add(existing)
                await session.commit()
                await session.refresh(existing)

                background_tasks = BackgroundTasks()
                await batch_create_or_update_endpoints(
                    session,
                    background_tasks,
                    EndpointBatchCreate(
                        endpoints=[
                            EndpointCreate(url=existing.url),
                            EndpointCreate(url="http://new.example"),
                            EndpointCreate(url="http://new.example"),
                        ]
                    ),
                )
                await background_tasks()

                endpoints = (await session.execute(select(EndpointDB))).scalars().all()
                assert {endpoint.url for endpoint in endpoints} == {
                    "http://existing.example",
                    "http://new.example",
                }
                assert next(
                    endpoint.name for endpoint in endpoints if endpoint.url == existing.url
                ) == "Custom name"
                assert set(fake_scheduler.endpoint_ids) == {
                    endpoint.id for endpoint in endpoints
                }
        finally:
            await manager.close()

    asyncio.run(run())


def test_external_feed_sync_is_add_only_and_schedules_only_new_urls(tmp_path, monkeypatch):
    async def run():
        manager = await create_sqlite_manager(tmp_path / "feed.db")
        fake_scheduler = FakeScheduler()

        async def download(_url: str) -> list[str]:
            return ["http://existing.example", "http://new.example"]

        monkeypatch.setattr(external_feed, "sessionmanager", manager)
        monkeypatch.setattr(external_feed, "download_external_feed", download)
        monkeypatch.setattr(scheduler_module, "get_scheduler", lambda: fake_scheduler)
        try:
            async with manager.session() as session:
                session.add(EndpointDB(url="http://existing.example", name="Custom name"))
                await session.commit()

            await external_feed.sync_external_feed()
            await external_feed.sync_external_feed()

            async with manager.session() as session:
                endpoints = (await session.execute(select(EndpointDB))).scalars().all()
                existing = next(
                    endpoint for endpoint in endpoints if endpoint.url == "http://existing.example"
                )
                new = next(
                    endpoint for endpoint in endpoints if endpoint.url == "http://new.example"
                )
                assert existing.name == "Custom name"
                assert fake_scheduler.endpoint_ids == [new.id]
                assert len(endpoints) == 2
        finally:
            await manager.close()

    asyncio.run(run())


def test_external_feed_sync_contains_download_failures(monkeypatch, caplog):
    async def fail(_url: str) -> list[str]:
        raise ValueError("malformed payload")

    monkeypatch.setattr(external_feed, "download_external_feed", fail)
    asyncio.run(external_feed.sync_external_feed())
    assert "External feed sync failed: malformed payload" in caplog.text
