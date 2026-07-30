from contextlib import asynccontextmanager
from pathlib import Path

import bcrypt
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import Env, get_config
from .database import create_db_and_tables, sessionmanager
from .endpoint.scheduler import get_scheduler
from .logging import get_logger
from .routes import router
from .setting.service import init_settings

bcrypt.__about__ = bcrypt  # type: ignore


config = get_config()
logger = get_logger(__name__)

logger.debug(f"Config: {config}")

# no doc other than dev env
docs_url = "/docs" if config.app.env == Env.DEV else None


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting application...")

    # Initialize database
    await create_db_and_tables()

    # Initialize settings
    async with sessionmanager.session() as session:
        await init_settings(session)

    # Initialize and start scheduler
    scheduler = get_scheduler()
    await scheduler.start()
    logger.info("Application startup complete")

    yield

    # Shutdown scheduler
    scheduler = get_scheduler()
    await scheduler.shutdown()

    # Close database connections
    if sessionmanager._engine is not None:
        await sessionmanager.close()

    logger.info("Application shutdown complete")


app = FastAPI(
    lifespan=lifespan,
    docs_url=docs_url,
    redoc_url=None,
    title="Ollama Hack Backend",
    description="Ollama Hack Backend",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
frontend_dir = Path(__file__).resolve().parents[1] / "frontend"
app.include_router(router)

if frontend_dir.is_dir():
    assets_dir = frontend_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_frontend(full_path: str):
        if full_path == "api" or full_path.startswith(("api/", "v1/")):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        requested_file = (frontend_dir / full_path).resolve()
        if requested_file.is_relative_to(frontend_dir) and requested_file.is_file():
            return FileResponse(requested_file)
        return FileResponse(frontend_dir / "index.html")
else:

    @app.get("/")
    async def root():
        return {"message": "Hello World"}
