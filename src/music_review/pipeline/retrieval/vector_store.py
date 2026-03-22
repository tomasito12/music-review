# music_review/pipeline/retrieval/vector_store.py

from __future__ import annotations

import json
import math
import os
import re
import time
from collections import defaultdict
from contextlib import suppress
from pathlib import Path
from typing import Any, Literal, cast

import chromadb
from chromadb.utils import embedding_functions
from openai import OpenAI

import music_review.config  # noqa: F401 - load .env early
from music_review.config import get_project_root, resolve_data_path
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map, write_jsonl
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

PROJECT_ROOT = get_project_root()
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "reviews.jsonl"
DEFAULT_METADATA_PATH = resolve_data_path("data/metadata_imputed.jsonl")
DEFAULT_METADATA_FALLBACK_PATH = resolve_data_path("data/metadata.jsonl")
DEFAULT_CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "music_reviews"
CHUNK_COLLECTION_NAME = "music_reviews_chunks_v1"


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

        # Paragraph too long: flush buffer and split paragraph into sentences.
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

    # Merge tiny tail chunk into previous chunk.
    if len(chunks) >= 2 and len(chunks[-1]) < min_chunk_chars:
        tail = chunks[-1]
        prev = chunks[-2]
        merged = f"{prev}\n\n{tail}"
        if len(merged) <= max_chunk_chars:
            chunks[-2] = merged
            chunks.pop()

    # Safety: ensure all chunks are <= max_chunk_chars.
    safe_chunks: list[str] = []
    for c in chunks:
        if len(c) <= max_chunk_chars:
            safe_chunks.append(c)
        else:
            safe_chunks.extend(_hard_split_by_chars(c, max_chunk_chars=max_chunk_chars))

    return [c.strip() for c in safe_chunks if c.strip()]


EMBEDDING_MODEL = "text-embedding-3-small"


def _load_top_communities_for_reviews(
    affinities_path: Path | str | None = None,
    *,
    res_key: str = "res_10",
    top_k: int = 3,
) -> dict[int, list[tuple[str, float]]]:
    """Load top-k communities per review for a given resolution key.

    Returns a mapping review_id -> list of (community_id, score), sorted by score
    descending and truncated to top_k entries. If the affinities file does not
    exist, returns an empty dict.
    """
    if affinities_path is None:
        affinities_path = resolve_data_path("data/album_community_affinities.jsonl")
    path = Path(affinities_path)
    if not path.exists():
        return {}

    result: dict[int, list[tuple[str, float]]] = {}
    for obj in iter_jsonl_objects(path, log_errors=False):
        review_id = obj.get("review_id")
        comms = (obj.get("communities") or {}).get(res_key)
        if not isinstance(review_id, int) or not isinstance(comms, list):
            continue
        items: list[tuple[str, float]] = []
        for entry in comms:
            if not isinstance(entry, dict):
                continue
            cid = entry.get("id")
            score = entry.get("score")
            if isinstance(cid, str) and isinstance(score, (int, float)):
                items.append((cid, float(score)))
        if not items:
            continue
        items.sort(key=lambda t: t[1], reverse=True)
        result[review_id] = items[:top_k]
    return result


def review_to_metadata(review: Review) -> dict[str, Any]:
    """Convert a Review into a flat metadata dict for Chroma.

    Only includes fields with non-None scalar values, because the current
    Chroma backend does not accept None as a metadata value.
    """
    meta: dict[str, Any] = {}

    if review.url:
        meta["url"] = review.url

    if review.artist:
        meta["artist"] = review.artist

    if review.album:
        meta["album"] = review.album

    if review.title:
        meta["title"] = review.title

    if review.author:
        meta["author"] = review.author

    if review.labels:
        meta["labels"] = ", ".join(review.labels)

    if review.release_date:
        meta["release_date"] = review.release_date.isoformat()

    if review.release_year is not None:
        meta["release_year"] = int(review.release_year)

    if review.rating is not None:
        meta["rating"] = float(review.rating)

    if review.user_rating is not None:
        meta["user_rating"] = float(review.user_rating)

    if review.highlights:
        meta["highlights"] = "; ".join(review.highlights)

    if review.references:
        meta["references"] = "; ".join(review.references)

    if review.total_duration:
        meta["total_duration"] = review.total_duration

    # Original review text for display (embedding uses enriched document).
    if review.text:
        meta["review_text"] = review.text

    return meta


def chunk_to_metadata(
    review: Review,
    *,
    chunk_index: int,
    chunk_text: str,
) -> dict[str, Any]:
    """Convert a Review into chunk-level Chroma metadata.

    Unlike `review_to_metadata`, this stores only the scalar fields needed for
    filtering and display, and it stores `chunk_text` for snippet rendering.
    """
    meta: dict[str, Any] = {"review_id": int(review.id), "chunk_index": chunk_index}

    if review.url:
        meta["url"] = review.url
    if review.artist:
        meta["artist"] = review.artist
    if review.album:
        meta["album"] = review.album
    if review.title:
        meta["title"] = review.title
    if review.author:
        meta["author"] = review.author
    if review.labels:
        meta["labels"] = ", ".join(review.labels)
    if review.release_date:
        meta["release_date"] = review.release_date.isoformat()
    if review.release_year is not None:
        meta["release_year"] = int(review.release_year)
    if review.rating is not None:
        meta["rating"] = float(review.rating)
    if review.user_rating is not None:
        meta["user_rating"] = float(review.user_rating)
    if review.highlights:
        meta["highlights"] = "; ".join(review.highlights)
    if review.references:
        meta["references"] = "; ".join(review.references)
    if review.total_duration:
        meta["total_duration"] = review.total_duration

    # The text used for display and (optionally) snippet extraction.
    meta["chunk_text"] = chunk_text
    return meta


