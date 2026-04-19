"""Pure text chunking logic for review documents."""

from __future__ import annotations

import re


def _split_text_into_paragraphs(text: str) -> list[str]:
    """Split review text into paragraphs (blank line separated)."""
    paragraphs = [p.strip() for p in text.split("\n\n")]
    return [p for p in paragraphs if p]


def _split_paragraph_into_sentences(paragraph: str) -> list[str]:
    """Split paragraph into sentences using punctuation heuristics."""
    normalized = paragraph.replace("\n", " ").strip()
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    return [p.strip() for p in parts if p.strip()]


def _hard_split_by_chars(text: str, *, max_chunk_chars: int) -> list[str]:
    """Hard split text by character count."""
    text = text.strip()
    if not text:
        return []
    return [text[i : i + max_chunk_chars] for i in range(0, len(text), max_chunk_chars)]


def hybrid_chunk_text(
    review_text: str,
    *,
    min_chunk_chars: int = 600,
    target_chunk_chars: int = 1600,
    max_chunk_chars: int = 2400,
) -> list[str]:
    """Hybrid paragraph chunking (merge short, split long).

    This is a heuristic that works without a tokenizer:
    - split by paragraph boundaries
    - merge paragraphs into chunks up to `max_chunk_chars`
    - if a paragraph is too long, split it by sentence boundaries
    - if a sentence is still too long, hard split by characters
    """
    if not review_text or not review_text.strip():
        return []

    paragraphs = _split_text_into_paragraphs(review_text)
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""

    def flush_buffer() -> None:
        nonlocal buffer
        if buffer.strip():
            chunks.append(buffer.strip())
        buffer = ""

    for p in paragraphs:
        if not p:
            continue
        p = p.strip()

        if len(p) <= max_chunk_chars:
            proposed = p if not buffer else f"{buffer}\n\n{p}"
            if len(proposed) <= max_chunk_chars:
                buffer = proposed
                if len(buffer) >= target_chunk_chars:
                    flush_buffer()
            else:
                flush_buffer()
                if len(p) >= target_chunk_chars:
                    chunks.append(p)
                else:
                    buffer = p
            continue

        flush_buffer()
        sentences = _split_paragraph_into_sentences(p)
        if not sentences:
            chunks.extend(_hard_split_by_chars(p, max_chunk_chars=max_chunk_chars))
            continue

        sent_buf = ""
        for s in sentences:
            if not s:
                continue
            if len(s) > max_chunk_chars:
                if sent_buf.strip():
                    chunks.append(sent_buf.strip())
                    sent_buf = ""
                chunks.extend(
                    _hard_split_by_chars(s, max_chunk_chars=max_chunk_chars),
                )
                continue

            proposed = s if not sent_buf else f"{sent_buf} {s}"
            if len(proposed) <= max_chunk_chars:
                sent_buf = proposed
                if len(sent_buf) >= target_chunk_chars:
                    chunks.append(sent_buf.strip())
                    sent_buf = ""
            else:
                if sent_buf.strip():
                    chunks.append(sent_buf.strip())
                sent_buf = s

        if sent_buf.strip():
            chunks.append(sent_buf.strip())

    if buffer.strip():
        chunks.append(buffer.strip())

    if len(chunks) >= 2 and len(chunks[-1]) < min_chunk_chars:
        tail = chunks[-1]
        prev = chunks[-2]
        merged = f"{prev}\n\n{tail}"
        if len(merged) <= max_chunk_chars:
            chunks[-2] = merged
            chunks.pop()

    safe_chunks: list[str] = []
    for c in chunks:
        if len(c) <= max_chunk_chars:
            safe_chunks.append(c)
        else:
            safe_chunks.extend(_hard_split_by_chars(c, max_chunk_chars=max_chunk_chars))

    return [c.strip() for c in safe_chunks if c.strip()]
