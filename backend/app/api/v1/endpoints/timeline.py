import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    GameSession,
    NarrativeMemoryType,
    SessionParticipantRole,
    SessionPlayer,
    Story,
    TimelineEvent,
    TimelineEventType,
    TranscriptSegment,
    VoiceConsentRecord,
    VoiceRecording,
)
from app.schemas.timeline import (
    AudioUploadResponse,
    ConsentCreate,
    ConsentRead,
    TimelineEventCreate,
    TimelineEventRead,
    TranscriptSegmentRead,
    VoiceRecordingRead,
)
from app.services.embedding import hash_text_embedding
from app.services.memory_store import create_memory_chunk

router = APIRouter(prefix="/timeline", tags=["timeline"])


def _memory_type_for_event(event_type: TimelineEventType) -> NarrativeMemoryType:
    if event_type in {TimelineEventType.choice_prompt, TimelineEventType.choice_selection}:
        return NarrativeMemoryType.quest
    if event_type == TimelineEventType.outcome:
        return NarrativeMemoryType.summary
    if event_type == TimelineEventType.system:
        return NarrativeMemoryType.rule
    return NarrativeMemoryType.fact


def _memory_source_text(payload: TimelineEventCreate) -> str:
    parts: list[str] = []
    if payload.text_content and payload.text_content.strip():
        parts.append(payload.text_content.strip())
    for segment in payload.transcript_segments:
        if segment.content.strip():
            parts.append(segment.content.strip())
    return "\n".join(parts).strip()


def _map_event(event: TimelineEvent) -> TimelineEventRead:
    turn_id_raw = event.metadata_json.get("turn_id")
    turn_id = (
        turn_id_raw.strip()
        if isinstance(turn_id_raw, str) and turn_id_raw.strip()
        else event.id
    )

    recording = None
    if event.recording is not None:
        recording = VoiceRecordingRead(
            id=event.recording.id,
            audio_ref=event.recording.audio_ref,
            duration_ms=event.recording.duration_ms,
            codec=event.recording.codec,
        )

    transcript_segments = [
        TranscriptSegmentRead(
            id=item.id,
            language=item.language,
            content=item.content,
            confidence=item.confidence,
            timestamp=item.timestamp,
        )
        for item in sorted(event.transcripts, key=lambda t: t.timestamp)
    ]

    return TimelineEventRead(
        id=event.id,
        turn_id=turn_id,
        story_id=event.story_id,
        actor_id=event.actor_id,
        event_type=event.event_type,
        text_content=event.text_content,
        language=event.language,
        source_event_id=event.source_event_id,
        metadata_json=event.metadata_json,
        created_at=event.created_at,
        recording=recording,
        transcript_segments=transcript_segments,
    )


