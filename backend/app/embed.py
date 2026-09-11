"""Embedding pipeline: offline n-gram hashing by default, MiniLM when opted in."""

from __future__ import annotations

import hashlib
import re
from typing import Any

import numpy as np

from app.config import SENTENCE_TRANSFORMERS

HASH_DIM = 256
_WORD_RE = re.compile(r"[a-z0-9]+", re.IGNORECASE)
_model: Any = None


def _bucket(token: str, dim: int) -> int:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little") % dim


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 1e-12:
        return vec
    return vec / norm


def hash_embed(text: str, dim: int = HASH_DIM) -> list[float]:
    """Character 3/4-grams plus word uni/bigrams, hashed into a dense vector."""
    vec = np.zeros(dim, dtype=np.float64)
    lowered = text.lower()
    cleaned = re.sub(r"[^a-z0-9]+", " ", lowered)
    compact = cleaned.replace(" ", "")

    for n in (3, 4):
        if len(compact) < n:
            continue
        for i in range(len(compact) - n + 1):
            vec[_bucket(f"c{n}:{compact[i : i + n]}", dim)] += 1.0

    words = _WORD_RE.findall(cleaned)
    for word in words:
        vec[_bucket(f"w1:{word}", dim)] += 1.6
    for left, right in zip(words, words[1:]):
        vec[_bucket(f"w2:{left}_{right}", dim)] += 1.25

    return _l2_normalize(vec).tolist()


def _sentence_transformer_embed(text: str) -> list[float]:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer("all-MiniLM-L6-v2")
    vector = _model.encode(text, normalize_embeddings=True)
    return [float(x) for x in vector]


def embed_text(text: str) -> list[float]:
    payload = (text or "").strip()
    if not payload:
        dim = 384 if SENTENCE_TRANSFORMERS else HASH_DIM
        return [0.0] * dim
    if SENTENCE_TRANSFORMERS:
        return _sentence_transformer_embed(payload)
    return hash_embed(payload)


def as_vector(values: list[float] | np.ndarray) -> np.ndarray:
    return np.asarray(values, dtype=np.float64)


def cosine_similarity(left: list[float] | np.ndarray, right: list[float] | np.ndarray) -> float:
    a = as_vector(left)
    b = as_vector(right)
    if a.size != b.size:
        return 0.0
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-12:
        return 0.0
    return float(np.dot(a, b) / denom)
