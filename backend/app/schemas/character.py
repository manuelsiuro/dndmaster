from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ABILITY_KEYS = (
    "strength",
    "dexterity",
    "constitution",
    "intelligence",
    "wisdom",
    "charisma",
)
STANDARD_ARRAY = [15, 14, 13, 12, 10, 8]
SRD_CLASSES = [
    "Barbarian",
    "Bard",
    "Cleric",
    "Druid",
    "Fighter",
    "Monk",
    "Paladin",
    "Ranger",
    "Rogue",
    "Sorcerer",
    "Warlock",
    "Wizard",
]
SRD_RACES = [
    "Dragonborn",
    "Dwarf",
    "Elf",
    "Gnome",
    "Half-Elf",
    "Half-Orc",
    "Halfling",
    "Human",
    "Tiefling",
]
SRD_BACKGROUNDS = [
    "Acolyte",
    "Criminal",
    "Folk Hero",
    "Noble",
    "Sage",
    "Soldier",
]
CharacterCreationMode = Literal["auto", "player_dice", "gm_dice"]


class CharacterInventoryItem(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    quantity: int = Field(default=1, ge=1, le=999)
    notes: str | None = Field(default=None, max_length=280)


class CharacterSpellEntry(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    level: int = Field(default=0, ge=0, le=9)
    prepared: bool = False
    uses_remaining: int | None = Field(default=None, ge=0, le=99)


class CharacterCreate(BaseModel):
    story_id: str
    owner_user_id: str | None = None
    name: str = Field(min_length=1, max_length=120)
    race: str = Field(min_length=1, max_length=64)
    character_class: str = Field(min_length=1, max_length=64)
    background: str = Field(min_length=1, max_length=64)
    level: int = Field(default=1, ge=1, le=20)
    alignment: str | None = Field(default=None, max_length=32)
    abilities: dict[str, int] | None = None
    max_hp: int = Field(ge=1, le=999)
    current_hp: int | None = Field(default=None, ge=0, le=999)
    armor_class: int = Field(default=10, ge=1, le=40)
    speed: int = Field(default=30, ge=0, le=120)
    initiative_bonus: int = Field(default=0, ge=-20, le=20)
    inventory: list[CharacterInventoryItem] = Field(default_factory=list)
    spells: list[CharacterSpellEntry] = Field(default_factory=list)
    creation_mode: CharacterCreationMode = "auto"
    ability_rolls: list[int] | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_payload(self) -> "CharacterCreate":
        abilities = self.abilities
        if abilities is not None:
            if set(abilities.keys()) != set(ABILITY_KEYS):
                raise ValueError(f"abilities must include exactly: {', '.join(ABILITY_KEYS)}")
            for key in ABILITY_KEYS:
                score = int(abilities[key])
                if score < 3 or score > 20:
                    raise ValueError(f"{key} must be between 3 and 20")

        if self.current_hp is not None and self.current_hp > self.max_hp:
            raise ValueError("current_hp cannot be greater than max_hp")

        if self.creation_mode == "auto":
            if self.ability_rolls is not None:
                raise ValueError("ability_rolls are only allowed for dice creation modes")
            if abilities is not None and sorted(abilities.values()) != sorted(STANDARD_ARRAY):
                raise ValueError("auto mode abilities must use the SRD standard array")
            return self

        rolls = self.ability_rolls
        if rolls is None or len(rolls) != len(ABILITY_KEYS):
            raise ValueError("ability_rolls must include six values for dice creation modes")
        for roll in rolls:
            if roll < 3 or roll > 18:
                raise ValueError("each ability roll must be between 3 and 18")
        if abilities is None:
            raise ValueError("abilities are required for dice creation modes")
        if Counter(abilities.values()) != Counter(rolls):
            raise ValueError("abilities must be assigned from the provided ability_rolls")
        return self


class CharacterUpdate(BaseModel):
    owner_user_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=120)
    race: str | None = Field(default=None, min_length=1, max_length=64)
    character_class: str | None = Field(default=None, min_length=1, max_length=64)
    background: str | None = Field(default=None, min_length=1, max_length=64)
    level: int | None = Field(default=None, ge=1, le=20)
    alignment: str | None = Field(default=None, max_length=32)
    abilities: dict[str, int] | None = None
    max_hp: int | None = Field(default=None, ge=1, le=999)
    current_hp: int | None = Field(default=None, ge=0, le=999)
    armor_class: int | None = Field(default=None, ge=1, le=40)
    speed: int | None = Field(default=None, ge=0, le=120)
    initiative_bonus: int | None = Field(default=None, ge=-20, le=20)
    inventory: list[CharacterInventoryItem] | None = None
    spells: list[CharacterSpellEntry] | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def validate_payload(self) -> "CharacterUpdate":
        abilities = self.abilities
        if abilities is None:
            return self
        if set(abilities.keys()) != set(ABILITY_KEYS):
            raise ValueError(f"abilities must include exactly: {', '.join(ABILITY_KEYS)}")
        for key in ABILITY_KEYS:
            score = int(abilities[key])
            if score < 3 or score > 20:
                raise ValueError(f"{key} must be between 3 and 20")
        return self


class CharacterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    story_id: str
    owner_user_id: str | None
    created_by_user_id: str | None
    name: str
    race: str
    character_class: str
    background: str
    level: int
    alignment: str | None
    abilities: dict[str, int]
    max_hp: int
    current_hp: int
    armor_class: int
    speed: int
    proficiency_bonus: int
    initiative_bonus: int
    inventory: list[CharacterInventoryItem]
    spells: list[CharacterSpellEntry]
    creation_mode: CharacterCreationMode
    creation_rolls: list[int]
    notes: str | None
    created_at: datetime
    updated_at: datetime


class CharacterSrdOptionsResponse(BaseModel):
    classes: list[str]
    races: list[str]
    backgrounds: list[str]
    ability_keys: list[str]
    standard_array: list[int]
    creation_modes: list[CharacterCreationMode]
