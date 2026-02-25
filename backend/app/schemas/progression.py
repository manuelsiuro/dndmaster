from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProgressionEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    story_id: str | None
    awarded_by_user_id: str | None
    xp_delta: int
    reason: str | None
    created_at: datetime


class UserProgressionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    xp_total: int
    level: int
    updated_at: datetime
    recent_entries: list[ProgressionEntryRead] = Field(default_factory=list)


class StoryProgressionRead(BaseModel):
    user_id: str
    user_email: str
    xp_total: int
    level: int
    last_award_at: datetime | None = None


class ProgressionAwardRequest(BaseModel):
    story_id: str
    user_id: str
    xp_delta: int = Field(ge=1, le=100000)
    reason: str | None = Field(default=None, max_length=400)


class ProgressionAwardResponse(BaseModel):
    progression: StoryProgressionRead
    entry: ProgressionEntryRead
