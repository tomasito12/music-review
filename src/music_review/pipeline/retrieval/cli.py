# music_review/pipeline/retrieval/cli.py

"""CLI for the batch embedding pipeline (OpenAI Batch API → Chroma)."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

from music_review.config import get_project_root, resolve_data_path
from music_review.pipeline.retrieval.vector_store import (
    DEFAULT_BATCH_INPUT_PATH,
    DEFAULT_CHROMA_PATH,
    DEFAULT_DATA_PATH,
    DEFAULT_METADATA_PATH,
    download_batch_results,
    get_batch_error_details,
    import_batch_results_into_chroma,
    is_token_limit_error,
    poll_batch_until_complete,
    submit_batch_embedding_job,
    write_batch_embedding_input,
)

PROJECT_ROOT = get_project_root()
DEFAULT_RESULTS_PATH = resolve_data_path("data/batch_embedding_results.jsonl")


def main(argv: list[str] | None = None) -> int:
    """Entry point for the batch embedding pipeline CLI."""
    args = _build_parser().parse_args(argv)

    try:
        if args.cmd == "prepare":
            return _cmd_prepare(args)
        if args.cmd == "submit":
            return _cmd_submit(args)
        if args.cmd == "poll":
            return _cmd_poll(args)
        if args.cmd == "download":
            return _cmd_download(args)
        if args.cmd == "import":
            return _cmd_import(args)
        if args.cmd == "run":
            return _cmd_run(args)
        if args.cmd == "status":
            return _cmd_status(args)
        return 0
    except (FileNotFoundError, RuntimeError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music-review-batch-embed",
        description=(
            "OpenAI Batch API embedding pipeline: prepare → submit → poll → "
            "download → import into Chroma."
        ),
    )
    subparsers = parser.add_subparsers(dest="cmd", required=True)

    # prepare
    p_prepare = subparsers.add_parser(
        "prepare",
        help="Generate batch input JSONL (only reviews not yet in Chroma).",
    )
    p_prepare.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_BATCH_INPUT_PATH,
        help="Output path for batch input JSONL.",
    )
    p_prepare.add_argument(
        "--data",
        type=Path,
        default=Path(DEFAULT_DATA_PATH),
        help="Reviews JSONL path.",
    )
    p_prepare.add_argument(
        "--metadata",
        type=Path,
        default=Path(DEFAULT_METADATA_PATH),
        help="Metadata JSONL path.",
    )
    p_prepare.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Include all reviews (do not skip those already in Chroma).",
    )
    p_prepare.add_argument(
        "--max-requests",
        type=int,
        default=2500,
        metavar="N",
        help="Split into multiple files with at most N requests each (default: 2500).",
    )

    # submit
    p_submit = subparsers.add_parser(
        "submit",
        help="Upload batch input file and create batch job.",
    )
    p_submit.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_BATCH_INPUT_PATH,
        help="Batch input JSONL path.",
    )

    # poll
    p_poll = subparsers.add_parser(
        "poll",
        help="Poll batch status until completed/failed/expired.",
    )
    p_poll.add_argument("batch_id", help="Batch ID from submit.")
    p_poll.add_argument(
        "--interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60).",
    )

    # download
    p_download = subparsers.add_parser(
        "download",
        help="Download batch results to a JSONL file.",
    )
    p_download.add_argument("batch_id", help="Batch ID (must be completed).")
    p_download.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="Output path for results JSONL.",
    )

    # import
    p_import = subparsers.add_parser(
        "import",
        help="Import batch results JSONL into Chroma (metadata + documents).",
    )
    p_import.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="Batch results JSONL path.",
    )
    p_import.add_argument(
        "--data",
        type=Path,
        default=Path(DEFAULT_DATA_PATH),
        help="Reviews JSONL path.",
    )
    p_import.add_argument(
        "--metadata",
        type=Path,
        default=Path(DEFAULT_METADATA_PATH),
        help="Metadata JSONL path.",
    )
    p_import.add_argument(
        "--chroma",
        type=Path,
        default=DEFAULT_CHROMA_PATH,
        help="Chroma persist directory.",
    )
    p_import.add_argument(
        "--recreate",
        action="store_true",
        help="Recreate Chroma collection before importing.",
    )

    # run (full pipeline: prepare → submit → poll → download → import)
    p_run = subparsers.add_parser(
        "run",
        help="Full pipeline: prepare, submit, poll, download, import.",
    )
    p_run.add_argument(
        "--data",
        type=Path,
        default=Path(DEFAULT_DATA_PATH),
        help="Reviews JSONL path.",
    )
    p_run.add_argument(
        "--metadata",
        type=Path,
        default=Path(DEFAULT_METADATA_PATH),
        help="Metadata JSONL path.",
    )
    p_run.add_argument(
        "--batch-input",
        type=Path,
        default=DEFAULT_BATCH_INPUT_PATH,
        help="Batch input JSONL path (written by prepare).",
    )
    p_run.add_argument(
        "--results",
        type=Path,
        default=DEFAULT_RESULTS_PATH,
        help="Batch results JSONL path (written by download).",
    )
    p_run.add_argument(
        "--chroma",
        type=Path,
        default=DEFAULT_CHROMA_PATH,
        help="Chroma persist directory.",
    )
    p_run.add_argument(
        "--poll-interval",
        type=int,
        default=60,
        help="Poll interval in seconds (default: 60).",
    )
    p_run.add_argument(
        "--no-skip-existing",
        action="store_true",
        help="Include all reviews in batch (do not skip those already in Chroma).",
    )
    p_run.add_argument(
        "--recreate",
        action="store_true",
        help=(
            "Recreate Chroma collection before importing "
            "(replaces all existing content)."
        ),
    )
    p_run.add_argument(
        "--max-requests-per-batch",
        type=int,
        default=2500,
        metavar="N",
        help=(
            "Split into batches of at most N requests "
            "(default: 2500, avoids token limit)."
        ),
    )
    p_run.add_argument(
        "--retry-wait",
        type=int,
        default=300,
        metavar="SECONDS",
        help=(
            "On token limit error, wait this many seconds before retry (default: 300)."
        ),
    )
    p_run.add_argument(
        "--max-retries",
        type=int,
        default=5,
        metavar="N",
        help="Max retries per batch when hitting token limit (default: 5).",
    )

    # status
    p_status = subparsers.add_parser(
        "status",
        help="Show batch status and error details (for failed batches).",
    )
    p_status.add_argument("batch_id", help="Batch ID from submit.")

    return parser


def _cmd_prepare(args: argparse.Namespace) -> int:
    total, paths = write_batch_embedding_input(
        args.input,
        data_path=args.data,
        metadata_path=args.metadata,
        skip_existing=not args.no_skip_existing,
        max_requests_per_file=getattr(args, "max_requests", None),
    )
    if len(paths) == 1:
        print(f"Wrote {total} batch request lines to {paths[0]}.")
    else:
        print(f"Wrote {total} batch request lines to {len(paths)} files.")
        for p in paths:
            print(f"  {p}")
    return 0


def _cmd_submit(args: argparse.Namespace) -> int:
    batch_id = submit_batch_embedding_job(args.input)
    print(f"Created batch: {batch_id}")
    print("Run: hatch run batch-embed poll", batch_id)
    return 0


def _cmd_poll(args: argparse.Namespace) -> int:
    status = poll_batch_until_complete(
        args.batch_id, poll_interval_seconds=args.interval
    )
    print(f"Batch status: {status}")
    return 0 if status == "completed" else 1


def _cmd_download(args: argparse.Namespace) -> int:
    n = download_batch_results(args.batch_id, args.output)
    print(f"Downloaded {n} result lines to {args.output}.")
    return 0


def _cmd_status(args: argparse.Namespace) -> int:
    print(get_batch_error_details(args.batch_id))
    return 0


def _cmd_import(args: argparse.Namespace) -> int:
    n = import_batch_results_into_chroma(
        args.results,
        data_path=args.data,
        metadata_path=args.metadata,
        persist_directory=args.chroma,
        recreate=args.recreate,
    )
    print(f"Imported {n} documents into Chroma at {args.chroma}.")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    # With --recreate we include all reviews; otherwise only those not in Chroma.
    skip_existing = not (args.no_skip_existing or args.recreate)
    max_per_batch = getattr(args, "max_requests_per_batch", None)
    total, input_paths = write_batch_embedding_input(
        args.batch_input,
        data_path=args.data,
        metadata_path=args.metadata,
        skip_existing=skip_existing,
        max_requests_per_file=max_per_batch,
    )
    if total == 0:
        print("No new reviews to embed. Exiting.")
        return 0
    if len(input_paths) == 1:
        print(f"Prepared {total} batch requests at {input_paths[0]}.")
    else:
        print(f"Prepared {total} requests in {len(input_paths)} batch files.")

    results_dir = args.results.parent
    results_stem = args.results.stem
    results_suffix = args.results.suffix
    total_imported = 0
    retry_wait = getattr(args, "retry_wait", 300)
    max_retries = getattr(args, "max_retries", 5)

    for i, inp in enumerate(input_paths):
        for attempt in range(max_retries + 1):
            batch_id = submit_batch_embedding_job(inp)
            if attempt == 0:
                print(f"[{i + 1}/{len(input_paths)}] Submitted batch: {batch_id}")
            else:
                print(
                    f"[{i + 1}/{len(input_paths)}] "
                    f"Retry {attempt}/{max_retries}: {batch_id}"
                )

            status = poll_batch_until_complete(
                batch_id, poll_interval_seconds=args.poll_interval
            )
            if status == "completed":
                break
            if not is_token_limit_error(batch_id) or attempt >= max_retries:
                print(
                    f"Batch ended with status: {status}. Not downloading or importing.",
                    file=sys.stderr,
                )
                print(get_batch_error_details(batch_id), file=sys.stderr)
                return 1
            print(
                f"Token limit reached. Waiting {retry_wait}s before retry...",
                file=sys.stderr,
            )
            time.sleep(retry_wait)

        part_results = results_dir / f"{results_stem}_part{i:05d}{results_suffix}"
        download_batch_results(batch_id, part_results)
        print(f"Downloaded results to {part_results}.")

        added = import_batch_results_into_chroma(
            part_results,
            data_path=args.data,
            metadata_path=args.metadata,
            persist_directory=args.chroma,
            recreate=(i == 0 and args.recreate),
        )
        total_imported += added
        print(f"Imported {added} documents (total so far: {total_imported}).")

    print(f"Done. Imported {total_imported} documents into Chroma at {args.chroma}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
