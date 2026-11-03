from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

MAX_TASK_FIELD_LENGTH = 255


class ApiSchema(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class Identity(ApiSchema):
    username: str = Field(min_length=1)
    role: str = Field(min_length=1)


class TaskCreateRequest(ApiSchema):
    title: str = Field(default="", max_length=MAX_TASK_FIELD_LENGTH)
    description: str = Field(default="", max_length=MAX_TASK_FIELD_LENGTH)
    status: str = Field(default="TODO", max_length=MAX_TASK_FIELD_LENGTH)
    priority: str = Field(default="MEDIUM", max_length=MAX_TASK_FIELD_LENGTH)
    owner: str | None = None


class TaskResponse(ApiSchema):
    id: int
    title: str
    description: str
    status: str
    owner: str
    priority: str
    created_at: str = Field(alias="createdAt")


class TaskSummaryResponse(ApiSchema):
    owner: str
    total: int
    by_status: dict[str, int] = Field(alias="byStatus")
    high_priority_open: int = Field(alias="highPriorityOpen")


class RequirementUploadResponse(ApiSchema):
    owner: str
    file_name: str = Field(alias="fileName")
    stored_at: str = Field(alias="storedAt")
    size: int


class BackendHealthResponse(ApiSchema):
    requested_by: str = Field(alias="requestedBy")
    status: int
    body: str
