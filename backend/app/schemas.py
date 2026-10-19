import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.security import validate_url


class MonitorCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    url: str = Field(max_length=2048)
    interval_seconds: int = Field(default=30, ge=30, le=3600)
    timeout_seconds: float = Field(default=5, ge=0.1, le=120)
    expected_status: int = Field(default=200, ge=100, le=599)
    expected_body: str | None = Field(default=None, max_length=1000)
    failure_threshold: int = Field(default=2, ge=1, le=10)

    @field_validator("name", "url", mode="before")
    @classmethod
    def trim_identity(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("url")
    @classmethod
    def check_url(cls, value):
        validate_url(value)
        return value


class MonitorRead(MonitorCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    state: str
    last_checked_at: datetime | None
    last_status_code: int | None
    last_response_ms: float | None
    consecutive_failures: int
    config_version: int
    run_requested: bool
    is_running: bool


class VersionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config_version: int = Field(ge=1)


class MonitorUpdate(MonitorCreate, VersionRequest):
    pass


class GroupCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=120)
    monitor_ids: list[uuid.UUID] = Field(default_factory=list, max_length=500)
    recipients: list[Annotated[EmailStr, Field(max_length=254)]] = Field(
        default_factory=list, max_length=100
    )

    @field_validator("name", mode="before")
    @classmethod
    def trim_name(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("monitor_ids", "recipients")
    @classmethod
    def distinct(cls, values):
        return list(dict.fromkeys(values))


class GroupUpdate(GroupCreate, VersionRequest):
    pass


class GroupRead(GroupCreate):
    id: uuid.UUID
    config_version: int
    state: str


class ResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    checked_at: datetime
    success: bool
    status_code: int | None
    response_ms: float
    error: str | None
    config_version: int
