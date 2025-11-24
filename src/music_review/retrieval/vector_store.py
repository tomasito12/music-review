# music_review/retrieval/vector_store.py

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List

import chromadb
from chromadb.api.models import Collection
from chromadb.utils import embedding_functions

from music_review.io.reviews_jsonl import load_reviews_from_jsonl
from music_review.scraper.models import Review

DEFAULT_DATA_PATH = Path("data/reviews.jsonl")
DEFAULT_CHROMA_PATH = Path("chroma_db")
COLLECTION_NAME = "music_reviews"
EMBEDDING_MODEL = "text-embedding-3-small"


def review_to_metadata(review: Review) -> Dict[str, Any]:
    """Convert a Review into a flat metadata dict for Chroma."""
    return {
        "url": review.url,
        "artist": review.artist,
        "album": review.album,
        "title": review.title,
        "author": review.author,
        "labels": review.labels,
        "release_date": (
            review.release_date.isoformat() if review.release_date else None
        ),
        "release_year": review.release_year,
        "rating": review.rating,
        "user_rating": review.user_rating,
        "highlights": review.highlights,
        "total_duration": review.total_duration,
        # tracklist, raw_html, extra can be added later if needed
    }


def get_chroma_collection(
    persist_directory: Path | str | None = None,
) -> Collection:
    """Create or load the Chroma collection configured with OpenAI embeddings."""
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
    """Index all reviews from a JSONL file into the Chroma collection.

    Returns the number of indexed reviews.
    """
    file_path = Path(data_path)
    if not file_path.exists():
        msg = f"Data file not found: {file_path}"
        raise FileNotFoundError(msg)

    reviews = load_reviews_from_jsonl(file_path)
    if not reviews:
        msg = f"No non-empty reviews found in {file_path}"
        raise RuntimeError(msg)

    collection = get_chroma_collection()

    if recreate:
        collection.delete(where={})

    for start in range(0, len(reviews), batch_size):
        batch = reviews[start : start + batch_size]

        ids = [str(r.id) for r in batch]
        documents = [r.text for r in batch]
        metadatas = [review_to_metadata(r) for r in batch]

        collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    return len(reviews)


def search_reviews(
    query_text: str,
    *,
    n_results: int = 5,
    where: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    """Search similar reviews for a free-text query.

    Optional `where` allows metadata filtering (e.g. {"release_year": {"$gte": 2010}}).
    """
    collection = get_chroma_collection()

    query_kwargs: Dict[str, Any] = {
        "query_texts": [query_text],
        "n_results": n_results,
    }
    if where is not None:
        query_kwargs["where"] = where

    result = collection.query(**query_kwargs)

    hits: List[Dict[str, Any]] = []

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
                "total_duration": meta.get("total_duration"),
            }
        )

    return hits


def main() -> None:
    """Build the index and run a small demo query."""
    count = build_index()
    print(f"Indexed {count} reviews into collection '{COLLECTION_NAME}'.")

    demo_query = "humorvolle Rockplatte mit Weltreise-Thema"
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
        print(f"  dist.:   {hit['distance']:.4f}")
        print(f"  text:    {hit['text'][:200]}...")
        print()


if __name__ == "__main__":
    main()
