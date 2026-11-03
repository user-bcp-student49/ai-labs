from __future__ import annotations

import os
from pathlib import Path, PurePosixPath, PureWindowsPath

import urllib3
from fastapi import HTTPException, UploadFile

from app.repository import TaskRepository
from app.schemas import (
    BackendHealthResponse,
    RequirementUploadResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskSummaryResponse,
)

ALLOWED_REQUIREMENT_EXTENSIONS = frozenset({".txt", ".md"})
MAX_REQUIREMENT_SIZE_BYTES = 1_048_576
UPLOAD_READ_CHUNK_BYTES = 64 * 1024
DEFAULT_AUTH_HEALTH_URL = "http://localhost:8080/q/health"
AUTH_HEALTH_TIMEOUT_SECONDS = 3.0


class TaskService:
    def __init__(self, repository: TaskRepository) -> None:
        self._repository = repository

    def list_tasks(self, owner: str) -> list[TaskResponse]:
        return [
            TaskResponse.model_validate(row)
            for row in self._repository.list_tasks(owner)
        ]

    def create_task(
        self,
        request: TaskCreateRequest,
        owner: str,
    ) -> TaskResponse:
        row = self._repository.create_task(
            title=request.title,
            description=request.description,
            status=request.status,
            owner=owner,
            priority=request.priority,
        )
        return TaskResponse.model_validate(row)

    def summary(self, owner: str) -> TaskSummaryResponse:
        rows = self._repository.task_summary_rows(owner)
        by_status: dict[str, int] = {}
        high_priority_open = 0

        for row in rows:
            status = row["status"]
            by_status[status] = by_status.get(status, 0) + 1
            if row["priority"] == "HIGH" and status not in {"DONE", "ARCHIVED"}:
                high_priority_open += 1

        return TaskSummaryResponse(
            owner=owner,
            total=len(rows),
            byStatus=by_status,
            highPriorityOpen=high_priority_open,
        )


class RequirementService:
    def __init__(self, upload_dir: Path) -> None:
        self._upload_dir = upload_dir

    async def save(
        self,
        upload: UploadFile,
        owner: str,
    ) -> RequirementUploadResponse:
        file_name = _normalize_file_name(upload.filename)
        _validate_file_extension(file_name)
        content = await _read_limited_content(upload)
        target = self._upload_dir / file_name
        resolved_upload_dir = self._upload_dir.resolve()
        resolved_target = target.resolve()
        if not resolved_target.is_relative_to(resolved_upload_dir):
            raise HTTPException(status_code=400, detail="Invalid file name")

        try:
            with target.open("xb") as destination:
                destination.write(content)
        except FileExistsError as error:
            raise HTTPException(
                status_code=409,
                detail="A file with this name already exists",
            ) from error

        return RequirementUploadResponse(
            owner=owner,
            fileName=file_name,
            storedAt=str(target),
            size=len(content),
        )


class BackendHealthService:
    def get_status(self, requested_by: str) -> BackendHealthResponse:
        url = os.getenv("AUTH_HEALTH_URL", DEFAULT_AUTH_HEALTH_URL)
        try:
            response = urllib3.PoolManager().request(
                "GET",
                url,
                timeout=AUTH_HEALTH_TIMEOUT_SECONDS,
            )
            body = response.data.decode("utf-8")
            return BackendHealthResponse(
                requestedBy=requested_by,
                status=response.status,
                body=body,
            )
        except Exception as error:
            return BackendHealthResponse(
                requestedBy=requested_by,
                status=0,
                body=str(error),
            )


def _normalize_file_name(filename: str | None) -> str:
    supplied_name = filename or ""
    windows_path = PureWindowsPath(supplied_name)
    if windows_path.drive and not windows_path.root:
        raise HTTPException(status_code=400, detail="Invalid file name")

    normalized_name = PurePosixPath(supplied_name.replace("\\", "/")).name
    if not normalized_name or normalized_name in {".", ".."}:
        raise HTTPException(status_code=400, detail="Invalid file name")
    return normalized_name


def _validate_file_extension(filename: str) -> None:
    extension = Path(filename).suffix.lower()
    if extension not in ALLOWED_REQUIREMENT_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file type")


async def _read_limited_content(upload: UploadFile) -> bytes:
    content = bytearray()

    while len(content) <= MAX_REQUIREMENT_SIZE_BYTES:
        remaining_capacity = MAX_REQUIREMENT_SIZE_BYTES + 1 - len(content)
        chunk_size = min(UPLOAD_READ_CHUNK_BYTES, remaining_capacity)
        chunk = await upload.read(chunk_size)
        if not chunk:
            break
        content.extend(chunk)
        if len(content) > MAX_REQUIREMENT_SIZE_BYTES:
            raise HTTPException(status_code=413, detail="Uploaded file is too large")

    return bytes(content)
