import json
import re
from typing import cast
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.request import Request as URLRequest
from urllib.request import urlopen

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DBSession
from app.db.models import UserSettings, UserTtsSettings
from app.schemas.settings import (
    LanguageCode,
    LLMProvider,
    OllamaModelsResponse,
    TtsProfileValidationRequest,
    TtsProfileValidationResponse,
    TTSProvider,
    TtsProviderHealthRequest,
    TtsProviderHealthResponse,
    TtsProvidersResponse,
    TtsProviderSummary,
    UserSettingsRead,
    UserSettingsUpdate,
    VoiceMode,
)

router = APIRouter(prefix="/settings", tags=["settings"])

TTS_PROVIDER_LABELS: dict[str, str] = {
    "codex": "Codex",
    "claude": "Claude",
    "ollama": "Ollama (local)",
}
TTS_PROVIDER_VOICES: dict[str, list[str]] = {
    "codex": ["alloy", "ash", "coral", "echo", "sage", "shimmer", "verse"],
    "claude": ["alloy", "ash", "coral", "echo", "sage", "shimmer", "verse"],
    "ollama": ["alloy"],
}
MODEL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
VOICE_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$")


async def _get_or_create_user_settings(current_user: CurrentUser, db: DBSession) -> UserSettings:
    settings = await db.scalar(select(UserSettings).where(UserSettings.user_id == current_user.id))
    if settings is not None:
        return settings

    settings = UserSettings(user_id=current_user.id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


async def _get_or_create_user_tts_settings(
    current_user: CurrentUser, db: DBSession
) -> UserTtsSettings:
    settings = await db.scalar(
        select(UserTtsSettings).where(UserTtsSettings.user_id == current_user.id)
    )
    if settings is not None:
        return settings

    settings = UserTtsSettings(user_id=current_user.id)
    db.add(settings)
    await db.commit()
    await db.refresh(settings)
    return settings


def _normalize_model(model: str | None) -> str | None:
    if model is None:
        return None
    normalized = model.strip()
    return normalized or None


def _normalize_voice(voice: str | None) -> str | None:
    if voice is None:
        return None
    normalized = voice.strip().lower()
    return normalized or None


def _validate_tts_profile(provider: str, model: str | None, voice: str | None) -> list[str]:
    issues: list[str] = []
    if provider not in TTS_PROVIDER_LABELS:
        issues.append("Unsupported TTS provider.")
    if model is not None and not MODEL_PATTERN.match(model):
        issues.append(
            "Model must use letters, numbers, dot, underscore, colon, or dash (max 128 chars)."
        )
    if voice is not None and not VOICE_PATTERN.match(voice):
        issues.append(
            "Voice must use letters, numbers, dot, underscore, colon, or dash (max 64 chars)."
        )
    if voice and provider in {"codex", "claude"}:
        supported = set(TTS_PROVIDER_VOICES[provider])
        if voice not in supported:
            supported_values = ", ".join(sorted(supported))
            issues.append(
                f"Voice '{voice}' is not supported for {provider} (supported: {supported_values})."
            )
    return issues


def _fetch_openai_compatible_models(
    *,
    base_url: str,
    api_key: str | None,
    timeout_seconds: float,
) -> tuple[bool, list[str]]:
    models_url = urljoin(base_url.rstrip("/") + "/", "v1/models")
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = URLRequest(models_url, headers=headers, method="GET")
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError):
        return False, []

    names: set[str] = set()
    for item in payload.get("data", []):
        model_name = str(item.get("id", "")).strip()
        if not model_name:
            continue
        names.add(model_name)
    return True, sorted(names)


def _probe_ollama_models(base_url: str, timeout_seconds: float = 2) -> tuple[bool, list[str]]:
    tags_url = urljoin(base_url.rstrip("/") + "/", "api/tags")
    try:
        with urlopen(tags_url, timeout=timeout_seconds) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (URLError, TimeoutError, ValueError):
        return False, []

    seen: set[str] = set()
    models: list[str] = []
    for item in payload.get("models", []):
        name = str(item.get("name", "")).strip()
        if not name or name in seen:
            continue
        seen.add(name)
        models.append(name)
    return True, sorted(models)