def build_enriched_document(review: Review, meta: dict[str, Any]) -> str:
    """Build text for embedding.

    Including metadata in the embedded text lets semantic search match on artist,
    album, and genre context as well as review content.
    """
    parts: list[str] = []
    if review.artist:
        parts.append(f"Artist: {review.artist}.")
    if review.album:
        parts.append(f"Album: {review.album}.")
    genres = meta.get("genres")
    if isinstance(genres, list) and genres:
        parts.append("Genres: " + ", ".join(str(g) for g in genres) + ".")
    elif isinstance(genres, list):
        pass
    if review.release_year is not None:
        parts.append(f"Release year: {review.release_year}.")
    elif review.release_date is not None:
        parts.append(f"Release: {review.release_date.isoformat()}.")
    if review.author:
        parts.append(f"Author: {review.author}.")
    if review.rating is not None:
        parts.append(f"Rating: {review.rating}/10.")
    if review.title:
        parts.append(f"Review title: {review.title}.")

    prefix = " ".join(parts)
    if prefix:
        return prefix + "\n\n" + review.text
    return review.text


def get_chroma_collection(
    persist_directory: Path | str | None = None,
    *,
    recreate: bool = False,
    collection_name: str = COLLECTION_NAME,
) -> Any:
    """Create or load the Chroma collection configured with OpenAI embeddings.

    If `recreate` is True, the existing collection (if any) is deleted first.
    """
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY environment variable is not set."
        raise RuntimeError(msg)

    directory = (
        Path(persist_directory)
        if persist_directory is not None
        else DEFAULT_CHROMA_PATH
    )

    openai_ef = embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name=EMBEDDING_MODEL,
    )

    client = chromadb.PersistentClient(path=str(directory))

    if recreate:
        # Delete the collection entirely if it exists, then recreate it fresh.
        with suppress(Exception):
            client.delete_collection(collection_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=cast(Any, openai_ef),
    )
    return collection


def _all_collection_document_ids(collection: Any, *, page_size: int = 2000) -> set[str]:
    """Collect all document ids via paginated ``get`` calls.

    A single ``collection.get(limit=...)`` with a very large limit can make
    Chroma/SQLite fail with ``too many SQL variables``.
    """
    out: set[str] = set()
    offset = 0
    while True:
        batch = collection.get(limit=page_size, offset=offset, include=[])
        ids = batch.get("ids") or []
        if not ids:
            break
        out.update(str(i) for i in ids)
        offset += len(ids)
        if len(ids) < page_size:
            break
    return out


def _load_metadata_map(
    metadata_path: Path | None,
    fallback_path: Path | None,
) -> dict[int, dict[str, Any]]:
    """Load review_id -> metadata dict from imputed or raw metadata JSONL."""
    for path in (metadata_path, fallback_path):
        if path is None or not path.exists():
            continue
        return load_jsonl_as_map(path, id_key="review_id", log_errors=False)
    return {}


# ---------------------------------------------------------------------------
# Batch embedding pipeline (OpenAI Batch API)
# ---------------------------------------------------------------------------

DEFAULT_BATCH_INPUT_PATH = PROJECT_ROOT / "data" / "batch_embedding_input.jsonl"
DEFAULT_CHUNK_BATCH_INPUT_PATH = (
    PROJECT_ROOT / "data" / "batch_embedding_input_chunks_v1.jsonl"
)
BATCH_COMPLETION_WINDOW: Literal["24h"] = "24h"
DEFAULT_CHUNK_BATCH_RESULTS_PATH = (
    PROJECT_ROOT / "data" / "batch_embedding_results_chunks_v1.jsonl"
)


def _get_openai_client() -> OpenAI:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY environment variable is not set."
        raise RuntimeError(msg)
    return OpenAI(api_key=api_key)


def write_batch_embedding_input(
    output_path: Path | str = DEFAULT_BATCH_INPUT_PATH,
    *,
    data_path: Path | str = DEFAULT_DATA_PATH,
    metadata_path: Path | str | None = None,
    skip_existing: bool = True,
    max_requests_per_file: int | None = None,
) -> tuple[int, list[Path]]:
    """Write OpenAI Batch API input JSONL for embeddings.

    One line per review: custom_id = review id, body = embeddings request.
    If skip_existing is True, only writes requests for reviews not already in Chroma.
    If max_requests_per_file is set, splits into multiple files (e.g. to stay under
    enqueued token limits); files are named output_stem_00000.jsonl, _00001.jsonl, ...

    Returns (total request count, list of output file paths).
    """
    out = Path(output_path)
    file_path = Path(data_path)
    if not file_path.exists():
        msg = f"Data file not found: {file_path}"
        raise FileNotFoundError(msg)

    reviews = load_reviews_from_jsonl(file_path)
    if not reviews:
        msg = f"No non-empty reviews found in {file_path}"
        raise RuntimeError(msg)

    meta_path = (
        Path(metadata_path) if metadata_path is not None else DEFAULT_METADATA_PATH
    )
    metadata_map = _load_metadata_map(meta_path, DEFAULT_METADATA_FALLBACK_PATH)

    existing_ids: set[str] = set()
    if skip_existing:
        try:
            collection = get_chroma_collection()
            existing_ids = _all_collection_document_ids(collection)
        except Exception:
            pass

    requests: list[dict[str, Any]] = []
    for review in reviews:
        if str(review.id) in existing_ids:
            continue
        meta = metadata_map.get(review.id, {})
        text = build_enriched_document(review, meta)
        requests.append(
            {
                "custom_id": str(review.id),
                "method": "POST",
                "url": "/v1/embeddings",
                "body": {
                    "model": EMBEDDING_MODEL,
                    "input": text,
                },
            }
        )

    out.parent.mkdir(parents=True, exist_ok=True)
    if max_requests_per_file is None:
        write_jsonl(out, requests)
        return (len(requests), [out])
    paths: list[Path] = []
    for idx in range(0, len(requests), max_requests_per_file):
        chunk = requests[idx : idx + max_requests_per_file]
        part_path = out.parent / f"{out.stem}_{len(paths):05d}{out.suffix}"
        write_jsonl(part_path, chunk)
        paths.append(part_path)
    return (len(requests), paths)


