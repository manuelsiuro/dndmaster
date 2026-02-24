from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LLMProvider = Literal["codex", "claude", "ollama"]
LanguageCode = Literal["en", "fr"]
VoiceMode = Literal["webrtc_with_fallback"]


class UserSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    llm_provider: LLMProvider
    llm_model: str | None
    language: LanguageCode
    voice_mode: VoiceMode
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    llm_provider: LLMProvider | None = None
    llm_model: str | None = Field(default=None, max_length=128)
    language: LanguageCode | None = None
    voice_mode: VoiceMode | None = None


class OllamaModelsResponse(BaseModel):
    available: bool
    models: list[str]