def _fetch_ollama_models(base_url: str) -> list[str]:
    _, models = _probe_ollama_models(base_url, timeout_seconds=2)
    return models


def _provider_runtime_settings(app_settings, provider: str) -> dict[str, str | bool | float | None]:
    if provider == "codex":
        base_url = app_settings.tts_codex_base_url.strip()
        return {
            "base_url": base_url,
            "api_key": app_settings.tts_codex_api_key,
            "default_model": app_settings.tts_codex_model,
            "default_voice": app_settings.tts_codex_voice,
            "configured": bool(base_url and app_settings.tts_codex_api_key),
            "requires_api_key": True,
            "timeout_seconds": app_settings.tts_http_timeout_seconds,
        }
    if provider == "claude":
        base_url = (app_settings.tts_claude_base_url or "").strip()
        return {
            "base_url": base_url,
            "api_key": app_settings.tts_claude_api_key,
            "default_model": app_settings.tts_claude_model,
            "default_voice": app_settings.tts_claude_voice,
            "configured": bool(base_url),
            "requires_api_key": False,
            "timeout_seconds": app_settings.tts_http_timeout_seconds,
        }
    if provider == "ollama":
        base_url = (app_settings.tts_ollama_base_url or app_settings.ollama_base_url).strip()
        return {
            "base_url": base_url,
            "api_key": app_settings.tts_ollama_api_key,
            "default_model": app_settings.tts_ollama_model,
            "default_voice": app_settings.tts_ollama_voice,
            "configured": bool(base_url),
            "requires_api_key": False,
            "timeout_seconds": app_settings.tts_http_timeout_seconds,
        }
    raise ValueError(f"Unsupported provider: {provider}")


def _build_tts_provider_summaries(app_settings) -> list[TtsProviderSummary]:
    providers: list[TtsProviderSummary] = []
    for provider in ("codex", "claude", "ollama"):
        runtime = _provider_runtime_settings(app_settings, provider)
        default_model = str(runtime["default_model"])
        if provider == "ollama":
            _, live_models = _probe_ollama_models(str(runtime["base_url"]), timeout_seconds=1)
            if live_models:
                default_model = live_models[0]
        providers.append(
            TtsProviderSummary(
                provider=cast(TTSProvider, provider),
                label=TTS_PROVIDER_LABELS[provider],
                configured=bool(runtime["configured"]),
                base_url=str(runtime["base_url"]),
                default_model=default_model,
                default_voice=str(runtime["default_voice"]),
                supported_voices=TTS_PROVIDER_VOICES[provider],
                requires_api_key=bool(runtime["requires_api_key"]),
            )
        )
    return providers


def _to_settings_read(settings: UserSettings, tts_settings: UserTtsSettings) -> UserSettingsRead:
    return UserSettingsRead(
        id=settings.id,
        user_id=settings.user_id,
        llm_provider=cast(LLMProvider, settings.llm_provider),
        llm_model=settings.llm_model,
        tts_provider=cast(TTSProvider, tts_settings.tts_provider),
        tts_model=tts_settings.tts_model,
        tts_voice=tts_settings.tts_voice,
        language=cast(LanguageCode, settings.language),
        voice_mode=cast(VoiceMode, settings.voice_mode),
        updated_at=max(settings.updated_at, tts_settings.updated_at),
    )


@router.get("/me", response_model=UserSettingsRead)
async def get_my_settings(current_user: CurrentUser, db: DBSession) -> UserSettingsRead:
    settings = await _get_or_create_user_settings(current_user, db)
    tts_settings = await _get_or_create_user_tts_settings(current_user, db)
    return _to_settings_read(settings, tts_settings)