def _parse_chunk_custom_id(custom_id: str) -> tuple[int, int]:
    """Parse chunk custom_id formatted as '{review_id}__chunk_{chunk_index}'."""
    review_part, chunk_part = custom_id.rsplit("__chunk_", 1)
    return int(review_part), int(chunk_part)


def write_batch_embedding_input_chunks_v1(
    output_path: Path | str = DEFAULT_CHUNK_BATCH_INPUT_PATH,
    *,
    data_path: Path | str = DEFAULT_DATA_PATH,
    _metadata_path: Path | str | None = None,
    skip_existing: bool = True,
    max_requests_per_file: int | None = None,
    persist_directory: Path | str | None = None,
    recreate: bool = False,
    collection_name: str = CHUNK_COLLECTION_NAME,
    min_chunk_chars: int = 600,
    target_chunk_chars: int = 1600,
    max_chunk_chars: int = 2400,
    batch_size: int = 50,
) -> tuple[int, list[Path]]:
    """Write OpenAI Batch API input JSONL for chunk-level embeddings (v1).

    Each batch request encodes exactly one chunk:
      - custom_id: '{review_id}__chunk_{chunk_index}'
      - input: chunk text only
    """
    out = Path(output_path)
    file_path = Path(data_path)
    if not file_path.exists():
        msg = f"Data file not found: {file_path}"
        raise FileNotFoundError(msg)

    reviews = load_reviews_from_jsonl(file_path)
    if not reviews:
        msg = f"No non-empty reviews found in {file_path}"
        raise RuntimeError(msg)

    directory = (
        Path(persist_directory)
        if persist_directory is not None
        else DEFAULT_CHROMA_PATH
    )

    # Use collection only for existing id checks.
    collection = get_chroma_collection(
        persist_directory=directory,
        recreate=recreate,
        collection_name=collection_name,
    )
    existing_ids: set[str] = set()
    if skip_existing and not recreate:
        existing_ids = _all_collection_document_ids(collection)

    requests: list[dict[str, Any]] = []

    total_new_chunks = 0
    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]
        if not batch:
            continue

        for review in batch:
            review_id = int(review.id)
            chunks = hybrid_chunk_text(
                review.text,
                min_chunk_chars=min_chunk_chars,
                target_chunk_chars=target_chunk_chars,
                max_chunk_chars=max_chunk_chars,
            )
            if not chunks:
                continue

            # Skip entire review if chunk_0 already exists.
            first_chunk_id = f"{review_id}__chunk_0"
            if first_chunk_id in existing_ids:
                continue

            for chunk_index, chunk_text in enumerate(chunks):
                chunk_id = f"{review_id}__chunk_{chunk_index}"
                if skip_existing and chunk_id in existing_ids:
                    continue

                requests.append(
                    {
                        "custom_id": chunk_id,
                        "method": "POST",
                        "url": "/v1/embeddings",
                        "body": {"model": EMBEDDING_MODEL, "input": chunk_text},
                    }
                )
                total_new_chunks += 1

    out.parent.mkdir(parents=True, exist_ok=True)
    if max_requests_per_file is None:
        write_jsonl(out, requests)
        return (total_new_chunks, [out])

    paths: list[Path] = []
    for idx in range(0, len(requests), max_requests_per_file):
        chunk = requests[idx : idx + max_requests_per_file]
        part_path = out.parent / f"{out.stem}_{len(paths):05d}{out.suffix}"
        write_jsonl(part_path, chunk)
        paths.append(part_path)
    return (total_new_chunks, paths)


