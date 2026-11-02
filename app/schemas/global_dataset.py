from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class GlobalDatasetItemCreate(BaseModel):
    dataset_key: str = Field(min_length=1, max_length=100)
    item_key: str = Field(min_length=1, max_length=150)
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
    source: str | None = Field(default=None, max_length=255)
    priority: int = 0
    is_active: bool = True


class GlobalDatasetItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    source: str | None = Field(default=None, max_length=255)
    priority: int | None = None
    is_active: bool | None = None


class GlobalDatasetItemResponse(BaseModel):
    id: int
    dataset_key: str
    item_key: str
    title: str
    content: str
    tags: list[str]
    source: str | None = None
    priority: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
