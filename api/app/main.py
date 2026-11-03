from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import os
import sqlite3
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.repository import TaskRepository
from app.routes import create_router
from app.services import BackendHealthService, RequirementService, TaskService


def create_app(db_path: str | None = None, upload_dir: str | None = None) -> FastAPI:
    selected_db = db_path or os.getenv("WORKSHOP_DB_PATH", "./data/workshop.db")
    selected_uploads = upload_dir or os.getenv("WORKSHOP_UPLOAD_DIR", "./uploads")
    Path(selected_db).parent.mkdir(parents=True, exist_ok=True)
    upload_directory = Path(selected_uploads)
    upload_directory.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(selected_db, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    repository = TaskRepository(connection)
    repository.initialize()
    task_service = TaskService(repository)
    requirement_service = RequirementService(upload_directory)
    backend_health_service = BackendHealthService()

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            repository.close()

    app = FastAPI(
        title="Workshop Requirements API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.connection = connection
    app.state.upload_dir = selected_uploads
    app.include_router(
        create_router(
            task_service,
            requirement_service,
            backend_health_service,
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    return app


app = create_app()