def import_batch_results_into_chroma_chunks_v1(
    results_path: Path | str,
    *,
    data_path: Path | str = DEFAULT_DATA_PATH,
    _metadata_path: Path | str | None = None,
    persist_directory: Path | str | None = None,
    recreate: bool = False,
    collection_name: str = CHUNK_COLLECTION_NAME,
    min_chunk_chars: int = 600,
    target_chunk_chars: int = 1600,
    max_chunk_chars: int = 2400,
    add_batch_size: int = 500,
) -> int:
    """Import chunk-level batch embedding results into Chroma (v1)."""
    parsed = parse_batch_output_jsonl(Path(results_path))
    if not parsed:
        return 0

    directory = (
        Path(persist_directory)
        if persist_directory is not None
        else DEFAULT_CHROMA_PATH
    )
    collection = get_chroma_collection(
        persist_directory=directory,
        recreate=recreate,
        collection_name=collection_name,
    )

    existing_ids: set[str] = set()
    if not recreate:
        existing_ids = _all_collection_document_ids(collection)

    needed_chunks: dict[int, set[int]] = {}
    for custom_id, _embedding in parsed:
        rid, chunk_index = _parse_chunk_custom_id(custom_id)
        needed_chunks.setdefault(rid, set()).add(chunk_index)

    file_path = Path(data_path)
    reviews = load_reviews_from_jsonl(file_path)
    review_by_id: dict[int, Review] = {int(r.id): r for r in reviews}

    top_comms_map = _load_top_communities_for_reviews(
        resolve_data_path("data/album_community_affinities.jsonl"),
        res_key="res_10",
        top_k=3,
    )

    # Precompute chunk texts only for reviews that appear in this result file.
    chunks_by_review: dict[int, list[str]] = {}
    for rid in needed_chunks:
        review = review_by_id.get(rid)
        if not review:
            continue
        chunks = hybrid_chunk_text(
            review.text,
            min_chunk_chars=min_chunk_chars,
            target_chunk_chars=target_chunk_chars,
            max_chunk_chars=max_chunk_chars,
        )
        chunks_by_review[rid] = chunks

    chunk_ids: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []
    documents: list[str] = []

    for custom_id, embedding in parsed:
        rid, chunk_index = _parse_chunk_custom_id(custom_id)
        if custom_id in existing_ids:
            continue

        chunks_for_review = chunks_by_review.get(rid)
        if chunks_for_review is None:
            continue
        if chunk_index >= len(chunks_for_review):
            continue
        chunk_text = chunks_for_review[chunk_index]

        review = review_by_id.get(rid)
        if review is None:
            continue

        meta = chunk_to_metadata(
            review,
            chunk_index=chunk_index,
            chunk_text=chunk_text,
        )
        top_comms = top_comms_map.get(rid)
        if top_comms:
            meta["communities_top_ids"] = [cid for cid, _ in top_comms]
            meta["communities_top_scores"] = [score for _cid, score in top_comms]

        chunk_ids.append(custom_id)
        embeddings.append(embedding)
        metadatas.append(meta)
        documents.append(chunk_text)

    if not chunk_ids:
        return 0

    added = 0
    for start in range(0, len(chunk_ids), add_batch_size):
        end = start + add_batch_size
        collection.add(
            ids=chunk_ids[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
            documents=documents[start:end],
        )
        added += end - start

    return added


def submit_batch_embedding_job(
    input_path: Path | str = DEFAULT_BATCH_INPUT_PATH,
) -> str:
    """Upload the batch input file and create a batch job. Returns the batch ID."""
    path = Path(input_path)
    if not path.exists():
        msg = f"Batch input file not found: {path}"
        raise FileNotFoundError(msg)

    client = _get_openai_client()
    with path.open("rb") as f:
        file_obj = client.files.create(file=f, purpose="batch")
    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint="/v1/embeddings",
        completion_window=BATCH_COMPLETION_WINDOW,
    )
    return batch.id


def poll_batch_until_complete(
    batch_id: str,
    *,
    poll_interval_seconds: int = 60,
) -> str:
    """Poll batch until completed/failed/expired/cancelled. Returns final status."""
    client = _get_openai_client()
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        if status in ("completed", "failed", "expired", "cancelled"):
            return status
        time.sleep(poll_interval_seconds)


