from __future__ import annotations

import math
import wave
from pathlib import Path

SAMPLE_RATE = 16000
AMPLITUDE = 12000
MAX_CHARS = 320


def _append_silence(samples: list[int], *, milliseconds: float) -> None:
    frame_count = max(1, int(SAMPLE_RATE * (milliseconds / 1000.0)))
    samples.extend(0 for _ in range(frame_count))


def _append_tone(samples: list[int], *, frequency_hz: float, milliseconds: float) -> None:
    frame_count = max(1, int(SAMPLE_RATE * (milliseconds / 1000.0)))
    for index in range(frame_count):
        phase = (2.0 * math.pi * frequency_hz * index) / SAMPLE_RATE
        envelope = min(index / max(frame_count * 0.15, 1), 1.0)
        tail = min((frame_count - index) / max(frame_count * 0.2, 1), 1.0)
        sample = int(AMPLITUDE * envelope * tail * math.sin(phase))
        samples.append(sample)


def synthesize_tts_wav(text: str, output_path: Path, *, language: str) -> int:
    normalized = " ".join(text.strip().split())
    if not normalized:
        normalized = "No response."
    normalized = normalized[:MAX_CHARS]

    output_path.parent.mkdir(parents=True, exist_ok=True)

    base_pitch = 180.0 if language.lower() == "fr" else 170.0
    samples: list[int] = []

    for char in normalized:
        if char.isspace():
            _append_silence(samples, milliseconds=22)
            continue
        if char in ",.;:!?":
            _append_silence(samples, milliseconds=45)
            continue

        frequency = base_pitch + float((ord(char) % 24) * 11)
        _append_tone(samples, frequency_hz=frequency, milliseconds=48)
        _append_silence(samples, milliseconds=12)

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(SAMPLE_RATE)
        frame_bytes = bytearray()
        for sample in samples:
            frame_bytes.extend(int(sample).to_bytes(2, byteorder="little", signed=True))
        wav_file.writeframes(bytes(frame_bytes))

    duration_ms = max(1, int((len(samples) / SAMPLE_RATE) * 1000))
    return duration_ms
