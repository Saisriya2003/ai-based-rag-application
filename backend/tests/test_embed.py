from __future__ import annotations

import numpy as np
import pytest

from app.embed import HASH_DIM, cosine_similarity, embed_text, hash_embed


def test_hash_embedding_is_deterministic_and_unit_length() -> None:
    a = hash_embed("Employees receive 22 days of paid time off per year.")
    b = hash_embed("Employees receive 22 days of paid time off per year.")
    assert a == b
    assert len(a) == HASH_DIM
    assert np.linalg.norm(a) == pytest.approx(1.0, abs=1e-9)


def test_similar_texts_are_closer_than_unrelated_texts() -> None:
    policy = embed_text("Full-time employees receive 22 days of paid time off per calendar year.")
    question = embed_text("How many PTO days do employees receive?")
    unrelated = embed_text("The warehouse scanner firmware update ships on Tuesday.")
    assert cosine_similarity(policy, question) > cosine_similarity(policy, unrelated)
    assert cosine_similarity(policy, policy) == pytest.approx(1.0, abs=1e-9)


def test_empty_and_mismatched_inputs_are_safe() -> None:
    assert embed_text("   ") == [0.0] * HASH_DIM
    assert cosine_similarity([0.0] * HASH_DIM, hash_embed("anything")) == 0.0
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0, 0.0]) == 0.0