def _get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute or dict key from SDK response (object or dict)."""
    if obj is None:
        return default
    v = getattr(obj, key, None)
    if v is not None:
        return v
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def get_batch_error_details(batch_id: str) -> str:
    """Retrieve batch and return a readable summary of status and errors (if failed)."""
    client = _get_openai_client()
    batch = client.batches.retrieve(batch_id)
    lines: list[str] = [
        f"Batch id: {batch.id}",
        f"Status: {batch.status}",
    ]
    counts = _get_attr_or_key(batch, "request_counts")
    if counts is not None:
        total = _get_attr_or_key(counts, "total")
        completed = _get_attr_or_key(counts, "completed")
        failed = _get_attr_or_key(counts, "failed")
        if total is not None:
            lines.append(
                f"Request counts: total={total}, completed={completed}, failed={failed}"
            )
    err = _get_attr_or_key(batch, "errors")
    if err is not None:
        data = _get_attr_or_key(err, "data")
        if isinstance(data, list) and data:
            lines.append("Batch-level errors:")
            for i, e in enumerate(data[:20], 1):
                msg = _get_attr_or_key(e, "message") or str(e)
                line_no = _get_attr_or_key(e, "line")
                code = _get_attr_or_key(e, "code")
                part = f"  {i}. {msg}"
                if line_no is not None:
                    part += f" (input line {line_no})"
                if code:
                    part += f" [{code}]"
                lines.append(part)
            if len(data) > 20:
                lines.append(f"  ... and {len(data) - 20} more.")
    efile = _get_attr_or_key(batch, "error_file_id")
    if efile:
        lines.append(f"Error file id (per-request errors): {efile}")
        lines.append("Download via OpenAI API or dashboard to inspect failed requests.")
    if (
        _get_attr_or_key(batch, "status") == "failed"
        and "Batch-level errors:" not in "\n".join(lines)
        and not efile
    ):
        lines.append(
            "No error details in response. Check https://platform.openai.com/batches "
            "for validation/input errors or account limits."
        )
    return "\n".join(lines)


def is_token_limit_error(batch_id: str) -> bool:
    """Return True on enqueued token-limit failure."""
    details = get_batch_error_details(batch_id)
    return "token_limit_exceeded" in details or "Enqueued token limit" in details


def download_batch_results(
    batch_id: str,
    output_path: Path | str,
) -> int:
    """Retrieve batch output file and save as JSONL. Returns result line count."""
    client = _get_openai_client()
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        msg = f"Batch {batch_id} is not completed (status={batch.status})."
        raise RuntimeError(msg)
    if not batch.output_file_id:
        msg = f"Batch {batch_id} has no output_file_id."
        raise RuntimeError(msg)

    content = client.files.content(batch.output_file_id)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw: bytes = content.content if hasattr(content, "content") else content.read()
    text = raw.decode("utf-8")
    lines = [line for line in text.strip().split("\n") if line.strip()]
    with out.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return len(lines)


def parse_batch_output_jsonl(path: Path | str) -> list[tuple[str, list[float]]]:
    """Parse batch output JSONL into (custom_id, embedding) pairs. Skips error lines."""
    return _parse_batch_output_lines(Path(path))


def _parse_batch_output_lines(path: Path) -> list[tuple[str, list[float]]]:
    """Parse batch output JSONL to (custom_id, embedding) per successful line."""
    if not path.exists():
        return []
    out: list[tuple[str, list[float]]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("error") is not None:
                continue
            custom_id = row.get("custom_id")
            response = row.get("response", {})
            body = response.get("body", {}) if isinstance(response, dict) else {}
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list) or not data:
                continue
            emb = data[0].get("embedding") if isinstance(data[0], dict) else None
            if not isinstance(emb, list):
                continue
            if custom_id is not None:
                out.append((str(custom_id), emb))
    return out


def import_batch_results_into_chroma(
    results_path: Path | str,
    *,
    data_path: Path | str = DEFAULT_DATA_PATH,
    metadata_path: Path | str | None = None,
    persist_directory: Path | str | None = None,
    recreate: bool = False,
) -> int:
    """Load batch output JSONL and add embeddings into Chroma with metadata/documents.

    Reviews and metadata are loaded from data_path and metadata_path to build
    metadatas and document strings for each result id. Returns number of docs added.
    """
    path = Path(results_path)
    if not path.exists():
        msg = f"Results file not found: {path}"
        raise FileNotFoundError(msg)

    # Parse (custom_id, embedding) from batch output
    parsed = parse_batch_output_jsonl(path)
    if not parsed:
        return 0

    reviews = load_reviews_from_jsonl(Path(data_path))
    review_by_id = {r.id: r for r in reviews}
    meta_path = (
        Path(metadata_path) if metadata_path is not None else DEFAULT_METADATA_PATH
    )
    metadata_map = _load_metadata_map(meta_path, DEFAULT_METADATA_FALLBACK_PATH)

    # Optional: top community memberships per review (e.g. from resolution 10).
    # Stored in metadatas as communities_top_ids / communities_top_scores so that
    # resolution can be changed later without renaming fields.
    top_comms_map = _load_top_communities_for_reviews(
        resolve_data_path("data/album_community_affinities.jsonl"),
        res_key="res_10",
        top_k=3,
    )

    ids: list[str] = []
    embeddings: list[list[float]] = []
    metadatas: list[dict[str, Any]] = []
    documents: list[str] = []

    for custom_id, embedding in parsed:
        review = review_by_id.get(int(custom_id)) if custom_id.isdigit() else None
        if review is None:
            continue
        meta = metadata_map.get(review.id, {})
        rmeta = review_to_metadata(review)
        genres = meta.get("genres")
        if isinstance(genres, list) and genres:
            rmeta["genres"] = genres
        top_comms = top_comms_map.get(review.id)
        if top_comms:
            rmeta["communities_top_ids"] = [cid for cid, _ in top_comms]
            rmeta["communities_top_scores"] = [score for _cid, score in top_comms]
        ids.append(custom_id)
        embeddings.append(embedding)
        metadatas.append(rmeta)
        documents.append(build_enriched_document(review, meta))

    if not ids:
        return 0

    directory = (
        Path(persist_directory)
        if persist_directory is not None
        else DEFAULT_CHROMA_PATH
    )
    collection = get_chroma_collection(persist_directory=directory, recreate=recreate)
    # Add in chunks to avoid huge single requests
    chunk_size = 500
    added = 0
    for start in range(0, len(ids), chunk_size):
        end = start + chunk_size
        collection.add(
            ids=ids[start:end],
            embeddings=embeddings[start:end],
            metadatas=metadatas[start:end],
            documents=documents[start:end],
        )
        added += end - start
    return added


def build_index(
    data_path: Path | str = DEFAULT_DATA_PATH,
    *,
    metadata_path: Path | str | None = None,
    batch_size: int = 100,
    recreate: bool = False,
) -> int:
    """Index reviews from a JSONL file into the Chroma collection.

    The embedded text is enriched with metadata (artist, album, genres, year, etc.)
    so that semantic search can match on that context. The original review text
    is stored in metadata under "review_text" for display in search results.

    If `recreate` is False (default), only reviews whose IDs are not yet present
    in the collection are embedded and added.

    Returns the number of newly indexed reviews.
    """
    file_path = Path(data_path)
    if not file_path.exists():
        msg = f"Data file not found: {file_path}"
        raise FileNotFoundError(msg)

    reviews = load_reviews_from_jsonl(file_path)
    if not reviews:
        msg = f"No non-empty reviews found in {file_path}"
        raise RuntimeError(msg)

    meta_path = (
        Path(metadata_path) if metadata_path is not None else DEFAULT_METADATA_PATH
    )
    fallback_path = DEFAULT_METADATA_FALLBACK_PATH
    metadata_map = _load_metadata_map(meta_path, fallback_path)

    # Optional: top community memberships per review (e.g. from resolution 10).
    # Stored in metadatas as communities_top_ids / communities_top_scores so that
    # resolution can be changed later without renaming fields.
    top_comms_map = _load_top_communities_for_reviews(
        resolve_data_path("data/album_community_affinities.jsonl"),
        res_key="res_10",
        top_k=3,
    )

    if recreate:
        collection = get_chroma_collection(recreate=True)
        existing_ids: set[str] = set()
    else:
        collection = get_chroma_collection()
        existing_ids = _all_collection_document_ids(collection)

    new_count = 0

    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]

        batch = [r for r in batch if str(r.id) not in existing_ids]
        if not batch:
            continue

        ids = [str(r.id) for r in batch]
        metadatas = []
        for r in batch:
            m = review_to_metadata(r)
            genres = metadata_map.get(r.id, {}).get("genres")
            if isinstance(genres, list) and genres:
                m["genres"] = genres
            top_comms = top_comms_map.get(r.id)
            if top_comms:
                m["communities_top_ids"] = [cid for cid, _ in top_comms]
                m["communities_top_scores"] = [score for _cid, score in top_comms]
            metadatas.append(m)
        # Enriched document = metadata prefix + review body (for embedding).
        documents = [
            build_enriched_document(r, metadata_map.get(r.id, {})) for r in batch
        ]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

        existing_ids.update(ids)
        new_count += len(batch)

    return new_count


def build_index_chunks_v1(
    data_path: Path | str = DEFAULT_DATA_PATH,
    *,
    metadata_path: Path | str | None = None,
    batch_size: int = 50,
    recreate: bool = False,
    collection_name: str = CHUNK_COLLECTION_NAME,
    min_chunk_chars: int = 600,
    target_chunk_chars: int = 1600,
    max_chunk_chars: int = 2400,
) -> int:
    """Index review text into chunk-level Chroma embeddings (v1).

    Creates one Chroma document per text chunk. The embedded document is the
    chunk text only (no metadata prefix).

    Returns the number of newly added chunks.
    """
    max_requests_per_file = 2500

    total_new_chunks, input_paths = write_batch_embedding_input_chunks_v1(
        output_path=DEFAULT_CHUNK_BATCH_INPUT_PATH,
        data_path=data_path,
        _metadata_path=metadata_path,
        skip_existing=True,
        max_requests_per_file=max_requests_per_file,
        persist_directory=DEFAULT_CHROMA_PATH,
        recreate=recreate,
        collection_name=collection_name,
        min_chunk_chars=min_chunk_chars,
        target_chunk_chars=target_chunk_chars,
        max_chunk_chars=max_chunk_chars,
        batch_size=batch_size,
    )

    if total_new_chunks == 0:
        return 0

    added_total = 0
    for idx, inp in enumerate(input_paths):
        batch_id = submit_batch_embedding_job(inp)
        _ = poll_batch_until_complete(batch_id)

        results_part_path = resolve_data_path(
            f"data/batch_embedding_results_chunks_v1_part_{idx:05d}.jsonl"
        )
        download_batch_results(batch_id, results_part_path)

        added_total += import_batch_results_into_chroma_chunks_v1(
            results_part_path,
            data_path=data_path,
            _metadata_path=metadata_path,
            persist_directory=DEFAULT_CHROMA_PATH,
            recreate=False,
            collection_name=collection_name,
            min_chunk_chars=min_chunk_chars,
            target_chunk_chars=target_chunk_chars,
            max_chunk_chars=max_chunk_chars,
        )

    return added_total


def search_reviews(
    query_text: str,
    *,
    n_results: int = 5,
    where: dict[str, Any] | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Search similar reviews for a free-text query.

    Optional `where` allows metadata filtering (e.g. {"release_year": {"$gte": 2010}}).
    """
    collection = get_chroma_collection(
        collection_name=collection_name or COLLECTION_NAME,
    )

    query_kwargs: dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": n_results,
    }
    if where is not None:
        query_kwargs["where"] = where

    result = collection.query(**query_kwargs)

    hits: list[dict[str, Any]] = []

    ids = result.get("ids", [[]])[0]
    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    for doc_id, doc, meta, dist in zip(
        ids, documents, metadatas, distances, strict=False
    ):
        meta = meta or {}

        # Old index: doc_id is the review id.
        # New chunk index: doc_id is "review_id__chunk_N" but meta["review_id"]
        # is the stable join key.
        review_id_val = meta.get("review_id")
        review_id: int | None
        if isinstance(review_id_val, int):
            review_id = review_id_val
        else:
            try:
                if review_id_val is not None:
                    review_id = int(review_id_val)
                else:
                    review_id = int(doc_id)
            except (TypeError, ValueError):
                review_id = None

        chunk_text = meta.get("chunk_text") or meta.get("review_text") or doc
        chunk_index = meta.get("chunk_index")

        hits.append(
            {
                # Keep `id` review-id compatible for legacy callers.
                "id": str(review_id) if review_id is not None else doc_id,
                "review_id": review_id,
                "chunk_index": chunk_index,
                "chunk_text": chunk_text,
                # Existing UI uses `text` as snippet; keep it aligned with chunk_text.
                "text": chunk_text,
                "distance": float(dist) if isinstance(dist, (int, float)) else dist,
                "url": meta.get("url"),
                "artist": meta.get("artist"),
                "album": meta.get("album"),
                "title": meta.get("title"),
                "author": meta.get("author"),
                "labels": meta.get("labels"),
                "release_date": meta.get("release_date"),
                "release_year": meta.get("release_year"),
                "rating": meta.get("rating"),
                "user_rating": meta.get("user_rating"),
                "highlights": meta.get("highlights"),
                "references": meta.get("references"),
                "total_duration": meta.get("total_duration"),
                "genres": meta.get("genres") or [],
                "communities_top_ids": meta.get("communities_top_ids") or [],
                "communities_top_scores": meta.get("communities_top_scores") or [],
            }
        )

    return hits


