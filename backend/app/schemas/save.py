from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.story import StoryRead


class StorySaveCreate(BaseModel):
    story_id: str
    label: str = Field(default="Checkpoint", min_length=1, max_length=120)


class StorySaveRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_id: str
    created_by_user_id: str | None
    label: str
    created_at: datetime
    timeline_event_count: int = 0
    session_count: int = 0


class StorySaveDetail(StorySaveRead):
    snapshot_json: dict[str, Any]


class StorySaveRestoreRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class StorySaveRestoreResponse(BaseModel):
    story: StoryRead
    timeline_events_restored: int
