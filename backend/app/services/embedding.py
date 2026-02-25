from __future__ import annotations

import hashlib
import math
import re
from collections.abc import Sequence

TOKEN_PATTERN = re.compile(r"[A-Za-z0-9_']+")


def hash_text_embedding(text: str, dimensions: int) -> list[float]:
    if dimensions <= 0:
        raise ValueError("dimensions must be positive")

    vector = [0.0] * dimensions
    tokens = TOKEN_PATTERN.findall(text.lower())
    if not tokens:
        tokens = ["empty"]

    for token in tokens:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
        index = int.from_bytes(digest[:8], "big") % dimensions
        sign = 1.0 if digest[8] % 2 == 0 else -1.0
        magnitude = 0.25 + (digest[9] / 255.0)
        vector[index] += sign * magnitude

    return _normalize(vector)


def _normalize(values: Sequence[float]) -> list[float]:
    norm = math.sqrt(sum(item * item for item in values))
    if norm == 0:
        return [0.0 for _ in values]
    return [float(item / norm) for item in values]