def _l2_distance_vec(a: list[float], b: list[float]) -> float:
    """Euclidean distance between two embedding vectors (Chroma default ``l2``)."""
    if len(a) != len(b):
        msg = f"Embedding dimension mismatch: {len(a)} vs {len(b)}"
        raise ValueError(msg)
    s = 0.0
    for x, y in zip(a, b, strict=True):
        d = float(x) - float(y)
        s += d * d
    return math.sqrt(s)


def embed_query_vector(query_text: str) -> list[float]:
    """Embed ``query_text`` with the same OpenAI model as the Chroma collections."""
    client = _get_openai_client()
    q = query_text.strip()
    if not q:
        msg = "Empty query text for embedding."
        raise ValueError(msg)
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=q)
    data0 = resp.data[0]
    emb = getattr(data0, "embedding", None) if data0 is not None else None
    if emb is None:
        msg = "OpenAI embeddings response missing embedding."
        raise RuntimeError(msg)
    return [float(x) for x in emb]


def semantic_distance_map_for_review_ids(
    query_text: str,
    review_ids: list[int],
    *,
    collection_name: str | None = None,
    batch_size: int = 40,
) -> dict[int, float | None]:
    """Minimum L2 distance from one query embedding to stored vectors per review.

    - **Chunk index** (``CHUNK_COLLECTION_NAME``): minimum over all chunks of that
      review (same idea as fusion dedupe).
    - **Legacy index** (``COLLECTION_NAME``): single vector per review id.

    Missing reviews (not in Chroma) map to ``None``.

    Uses one OpenAI embedding call for ``query_text``, then batched
    ``collection.get``. Distances are comparable to Chroma ``query`` distances when
    the collection uses the default ``l2`` space (project default).

    Note: Multi-variant fusion can yield **different** per-review distances than
    this single-query embedding because variants are not applied here.
    """
    name = collection_name or COLLECTION_NAME
    if not review_ids:
        return {}

    qvec = embed_query_vector(query_text)
    collection = get_chroma_collection(collection_name=name)

    unique_ids = list(dict.fromkeys(review_ids))
    out: dict[int, float | None] = dict.fromkeys(unique_ids)

    is_chunks = name == CHUNK_COLLECTION_NAME

    for i in range(0, len(unique_ids), batch_size):
        batch = unique_ids[i : i + batch_size]
        if is_chunks:
            got = collection.get(
                where={"review_id": {"$in": batch}},
                include=["embeddings", "metadatas"],
            )
        else:
            got = collection.get(
                ids=[str(rid) for rid in batch],
                include=["embeddings", "metadatas"],
            )

        embs = got.get("embeddings")
        metas = got.get("metadatas") or []

        if embs is None:
            continue
        # Chroma may return ndarray; bool(ndarray) is ambiguous (avoid `if not embs`).
        try:
            if len(embs) == 0:
                continue
        except TypeError:
            continue

        ids_out = got.get("ids") or []

        if is_chunks:
            by_rid: dict[int, list[list[float]]] = defaultdict(list)
            for emb, meta in zip(embs, metas, strict=False):
                if emb is None:
                    continue
                meta = meta or {}
                rv = meta.get("review_id")
                if not isinstance(rv, int):
                    try:
                        rv = int(rv) if rv is not None else None
                    except (TypeError, ValueError):
                        rv = None
                if rv is None:
                    continue
                by_rid[rv].append([float(x) for x in emb])

            for rid in batch:
                chunks = by_rid.get(rid)
                if not chunks:
                    continue
                out[rid] = min(_l2_distance_vec(qvec, c) for c in chunks)
        else:
            for doc_id, emb in zip(ids_out, embs, strict=False):
                if emb is None:
                    continue
                try:
                    rid = int(doc_id)
                except (TypeError, ValueError):
                    continue
                out[rid] = _l2_distance_vec(qvec, [float(x) for x in emb])

    return out


