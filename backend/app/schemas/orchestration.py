from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import NarrativeMemoryType, TimelineEventType


class OrchestrationContextRequest(BaseModel):
    story_id: str
    query_text: str = Field(min_length=1, max_length=4000)
    language: str = Field(default="en", min_length=2, max_length=8)
    memory_limit: int = Field(default=8, ge=1, le=20)
    summary_limit: int = Field(default=3, ge=0, le=10)
    timeline_limit: int = Field(default=12, ge=0, le=30)
    memory_types: list[NarrativeMemoryType] = Field(default_factory=list)


class OrchestrationMemoryItem(BaseModel):
    id: str
    memory_type: NarrativeMemoryType
    content: str
    similarity: float
    source_event_id: str | None
    metadata_json: dict[str, str | int | float | bool | None]
    created_at: datetime


class OrchestrationSummaryItem(BaseModel):
    id: str
    summary_window: str
    summary_text: str
    quality_score: float | None
    created_at: datetime


class OrchestrationTimelineItem(BaseModel):
    id: str
    event_type: TimelineEventType
    text_content: str | None
    language: str | None
    created_at: datetime


class OrchestrationContextRead(BaseModel):
    story_id: str
    query_text: str
    language: str
    assembled_at: datetime
    prompt_context: str
    retrieval_audit_id: str
    retrieved_memory: list[OrchestrationMemoryItem]
    summaries: list[OrchestrationSummaryItem]
    recent_events: list[OrchestrationTimelineItem]


class OrchestrationRespondRequest(BaseModel):
    story_id: str
    player_input: str = Field(min_length=1, max_length=4000)
    language: str | None = Field(default=None, min_length=2, max_length=8)
    source_event_id: str | None = Field(default=None, min_length=1, max_length=36)
    turn_id: str | None = Field(default=None, min_length=1, max_length=96)
    memory_limit: int = Field(default=8, ge=1, le=20)
    summary_limit: int = Field(default=3, ge=0, le=10)
    timeline_limit: int = Field(default=12, ge=0, le=30)
    memory_types: list[NarrativeMemoryType] = Field(default_factory=list)
    persist_to_timeline: bool = True
    synthesize_audio: bool = True


class OrchestrationRespondRead(BaseModel):
    story_id: str
    provider: str
    model: str
    language: str
    response_text: str
    timeline_event_id: str | None
    source_event_id: str | None
    turn_id: str | None
    audio_provider: str | None
    audio_model: str | None
    audio_ref: str | None
    audio_duration_ms: int | None
    audio_codec: str | None
    context: OrchestrationContextRead
