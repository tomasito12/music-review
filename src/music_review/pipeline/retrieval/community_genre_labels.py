# music_review/pipeline/retrieval/community_genre_labels.py

"""Generate one genre label per community via LLM (offline pipeline).

Reads communities_res_*.json from the graph export, calls an OpenAI chat model
once per community with a prompt based on centroid and top_artists, and writes
data/community_genre_labels_res_{resolution}.json for use in the dashboard.

Output format:
  {
    "resolution": <float>,
    "source_file": "<basename>",
    "labels": [
      { "community_id": "C001", "genre_label": "Indie Rock" },
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

import music_review.config  # noqa: F401 - load .env early
from music_review.config import resolve_data_path

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_DELAY_SECONDS = 0.5

PROMPT_TEMPLATE = (
    "Diese Musik-Community wird durch folgende Künstler repräsentiert: {artists}.\n\n"
    "Aufgabe: Nenne genau ein kurzes Genre-Label (auf Englisch), das diesen Cluster "
    "spezifisch und feingliedrig beschreibt.\n\n"
    "Anforderungen:\n"
    "- Keine groben Oberbegriffe wie „Indie-Rock“, „Elektronik“ oder „Pop“. "
    "Stattdessen präzise, beschreibende Bezeichnungen (z. B. „Anthemic Indie“, "
    "„Outlaw Americana“, „Neoclassical“, „Female Indie Songwriters“).\n"
    "- Begriffe wie „Female“, „German“ oder ähnlich nur verwenden, wenn sie ein "
    "deutlich erkennbares Kennzeichen der Community sind.\n"
    "- Das Label soll in wenigen Worten den gemeinsamen Nenner treffen.\n"
    "{already_assigned_block}"
    "Antworte nur mit dem Genre-Label, ohne Erklärung oder Anführungszeichen."
)

ALREADY_ASSIGNED_BLOCK = (
    "\n"
    "- Bereits an andere Communities vergebene Labels (nicht wiederholen, "
    "stattdessen abgrenzend und spezifischer wählen): {already_assigned}.\n\n"
)


def _get_openai_client() -> Any:
    """Return OpenAI client. Requires OPENAI_API_KEY."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY environment variable is not set."
        raise RuntimeError(msg)
    from openai import OpenAI

    return OpenAI(api_key=api_key)