def _normalize_query_text(query_text: str) -> str:
    """Normalize query for rule-based variant generation."""
    q = query_text.strip().lower()
    q = re.sub(r"\s+", " ", q)
    return q


_QUERY_SYNONYMS: dict[str, list[str]] = {
    "spröde": ["karg", "trocken", "austere"],
    "sproede": ["karg", "trocken", "austere"],
    "monoton": ["gleichförmig", "repetitiv", "monotone"],
    "langsam": ["ruhig", "slow", "slow-burn"],
    "aufbau": ["steigerung", "build-up", "crescendo"],
    "höhepunkt": ["climax", "peak", "kulmination"],
    "gaensehaut": ["gänsehaut", "goosebumps", "goosebump"],
    "gänsehaut": ["gaensehaut", "goosebumps", "goosebump"],
}


def generate_query_variants(
    query_text: str,
    *,
    strategy: str = "B",
    max_variants: int = 4,
) -> list[str]:
    """Generate query variants for multi-query retrieval.

    Strategies:
    - A: original query only
    - B: rule-based DE/EN variants (default)
    - C: stronger expansion (B + structured intent variant)
    """
    original = query_text.strip()
    if not original:
        return []
    if strategy.upper() == "A":
        return [original]

    normalized = _normalize_query_text(original)
    tokens = re.findall(r"[a-zA-ZäöüÄÖÜß]+", normalized)

    expansions: list[str] = []
    for t in tokens:
        key = t.replace("ß", "ss")
        syns = _QUERY_SYNONYMS.get(t) or _QUERY_SYNONYMS.get(key) or []
        expansions.extend(syns)

    # Keep stable unique order.
    seen: set[str] = set()
    unique_expansions: list[str] = []
    for e in expansions:
        if e not in seen:
            unique_expansions.append(e)
            seen.add(e)

    variants: list[str] = [original]
    if unique_expansions:
        de_variant = f"{original} {' '.join(unique_expansions[:4])}".strip()
        en_hint = " ".join(e for e in unique_expansions if re.search(r"[a-zA-Z]", e))
        en_variant = f"{original} {en_hint}".strip()
        mixed_variant = (
            f"music mood {' '.join(tokens[:6])} {' '.join(unique_expansions[:5])}"
        ).strip()
        variants.extend([de_variant, en_variant, mixed_variant])
    else:
        # Fallback variants when no dictionary expansion is available.
        variants.extend(
            [
                f"{original} music mood",
                f"{original} song structure atmosphere",
                f"{original} review passage",
            ],
        )

    if strategy.upper() == "C":
        # C adds one intent-focused variant on top of B.
        intent_variant = (
            f"find review passage about: {original}; "
            "mood, dynamics, structure, instrumentation"
        )
        variants.append(intent_variant)

    # Stable unique while preserving order.
    out: list[str] = []
    out_seen: set[str] = set()
    for v in variants:
        vv = v.strip()
        if not vv or vv in out_seen:
            continue
        out.append(vv)
        out_seen.add(vv)

    return out[: max(1, max_variants)]


