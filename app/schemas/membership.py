from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    email: str
    role: str


class MemberRoleUpdateIn(BaseModel):
    role: str = Field(pattern="^(owner|admin|member|viewer)$")
