from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    CharacterCreationMode,
    CharacterSheet,
    GameSession,
    SessionPlayer,
    Story,
    StorySave,
    TimelineEvent,
    TimelineEventType,
    TranscriptSegment,
    VoiceRecording,
)
from app.schemas.save import (
    StorySaveCreate,
    StorySaveDetail,
    StorySaveRead,
    StorySaveRestoreRequest,
    StorySaveRestoreResponse,
)
from app.schemas.story import StoryRead

router = APIRouter(prefix="/saves", tags=["saves"])


def _save_counts(snapshot: dict[str, Any]) -> tuple[int, int]:
    timeline_events = snapshot.get("timeline_events", [])
    sessions = snapshot.get("sessions", [])
    return len(timeline_events), len(sessions)


def _map_save(item: StorySave) -> StorySaveRead:
    timeline_event_count, session_count = _save_counts(item.snapshot_json)
    return StorySaveRead(
        id=item.id,
        story_id=item.story_id,
        created_by_user_id=item.created_by_user_id,
        label=item.label,
        created_at=item.created_at,
        timeline_event_count=timeline_event_count,
        session_count=session_count,
    )


def _safe_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.isoformat()


async def _assert_story_owner(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


async def _load_save(save_id: str, db: DBSession) -> StorySave | None:
    return await db.scalar(select(StorySave).where(StorySave.id == save_id))


async def _build_snapshot(story: Story, db: DBSession) -> dict[str, Any]:
    timeline_events = await db.scalars(
        select(TimelineEvent)
        .where(TimelineEvent.story_id == story.id)
        .options(
            selectinload(TimelineEvent.transcripts),
            selectinload(TimelineEvent.recording),
        )
        .order_by(TimelineEvent.created_at.asc())
    )

    sessions = await db.scalars(
        select(GameSession)
        .where(GameSession.story_id == story.id)
        .options(selectinload(GameSession.players).selectinload(SessionPlayer.user))
        .order_by(GameSession.created_at.asc())
    )
    characters = await db.scalars(
        select(CharacterSheet)
        .where(CharacterSheet.story_id == story.id)
        .order_by(CharacterSheet.created_at.asc())
    )

    event_payloads: list[dict[str, Any]] = []
    for event_obj in timeline_events.all():
        event_payloads.append(
            {
                "event_type": event_obj.event_type.value,
                "text_content": event_obj.text_content,
                "language": event_obj.language,
                "metadata_json": event_obj.metadata_json,
                "created_at": _safe_iso(event_obj.created_at),
                "audio": (
                    None
                    if event_obj.recording is None
                    else {
                        "audio_ref": event_obj.recording.audio_ref,
                        "duration_ms": event_obj.recording.duration_ms,
                        "codec": event_obj.recording.codec,
                    }
                ),
                "transcript_segments": [
                    {
                        "language": segment.language,
                        "content": segment.content,
                        "confidence": segment.confidence,
                        "timestamp": _safe_iso(segment.timestamp),
                    }
                    for segment in sorted(
                        event_obj.transcripts, key=lambda segment: segment.timestamp
                    )
                ],
            }
        )

    session_payloads: list[dict[str, Any]] = []
    for session_obj in sessions.all():
        players = [
            {
                "email": player.user.email,
                "role": player.role.value,
                "joined_at": _safe_iso(player.joined_at),
                "kicked_at": _safe_iso(player.kicked_at),
            }
            for player in session_obj.players
        ]
        session_payloads.append(
            {
                "status": session_obj.status.value,
                "max_players": session_obj.max_players,
                "created_at": _safe_iso(session_obj.created_at),
                "started_at": _safe_iso(session_obj.started_at),
                "ended_at": _safe_iso(session_obj.ended_at),
                "players": players,
            }
        )

    character_payloads: list[dict[str, Any]] = []
    for character_obj in characters.all():
        character_payloads.append(
            {
                "name": character_obj.name,
                "race": character_obj.race,
                "character_class": character_obj.character_class,
                "background": character_obj.background,
                "level": character_obj.level,
                "alignment": character_obj.alignment,
                "abilities": character_obj.abilities_json,
                "max_hp": character_obj.max_hp,
                "current_hp": character_obj.current_hp,
                "armor_class": character_obj.armor_class,
                "speed": character_obj.speed,
                "proficiency_bonus": character_obj.proficiency_bonus,
                "initiative_bonus": character_obj.initiative_bonus,
                "inventory": character_obj.inventory_json,
                "spells": character_obj.spells_json,
                "creation_mode": character_obj.creation_mode.value,
                "creation_rolls": character_obj.creation_rolls_json,
                "notes": character_obj.notes,
            }
        )

    return {
        "version": 1,
        "saved_at": datetime.now(UTC).isoformat(),
        "story": {
            "title": story.title,
            "description": story.description,
            "status": story.status,
        },
        "timeline_events": event_payloads,
        "sessions": session_payloads,
        "characters": character_payloads,
    }


@router.post("", response_model=StorySaveRead, status_code=status.HTTP_201_CREATED)
async def create_save(
    payload: StorySaveCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> StorySaveRead:
    story = await _assert_story_owner(payload.story_id, current_user, db)
    snapshot = await _build_snapshot(story, db)
    save = StorySave(
        story_id=story.id,
        created_by_user_id=current_user.id,
        label=payload.label,
        snapshot_json=snapshot,
    )
    db.add(save)
    await db.commit()
    await db.refresh(save)
    return _map_save(save)


@router.get("", response_model=list[StorySaveRead])
async def list_saves(
    story_id: Annotated[str, Query(...)],
    current_user: CurrentUser,
    db: DBSession,
) -> list[StorySaveRead]:
    await _assert_story_owner(story_id, current_user, db)
    saves = await db.scalars(
        select(StorySave)
        .where(StorySave.story_id == story_id)
        .order_by(StorySave.created_at.desc())
    )
    return [_map_save(item) for item in saves.all()]


@router.get("/{save_id}", response_model=StorySaveDetail)
async def get_save(
    save_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> StorySaveDetail:
    save = await _load_save(save_id, db)
    if save is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Save not found")
    await _assert_story_owner(save.story_id, current_user, db)
    mapped = _map_save(save)
    return StorySaveDetail(**mapped.model_dump(), snapshot_json=save.snapshot_json)


@router.post("/{save_id}/restore", response_model=StorySaveRestoreResponse)
async def restore_save(
    save_id: str,
    payload: StorySaveRestoreRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> StorySaveRestoreResponse:
    save = await _load_save(save_id, db)
    if save is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Save not found")

    source_story = await _assert_story_owner(save.story_id, current_user, db)
    snapshot = save.snapshot_json
    story_snapshot = snapshot.get("story", {})
    restored_story = Story(
        owner_user_id=current_user.id,
        title=payload.title or f"{source_story.title} (Restored)",
        description=story_snapshot.get("description"),
        status=story_snapshot.get("status") or "active",
    )
    db.add(restored_story)
    await db.flush()

    restored_count = 0
    for item in snapshot.get("timeline_events", []):
        raw_event_type = str(item.get("event_type", TimelineEventType.system.value))
        try:
            event_type = TimelineEventType(raw_event_type)
        except ValueError:
            event_type = TimelineEventType.system

        recording: VoiceRecording | None = None
        audio = item.get("audio")
        if isinstance(audio, dict) and audio.get("audio_ref"):
            recording = VoiceRecording(
                story_id=restored_story.id,
                speaker_id=None,
                audio_ref=str(audio.get("audio_ref")),
                duration_ms=max(int(audio.get("duration_ms", 1)), 1),
                codec=str(audio.get("codec") or "audio/webm;codecs=opus"),
            )
            db.add(recording)
            await db.flush()

        metadata_json = item.get("metadata_json")
        if not isinstance(metadata_json, dict):
            metadata_json = {}

        event = TimelineEvent(
            story_id=restored_story.id,
            actor_id=None,
            event_type=event_type,
            text_content=item.get("text_content"),
            language=str(item.get("language") or "en"),
            metadata_json=metadata_json,
            audio_recording_id=recording.id if recording is not None else None,
        )
        db.add(event)
        await db.flush()

        for transcript in item.get("transcript_segments", []):
            if not isinstance(transcript, dict):
                continue
            content = str(transcript.get("content") or "").strip()
            if not content:
                continue
            db.add(
                TranscriptSegment(
                    timeline_event_id=event.id,
                    story_id=restored_story.id,
                    speaker_id=None,
                    language=str(transcript.get("language") or "en"),
                    content=content,
                    confidence=(
                        float(transcript["confidence"])
                        if transcript.get("confidence") is not None
                        else None
                    ),
                    timestamp=datetime.now(UTC),
                )
            )
        restored_count += 1

    for item in snapshot.get("characters", []):
        if not isinstance(item, dict):
            continue
        raw_creation_mode = str(item.get("creation_mode") or CharacterCreationMode.auto.value)
        try:
            creation_mode = CharacterCreationMode(raw_creation_mode)
        except ValueError:
            creation_mode = CharacterCreationMode.auto

        abilities = item.get("abilities")
        if not isinstance(abilities, dict):
            abilities = {}
        inventory = item.get("inventory")
        if not isinstance(inventory, list):
            inventory = []
        spells = item.get("spells")
        if not isinstance(spells, list):
            spells = []
        creation_rolls = item.get("creation_rolls")
        if not isinstance(creation_rolls, list):
            creation_rolls = []

        restored_max_hp = max(int(item.get("max_hp", 1)), 1)
        restored_current_hp = min(max(int(item.get("current_hp", 1)), 0), restored_max_hp)

        db.add(
            CharacterSheet(
                story_id=restored_story.id,
                owner_user_id=None,
                created_by_user_id=current_user.id,
                name=str(item.get("name") or "Unnamed Adventurer"),
                race=str(item.get("race") or "Human"),
                character_class=str(item.get("character_class") or "Fighter"),
                background=str(item.get("background") or "Soldier"),
                level=max(int(item.get("level", 1)), 1),
                alignment=str(item["alignment"]) if item.get("alignment") else None,
                abilities_json={
                    str(ability): int(score)
                    for ability, score in abilities.items()
                    if isinstance(ability, str)
                },
                max_hp=restored_max_hp,
                current_hp=restored_current_hp,
                armor_class=max(int(item.get("armor_class", 10)), 1),
                speed=max(int(item.get("speed", 30)), 0),
                proficiency_bonus=max(int(item.get("proficiency_bonus", 2)), 2),
                initiative_bonus=int(item.get("initiative_bonus", 0)),
                inventory_json=[entry for entry in inventory if isinstance(entry, dict)],
                spells_json=[entry for entry in spells if isinstance(entry, dict)],
                creation_mode=creation_mode,
                creation_rolls_json=[int(roll) for roll in creation_rolls],
                notes=str(item["notes"]) if item.get("notes") else None,
            )
        )

    await db.commit()
    await db.refresh(restored_story)

    return StorySaveRestoreResponse(
        story=StoryRead.model_validate(restored_story),
        timeline_events_restored=restored_count,
    )