def search_reviews_with_variants(
    query_text: str,
    *,
    strategy: str = "B",
    n_results: int = 100,
    top_k_per_variant: int = 30,
    where: dict[str, Any] | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Run multi-variant retrieval and fuse per-review hits.

    Fusion:
    - Deduplicate by `review_id`.
    - Keep the best (smallest) distance chunk as representative.
    - For strategy C, apply a small vote/rank bonus to prioritize reviews found
      consistently across variants.
    """
    variants = generate_query_variants(query_text, strategy=strategy, max_variants=5)
    if not variants:
        return []

    # review_id -> aggregate
    agg: dict[int, dict[str, Any]] = {}
    # review_id -> number of variants where it appeared
    votes: dict[int, int] = {}
    # review_id -> rank bonus accumulator
    rank_bonus: dict[int, float] = {}

    for v in variants:
        hits = search_reviews(
            v,
            n_results=top_k_per_variant,
            where=where,
            collection_name=collection_name,
        )
        seen_in_variant: set[int] = set()
        for rank, h in enumerate(hits, start=1):
            rid = h.get("review_id")
            dist = h.get("distance")
            if not isinstance(rid, int) or not isinstance(dist, (int, float)):
                continue

            prev = agg.get(rid)
            if prev is None or float(dist) < float(prev.get("distance", 999.0)):
                agg[rid] = h

            # Count each review once per variant.
            if rid not in seen_in_variant:
                votes[rid] = votes.get(rid, 0) + 1
                # Reciprocal-rank style bonus (higher is better).
                rank_bonus[rid] = rank_bonus.get(rid, 0.0) + (1.0 / (50.0 + rank))
                seen_in_variant.add(rid)

    fused = list(agg.values())
    if not fused:
        return []

    strat = strategy.upper()
    if strat == "C":
        # Lower score is better: distance minus agreement bonus.
        def _score(item: dict[str, Any]) -> float:
            rid = item.get("review_id")
            dist = float(item.get("distance") or 999.0)
            if not isinstance(rid, int):
                return dist
            vote_bonus = 0.015 * votes.get(rid, 0)
            rr_bonus = 0.75 * rank_bonus.get(rid, 0.0)
            return dist - vote_bonus - rr_bonus

        fused.sort(key=_score)
    else:
        # A and B: pure semantic distance ordering after dedupe.
        fused.sort(key=lambda h: float(h.get("distance") or 999.0))

    return fused[:n_results]


def main() -> None:
    """Build the index and run a small demo query."""
    new_count = build_index(recreate=True)
    print(f"Indexed {new_count} new reviews into collection '{COLLECTION_NAME}'.")

    demo_query = "Grunge-Platte mit schönen Melodien"
    results = search_reviews(demo_query, n_results=3)

    print(f"\nQuery: {demo_query}\n")
    for i, hit in enumerate(results, start=1):
        print(f"Result #{i}")
        print(f"  id:      {hit['id']}")
        print(f"  artist:  {hit['artist']}")
        print(f"  album:   {hit['album']}")
        print(f"  title:   {hit['title']}")
        print(f"  url:     {hit['url']}")
        print(f"  rating:  {hit['rating']} (users: {hit['user_rating']})")
        print(f"  year:    {hit['release_year']}")
        print(f"  labels:  {hit['labels']}")
        print(f"  references:  {hit['references']}")
        print(f"  dist.:   {hit['distance']:.4f}")
        print(f"  text:    {hit['text'][:200]}...")
        print()


if __name__ == "__main__":
    main()
