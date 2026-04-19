"""Semantic search, query variant generation, and distance utilities."""

from __future__ import annotations

import math
import re
from collections import defaultdict
from typing import Any

from music_review.pipeline.retrieval.batch_api import embed_query_vector
from music_review.pipeline.retrieval.chroma_repo import (
    CHUNK_COLLECTION_NAME,
    COLLECTION_NAME,
    get_chroma_collection,
)


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
        variants.extend(
            [
                f"{original} music mood",
                f"{original} song structure atmosphere",
                f"{original} review passage",
            ],
        )

    if strategy.upper() == "C":
        intent_variant = (
            f"find review passage about: {original}; "
            "mood, dynamics, structure, instrumentation"
        )
        variants.append(intent_variant)

    out: list[str] = []
    out_seen: set[str] = set()
    for v in variants:
        vv = v.strip()
        if not vv or vv in out_seen:
            continue
        out.append(vv)
        out_seen.add(vv)

    return out[: max(1, max_variants)]


def search_reviews(
    query_text: str,
    *,
    n_results: int = 5,
    where: dict[str, Any] | None = None,
    collection_name: str | None = None,
) -> list[dict[str, Any]]:
    """Search similar reviews for a free-text query.

    Optional ``where`` allows metadata filtering
    (e.g. ``{"release_year": {"$gte": 2010}}``).
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
        review_id = _extract_review_id(meta, doc_id)
        chunk_text = meta.get("chunk_text") or meta.get("review_text") or doc

        hits.append(
            {
                "id": str(review_id) if review_id is not None else doc_id,
                "review_id": review_id,
                "chunk_index": meta.get("chunk_index"),
                "chunk_text": chunk_text,
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


def _extract_review_id(meta: dict[str, Any], doc_id: str) -> int | None:
    """Extract review_id from Chroma metadata or doc_id."""
    review_id_val = meta.get("review_id")
    if isinstance(review_id_val, int):
        return review_id_val
    try:
        if review_id_val is not None:
            return int(review_id_val)
        return int(doc_id)
    except (TypeError, ValueError):
        return None


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
    - Deduplicate by ``review_id``.
    - Keep the best (smallest) distance chunk as representative.
    - For strategy C, apply a small vote/rank bonus to prioritize reviews found
      consistently across variants.
    """
    variants = generate_query_variants(query_text, strategy=strategy, max_variants=5)
    if not variants:
        return []

    agg: dict[int, dict[str, Any]] = {}
    votes: dict[int, int] = {}
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

            if rid not in seen_in_variant:
                votes[rid] = votes.get(rid, 0) + 1
                rank_bonus[rid] = rank_bonus.get(rid, 0.0) + (1.0 / (50.0 + rank))
                seen_in_variant.add(rid)

    fused = list(agg.values())
    if not fused:
        return []

    strat = strategy.upper()
    if strat == "C":

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
        fused.sort(key=lambda h: float(h.get("distance") or 999.0))

    return fused[:n_results]


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