async def _assert_story_access(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(select(Story).where(Story.id == story_id))
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    if story.owner_user_id == current_user.id:
        return story

    membership_id = await db.scalar(
        select(SessionPlayer.id)
        .join(GameSession, SessionPlayer.session_id == GameSession.id)
        .where(
            GameSession.story_id == story_id,
            SessionPlayer.user_id == current_user.id,
            SessionPlayer.kicked_at.is_(None),
        )
        .limit(1)
    )
    if membership_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")

    return story


async def _assert_story_compose_access(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> Story:
    story = await _assert_story_access(story_id, current_user, db)
    if story.owner_user_id == current_user.id:
        return story

    host_membership_id = await db.scalar(
        select(SessionPlayer.id)
        .join(GameSession, SessionPlayer.session_id == GameSession.id)
        .where(
            GameSession.story_id == story_id,
            SessionPlayer.user_id == current_user.id,
            SessionPlayer.role == SessionParticipantRole.host,
            SessionPlayer.kicked_at.is_(None),
        )
        .limit(1)
    )
    if host_membership_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Host access required for timeline composition",
        )

    return story


def _audio_extension(upload: UploadFile) -> str:
    filename = upload.filename or ""
    ext = Path(filename).suffix
    if ext:
        return ext
    if upload.content_type == "audio/webm":
        return ".webm"
    if upload.content_type == "audio/ogg":
        return ".ogg"
    if upload.content_type == "audio/wav":
        return ".wav"
    if upload.content_type == "audio/mpeg":
        return ".mp3"
    return ".bin"


@router.post(
    "/audio-upload",
    response_model=AudioUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_audio(
    request: Request,
    current_user: CurrentUser,
    db: DBSession,
    story_id: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
) -> AudioUploadResponse:
    await _assert_story_access(story_id, current_user, db)
    if not (file.content_type or "").startswith("audio/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Audio file is required",
        )

    settings = request.app.state.settings
    media_root = Path(settings.media_root)
    target_dir = media_root / "timeline-audio" / story_id
    target_dir.mkdir(parents=True, exist_ok=True)

    extension = _audio_extension(file)
    filename = f"{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(8)}{extension}"
    target_path = target_dir / filename

    written = 0
    try:
        with target_path.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                written += len(chunk)
                if written > settings.max_audio_upload_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail="Audio file too large",
                    )
                output.write(chunk)
    except HTTPException:
        if target_path.exists():
            target_path.unlink(missing_ok=True)
        raise
    finally:
        await file.close()

    relative_path = target_path.relative_to(media_root).as_posix()
    prefix = settings.media_url_prefix.strip("/")
    audio_ref = f"{str(request.base_url).rstrip('/')}/{prefix}/{relative_path}"
    return AudioUploadResponse(
        audio_ref=audio_ref,
        bytes_size=written,
        content_type=file.content_type or "application/octet-stream",
    )


@router.post("/consents", response_model=ConsentRead, status_code=status.HTTP_201_CREATED)
async def grant_voice_consent(
    payload: ConsentCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> ConsentRead:
    await _assert_story_access(payload.story_id, current_user, db)

    consent = VoiceConsentRecord(
        user_id=current_user.id,
        story_id=payload.story_id,
        consent_scope=payload.consent_scope,
    )
    db.add(consent)
    await db.commit()
    await db.refresh(consent)

    return ConsentRead.model_validate(consent)


@router.post("/events", response_model=TimelineEventRead, status_code=status.HTTP_201_CREATED)
async def create_event(
    request: Request,
    payload: TimelineEventCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> TimelineEventRead:
    await _assert_story_compose_access(payload.story_id, current_user, db)

    recording: VoiceRecording | None = None

    if payload.audio is not None:
        consent = await db.scalar(
            select(VoiceConsentRecord)
            .where(
                VoiceConsentRecord.story_id == payload.story_id,
                VoiceConsentRecord.user_id == current_user.id,
                VoiceConsentRecord.revoked_at.is_(None),
            )
            .order_by(VoiceConsentRecord.accepted_at.desc())
        )
        if consent is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Recording consent required before voice capture",
            )

        recording = VoiceRecording(
            story_id=payload.story_id,
            speaker_id=current_user.id,
            audio_ref=payload.audio.audio_ref,
            duration_ms=payload.audio.duration_ms,
            codec=payload.audio.codec,
        )
        db.add(recording)
        await db.flush()

    event = TimelineEvent(
        story_id=payload.story_id,
        actor_id=current_user.id,
        event_type=payload.event_type,
        text_content=payload.text_content,
        language=payload.language,
        source_event_id=payload.source_event_id,
        metadata_json=payload.metadata_json,
        audio_recording_id=recording.id if recording is not None else None,
    )
    db.add(event)
    await db.flush()

    for segment in payload.transcript_segments:
        transcript = TranscriptSegment(
            timeline_event_id=event.id,
            story_id=payload.story_id,
            speaker_id=current_user.id,
            language=segment.language,
            content=segment.content,
            confidence=segment.confidence,
            timestamp=segment.timestamp or datetime.now(UTC),
        )
        db.add(transcript)

    settings = request.app.state.settings
    memory_text = _memory_source_text(payload)
    if settings.memory_auto_ingest_timeline and memory_text:
        memory_embedding = hash_text_embedding(memory_text, settings.memory_embedding_dimensions)
        await create_memory_chunk(
            db,
            story_id=payload.story_id,
            memory_type=_memory_type_for_event(payload.event_type),
            content=memory_text,
            embedding=memory_embedding,
            source_event_id=event.id,
            metadata_json={
                "event_type": payload.event_type.value,
                "language": payload.language,
            },
            commit=False,
        )

    await db.commit()

    loaded_event = await db.scalar(
        select(TimelineEvent)
        .where(TimelineEvent.id == event.id)
        .options(
            selectinload(TimelineEvent.transcripts),
            selectinload(TimelineEvent.recording),
        )
    )
    if loaded_event is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Event not found",
        )

    return _map_event(loaded_event)


@router.get("/events", response_model=list[TimelineEventRead])
async def list_events(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TimelineEventRead]:
    await _assert_story_access(story_id, current_user, db)

    events = await db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.story_id == story_id)
        .options(
            selectinload(TimelineEvent.transcripts),
            selectinload(TimelineEvent.recording),
        )
        .order_by(TimelineEvent.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    return [_map_event(item) for item in events.all()]
