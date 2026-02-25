from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    type: str
    status: str
    idempotency_key: str
    created_at: datetime
    updated_at: datetime
