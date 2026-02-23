from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DocumentCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list, max_length=10)


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    title: str
    body: str
    status: str
    tags: list[str]
    created_by: UUID
    updated_by: UUID
    created_at: datetime
    updated_at: datetime


class DocumentUpdateIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    body: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = Field(default=None, max_length=10)
