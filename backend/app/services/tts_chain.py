from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request
import wave
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from app.core.config import Settings
from app.services.tts_audio import synthesize_tts_wav

ALLOWED_TTS_ADAPTERS = {"preferred", "codex", "claude", "ollama", "deterministic"}


@dataclass(slots=True)
class TtsSynthesisResult:
    provider: str
    model: str
    audio_ref: str
    duration_ms: int
    codec: str


def _normalize_chain(configured: list[str]) -> list[str]:
    chain: list[str] = []
    for raw in configured:
        item = raw.strip().lower()
        if item in ALLOWED_TTS_ADAPTERS and item not in chain:
            chain.append(item)
    if "deterministic" not in chain:
        chain.append("deterministic")
    return chain


def _target_provider(step: str, preferred_provider: str) -> str:
    if step == "preferred":
        preferred = preferred_provider.strip().lower()
        if preferred in {"codex", "claude", "ollama"}:
            return preferred
        return "codex"
    return step


def _response_duration_ms(wav_bytes: bytes) -> int:
    with wave.open(BytesIO(wav_bytes), "rb") as wav_file:
        frames = wav_file.getnframes()
        rate = wav_file.getframerate()
    if rate <= 0:
        return 1
    return max(1, int((frames / rate) * 1000))


def _openai_compatible_tts(
    *,
    base_url: str,
    api_key: str | None,
    model: str,
    voice: str,
    text: str,
    timeout_seconds: float,
) -> bytes:
    endpoint = urllib.parse.urljoin(base_url.rstrip("/") + "/", "v1/audio/speech")
    body = json.dumps(
        {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": "wav",
        }
    ).encode("utf-8")

    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    request = urllib.request.Request(
        endpoint,
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
        return response.read()


def _write_wav(path: Path, wav_bytes: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(wav_bytes)


def _build_audio_ref(base_url: str, settings: Settings, relative_path: str) -> str:
    prefix = settings.media_url_prefix.strip("/")
    return f"{base_url}/{prefix}/{relative_path}"


def synthesize_tts_with_fallback(
    *,
    settings: Settings,
    story_id: str,
    text: str,
    language: str,
    preferred_provider: str,
    preferred_model: str | None,
    preferred_voice: str | None,
    request_base_url: str,
) -> TtsSynthesisResult:
    media_root = Path(settings.media_root)
    output_dir = media_root / "timeline-audio" / story_id
    chain = _normalize_chain(settings.tts_provider_fallback_chain)
    normalized_text = " ".join(text.strip().split())[:1200]
    if not normalized_text:
        normalized_text = "No response."

    base_url = request_base_url.rstrip("/")
    normalized_preferred_provider = preferred_provider.strip().lower()
    normalized_preferred_model = (preferred_model or "").strip() or None
    normalized_preferred_voice = (preferred_voice or "").strip().lower() or None

    for step in chain:
        provider = _target_provider(step, preferred_provider)
        stem = f"gm-tts-{provider}-{secrets.token_hex(6)}"
        target = output_dir / f"{stem}.wav"

        try:
            if provider == "deterministic":
                duration_ms = synthesize_tts_wav(normalized_text, target, language=language)
                relative = target.relative_to(media_root).as_posix()
                return TtsSynthesisResult(
                    provider="deterministic",
                    model="local-tone",
                    audio_ref=_build_audio_ref(base_url, settings, relative),
                    duration_ms=duration_ms,
                    codec="audio/wav",
                )

            if provider == "codex":
                provider_base = settings.tts_codex_base_url
                provider_key = settings.tts_codex_api_key
                provider_model = settings.tts_codex_model.strip()
                provider_voice = settings.tts_codex_voice
            elif provider == "claude":
                provider_base = (settings.tts_claude_base_url or "").strip()
                provider_key = settings.tts_claude_api_key
                provider_model = settings.tts_claude_model.strip()
                provider_voice = settings.tts_claude_voice
            elif provider == "ollama":
                provider_base = (settings.tts_ollama_base_url or settings.ollama_base_url).strip()
                provider_key = settings.tts_ollama_api_key
                provider_model = settings.tts_ollama_model.strip()
                provider_voice = settings.tts_ollama_voice
            else:
                continue

            if provider == normalized_preferred_provider and normalized_preferred_model:
                provider_model = normalized_preferred_model
            if provider == normalized_preferred_provider and normalized_preferred_voice:
                provider_voice = normalized_preferred_voice

            if not provider_base or not provider_model:
                continue
            if provider == "codex" and not provider_key:
                continue

            wav_bytes = _openai_compatible_tts(
                base_url=provider_base,
                api_key=provider_key,
                model=provider_model,
                voice=provider_voice,
                text=normalized_text,
                timeout_seconds=settings.tts_http_timeout_seconds,
            )
            _write_wav(target, wav_bytes)
            duration_ms = _response_duration_ms(wav_bytes)
            relative = target.relative_to(media_root).as_posix()
            return TtsSynthesisResult(
                provider=provider,
                model=provider_model,
                audio_ref=_build_audio_ref(base_url, settings, relative),
                duration_ms=duration_ms,
                codec="audio/wav",
            )
        except (
            OSError,
            ValueError,
            EOFError,
            wave.Error,
            urllib.error.URLError,
            urllib.error.HTTPError,
        ):
            continue

    # Deterministic provider is always added to chain, so this should not happen.
    raise RuntimeError("Unable to synthesize TTS audio")
