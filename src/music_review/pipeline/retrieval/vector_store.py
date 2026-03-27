# music_review/pipeline/retrieval/vector_store.py

"""Orchestration layer for indexing, batch import, and metadata building.

Pure logic (chunking, search, Chroma access, batch API lifecycle) lives in
dedicated sub-modules. This module wires them together and re-exports all
public names so that existing callers continue to work unchanged.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from music_review.config import get_project_root, resolve_data_path
from music_review.domain.models import Review
from music_review.io.jsonl import iter_jsonl_objects, load_jsonl_as_map, write_jsonl
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

# Re-export from sub-modules so callers that import from vector_store keep working.
from music_review.pipeline.retrieval.batch_api import (  # noqa: F401
    BATCH_COMPLETION_WINDOW,
    DEFAULT_BATCH_INPUT_PATH,
    DEFAULT_CHUNK_BATCH_INPUT_PATH,
    DEFAULT_CHUNK_BATCH_RESULTS_PATH,
    _get_attr_or_key,
    _get_openai_client,
    _parse_batch_output_lines,
    download_batch_results,
    embed_query_vector,
    get_batch_error_details,
    is_token_limit_error,
    parse_batch_output_jsonl,
    poll_batch_until_complete,
    submit_batch_embedding_job,
)
from music_review.pipeline.retrieval.chroma_repo import (
    CHUNK_COLLECTION_NAME,
    COLLECTION_NAME,
    DEFAULT_CHROMA_PATH,
    EMBEDDING_MODEL,
    all_collection_document_ids,
    get_chroma_collection,
)
from music_review.pipeline.retrieval.chunking import (  # noqa: F401
    _hard_split_by_chars,
    _split_paragraph_into_sentences,
    _split_text_into_paragraphs,
    hybrid_chunk_text,
)
from music_review.pipeline.retrieval.search import (  # noqa: F401
    _QUERY_SYNONYMS,
    _l2_distance_vec,
    _normalize_query_text,
    generate_query_variants,
    search_reviews,
    search_reviews_with_variants,
    semantic_distance_map_for_review_ids,
)

# Keep the old private name available for any internal callers.
_all_collection_document_ids = all_collection_document_ids

PROJECT_ROOT = get_project_root()
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "reviews.jsonl"
DEFAULT_METADATA_PATH = resolve_data_path("data/metadata_imputed.jsonl")
DEFAULT_METADATA_FALLBACK_PATH = resolve_data_path("data/metadata.jsonl")


# ---------------------------------------------------------------------------
# Metadata / document helpers
# ---------------------------------------------------------------------------


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

    Unlike ``review_to_metadata``, this stores only the scalar fields needed for
    filtering and display, and it stores ``chunk_text`` for snippet rendering.
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
# Batch embedding input preparation
# ---------------------------------------------------------------------------


def _parse_chunk_custom_id(custom_id: str) -> tuple[int, int]:
    """Parse chunk custom_id formatted as '{review_id}__chunk_{chunk_index}'."""
    review_part, chunk_part = custom_id.rsplit("__chunk_", 1)
    return int(review_part), int(chunk_part)


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
    If max_requests_per_file is set, splits into multiple files.

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
            existing_ids = all_collection_document_ids(collection)
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

    collection = get_chroma_collection(
        persist_directory=directory,
        recreate=recreate,
        collection_name=collection_name,
    )
    existing_ids: set[str] = set()
    if skip_existing and not recreate:
        existing_ids = all_collection_document_ids(collection)

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


# ---------------------------------------------------------------------------
# Chroma import
# ---------------------------------------------------------------------------


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
        existing_ids = all_collection_document_ids(collection)

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

    parsed = parse_batch_output_jsonl(path)
    if not parsed:
        return 0

    reviews = load_reviews_from_jsonl(Path(data_path))
    review_by_id = {r.id: r for r in reviews}
    meta_path = (
        Path(metadata_path) if metadata_path is not None else DEFAULT_METADATA_PATH
    )
    metadata_map = _load_metadata_map(meta_path, DEFAULT_METADATA_FALLBACK_PATH)

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


# ---------------------------------------------------------------------------
# Index building (online, via Chroma embedding function)
# ---------------------------------------------------------------------------


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
        existing_ids = all_collection_document_ids(collection)

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