@router.put("/me", response_model=UserSettingsRead)
async def update_my_settings(
    payload: UserSettingsUpdate,
    current_user: CurrentUser,
    db: DBSession,
) -> UserSettingsRead:
    settings = await _get_or_create_user_settings(current_user, db)
    tts_settings = await _get_or_create_user_tts_settings(current_user, db)
    patch = payload.model_dump(exclude_unset=True)

    tts_provider = patch.pop("tts_provider", tts_settings.tts_provider)
    tts_model = _normalize_model(patch.pop("tts_model", tts_settings.tts_model))
    tts_voice = _normalize_voice(patch.pop("tts_voice", tts_settings.tts_voice))
    issues = _validate_tts_profile(tts_provider, tts_model, tts_voice)
    if issues:
        raise HTTPException(
            status_code=422,
            detail={"message": "Invalid TTS settings", "issues": issues},
        )

    for key, value in patch.items():
        setattr(settings, key, value)
    tts_settings.tts_provider = tts_provider
    tts_settings.tts_model = tts_model
    tts_settings.tts_voice = tts_voice or "alloy"
    await db.commit()
    await db.refresh(settings)
    await db.refresh(tts_settings)
    return _to_settings_read(settings, tts_settings)


@router.get("/ollama/models", response_model=OllamaModelsResponse)
async def list_ollama_models(request: Request, current_user: CurrentUser) -> OllamaModelsResponse:
    # Current user dependency enforces authenticated access.
    _ = current_user
    base_url = request.app.state.settings.ollama_base_url
    models = _fetch_ollama_models(base_url)
    return OllamaModelsResponse(available=len(models) > 0, models=models)


@router.get("/tts/providers", response_model=TtsProvidersResponse)
async def list_tts_providers(request: Request, current_user: CurrentUser) -> TtsProvidersResponse:
    # Current user dependency enforces authenticated access.
    _ = current_user
    providers = _build_tts_provider_summaries(request.app.state.settings)
    return TtsProvidersResponse(providers=providers)


@router.post("/tts/validate", response_model=TtsProfileValidationResponse)
async def validate_tts_profile_endpoint(
    payload: TtsProfileValidationRequest,
    current_user: CurrentUser,
) -> TtsProfileValidationResponse:
    # Current user dependency enforces authenticated access.
    _ = current_user
    model = _normalize_model(payload.model)
    voice = _normalize_voice(payload.voice)
    issues = _validate_tts_profile(payload.provider, model, voice)
    return TtsProfileValidationResponse(
        provider=payload.provider,
        model=model,
        voice=voice,
        valid=len(issues) == 0,
        issues=issues,
    )


@router.post("/tts/health", response_model=TtsProviderHealthResponse)
async def check_tts_provider_health_endpoint(
    payload: TtsProviderHealthRequest,
    request: Request,
    current_user: CurrentUser,
) -> TtsProviderHealthResponse:
    # Current user dependency enforces authenticated access.
    _ = current_user
    model = _normalize_model(payload.model)
    voice = _normalize_voice(payload.voice)
    issues = _validate_tts_profile(payload.provider, model, voice)

    runtime = _provider_runtime_settings(request.app.state.settings, payload.provider)
    configured = bool(runtime["configured"])
    if not configured:
        issues.append(f"{payload.provider} is not configured in backend environment.")

    available_models: list[str] = []
    reachable = False
    if configured:
        base_url = str(runtime["base_url"])
        timeout_seconds = float(runtime["timeout_seconds"] or 1.5)
        if payload.provider in {"codex", "claude"}:
            reachable, available_models = _fetch_openai_compatible_models(
                base_url=base_url,
                api_key=runtime["api_key"] if isinstance(runtime["api_key"], str) else None,
                timeout_seconds=timeout_seconds,
            )
        else:
            reachable, available_models = _probe_ollama_models(
                base_url=base_url,
                timeout_seconds=timeout_seconds,
            )
        if not reachable:
            issues.append(f"{payload.provider} endpoint is unreachable.")

    model_available = True
    if model:
        if available_models:
            model_available = model in available_models
            if not model_available:
                issues.append(f"Model '{model}' is not available on {payload.provider}.")
        elif not reachable:
            model_available = False

    healthy = configured and reachable and model_available and len(issues) == 0
    return TtsProviderHealthResponse(
        provider=payload.provider,
        model=model,
        voice=voice,
        valid=len(_validate_tts_profile(payload.provider, model, voice)) == 0,
        healthy=healthy,
        configured=configured,
        reachable=reachable,
        model_available=model_available,
        issues=issues,
        available_models=available_models,
    )
