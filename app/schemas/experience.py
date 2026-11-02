from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ExperienceCreate(BaseModel):
    title: str
    description: str
    category: str | None = None
    experience_date: datetime | None = None
    importance: int = Field(default=3, ge=1, le=5)


class ExperienceUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    category: str | None = None
    experience_date: datetime | None = None
    importance: int | None = Field(default=None, ge=1, le=5)


class ExperienceResponse(BaseModel):
    id: int
    user_id: int
    title: str
    description: str
    category: str | None = None
    experience_date: datetime | None = None
    importance: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
