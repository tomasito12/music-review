"""Tests for chroma_repo module (uses a mock collection)."""

from __future__ import annotations

from music_review.pipeline.retrieval.chroma_repo import all_collection_document_ids


class _FakeCollection:
    """Minimal mock that emulates Chroma's paginated .get()."""

    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def get(
        self,
        *,
        limit: int = 100,
        offset: int = 0,
        include: list[str] | None = None,
    ) -> dict[str, list[str]]:
        page = self._ids[offset : offset + limit]
        return {"ids": page}


class TestAllCollectionDocumentIds:
    def test_empty_collection(self) -> None:
        coll = _FakeCollection([])
        assert all_collection_document_ids(coll) == set()

    def test_single_page(self) -> None:
        coll = _FakeCollection(["1", "2", "3"])
        result = all_collection_document_ids(coll, page_size=10)
        assert result == {"1", "2", "3"}

    def test_multiple_pages(self) -> None:
        ids = [str(i) for i in range(7)]
        coll = _FakeCollection(ids)
        result = all_collection_document_ids(coll, page_size=3)
        assert result == set(ids)

    def test_exact_page_boundary(self) -> None:
        ids = [str(i) for i in range(6)]
        coll = _FakeCollection(ids)
        result = all_collection_document_ids(coll, page_size=3)
        assert result == set(ids)
