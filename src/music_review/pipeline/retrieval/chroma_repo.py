"""Chroma collection management and configuration constants."""

from __future__ import annotations

import os
from contextlib import suppress
from pathlib import Path
from typing import Any, cast

import chromadb
from chromadb.utils import embedding_functions

from music_review.config import get_project_root

PROJECT_ROOT = get_project_root()
DEFAULT_CHROMA_PATH = PROJECT_ROOT / "chroma_db"
COLLECTION_NAME = "music_reviews"
CHUNK_COLLECTION_NAME = "music_reviews_chunks_v1"
EMBEDDING_MODEL = "text-embedding-3-small"


def get_chroma_collection(
    persist_directory: Path | str | None = None,
    *,
    recreate: bool = False,
    collection_name: str = COLLECTION_NAME,
) -> Any:
    """Create or load the Chroma collection configured with OpenAI embeddings.

    If ``recreate`` is True, the existing collection (if any) is deleted first.
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
        with suppress(Exception):
            client.delete_collection(collection_name)

    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=cast(Any, openai_ef),
    )
    return collection


def all_collection_document_ids(
    collection: Any,
    *,
    page_size: int = 2000,
) -> set[str]:
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
