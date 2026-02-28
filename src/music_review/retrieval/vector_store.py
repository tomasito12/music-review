# music_review/retrieval/vector_store.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api.models import Collection
from chromadb.utils import embedding_functions

import music_review.config  # noqa: F401 - load .env early
from music_review.config import get_project_root
from music_review.domain.models import Review
from music_review.io.reviews_jsonl import load_reviews_from_jsonl

PROJECT_ROOT = get_project_root()
DEFAULT_DATA_PATH = PROJECT_ROOT / "data" / "reviews.jsonl"
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

    return meta


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


def build_index(
    data_path: Path | str = DEFAULT_DATA_PATH,
    *,
    batch_size: int = 100,
    recreate: bool = False,
) -> int:
    """Index reviews from a JSONL file into the Chroma collection.

    If `recreate` is False (default), only reviews whose IDs are not yet present
    in the collection are embedded and added. This avoids paying twice for the
    same embeddings.

    If `recreate` is True, the collection is dropped and rebuilt from scratch.

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

    if recreate:
        # Fresh collection, no existing IDs.
        collection = get_chroma_collection(recreate=True)
        existing_ids: set[str] = set()
    else:
        collection = get_chroma_collection()
        existing = collection.get(limit=100_000_000)
        existing_ids = set(existing.get("ids", []))

    new_count = 0

    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]

        # Keep only reviews that are not already in the collection.
        batch = [r for r in batch if str(r.id) not in existing_ids]
        if not batch:
            continue

        ids = [str(r.id) for r in batch]
        documents = [r.text for r in batch]
        metadatas = [review_to_metadata(r) for r in batch]

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
        hits.append(
            {
                "id": doc_id,
                "text": doc,
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
