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
    stories: Mapped[list["Story"]] = relationship(back_populates="owner")


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
Index(
    "ix_transcript_event_timestamp",
    TranscriptSegment.timeline_event_id,
    TranscriptSegment.timestamp,
)
