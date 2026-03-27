from __future__ import annotations

from pathlib import Path
from typing import Any

from chromadb.api.models import Collection

from music_review.config import resolve_data_path
from music_review.io.jsonl import iter_jsonl_objects
from music_review.pipeline.retrieval.vector_store import (
    COLLECTION_NAME,
    DEFAULT_CHROMA_PATH,
    get_chroma_collection,
)


def load_top_communities_for_reviews(
    affinities_path: Path,
    *,
    res_key: str = "res_10",
    top_k: int = 3,
) -> dict[int, list[tuple[str, float]]]:
    """review_id -> top-k (community_id, score) for given resolution key."""
    if not affinities_path.exists():
        raise FileNotFoundError(f"Affinities file not found: {affinities_path}")

    result: dict[int, list[tuple[str, float]]] = {}
    for obj in iter_jsonl_objects(affinities_path, log_errors=False):
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


def update_chroma_communities(
    *,
    res_key: str = "res_10",
    top_k: int = 3,
    persist_directory: Path | None = None,
) -> int:
    """Add/refresh communities_top_ids/_scores in existing Chroma collection.

    Returns number of documents that were updated.
    """
    data_dir = resolve_data_path("data")
    affinities_path = data_dir / "album_community_affinities.jsonl"
    top_map = load_top_communities_for_reviews(
        affinities_path, res_key=res_key, top_k=top_k
    )
    if not top_map:
        print(f"No communities found in {affinities_path} for key {res_key}.")
        return 0

    directory = persist_directory or DEFAULT_CHROMA_PATH
    collection: Collection = get_chroma_collection(persist_directory=directory)

    # Fetch all existing docs (ids + metadatas)
    existing = collection.get(limit=100_000_000)
    ids: list[str] = existing.get("ids") or []
    metadatas: list[dict[str, Any] | None] = existing.get("metadatas") or []

    if not ids:
        print(f"No documents found in collection '{COLLECTION_NAME}'.")
        return 0

    updates_ids: list[str] = []
    updates_metas: list[dict[str, Any]] = []

    for doc_id, meta in zip(ids, metadatas, strict=False):
        # Chroma always stores ids as str; our review_ids sind ints.
        try:
            review_id = int(doc_id)
        except (ValueError, TypeError):
            continue
        top = top_map.get(review_id)
        if not top:
            continue

        current = dict(meta or {})
        current["communities_top_ids"] = [cid for cid, _ in top]
        current["communities_top_scores"] = [score for _cid, score in top]

        updates_ids.append(doc_id)
        updates_metas.append(current)

    if not updates_ids:
        print("No matching reviews between Chroma and affinities file.")
        return 0

    # In sinnvollen Batches updaten (z.B. 500)
    batch_size = 500
    for start in range(0, len(updates_ids), batch_size):
        end = start + batch_size
        collection.update(
            ids=updates_ids[start:end],
            metadatas=updates_metas[start:end],
        )

    print(
        f"Updated {len(updates_ids)} documents in collection "
        f"'{COLLECTION_NAME}' with communities_top_ids/_scores."
    )
    return len(updates_ids)


def main() -> None:
    update_chroma_communities()


if __name__ == "__main__":
    main()
