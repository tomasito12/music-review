"""Assign each community to one or more broad genre categories via LLM.

Two-step pipeline:
  1. Define broad categories from all fine-grained genre labels (single LLM call).
  2. Assign each community to 1-3 broad categories (one LLM call per community).

Reads ``communities_res_*.json`` and ``community_genre_labels_res_*.json``,
writes ``data/community_broad_categories_res_{resolution}.json``.

Output format::

    {
      "resolution": 10,
      "broad_categories": ["Rock & Alternative", "Electronic & Dance", ...],
      "mappings": [
        {
          "community_id": "C001",
          "genre_label": "Shoegaze & Dream Pop",
          "broad_categories": ["Rock & Alternative", "Experimental"]
        },
        ...
      ]
    }
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from music_review.config import resolve_data_path
from music_review.pipeline.retrieval.community_genre_labels import (
    load_communities,
    load_existing_genre_labels,
)

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_DELAY_SECONDS = 0.5

# ---------------------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------------------

DEFINE_CATEGORIES_PROMPT = (
    "Du erhältst eine Liste feingranularer Genre-Labels von Musik-Communities:\n\n"
    "{label_list}\n\n"
    "Aufgabe: Erstelle 10-15 übergeordnete Musikrichtungen (Grobkategorien), "
    "die das gesamte Spektrum dieser Labels abdecken.\n\n"
    "Anforderungen:\n"
    "- Jede Grobkategorie soll mehrere feingranulare Labels umfassen können.\n"
    "- Grobkategorien dürfen sich überlappen (ein feingranulares Label kann in "
    "mehrere Grobkategorien fallen).\n"
    "- Verwende kurze, prägnante Namen auf Englisch (z.B. 'Rock & Alternative', "
    "'Electronic & Dance', 'Metal & Hardcore').\n"
    "- Decke das gesamte Spektrum ab, auch Nischen wie Klassik, Jazz, World Music.\n\n"
    "Antworte ausschließlich mit einem JSON-Array der Kategorienamen, z.B.:\n"
    '["Rock & Alternative", "Electronic & Dance", "Hip-Hop & R&B"]\n'
    "Keine Erklärung, kein Markdown, nur das JSON-Array."
)

ASSIGN_CATEGORIES_PROMPT = (
    "Gegeben sind folgende übergeordnete Musikrichtungen:\n"
    "{categories}\n\n"
    "Eine Musik-Community hat dieses feingranulare Genre-Label: {genre_label}\n"
    "Repräsentative Künstler: {artists}\n\n"
    "Aufgabe: Ordne diese Community 1-3 der übergeordneten Kategorien zu. "
    "Mehrfachzuordnung ist erwünscht, wenn die Community stilistisch "
    "in mehrere Richtungen passt.\n\n"
    "Antworte ausschließlich mit einem JSON-Array der zutreffenden Kategorienamen, "
    "z.B.:\n"
    '["Rock & Alternative", "Punk & Post-Punk"]\n'
    "Keine Erklärung, kein Markdown, nur das JSON-Array."
)


# ---------------------------------------------------------------------------
# OpenAI client
# ---------------------------------------------------------------------------


def _get_openai_client() -> Any:
    """Return OpenAI client. Requires OPENAI_API_KEY."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY environment variable is not set."
        raise RuntimeError(msg)
    from openai import OpenAI

    return OpenAI(api_key=api_key)


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------


def build_define_categories_prompt(genre_labels: list[str]) -> str:
    """Build the prompt that asks the LLM to define broad categories."""
    label_list = "\n".join(f"- {lbl}" for lbl in sorted(set(genre_labels)))
    return DEFINE_CATEGORIES_PROMPT.format(label_list=label_list)


def build_assign_prompt(
    broad_categories: list[str],
    genre_label: str,
    top_artists: list[str],
) -> str:
    """Build the prompt that assigns a community to broad categories."""
    cats = ", ".join(broad_categories)
    artists_str = ", ".join(top_artists[:5]) if top_artists else "(keine Künstler)"
    return ASSIGN_CATEGORIES_PROMPT.format(
        categories=cats,
        genre_label=genre_label,
        artists=artists_str,
    )


# ---------------------------------------------------------------------------
# LLM response parsing
# ---------------------------------------------------------------------------


