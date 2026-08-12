import asyncio
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi_pagination import Params
from sqlalchemy import event
from starlette.requests import Request

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.ai_model.models import AIModelDB, AIModelStatusEnum, EndpointAIModelDB
from src.ai_model.schemas import AIModelFilterParams
from src.ai_model.service import (
    get_ai_models,
    get_endpoint_counts,
    get_endpoint_links_by_ai_model_id,
)
from src.config import DatabaseConfig, DatabaseEngine
from src.database import DatabaseSessionManager, SQLModel, get_engine_kwargs, get_engine_schema
from src.endpoint.models import EndpointDB, EndpointStatusEnum
from src.endpoint.schemas import EndpointFilterParams
from src.endpoint.service import (
    get_ai_model_links_by_endpoint_id,
    get_best_endpoints_for_model,
    get_endpoints,
)
from src.ollama import services as ollama_services
from src.ollama.services import RequestInfo, request_forwarding, send_request_to_endpoints


def test_main_imports_in_fresh_process(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE__ENGINE", "sqlite")
    monkeypatch.setenv("DATABASE__DB", str(tmp_path / "import.db"))
    result = subprocess.run(
        [sys.executable, "-c", "import src.main"],
        cwd=Path(__file__).parents[1],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_sqlite_availability_filters_and_tps_priority(tmp_path):
    async def run():
        config = DatabaseConfig(
            engine=DatabaseEngine.SQLITE,
            db=str(tmp_path / "availability.db"),
        )
        manager = DatabaseSessionManager(get_engine_schema(config), get_engine_kwargs(config))
        try:
            async with manager.connect() as connection:
                await connection.run_sync(SQLModel.metadata.create_all)

            async with manager.session() as session:

                def endpoint(
                    name: str,
                    status: EndpointStatusEnum = EndpointStatusEnum.AVAILABLE,
                ) -> EndpointDB:
                    return EndpointDB(url=f"http://{name}.example", name=name, status=status)

                primary = endpoint("primary")
                secondary = endpoint("secondary")
                down = endpoint("down", EndpointStatusEnum.UNAVAILABLE)
                fake = endpoint("fake", EndpointStatusEnum.FAKE)
                routing_endpoints = [endpoint(f"route-{tps}") for tps in range(1, 13)]
                endpoints = [primary, secondary, down, fake, *routing_endpoints]

                def model(name: str) -> AIModelDB:
                    return AIModelDB(name=name, tag="latest")

                routable = model("routable")
                stale = model("stale")
                offline = model("offline")
                secondary_model = model("secondary-model")
                routing_model = model("routing")
                models = [routable, stale, offline, secondary_model, routing_model]
                session.add_all([*endpoints, *models])
                await session.commit()
                for item in [*endpoints, *models]:
                    await session.refresh(item)

                def link(
                    endpoint: EndpointDB,
                    model: AIModelDB,
                    tps: float,
                    status: AIModelStatusEnum = AIModelStatusEnum.AVAILABLE,
                ) -> EndpointAIModelDB:
                    return EndpointAIModelDB(
                        endpoint_id=endpoint.id,
                        ai_model_id=model.id,
                        status=status,
                        token_per_second=tps,
                    )

                links = [
                    link(primary, routable, 30),
                    link(secondary, routable, 20),
                    link(down, routable, 200),
                    link(fake, routable, 300, AIModelStatusEnum.UNAVAILABLE),
                    link(down, stale, 900, AIModelStatusEnum.UNAVAILABLE),
                    link(primary, stale, 500, AIModelStatusEnum.UNAVAILABLE),
                    link(primary, offline, 400, AIModelStatusEnum.UNAVAILABLE),
                    link(primary, secondary_model, 10),
                    link(primary, routing_model, 1000, AIModelStatusEnum.UNAVAILABLE),
                    link(down, routing_model, 999),
                    *[
                        link(endpoint, routing_model, tps)
                        for tps, endpoint in enumerate(routing_endpoints, 1)
                    ],
                ]
                session.add_all(links)
                await session.commit()

                all_endpoints = await get_endpoints(session, EndpointFilterParams(page=1, size=100))
                available_endpoints = await get_endpoints(
                    session,
                    EndpointFilterParams(is_available=True, page=1, size=100),
                )
                unavailable_endpoints = await get_endpoints(
                    session,
                    EndpointFilterParams(is_available=False, page=1, size=100),
                )
                assert {endpoint.id for endpoint in all_endpoints.items} == {
                    endpoint.id for endpoint in endpoints
                }
                assert {endpoint.id for endpoint in available_endpoints.items} == {
                    endpoint.id
                    for endpoint in endpoints
                    if endpoint.status == EndpointStatusEnum.AVAILABLE
                }
                assert {endpoint.id for endpoint in unavailable_endpoints.items} == {
                    down.id,
                    fake.id,
                }
                contradictory = await get_endpoints(
                    session,
                    EndpointFilterParams(
                        status=EndpointStatusEnum.FAKE,
                        is_available=True,
                        page=1,
                        size=100,
                    ),
                )
                assert contradictory.items == []

                all_models = await get_ai_models(session, AIModelFilterParams(page=1, size=100))
                available_models = await get_ai_models(
                    session,
                    AIModelFilterParams(is_available=True, page=1, size=100),
                )
                unavailable_models = await get_ai_models(
                    session,
                    AIModelFilterParams(is_available=False, page=1, size=100),
                )
                assert {model.id for model in all_models.items} == {model.id for model in models}
                assert {model.id for model in available_models.items} == {
                    routable.id,
                    secondary_model.id,
                    routing_model.id,
                }
                assert {model.id for model in unavailable_models.items} == {
                    stale.id,
                    offline.id,
                }

                assert await get_endpoint_counts(session, [routable.id, stale.id]) == {
                    routable.id: (4, 2),
                    stale.id: (2, 0),
                }

                endpoint_links = await get_ai_model_links_by_endpoint_id(
                    session, primary.id, Params(page=1, size=100)
                )
                assert [
                    (link.ai_model.name, link.token_per_second) for link in endpoint_links.items
                ] == [
                    ("routable", 30),
                    ("secondary-model", 10),
                    ("routing", 1000),
                    ("stale", 500),
                    ("offline", 400),
                ]

                down_links = await get_ai_model_links_by_endpoint_id(
                    session, down.id, Params(page=1, size=100)
                )
                assert [
                    (link.ai_model.name, link.token_per_second) for link in down_links.items
                ] == [
                    ("routing", 999),
                    ("stale", 900),
                    ("routable", 200),
                ]

                model_links = await get_endpoint_links_by_ai_model_id(
                    session, routable.id, Params(page=1, size=100)
                )
                assert [link.endpoint_id for link in model_links.items] == [
                    primary.id,
                    secondary.id,
                    fake.id,
                    down.id,
                ]

                statements = []

                def capture_statement(_conn, _cursor, statement, *_args):
                    statements.append(statement)

                event.listen(
                    manager._engine.sync_engine,
                    "before_cursor_execute",
                    capture_statement,
                )
                best_endpoints = await get_best_endpoints_for_model(session, routing_model.id)
                event.remove(
                    manager._engine.sync_engine,
                    "before_cursor_execute",
                    capture_statement,
                )
                assert [endpoint.name for endpoint in best_endpoints] == [
                    f"route-{tps}" for tps in range(12, 2, -1)
                ]
                assert len(statements) == 1
                assert "LIMIT" in statements[0].upper()

                def request(path: str) -> Request:
                    return Request(
                        {
                            "type": "http",
                            "method": "GET",
                            "path": path,
                            "headers": [],
                            "query_string": b"",
                            "server": ("testserver", 80),
                            "scheme": "http",
                        }
                    )

                expected_models = {
                    "routable:latest",
                    "secondary-model:latest",
                    "routing:latest",
                }
                tags_response = await request_forwarding(request("/api/tags"), session)
                models_response = await request_forwarding(request("/v1/models"), session)
                assert {
                    model["model"] for model in json.loads(tags_response.body)["models"]
                } == expected_models
                assert {
                    model["id"] for model in json.loads(models_response.body)["data"]
                } == expected_models
        finally:
            await manager.close()

    asyncio.run(run())


def test_request_forwarding_keeps_sequential_failover(monkeypatch):
    async def run():
        attempts = []

        class FakeClient:
            def __init__(self, url: str):
                self.url = url

            def connect(self):
                return self

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

            async def _request(self, *_args, **_kwargs):
                attempts.append(self.url)
                if "first" in self.url:
                    raise ConnectionError("first endpoint failed")
                return "ok"

        monkeypatch.setattr(ollama_services, "OllamaClient", FakeClient)
        endpoints = [
            EndpointDB(url=f"http://{name}.example", name=name)
            for name in ("first", "second", "third")
        ]
        response = await send_request_to_endpoints(
            RequestInfo(
                full_path="api/chat",
                method="POST",
                request={"model": "model:latest", "stream": False},
                headers={},
                params={},
                model_name="model",
                model_tag="latest",
                stream=False,
            ),
            None,
            SimpleNamespace(id=None),
            endpoints,
        )
        assert response.body == b"ok"
        assert attempts == ["http://first.example", "http://second.example"]

    asyncio.run(run())
