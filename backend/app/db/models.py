import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class TimelineEventType(enum.StrEnum):
    gm_prompt = "gm_prompt"
    player_action = "player_action"
    choice_prompt = "choice_prompt"
    choice_selection = "choice_selection"
    outcome = "outcome"
    system = "system"


class SessionStatus(enum.StrEnum):
    lobby = "lobby"
    active = "active"
    ended = "ended"


class SessionParticipantRole(enum.StrEnum):
    host = "host"
    player = "player"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    credential: Mapped["AuthCredential"] = relationship(back_populates="user", uselist=False)
    settings: Mapped["UserSettings"] = relationship(back_populates="user", uselist=False)
    stories: Mapped[list["Story"]] = relationship(back_populates="owner")
    hosted_sessions: Mapped[list["GameSession"]] = relationship(back_populates="host")
    session_memberships: Mapped[list["SessionPlayer"]] = relationship(back_populates="user")


class AuthCredential(Base):
    __tablename__ = "auth_credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    password_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    password_algo: Mapped[str] = mapped_column(String(64), default="argon2id", nullable=False)
    password_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="credential")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    llm_provider: Mapped[str] = mapped_column(String(32), default="codex", nullable=False)
    llm_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    voice_mode: Mapped[str] = mapped_column(
        String(64),
        default="webrtc_with_fallback",
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="settings")


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    owner: Mapped[User] = relationship(back_populates="stories")
    sessions: Mapped[list["GameSession"]] = relationship(back_populates="story")


class GameSession(Base):
    __tablename__ = "game_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    host_user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, native_enum=False),
        default=SessionStatus.lobby,
        nullable=False,
    )
    max_players: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    story: Mapped[Story] = relationship(back_populates="sessions")
    host: Mapped[User] = relationship(back_populates="hosted_sessions")
    players: Mapped[list["SessionPlayer"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )
    join_tokens: Mapped[list["JoinToken"]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
    )


class SessionPlayer(Base):
    __tablename__ = "session_players"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_players_session_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    role: Mapped[SessionParticipantRole] = mapped_column(
        Enum(SessionParticipantRole, native_enum=False),
        default=SessionParticipantRole.player,
        nullable=False,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    kicked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[GameSession] = relationship(back_populates="players")
    user: Mapped[User] = relationship(back_populates="session_memberships")


class JoinToken(Base):
    __tablename__ = "join_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    session: Mapped[GameSession] = relationship(back_populates="join_tokens")


class SessionDeviceBinding(Base):
    __tablename__ = "session_device_bindings"
    __table_args__ = (
        UniqueConstraint("session_id", "user_id", name="uq_session_device_session_user"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        ForeignKey("game_sessions.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    device_fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)
    bound_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VoiceConsentRecord(Base):
    __tablename__ = "voice_consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    consent_scope: Mapped[str] = mapped_column(
        String(64),
        default="session_recording",
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class VoiceRecording(Base):
    __tablename__ = "voice_recordings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    speaker_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    audio_ref: Mapped[str] = mapped_column(String(1024), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    codec: Mapped[str] = mapped_column(
        String(128),
        default="audio/webm;codecs=opus",
        nullable=False,
    )
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )


class TimelineEvent(Base):
    __tablename__ = "interaction_timeline_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    actor_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    event_type: Mapped[TimelineEventType] = mapped_column(
        Enum(TimelineEventType, native_enum=False),
        nullable=False,
    )
    text_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    audio_recording_id: Mapped[str | None] = mapped_column(
        ForeignKey("voice_recordings.id", ondelete="SET NULL"),
        nullable=True,
    )
    source_event_id: Mapped[str | None] = mapped_column(
        ForeignKey("interaction_timeline_events.id", ondelete="SET NULL"),
        nullable=True,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    transcripts: Mapped[list["TranscriptSegment"]] = relationship(
        back_populates="timeline_event",
        cascade="all, delete-orphan",
    )
    recording: Mapped[VoiceRecording | None] = relationship()


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    timeline_event_id: Mapped[str] = mapped_column(
        ForeignKey("interaction_timeline_events.id", ondelete="CASCADE"),
        index=True,
    )
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    speaker_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    timeline_event: Mapped[TimelineEvent] = relationship(back_populates="transcripts")


Index("ix_timeline_story_created", TimelineEvent.story_id, TimelineEvent.created_at)
Index("ix_game_session_story_created", GameSession.story_id, GameSession.created_at)
Index("ix_game_session_status_created", GameSession.status, GameSession.created_at)
Index("ix_session_player_joined", SessionPlayer.session_id, SessionPlayer.joined_at)
Index("ix_join_token_expires", JoinToken.session_id, JoinToken.expires_at)
Index(
    "ix_transcript_event_timestamp",
    TranscriptSegment.timeline_event_id,
    TranscriptSegment.timestamp,
)
