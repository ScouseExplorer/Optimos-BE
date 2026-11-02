from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OpinionCreate(BaseModel):
    topic: str
    opinion: str
    confidence: int | None = Field(default=None, ge=1, le=5)


class OpinionUpdate(BaseModel):
    topic: str | None = None
    opinion: str | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)


class OpinionResponse(BaseModel):
    id: int
    user_id: int
    topic: str
    opinion: str
    confidence: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
