from datetime import datetime

from pydantic import BaseModel, Field

from app.db.models import SessionParticipantRole, SessionStatus


class SessionCreateRequest(BaseModel):
    story_id: str
    max_players: int = Field(default=4, ge=1, le=4)


class SessionPlayerRead(BaseModel):
    user_id: str
    user_email: str
    role: SessionParticipantRole
    joined_at: datetime


class SessionRead(BaseModel):
    id: str
    story_id: str
    host_user_id: str
    status: SessionStatus
    max_players: int
    created_at: datetime
    started_at: datetime | None
    ended_at: datetime | None
    active_join_token_expires_at: datetime | None
    players: list[SessionPlayerRead]


class SessionStartRequest(BaseModel):
    token_ttl_minutes: int = Field(default=15, ge=1, le=120)


class SessionStartResponse(BaseModel):
    session: SessionRead
    join_token: str
    join_url: str
    expires_at: datetime


class JoinSessionRequest(BaseModel):
    join_token: str = Field(min_length=8, max_length=256)
    device_fingerprint: str = Field(min_length=4, max_length=128)


class KickPlayerRequest(BaseModel):
    user_id: str
