from collections.abc import Sequence
from datetime import datetime
from typing import cast

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    GameSession,
    ProgressionEntry,
    SessionPlayer,
    Story,
    User,
    UserProgression,
)
from app.schemas.progression import (
    ProgressionAwardRequest,
    ProgressionAwardResponse,
    ProgressionEntryRead,
    StoryProgressionRead,
    UserProgressionRead,
)

router = APIRouter(prefix="/progression", tags=["progression"])

# D&D 5e SRD XP thresholds by level (1..20).
SRD_LEVEL_THRESHOLDS = [
    (20, 355000),
    (19, 305000),
    (18, 265000),
    (17, 225000),
    (16, 195000),
    (15, 165000),
    (14, 140000),
    (13, 120000),
    (12, 100000),
    (11, 85000),
    (10, 64000),
    (9, 48000),
    (8, 34000),
    (7, 23000),
    (6, 14000),
    (5, 6500),
    (4, 2700),
    (3, 900),
    (2, 300),
    (1, 0),
]


def _level_for_xp(xp_total: int) -> int:
    for level, threshold in SRD_LEVEL_THRESHOLDS:
        if xp_total >= threshold:
            return level
    return 1


def _map_story_progression(
    user: User,
    progression: UserProgression | None,
    last_award_at: datetime | None,
) -> StoryProgressionRead:
    xp_total = progression.xp_total if progression is not None else 0
    level = progression.level if progression is not None else 1
    return StoryProgressionRead(
        user_id=user.id,
        user_email=user.email,
        xp_total=xp_total,
        level=level,
        last_award_at=last_award_at,
    )


async def _assert_story_owner(story_id: str, current_user: CurrentUser, db: DBSession) -> Story:
    story = await db.scalar(
        select(Story).where(Story.id == story_id, Story.owner_user_id == current_user.id)
    )
    if story is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Story not found")
    return story


async def _get_or_create_progression(user_id: str, db: DBSession) -> UserProgression:
    progression = await db.scalar(select(UserProgression).where(UserProgression.user_id == user_id))
    if progression is not None:
        return progression

    progression = UserProgression(user_id=user_id, xp_total=0, level=1)
    db.add(progression)
    await db.flush()
    return progression


async def _active_story_participants(story_id: str, db: DBSession) -> Sequence[User]:
    participants = await db.scalars(
        select(User)
        .join(SessionPlayer, SessionPlayer.user_id == User.id)
        .join(GameSession, SessionPlayer.session_id == GameSession.id)
        .where(
            GameSession.story_id == story_id,
            SessionPlayer.kicked_at.is_(None),
        )
        .distinct()
    )
    return participants.all()


@router.get("/me", response_model=UserProgressionRead)
async def get_my_progression(
    current_user: CurrentUser,
    db: DBSession,
    limit: int = Query(default=20, ge=1, le=100),
) -> UserProgressionRead:
    progression = await _get_or_create_progression(current_user.id, db)
    await db.commit()
    await db.refresh(progression)

    entries = await db.scalars(
        select(ProgressionEntry)
        .where(ProgressionEntry.user_id == current_user.id)
        .order_by(ProgressionEntry.created_at.desc())
        .limit(limit)
    )

    return UserProgressionRead(
        id=progression.id,
        user_id=progression.user_id,
        xp_total=progression.xp_total,
        level=progression.level,
        updated_at=progression.updated_at,
        recent_entries=[ProgressionEntryRead.model_validate(item) for item in entries.all()],
    )


@router.get("/story/{story_id}", response_model=list[StoryProgressionRead])
async def list_story_progression(
    story_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> list[StoryProgressionRead]:
    await _assert_story_owner(story_id, current_user, db)
    participants = await _active_story_participants(story_id, db)
    if not participants:
        return []

    participant_ids = [user.id for user in participants]

    progressions = await db.scalars(
        select(UserProgression).where(UserProgression.user_id.in_(participant_ids))
    )
    progression_by_user = {item.user_id: item for item in progressions.all()}

    last_awards = await db.execute(
        select(
            ProgressionEntry.user_id,
            func.max(ProgressionEntry.created_at),
        )
        .where(
            ProgressionEntry.story_id == story_id,
            ProgressionEntry.user_id.in_(participant_ids),
        )
        .group_by(ProgressionEntry.user_id)
    )
    last_award_rows = cast(list[tuple[str, datetime]], last_awards.all())
    last_award_by_user = dict(last_award_rows)

    items = [
        _map_story_progression(
            user=user,
            progression=progression_by_user.get(user.id),
            last_award_at=last_award_by_user.get(user.id),
        )
        for user in participants
    ]
    return sorted(items, key=lambda item: (-item.xp_total, item.user_email))


@router.post("/award", response_model=ProgressionAwardResponse, status_code=status.HTTP_201_CREATED)
async def award_story_xp(
    payload: ProgressionAwardRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> ProgressionAwardResponse:
    await _assert_story_owner(payload.story_id, current_user, db)

    target_user = await db.scalar(select(User).where(User.id == payload.user_id))
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    participant = await db.scalar(
        select(SessionPlayer.id)
        .join(GameSession, SessionPlayer.session_id == GameSession.id)
        .where(
            GameSession.story_id == payload.story_id,
            SessionPlayer.user_id == payload.user_id,
            SessionPlayer.kicked_at.is_(None),
        )
        .limit(1)
    )
    if participant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Player is not part of this story session",
        )

    progression = await _get_or_create_progression(payload.user_id, db)
    progression.xp_total += payload.xp_delta
    progression.level = _level_for_xp(progression.xp_total)

    entry = ProgressionEntry(
        user_id=payload.user_id,
        story_id=payload.story_id,
        awarded_by_user_id=current_user.id,
        xp_delta=payload.xp_delta,
        reason=(payload.reason or "").strip() or None,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(progression)
    await db.refresh(entry)

    return ProgressionAwardResponse(
        progression=_map_story_progression(
            user=target_user,
            progression=progression,
            last_award_at=entry.created_at,
        ),
        entry=ProgressionEntryRead.model_validate(entry),
    )
