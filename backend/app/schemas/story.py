from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class StoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = None


class StoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    owner_user_id: str
    title: str
    description: str | None
    status: str
    created_at: datetime
