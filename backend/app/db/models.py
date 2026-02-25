import enum
import uuid
from datetime import UTC, datetime
from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
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


MEMORY_VECTOR_DIMENSIONS = 1536


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


class NarrativeMemoryType(enum.StrEnum):
    summary = "summary"
    fact = "fact"
    quest = "quest"
    npc = "npc"
    location = "location"
    rule = "rule"


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
    tts_settings: Mapped["UserTtsSettings"] = relationship(back_populates="user", uselist=False)
    progression: Mapped["UserProgression"] = relationship(back_populates="user", uselist=False)
    progression_entries: Mapped[list["ProgressionEntry"]] = relationship(
        back_populates="user",
        foreign_keys="ProgressionEntry.user_id",
    )
    progression_awards_issued: Mapped[list["ProgressionEntry"]] = relationship(
        back_populates="awarded_by",
        foreign_keys="ProgressionEntry.awarded_by_user_id",
    )
    stories: Mapped[list["Story"]] = relationship(back_populates="owner")
    story_saves: Mapped[list["StorySave"]] = relationship(back_populates="created_by")
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


class UserTtsSettings(Base):
    __tablename__ = "user_tts_settings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    tts_provider: Mapped[str] = mapped_column(String(32), default="codex", nullable=False)
    tts_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tts_voice: Mapped[str] = mapped_column(String(64), default="alloy", nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="tts_settings")


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
    progression_entries: Mapped[list["ProgressionEntry"]] = relationship(back_populates="story")
    saves: Mapped[list["StorySave"]] = relationship(
        back_populates="story",
        cascade="all, delete-orphan",
    )


class UserProgression(Base):
    __tablename__ = "user_progressions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    xp_total: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(back_populates="progression")


class ProgressionEntry(Base):
    __tablename__ = "progression_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    story_id: Mapped[str | None] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    awarded_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        index=True,
        nullable=True,
    )
    xp_delta: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    user: Mapped[User] = relationship(
        back_populates="progression_entries",
        foreign_keys=[user_id],
    )
    story: Mapped[Story | None] = relationship(back_populates="progression_entries")
    awarded_by: Mapped[User | None] = relationship(
        back_populates="progression_awards_issued",
        foreign_keys=[awarded_by_user_id],
    )


class NarrativeMemoryChunk(Base):
    __tablename__ = "narrative_memory_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    memory_type: Mapped[NarrativeMemoryType] = mapped_column(
        Enum(NarrativeMemoryType, native_enum=False),
        default=NarrativeMemoryType.fact,
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(MEMORY_VECTOR_DIMENSIONS), nullable=False)
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
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        onupdate=_now,
        nullable=False,
    )


class NarrativeSummary(Base):
    __tablename__ = "narrative_summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    summary_window: Mapped[str] = mapped_column(String(64), nullable=False)
    summary_text: Mapped[str] = mapped_column(Text, nullable=False)
    quality_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )


class RetrievalAuditEvent(Base):
    __tablename__ = "retrieval_audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    retrieved_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    applied_memory_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )


class StorySave(Base):
    __tablename__ = "story_saves"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"),
        index=True,
    )
    created_by_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    label: Mapped[str] = mapped_column(String(120), default="Checkpoint", nullable=False)
    snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=_now,
        nullable=False,
    )

    story: Mapped[Story] = relationship(back_populates="saves")
    created_by: Mapped[User | None] = relationship(back_populates="story_saves")


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
Index("ix_progression_entry_user_created", ProgressionEntry.user_id, ProgressionEntry.created_at)
Index(
    "ix_memory_chunk_story_type_created",
    NarrativeMemoryChunk.story_id,
    NarrativeMemoryChunk.memory_type,
    NarrativeMemoryChunk.created_at,
)
Index("ix_memory_summary_story_created", NarrativeSummary.story_id, NarrativeSummary.created_at)
Index(
    "ix_retrieval_audit_story_created",
    RetrievalAuditEvent.story_id,
    RetrievalAuditEvent.created_at,
)
Index("ix_story_saves_story_created", StorySave.story_id, StorySave.created_at)
Index("ix_session_player_joined", SessionPlayer.session_id, SessionPlayer.joined_at)
Index("ix_join_token_expires", JoinToken.session_id, JoinToken.expires_at)
Index(
    "ix_transcript_event_timestamp",
    TranscriptSegment.timeline_event_id,
    TranscriptSegment.timestamp,
)
