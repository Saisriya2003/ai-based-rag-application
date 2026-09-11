from __future__ import annotations

from app.generate import answer_question, extractive_answer

PASSAGES = [
    {
        "chunk_id": 1,
        "document_id": 1,
        "doc": "Helios Labs - Time Away Policy.md",
        "chunk_index": 2,
        "score": 0.61,
        "text": (
            "Full-time employees receive 22 days of paid time off (PTO) per calendar year, "
            "accrued monthly. Unused PTO may carry over by up to 5 days into the next year. "
            "Requests go to the direct manager at least two weeks ahead."
        ),
    },
    {
        "chunk_id": 9,
        "document_id": 2,
        "doc": "Riverline - Q3 Project Brief.md",
        "chunk_index": 0,
        "score": 0.22,
        "text": "Riverline is a warehouse visibility program owned by Ananya Rao in Operations.",
    },
]


def test_extractive_answer_picks_the_numeric_sentence_for_how_many() -> None:
    answer = extractive_answer("How many PTO days do employees receive?", PASSAGES)
    assert "22 days" in answer
    assert "Riverline" not in answer


def test_extractive_answer_leads_with_the_best_matching_document() -> None:
    """A lower-ranked distractor from an earlier document must not come first."""
    distractor = {
        "chunk_id": 3,
        "document_id": 1,  # earlier document id, weaker match
        "doc": "Aether Desk - Product Spec.md",
        "chunk_index": 4,
        "score": 0.20,
        "text": "Launch on 14 October 2026 if at least two internal squads have used the pulse for a month.",
    }
    target = {
        "chunk_id": 40,
        "document_id": 4,
        "doc": "zephyr.txt",
        "chunk_index": 0,
        "score": 0.62,
        "text": "The Zephyr launch is planned for 9 June 2027 with a budget of 120000 rupees.",
    }
    answer = extractive_answer("When is the Zephyr launch?", [target, distractor])
    assert answer.startswith("The Zephyr launch is planned for 9 June 2027")


def test_extractive_answer_drops_weak_distractors() -> None:
    strong = {"chunk_id": 1, "document_id": 2, "doc": "b.txt", "chunk_index": 0, "score": 0.7,
              "text": "The Orion budget is 450000 rupees and it is owned by Priya Menon."}
    weak = {"chunk_id": 2, "document_id": 1, "doc": "a.txt", "chunk_index": 0, "score": 0.05,
            "text": "The finance team publishes a budget calendar every quarter for all programs."}
    answer = extractive_answer("What is the budget for Orion?", [strong, weak])
    assert "450000" in answer
    assert "budget calendar" not in answer


def test_extractive_answer_handles_no_passages() -> None:
    answer = extractive_answer("Anything?", [])
    assert "No indexed passages" in answer


def test_answer_question_reports_mode_and_citations() -> None:
    result = answer_question("Who owns Riverline?", PASSAGES)
    assert result["mode"] == "extractive"  # OPENAI_API_KEY is blank in tests
    assert result["warning"] is None
    assert "Ananya Rao" in result["answer"]
    assert [c["doc"] for c in result["citations"]] == [p["doc"] for p in PASSAGES]
    assert all(len(c["snippet"]) <= 240 for c in result["citations"])
    assert result["passages"] == PASSAGES