def parse_categories_response(response_text: str) -> list[str]:
    """Extract a JSON array of category names from the LLM response."""
    text = (response_text or "").strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if not match:
        return []
    try:
        parsed = json.loads(match.group())
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [
        str(item).strip() for item in parsed if isinstance(item, str) and item.strip()
    ]


def parse_assignment_response(
    response_text: str,
    valid_categories: list[str],
) -> list[str]:
    """Extract assigned categories from the LLM response, filtered to valid ones."""
    raw = parse_categories_response(response_text)
    valid_set = {c.lower() for c in valid_categories}
    valid_map = {c.lower(): c for c in valid_categories}
    return [valid_map[r.lower()] for r in raw if r.lower() in valid_set]


# ---------------------------------------------------------------------------
# Load / save helpers
# ---------------------------------------------------------------------------


def load_existing_broad_categories(
    path: Path | str,
) -> tuple[list[str], dict[str, list[str]]]:
    """Load broad categories and per-community mappings from existing output.

    Returns (broad_categories list, community_id -> broad_categories mapping).
    """
    p = Path(path)
    if not p.exists():
        return [], {}
    try:
        with p.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return [], {}
    cats = data.get("broad_categories")
    if not isinstance(cats, list):
        cats = []
    cats = [str(c) for c in cats if isinstance(c, str)]
    mappings = data.get("mappings")
    if not isinstance(mappings, list):
        return cats, {}
    mapping_dict: dict[str, list[str]] = {}
    for item in mappings:
        if not isinstance(item, dict):
            continue
        cid = item.get("community_id")
        bc = item.get("broad_categories")
        if isinstance(cid, str) and isinstance(bc, list):
            mapping_dict[cid] = [str(c) for c in bc]
    return cats, mapping_dict


def _save_output(
    output_path: Path,
    resolution: float,
    broad_categories: list[str],
    mappings: list[dict[str, Any]],
) -> None:
    """Write the broad categories JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "resolution": resolution,
        "broad_categories": broad_categories,
        "mappings": mappings,
    }
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d mappings to %s", len(mappings), output_path)


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


def _top_artists_for_community(community: dict[str, Any]) -> list[str]:
    """Extract up to 5 top artist names."""
    top = community.get("top_artists") or []
    if not isinstance(top, list):
        return []
    return [str(a).strip() for a in top[:5] if str(a).strip()]


def define_broad_categories(
    client: Any,
    genre_labels: list[str],
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Step 1: Ask the LLM to define 10-15 broad categories."""
    prompt = build_define_categories_prompt(genre_labels)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=500,
    )
    content = (resp.choices or [{}])[0].message.content if resp.choices else ""
    cats = parse_categories_response(content or "")
    if not cats:
        logger.warning("LLM returned no categories; using fallback.")
        cats = [
            "Rock & Alternative",
            "Electronic & Dance",
            "Pop",
            "Hip-Hop & R&B",
            "Metal & Hardcore",
            "Jazz & Soul",
            "Folk & Singer-Songwriter",
            "Classical & Ambient",
            "Punk & Post-Punk",
            "World & Latin",
        ]
    logger.info("Defined %d broad categories: %s", len(cats), cats)
    return cats


def assign_community_categories(
    client: Any,
    broad_categories: list[str],
    genre_label: str,
    top_artists: list[str],
    model: str = DEFAULT_MODEL,
) -> list[str]:
    """Step 2: Assign one community to 1-3 broad categories."""
    prompt = build_assign_prompt(broad_categories, genre_label, top_artists)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
    )
    content = (resp.choices or [{}])[0].message.content if resp.choices else ""
    assigned = parse_assignment_response(content or "", broad_categories)
    if not assigned:
        logger.warning(
            "No valid categories for '%s'; defaulting to first category.",
            genre_label,
        )
        assigned = [broad_categories[0]] if broad_categories else []
    return assigned


