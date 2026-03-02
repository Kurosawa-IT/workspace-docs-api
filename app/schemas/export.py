from pydantic import BaseModel, Field


class ExportStartIn(BaseModel):
    format: str = Field(default="json", pattern="^(json|csv)$")
