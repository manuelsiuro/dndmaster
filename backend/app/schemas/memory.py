from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import NarrativeMemoryType


class MemoryChunkCreate(BaseModel):
    story_id: str
    memory_type: NarrativeMemoryType = NarrativeMemoryType.fact
    content: str = Field(min_length=1)
    embedding: list[float] = Field(min_length=1)
    source_event_id: str | None = None
    metadata_json: dict[str, str | int | float | bool | None] = Field(default_factory=dict)


class MemoryChunkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_id: str
    memory_type: NarrativeMemoryType
    content: str
    embedding: list[float]
    source_event_id: str | None
    metadata_json: dict[str, str | int | float | bool | None]
    created_at: datetime
    updated_at: datetime


class MemorySearchRequest(BaseModel):
    story_id: str
    query_embedding: list[float] = Field(min_length=1)
    limit: int = Field(default=8, ge=1, le=20)
    memory_types: list[NarrativeMemoryType] = Field(default_factory=list)


class MemorySearchResult(BaseModel):
    chunk: MemoryChunkRead
    similarity: float