def load_communities(path: Path | str) -> tuple[list[dict[str, Any]], float]:
    """Load communities from a communities_res_*.json file.

    Returns (communities list, resolution). Raises if file invalid.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Communities file not found: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)
    resolution = float(data.get("resolution", 0))
    communities = data.get("communities")
    if not isinstance(communities, list):
        raise ValueError("Expected 'communities' array in JSON.")
    return communities, resolution


def _artist_list_for_prompt(
    community: dict[str, Any], max_artists: int = 15
) -> list[str]:
    """Up to max_artists for prompt: top_artists first, then from artists."""
    top = community.get("top_artists") or []
    all_artists = community.get("artists") or []
    if not isinstance(top, list):
        top = []
    if not isinstance(all_artists, list):
        all_artists = []
    seen: set[str] = set()
    result: list[str] = []
    for name in top:
        s = str(name).strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
            if len(result) >= max_artists:
                return result
    for name in all_artists:
        if len(result) >= max_artists:
            break
        s = str(name).strip()
        if s and s not in seen:
            seen.add(s)
            result.append(s)
    return result


def build_prompt(
    community: dict[str, Any],
    already_assigned_labels: list[str] | None = None,
) -> str:
    """Build the LLM prompt for one community (up to 15 artists).

    If already_assigned_labels is non-empty, the prompt asks for a distinct
    label that contrasts with these to avoid overlap.
    """
    artists = _artist_list_for_prompt(community, max_artists=15)
    artists_str = ", ".join(artists) if artists else "(keine Künstler)"
    if already_assigned_labels:
        already_str = ", ".join(already_assigned_labels)
        block = ALREADY_ASSIGNED_BLOCK.format(already_assigned=already_str)
    else:
        block = "\n\n"
    return PROMPT_TEMPLATE.format(artists=artists_str, already_assigned_block=block)


def _parse_label(response_text: str) -> str:
    """Extract a single genre label from the model response."""
    text = (response_text or "").strip()
    # Take first line and remove common wrappers
    first_line = text.split("\n")[0].strip()
    first_line = re.sub(r'^["\']|["\']$', "", first_line)
    return first_line or "Unbekannt"


def fetch_label_for_community(
    client: Any,
    community: dict[str, Any],
    model: str = DEFAULT_MODEL,
    already_assigned_labels: list[str] | None = None,
) -> str:
    """Call the LLM once for this community and return the genre label.

    If already_assigned_labels is provided, the prompt instructs the model to
    choose a distinct, contrasting label to avoid overlap with earlier communities.
    """
    prompt = build_prompt(community, already_assigned_labels=already_assigned_labels)
    resp = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=50,
    )
    content = (resp.choices or [{}])[0].message.content if resp.choices else ""
    return _parse_label(content or "")


def run_pipeline(
    communities_path: Path | str,
    output_path: Path | str,
    *,
    model: str = DEFAULT_MODEL,
    delay_seconds: float = DEFAULT_DELAY_SECONDS,
) -> int:
    """Fetch one genre label per community via LLM and write output. Returns count."""
    communities, resolution = load_communities(communities_path)
    total = len(communities)
    source_basename = Path(communities_path).name
    logger.info(
        "Starting community genre labels: %d communities, model=%s, output=%s",
        total,
        model,
        output_path,
    )
    client = _get_openai_client()

    labels: list[dict[str, Any]] = []
    assigned_so_far: list[str] = []
    for i, comm in enumerate(communities):
        cid = comm.get("id") or f"C{i + 1:03d}"
        if delay_seconds > 0 and i > 0:
            time.sleep(delay_seconds)
        logger.debug(
            "Community %s (%d/%d), already_assigned=%d",
            cid,
            i + 1,
            total,
            len(assigned_so_far),
        )
        try:
            label = fetch_label_for_community(
                client,
                comm,
                model=model,
                already_assigned_labels=assigned_so_far if assigned_so_far else None,
            )
        except Exception as e:
            label = "Unbekannt"
            logger.warning("LLM call failed for %s: %s", cid, e, exc_info=False)
        labels.append({"community_id": str(cid), "genre_label": label})
        assigned_so_far.append(label)
        logger.info("%s (%d/%d) -> %s", cid, i + 1, total, label)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "resolution": resolution,
        "source_file": source_basename,
        "labels": labels,
    }
    with out.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    logger.info("Wrote %d labels to %s", len(labels), out)
    return len(labels)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate one genre label per community via LLM (offline).",
    )
    parser.add_argument(
        "--communities",
        type=Path,
        default=None,
        help="Path to communities_res_*.json. Default: data/communities_res_10.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSON. Default: data/community_genre_labels_res_<resolution>.json",
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    data_dir = resolve_data_path("data")
    communities_path = (
        Path(args.communities)
        if args.communities is not None
        else data_dir / "communities_res_10.json"
    )
    communities_path = communities_path.resolve()

    if not communities_path.exists():
        logger.error("Communities file not found: %s", communities_path)
        return 1

    try:
        _communities, resolution = load_communities(communities_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error("%s", e)
        return 1

    res_name = (
        str(int(resolution))
        if float(resolution).is_integer()
        else str(resolution).replace(".", "_")
    )
    output_path = (
        Path(args.output).resolve()
        if args.output is not None
        else (data_dir / f"community_genre_labels_res_{res_name}.json")
    )

    n = run_pipeline(
        communities_path,
        output_path,
        model=args.model,
        delay_seconds=args.delay,
    )
    logger.info("Done. %d labels written.", n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