def run_pipeline(
    communities_path: Path | str,
    labels_path: Path | str,
    output_path: Path | str,
    *,
    model: str = DEFAULT_MODEL,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
    existing_categories: list[str] | None = None,
    existing_mappings: dict[str, list[str]] | None = None,
) -> int:
    """Run the two-step pipeline and write the output file."""
    communities, resolution = load_communities(communities_path)
    genre_labels_map = load_existing_genre_labels(labels_path)
    all_labels = list(genre_labels_map.values())
    reuse_mappings = existing_mappings or {}
    total = len(communities)

    client = _get_openai_client()

    if existing_categories:
        broad_categories = existing_categories
        logger.info("Reusing %d existing broad categories.", len(broad_categories))
    else:
        logger.info(
            "Step 1: Defining broad categories from %d labels...",
            len(all_labels),
        )
        broad_categories = define_broad_categories(client, all_labels, model=model)
        if delay_seconds > 0:
            time.sleep(delay_seconds)

    n_reuse = sum(1 for c in communities if str(c.get("id", "")) in reuse_mappings)
    logger.info(
        "Step 2: Assigning %d communities (%d reused), model=%s",
        total,
        n_reuse,
        model,
    )

    mappings: list[dict[str, Any]] = []
    llm_calls = 0
    for i, comm in enumerate(communities):
        cid = str(comm.get("id") or f"C{i + 1:03d}")
        genre_label = genre_labels_map.get(cid, "Unbekannt")
        top_artists = _top_artists_for_community(comm)

        if cid in reuse_mappings:
            assigned = reuse_mappings[cid]
            logger.info("%s (%d/%d) -> %s (reused)", cid, i + 1, total, assigned)
        else:
            if delay_seconds > 0 and llm_calls > 0:
                time.sleep(delay_seconds)
            llm_calls += 1
            try:
                assigned = assign_community_categories(
                    client,
                    broad_categories,
                    genre_label,
                    top_artists,
                    model=model,
                )
            except Exception as e:
                assigned = [broad_categories[0]] if broad_categories else []
                logger.warning("LLM call failed for %s: %s", cid, e, exc_info=False)
            logger.info("%s (%d/%d) -> %s", cid, i + 1, total, assigned)

        mappings.append(
            {
                "community_id": cid,
                "genre_label": genre_label,
                "broad_categories": assigned,
            }
        )

    _save_output(Path(output_path), resolution, broad_categories, mappings)
    return len(mappings)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Assign communities to broad genre categories via LLM.",
    )
    parser.add_argument(
        "--communities",
        type=Path,
        default=None,
        help="Path to communities_res_*.json. Default: data/communities_res_10.json",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help="Path to community_genre_labels_res_*.json. "
        "Default: data/community_genre_labels_res_10.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON. Default: data/community_broad_categories_res_<res>.json",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        help=f"OpenAI chat model (default: {DEFAULT_MODEL}).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help=f"Seconds between API calls (default: {DEFAULT_DELAY_SECONDS}).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable DEBUG logging.",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Reuse existing broad categories and mappings; only call LLM for new ids.",
    )
    return parser.parse_args(argv)


def _resolve_res_name(resolution: float) -> str:
    if float(resolution).is_integer():
        return str(int(resolution))
    return str(resolution).replace(".", "_")


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    data_dir = resolve_data_path("data")

    communities_path = (
        Path(args.communities).resolve()
        if args.communities is not None
        else data_dir / "communities_res_10.json"
    )
    if not communities_path.exists():
        logger.error("Communities file not found: %s", communities_path)
        return 1

    try:
        _comms, resolution = load_communities(communities_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("%s", e)
        return 1

    res_name = _resolve_res_name(resolution)

    labels_path = (
        Path(args.labels).resolve()
        if args.labels is not None
        else data_dir / f"community_genre_labels_res_{res_name}.json"
    )
    if not labels_path.exists():
        logger.error("Genre labels file not found: %s", labels_path)
        return 1

    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else data_dir / f"community_broad_categories_res_{res_name}.json"
    )

    existing_cats: list[str] | None = None
    existing_maps: dict[str, list[str]] | None = None
    if args.only_missing:
        existing_cats, existing_maps = load_existing_broad_categories(output_path)
        if existing_cats:
            logger.info(
                "Only-missing: reusing %d categories, %d mappings from %s",
                len(existing_cats),
                len(existing_maps),
                output_path,
            )

    n = run_pipeline(
        communities_path,
        labels_path,
        output_path,
        model=args.model,
        delay_seconds=args.delay,
        existing_categories=existing_cats if existing_cats else None,
        existing_mappings=existing_maps if existing_maps else None,
    )
    logger.info("Done. %d mappings written.", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
