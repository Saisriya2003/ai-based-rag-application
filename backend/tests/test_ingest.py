from __future__ import annotations

import re

from app.ingest import CHUNK_OVERLAP, CHUNK_SIZE, _soften_markdown, chunk_text, guess_mime


def test_guess_mime_prefers_extension() -> None:
    assert guess_mime("brief.PDF", "application/octet-stream") == "application/pdf"
    assert guess_mime("notes.md", "") == "text/markdown"
    assert guess_mime("notes.txt", "text/plain") == "text/plain"
    assert guess_mime("archive.bin", "application/octet-stream") == ""
    assert guess_mime("archive.bin", "text/plain") == "text/plain"


def test_soften_markdown_strips_syntax_but_keeps_words() -> None:
    text = "# Title\n\nSome **bold** and `code` here.\n- bullet one\n- bullet two\n"
    soft = _soften_markdown(text)
    assert "#" not in soft and "**" not in soft and "`" not in soft
    assert "Title" in soft and "bold" in soft and "bullet one" in soft
    assert not re.search(r"^\s*[-*+]\s", soft, flags=re.MULTILINE)


def test_short_text_is_a_single_chunk() -> None:
    assert chunk_text("One short paragraph.") == ["One short paragraph."]
    assert chunk_text("   \n\n ") == []


def test_chunks_respect_size_and_cover_the_document() -> None:
    # Unique numbered sentences so every chunk has exactly one position in the text.
    sentences = [f"Decision {i} assigns owner number {i * 7} to the Helios pulse item {i}." for i in range(90)]
    text = "\n\n".join(" ".join(sentences[i : i + 6]) for i in range(0, 90, 6))  # ~6,000 characters
    chunks = chunk_text(text)
    assert len(chunks) > 3
    assert all(len(chunk) <= CHUNK_SIZE for chunk in chunks)

    joined = "\n\n".join(re.sub(r"\s+", " ", block).strip() for block in re.split(r"\n{2,}", text))
    # Every chunk is a verbatim slice of the normalised document and starts on a word.
    for chunk in chunks:
        position = joined.find(chunk)
        assert position >= 0
        assert position == 0 or not joined[position - 1].isalnum()

    # Consecutive chunks overlap, and nothing is skipped between them.
    for left, right in zip(chunks, chunks[1:]):
        left_end = joined.find(left) + len(left)
        right_start = joined.find(right)
        assert right_start < left_end  # overlap present
        assert left_end - right_start <= CHUNK_OVERLAP + 48  # bounded by overlap + word snap

    # The tail of the document is included.
    assert joined.rstrip().endswith(chunks[-1].rstrip()[-40:])
