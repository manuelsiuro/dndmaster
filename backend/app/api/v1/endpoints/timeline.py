from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    Story,
    TimelineEvent,
    TranscriptSegment,
    VoiceConsentRecord,
    VoiceRecording,
)
from app.schemas.timeline import (
    ConsentCreate,
    ConsentRead,
    TimelineEventCreate,
    TimelineEventRead,
    TranscriptSegmentRead,
    VoiceRecordingRead,
)

router = APIRouter(prefix="/timeline", tags=["timeline"])


def _map_event(event: TimelineEvent) -> TimelineEventRead:
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
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


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
    payload: TimelineEventCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> TimelineEventRead:
    await _assert_story_access(payload.story_id, current_user, db)

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
