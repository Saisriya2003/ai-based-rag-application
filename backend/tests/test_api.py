"""End-to-end API tests on an isolated SQLite library (see conftest.py)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import MAX_UPLOAD_BYTES, app


@pytest.fixture(scope="module")
def client() -> Iterator[TestClient]:
    # Entering the context runs the startup hook: create tables, seed documents.
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_offline_modes_and_seeded_library(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] is True
    assert body["mode"] == "extractive"
    assert body["embedding"] == "hashing"
    assert body["database"] == "sqlite"
    assert body["documents"] == 3


def test_documents_list_seeds_with_chunk_counts(client: TestClient) -> None:
    docs = client.get("/api/documents").json()["documents"]
    assert len(docs) == 3
    assert all(doc["chunk_count"] > 0 for doc in docs)
    assert {doc["mime"] for doc in docs} == {"text/markdown"}


def test_ask_is_grounded_with_citations(client: TestClient) -> None:
    body = client.post("/api/ask", json={"question": "How many PTO days do Helios employees receive?"}).json()
    assert "22" in body["answer"]
    assert body["mode"] == "extractive"
    assert 1 <= len(body["citations"]) <= 5
    assert body["citations"][0]["doc"].startswith("Helios Labs")
    assert len(body["passages"]) == len(body["citations"])


def test_search_returns_ranked_passages(client: TestClient) -> None:
    body = client.post("/api/search", json={"query": "warehouse visibility owner", "top_k": 3}).json()
    scores = [p["score"] for p in body["passages"]]
    assert len(scores) == 3
    assert scores == sorted(scores, reverse=True)
    assert body["passages"][0]["doc"].startswith("Riverline")


def test_validation_errors(client: TestClient) -> None:
    assert client.post("/api/ask", json={"question": "   "}).status_code == 422
    assert client.post("/api/ask", json={}).status_code == 422
    assert client.delete("/api/documents/999999").status_code == 404


def test_upload_ask_and_delete_roundtrip(client: TestClient) -> None:
    text = (
        "Project Orion kickoff is on 3 March 2027. The budget for Orion is 450000 rupees "
        "and the project is owned by Priya Menon. The team meets every Tuesday morning."
    )
    upload = client.post(
        "/api/documents/upload",
        files={"file": ("orion-notes.txt", text.encode("utf-8"), "text/plain")},
    )
    assert upload.status_code == 200
    document = upload.json()["document"]
    assert document["name"] == "orion-notes.txt"
    assert document["chunk_count"] >= 1
    assert client.get("/api/health").json()["documents"] == 4

    answer = client.post("/api/ask", json={"question": "What is the budget for Orion?"}).json()
    assert "450000" in answer["answer"]
    assert any(c["doc"] == "orion-notes.txt" for c in answer["citations"])

    removed = client.delete(f"/api/documents/{document['id']}")
    assert removed.status_code == 200 and removed.json()["ok"] is True
    assert client.get("/api/health").json()["documents"] == 3
    # Chunks are gone too: the Orion fact is no longer retrievable.
    after = client.post("/api/search", json={"query": "Orion budget rupees", "top_k": 8}).json()
    assert all(p["doc"] != "orion-notes.txt" for p in after["passages"])


def test_upload_rejects_unsupported_empty_and_oversized_files(client: TestClient) -> None:
    unsupported = client.post("/api/documents/upload", files={"file": ("tool.exe", b"\x00\x01\x02", "application/octet-stream")})
    assert unsupported.status_code == 400

    empty = client.post("/api/documents/upload", files={"file": ("empty.txt", b"", "text/plain")})
    assert empty.status_code == 400

    too_big = client.post(
        "/api/documents/upload",
        files={"file": ("big.txt", b"a" * (MAX_UPLOAD_BYTES + 1), "text/plain")},
    )
    assert too_big.status_code == 413
    assert client.get("/api/health").json()["documents"] == 3
