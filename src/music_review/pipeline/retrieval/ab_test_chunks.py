"""A/B test: old review-level index vs new chunk-level index.

Compares freetext query results in terms of:
- top-N hits and distance values
- whether specific target reviews appear in top results
- distance summary stats
"""

from __future__ import annotations

import statistics
from typing import Any

from music_review.pipeline.retrieval.vector_store import (
    CHUNK_COLLECTION_NAME,
    COLLECTION_NAME,
    generate_query_variants,
    get_chroma_collection,
    search_reviews,
    search_reviews_with_variants,
)


def _distance_stats(distances: list[float]) -> dict[str, Any]:
    if not distances:
        return {"count": 0}
    return {
        "count": len(distances),
        "min": min(distances),
        "median": statistics.median(distances),
        "mean": statistics.mean(distances),
        "max": max(distances),
    }


def _top_hit_str(h: dict[str, Any]) -> str:
    artist = h.get("artist") or ""
    album = h.get("album") or ""
    rid = h.get("review_id")
    dist = h.get("distance")
    if rid is None:
        rid_part = ""
    else:
        rid_part = f" (id={rid})"
    return f"{artist} — {album}{rid_part} dist={dist:.4f}" if isinstance(dist, (int, float)) else f"{artist} — {album}{rid_part} dist=?"


def _find_target_ranks(
    hits: list[dict[str, Any]],
    target_review_ids: list[int],
) -> dict[int, list[tuple[int, float | None]]]:
    """Return ranking positions for targets within the provided hit list."""
    ranks: dict[int, list[tuple[int, float | None]]] = {tid: [] for tid in target_review_ids}
    for idx, h in enumerate(hits, start=1):
        rid = h.get("review_id")
        if not isinstance(rid, int) or rid not in ranks:
            continue
        dist = h.get("distance")
        ranks[rid].append((idx, float(dist) if isinstance(dist, (int, float)) else None))
    return ranks


def _print_target_ranks(
    *,
    hits: list[dict[str, Any]],
    target_review_ids: list[int],
    top_label: str,
) -> None:
    """Print ranks for target reviews in a given result window."""
    target_ranks = _find_target_ranks(hits, target_review_ids)
    for target_id in target_review_ids:
        ranks = target_ranks.get(target_id) or []
        if not ranks:
            print(f"  target review {target_id}: not in {top_label}")
            continue
        rank_str = ", ".join(
            f"rank={rank} dist={dist:.4f}" if isinstance(dist, float) else f"rank={rank} dist=?"
            for rank, dist in ranks
        )
        best_hit = next(h for h in hits if h.get("review_id") == target_id)
        snippet_source = best_hit.get("chunk_text") or best_hit.get("text") or ""
        snippet_preview = snippet_source.replace("\n", " ")[:140]
        print(f"  target review {target_id}: {rank_str} | snippet={snippet_preview!r}")


def run_ab_test() -> None:
    freetext_queries = [
        # Derived from the target review bodies so the test hits are meaningful
        # for comparing snippet quality.
        "schrecklich langen Atem, Pulver schon verschossen",
        "I'll put a spell on you, you'll fall asleep, Strange & beautiful",
    ]

    # Target review ids from the plan.
    target_review_ids = [2624, 1347]

    top_n = 25
    rank_probe_n = 5000

    collections = [("old_review_index", COLLECTION_NAME)]

    print("== Chroma collection sizes ==")
    for label, name in collections:
        collection = get_chroma_collection(collection_name=name)
        try:
            count = collection.count()
        except Exception:
            count = None
        print(f"- {label} ({name}): count={count}")
    print()

    for query in freetext_queries:
        print(f"== Query: {query!r} ==")
        for label, name in collections:
            print(f"-- {label} ({name}) --")
            try:
                hits = search_reviews(query, n_results=top_n, collection_name=name)
            except Exception as e:
                print(f"Search failed: {e}")
                continue

            distances: list[float] = [
                float(h["distance"]) for h in hits if isinstance(h.get("distance"), (int, float))
            ]
            print(f"Returned hits: {len(hits)}; distance stats: {_distance_stats(distances)}")

            # Top-3 preview.
            top3 = hits[:3]
            for i, h in enumerate(top3, start=1):
                print(f"  {i}. {_top_hit_str(h)}")

            # Target-review appearance in top-N.
            _print_target_ranks(
                hits=hits,
                target_review_ids=target_review_ids,
                top_label=f"top-{top_n}",
            )
            # Extended probe to estimate global rank better.
            if rank_probe_n > top_n:
                probe_hits = search_reviews(
                    query,
                    n_results=rank_probe_n,
                    collection_name=name,
                )
                _print_target_ranks(
                    hits=probe_hits,
                    target_review_ids=target_review_ids,
                    top_label=f"top-{rank_probe_n}",
                )
            print()

        # Compare strategies on chunk index.
        print(f"-- chunk_index_v1 ({CHUNK_COLLECTION_NAME}) strategy comparison --")
        for strategy in ("A", "B", "C"):
            variants = generate_query_variants(query, strategy=strategy, max_variants=5)
            try:
                hits = search_reviews_with_variants(
                    query,
                    strategy=strategy,
                    n_results=top_n,
                    top_k_per_variant=30,
                    collection_name=CHUNK_COLLECTION_NAME,
                )
            except Exception as e:
                print(f"  strategy {strategy}: search failed: {e}")
                continue

            distances: list[float] = [
                float(h["distance"])
                for h in hits
                if isinstance(h.get("distance"), (int, float))
            ]
            print(
                f"  strategy {strategy}: variants={len(variants)} "
                f"hits={len(hits)} distance_stats={_distance_stats(distances)}"
            )
            print(f"    variants: {variants}")

            top3 = hits[:3]
            for i, h in enumerate(top3, start=1):
                print(f"    {i}. {_top_hit_str(h)}")

            _print_target_ranks(
                hits=hits,
                target_review_ids=target_review_ids,
                top_label=f"top-{top_n}",
            )
            if rank_probe_n > top_n:
                probe_hits = search_reviews_with_variants(
                    query,
                    strategy=strategy,
                    n_results=rank_probe_n,
                    top_k_per_variant=rank_probe_n,
                    collection_name=CHUNK_COLLECTION_NAME,
                )
                _print_target_ranks(
                    hits=probe_hits,
                    target_review_ids=target_review_ids,
                    top_label=f"top-{rank_probe_n}",
                )
            print()

        print()


def main() -> None:
    run_ab_test()


if __name__ == "__main__":
    main()

