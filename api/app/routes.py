from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile

from app.schemas import (
    BackendHealthResponse,
    Identity,
    RequirementUploadResponse,
    TaskCreateRequest,
    TaskResponse,
    TaskSummaryResponse,
)
from app.security import get_identity
from app.services import (
    BackendHealthService,
    RequirementService,
    TaskService,
)


def create_router(
    task_service: TaskService,
    requirement_service: RequirementService,
    backend_health_service: BackendHealthService,
) -> APIRouter:
    router = APIRouter()

    @router.get("/api/tasks", response_model=list[TaskResponse])
    def list_tasks(
        owner: str | None = Query(default=None),
        identity: Identity = Depends(get_identity),
    ) -> list[TaskResponse]:
        requested_owner = _authorized_owner(owner, identity)
        return task_service.list_tasks(requested_owner)

    @router.post(
        "/api/tasks",
        status_code=201,
        response_model=TaskResponse,
    )
    def create_task(
        payload: TaskCreateRequest,
        identity: Identity = Depends(get_identity),
    ) -> TaskResponse:
        _authorized_owner(payload.owner, identity)
        return task_service.create_task(payload, identity.username)

    @router.get("/api/summary", response_model=TaskSummaryResponse)
    def summary(
        owner: str | None = Query(default=None),
        identity: Identity = Depends(get_identity),
    ) -> TaskSummaryResponse:
        requested_owner = _authorized_owner(owner, identity)
        return task_service.summary(requested_owner)

    @router.post(
        "/api/requirements",
        status_code=201,
        response_model=RequirementUploadResponse,
    )
    async def upload_requirement(
        file: UploadFile = File(...),
        identity: Identity = Depends(get_identity),
    ) -> RequirementUploadResponse:
        try:
            return await requirement_service.save(file, identity.username)
        finally:
            await file.close()

    @router.get("/api/backend-health", response_model=BackendHealthResponse)
    def backend_health(
        identity: Identity = Depends(get_identity),
    ) -> BackendHealthResponse:
        return backend_health_service.get_status(identity.username)

    return router


def _authorized_owner(owner: str | None, identity: Identity) -> str:
    if owner is None or owner == "":
        return identity.username
    if owner != identity.username:
        raise HTTPException(status_code=403, detail="Owner does not match identity")
    return identity.username
