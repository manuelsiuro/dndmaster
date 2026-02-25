from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

LLMProvider = Literal["codex", "claude", "ollama"]
TTSProvider = Literal["codex", "claude", "ollama"]
LanguageCode = Literal["en", "fr"]
VoiceMode = Literal["webrtc_with_fallback"]


class UserSettingsRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    llm_provider: LLMProvider
    llm_model: str | None
    tts_provider: TTSProvider
    tts_model: str | None
    tts_voice: str
    language: LanguageCode
    voice_mode: VoiceMode
    updated_at: datetime


class UserSettingsUpdate(BaseModel):
    llm_provider: LLMProvider | None = None
    llm_model: str | None = Field(default=None, max_length=128)
    tts_provider: TTSProvider | None = None
    tts_model: str | None = Field(default=None, max_length=128)
    tts_voice: str | None = Field(default=None, min_length=1, max_length=64)
    language: LanguageCode | None = None
    voice_mode: VoiceMode | None = None


class OllamaModelsResponse(BaseModel):
    available: bool
    models: list[str]


class TtsProviderSummary(BaseModel):
    provider: TTSProvider
    label: str
    configured: bool
    base_url: str
    default_model: str
    default_voice: str
    supported_voices: list[str]
    requires_api_key: bool


class TtsProvidersResponse(BaseModel):
    providers: list[TtsProviderSummary]


class TtsProfileValidationRequest(BaseModel):
    provider: TTSProvider
    model: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, min_length=1, max_length=64)


class TtsProfileValidationResponse(BaseModel):
    provider: TTSProvider
    model: str | None
    voice: str | None
    valid: bool
    issues: list[str]


class TtsProviderHealthRequest(BaseModel):
    provider: TTSProvider
    model: str | None = Field(default=None, max_length=128)
    voice: str | None = Field(default=None, min_length=1, max_length=64)


class TtsProviderHealthResponse(BaseModel):
    provider: TTSProvider
    model: str | None
    voice: str | None
    valid: bool
    healthy: bool
    configured: bool
    reachable: bool
    model_available: bool
    issues: list[str]
    available_models: list[str]
