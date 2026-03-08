# music_review/pipeline/retrieval/vector_store.py

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models import Collection
from chromadb.utils import embedding_functions
from openai import OpenAI

import music_review.config  # noqa: F401 - load .env early
from music_review.config import get_project_root, resolve_data_path
from music_review.domain.models import Review
from music_review.io.jsonl import load_jsonl_as_map, write_jsonl
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

PROJECT_ROOT = get_project_root()
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "reviews.jsonl"
DEFAULT_METADATA_PATH = resolve_data_path("data/metadata_imputed.jsonl")
DEFAULT_METADATA_FALLBACK_PATH = resolve_data_path("data/metadata.jsonl")
DEFAULT_CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "music_reviews"
EMBEDDING_MODEL = "text-embedding-3-small"


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


def build_enriched_document(review: Review, meta: dict[str, Any]) -> str:
    """Build the text to embed: metadata prefix (artist, album, genres, etc.) + review body.

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
) -> Collection:
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
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            # If it does not exist yet, that's fine.
            pass

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=openai_ef,
    )
    return collection


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
BATCH_COMPLETION_WINDOW = "24h"


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
            existing = collection.get(limit=100_000_000)
            existing_ids = set(existing.get("ids", []))
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
    if _get_attr_or_key(batch, "status") == "failed" and "Batch-level errors:" not in "\n".join(lines) and not efile:
        lines.append(
            "No error details in response. Check https://platform.openai.com/batches "
            "for validation/input errors or account limits."
        )
    return "\n".join(lines)


def is_token_limit_error(batch_id: str) -> bool:
    """Return True if the batch failed due to enqueued token limit (retry after wait)."""
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

    if recreate:
        collection = get_chroma_collection(recreate=True)
        existing_ids: set[str] = set()
    else:
        collection = get_chroma_collection()
        existing = collection.get(limit=100_000_000)
        existing_ids = set(existing.get("ids", []))

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


def search_reviews(
    query_text: str,
    *,
    n_results: int = 5,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Search similar reviews for a free-text query.

    Optional `where` allows metadata filtering (e.g. {"release_year": {"$gte": 2010}}).
    """
    collection = get_chroma_collection()

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

    for doc_id, doc, meta, dist in zip(ids, documents, metadatas, distances):
        # Prefer stored original review text for display; fallback to document.
        text = (meta or {}).get("review_text") or doc
        hits.append(
            {
                "id": doc_id,
                "text": text,
                "distance": dist,
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
            }
        )

    return hits


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
