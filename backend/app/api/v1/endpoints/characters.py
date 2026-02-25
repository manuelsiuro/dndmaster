from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import (
    CharacterCreationMode,
    CharacterSheet,
    GameSession,
    SessionParticipantRole,
    SessionPlayer,
    Story,
)
from app.schemas.character import (
    ABILITY_KEYS,
    SRD_BACKGROUNDS,
    SRD_CLASSES,
    SRD_RACES,
    STANDARD_ARRAY,
    CharacterCreate,
    CharacterInventoryItem,
    CharacterRead,
    CharacterSpellEntry,
    CharacterSrdOptionsResponse,
    CharacterUpdate,
)

router = APIRouter(prefix="/characters", tags=["characters"])


def _canonical_srd_option(value: str, options: list[str], field_name: str) -> str:
    value_normalized = value.strip().casefold()
    for option in options:
        if option.casefold() == value_normalized:
            return option
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"{field_name} must be a strict SRD 5.1 option",
    )


def _proficiency_bonus(level: int) -> int:
    return 2 + ((max(level, 1) - 1) // 4)


def _default_auto_abilities() -> dict[str, int]:
    return dict(zip(ABILITY_KEYS, STANDARD_ARRAY, strict=True))


def _map_character(item: CharacterSheet) -> CharacterRead:
    return CharacterRead(
        id=item.id,
        story_id=item.story_id,
        owner_user_id=item.owner_user_id,
        created_by_user_id=item.created_by_user_id,
        name=item.name,
        race=item.race,
        character_class=item.character_class,
        background=item.background,
        level=item.level,
        alignment=item.alignment,
        abilities=item.abilities_json,
        max_hp=item.max_hp,
        current_hp=item.current_hp,
        armor_class=item.armor_class,
        speed=item.speed,
        proficiency_bonus=item.proficiency_bonus,
        initiative_bonus=item.initiative_bonus,
        inventory=[CharacterInventoryItem.model_validate(entry) for entry in item.inventory_json],
        spells=[CharacterSpellEntry.model_validate(entry) for entry in item.spells_json],
        creation_mode=item.creation_mode.value,
        creation_rolls=item.creation_rolls_json,
        notes=item.notes,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _load_character(character_id: str, db: DBSession) -> CharacterSheet | None:
    return await db.scalar(select(CharacterSheet).where(CharacterSheet.id == character_id))


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


async def _assert_story_manage_access(
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Host access required")
    return story


@router.get("/srd-options", response_model=CharacterSrdOptionsResponse)
async def get_srd_options(current_user: CurrentUser) -> CharacterSrdOptionsResponse:
    return CharacterSrdOptionsResponse(
        classes=SRD_CLASSES,
        races=SRD_RACES,
        backgrounds=SRD_BACKGROUNDS,
        ability_keys=list(ABILITY_KEYS),
        standard_array=STANDARD_ARRAY,
        creation_modes=["auto", "player_dice", "gm_dice"],
    )


@router.post("", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(
    payload: CharacterCreate,
    current_user: CurrentUser,
    db: DBSession,
) -> CharacterRead:
    await _assert_story_manage_access(payload.story_id, current_user, db)

    abilities = payload.abilities or _default_auto_abilities()
    max_hp = payload.max_hp
    current_hp = payload.current_hp if payload.current_hp is not None else max_hp

    if current_hp > max_hp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_hp cannot be greater than max_hp",
        )

    item = CharacterSheet(
        story_id=payload.story_id,
        owner_user_id=payload.owner_user_id or current_user.id,
        created_by_user_id=current_user.id,
        name=payload.name.strip(),
        race=_canonical_srd_option(payload.race, SRD_RACES, "race"),
        character_class=_canonical_srd_option(
            payload.character_class,
            SRD_CLASSES,
            "character_class",
        ),
        background=_canonical_srd_option(payload.background, SRD_BACKGROUNDS, "background"),
        level=payload.level,
        alignment=payload.alignment.strip() if payload.alignment else None,
        abilities_json=abilities,
        max_hp=max_hp,
        current_hp=current_hp,
        armor_class=payload.armor_class,
        speed=payload.speed,
        proficiency_bonus=_proficiency_bonus(payload.level),
        initiative_bonus=payload.initiative_bonus,
        inventory_json=[item.model_dump(mode="json") for item in payload.inventory],
        spells_json=[entry.model_dump(mode="json") for entry in payload.spells],
        creation_mode=CharacterCreationMode(payload.creation_mode),
        creation_rolls_json=payload.ability_rolls or [],
        notes=payload.notes,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _map_character(item)


@router.get("", response_model=list[CharacterRead])
async def list_characters(
    story_id: Annotated[str, Query(...)],
    current_user: CurrentUser,
    db: DBSession,
) -> list[CharacterRead]:
    await _assert_story_access(story_id, current_user, db)
    result = await db.scalars(
        select(CharacterSheet)
        .where(CharacterSheet.story_id == story_id)
        .order_by(CharacterSheet.created_at.asc())
    )
    return [_map_character(item) for item in result.all()]


@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(
    character_id: str,
    current_user: CurrentUser,
    db: DBSession,
) -> CharacterRead:
    item = await _load_character(character_id, db)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    await _assert_story_access(item.story_id, current_user, db)
    return _map_character(item)


@router.put("/{character_id}", response_model=CharacterRead)
async def update_character(
    character_id: str,
    payload: CharacterUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> CharacterRead:
    item = await _load_character(character_id, db)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
    await _assert_story_manage_access(item.story_id, current_user, db)

    updates = payload.model_dump(exclude_unset=True)
    if "name" in updates:
        item.name = str(updates["name"]).strip()
    if "race" in updates:
        item.race = _canonical_srd_option(str(updates["race"]), SRD_RACES, "race")
    if "character_class" in updates:
        item.character_class = _canonical_srd_option(
            str(updates["character_class"]),
            SRD_CLASSES,
            "character_class",
        )
    if "background" in updates:
        item.background = _canonical_srd_option(
            str(updates["background"]),
            SRD_BACKGROUNDS,
            "background",
        )
    if "level" in updates:
        next_level = int(updates["level"])
        item.level = next_level
        item.proficiency_bonus = _proficiency_bonus(next_level)
    if "alignment" in updates:
        alignment = updates["alignment"]
        item.alignment = str(alignment).strip() if alignment else None
    if "abilities" in updates:
        item.abilities_json = {
            ability: int(score)
            for ability, score in updates["abilities"].items()
        }
    if "armor_class" in updates:
        item.armor_class = int(updates["armor_class"])
    if "speed" in updates:
        item.speed = int(updates["speed"])
    if "initiative_bonus" in updates:
        item.initiative_bonus = int(updates["initiative_bonus"])
    if "inventory" in updates:
        item.inventory_json = [entry.model_dump(mode="json") for entry in payload.inventory or []]
    if "spells" in updates:
        item.spells_json = [entry.model_dump(mode="json") for entry in payload.spells or []]
    if "notes" in updates:
        item.notes = str(updates["notes"]).strip() if updates["notes"] else None

    next_max_hp = int(updates.get("max_hp", item.max_hp))
    next_current_hp = int(updates.get("current_hp", item.current_hp))
    if next_current_hp > next_max_hp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="current_hp cannot be greater than max_hp",
        )
    item.max_hp = next_max_hp
    item.current_hp = next_current_hp

    await db.commit()
    await db.refresh(item)
    return _map_character(item)
