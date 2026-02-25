from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    query_embedding: list[float] | None = None
    query_text: str | None = None
    applied_memory_ids: list[str] = Field(default_factory=list)
    limit: int = Field(default=8, ge=1, le=20)
    memory_types: list[NarrativeMemoryType] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate_query_payload(self) -> "MemorySearchRequest":
        has_embedding = bool(self.query_embedding)
        has_text = bool((self.query_text or "").strip())
        if not has_embedding and not has_text:
            raise ValueError("query_embedding or query_text is required")
        return self


class MemorySearchResult(BaseModel):
    chunk: MemoryChunkRead
    similarity: float


class MemorySummaryGenerateRequest(BaseModel):
    story_id: str
    summary_window: str = Field(default="latest", min_length=1, max_length=64)
    max_events: int = Field(default=20, ge=1, le=100)


class MemorySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_id: str
    summary_window: str
    summary_text: str
    quality_score: float | None
    created_at: datetime


class RetrievalAuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_id: str
    query_text: str
    retrieved_memory_ids: list[str]
    applied_memory_ids: list[str]
    created_at: datetime
