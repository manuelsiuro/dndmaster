from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.db.models import TimelineEventType


class ConsentCreate(BaseModel):
    story_id: str
    consent_scope: str = Field(default="session_recording", max_length=64)


class ConsentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    story_id: str
    consent_scope: str
    accepted_at: datetime
    revoked_at: datetime | None


class VoiceRecordingCreate(BaseModel):
    audio_ref: str = Field(min_length=1, max_length=1024)
    duration_ms: int = Field(ge=1)
    codec: str = Field(default="audio/webm;codecs=opus", max_length=128)


class VoiceRecordingRead(BaseModel):
    id: str
    audio_ref: str
    duration_ms: int
    codec: str


class AudioUploadResponse(BaseModel):
    audio_ref: str
    bytes_size: int
    content_type: str


class TranscriptSegmentCreate(BaseModel):
    content: str = Field(min_length=1)
    language: str = Field(default="en", max_length=8)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    timestamp: datetime | None = None


class TranscriptSegmentRead(BaseModel):
    id: str
    language: str
    content: str
    confidence: float | None
    timestamp: datetime


class TimelineEventCreate(BaseModel):
    story_id: str
    event_type: TimelineEventType
    text_content: str | None = None
    language: str = Field(default="en", max_length=8)
    source_event_id: str | None = None
    metadata_json: dict[str, str | int | float | bool | None] = Field(default_factory=dict)
    audio: VoiceRecordingCreate | None = None
    transcript_segments: list[TranscriptSegmentCreate] = Field(default_factory=list)


class TimelineEventRead(BaseModel):
    id: str
    story_id: str
    actor_id: str | None
    event_type: TimelineEventType
    text_content: str | None
    language: str
    source_event_id: str | None
    metadata_json: dict[str, str | int | float | bool | None]
    created_at: datetime
    recording: VoiceRecordingRead | None
    transcript_segments: list[TranscriptSegmentRead]
