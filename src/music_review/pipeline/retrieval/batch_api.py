"""OpenAI Batch API lifecycle: submit, poll, download, parse, and embed."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

from music_review.config import get_project_root
from music_review.pipeline.retrieval.chroma_repo import EMBEDDING_MODEL

PROJECT_ROOT = get_project_root()
DEFAULT_BATCH_INPUT_PATH = PROJECT_ROOT / "data" / "batch_embedding_input.jsonl"
DEFAULT_CHUNK_BATCH_INPUT_PATH = (
    PROJECT_ROOT / "data" / "batch_embedding_input_chunks_v1.jsonl"
)
BATCH_COMPLETION_WINDOW: Literal["24h"] = "24h"
DEFAULT_CHUNK_BATCH_RESULTS_PATH = (
    PROJECT_ROOT / "data" / "batch_embedding_results_chunks_v1.jsonl"
)


def _get_openai_client() -> OpenAI:
    """Return an authenticated OpenAI client."""
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        msg = "OPENAI_API_KEY environment variable is not set."
        raise RuntimeError(msg)
    return OpenAI(api_key=api_key)


def submit_batch_embedding_job(
    input_path: Path | str = DEFAULT_BATCH_INPUT_PATH,
) -> str:
    """Upload the batch input file and create a batch job. Returns the batch ID."""
    path = Path(input_path)
    if not path.exists():
        msg = f"Batch input file not found: {path}"
        raise FileNotFoundError(msg)

    client = _get_openai_client()
    with path.open("rb") as f:
        file_obj = client.files.create(file=f, purpose="batch")
    batch = client.batches.create(
        input_file_id=file_obj.id,
        endpoint="/v1/embeddings",
        completion_window=BATCH_COMPLETION_WINDOW,
    )
    return batch.id


def poll_batch_until_complete(
    batch_id: str,
    *,
    poll_interval_seconds: int = 60,
) -> str:
    """Poll batch until completed/failed/expired/cancelled. Returns final status."""
    client = _get_openai_client()
    while True:
        batch = client.batches.retrieve(batch_id)
        status = batch.status
        if status in ("completed", "failed", "expired", "cancelled"):
            return status
        time.sleep(poll_interval_seconds)


def _get_attr_or_key(obj: Any, key: str, default: Any = None) -> Any:
    """Get attribute or dict key from SDK response (object or dict)."""
    if obj is None:
        return default
    v = getattr(obj, key, None)
    if v is not None:
        return v
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


def get_batch_error_details(batch_id: str) -> str:
    """Retrieve batch and return a readable summary of status and errors."""
    client = _get_openai_client()
    batch = client.batches.retrieve(batch_id)
    lines: list[str] = [
        f"Batch id: {batch.id}",
        f"Status: {batch.status}",
    ]
    counts = _get_attr_or_key(batch, "request_counts")
    if counts is not None:
        total = _get_attr_or_key(counts, "total")
        completed = _get_attr_or_key(counts, "completed")
        failed = _get_attr_or_key(counts, "failed")
        if total is not None:
            lines.append(
                f"Request counts: total={total}, completed={completed}, failed={failed}"
            )
    err = _get_attr_or_key(batch, "errors")
    if err is not None:
        data = _get_attr_or_key(err, "data")
        if isinstance(data, list) and data:
            lines.append("Batch-level errors:")
            for i, e in enumerate(data[:20], 1):
                msg = _get_attr_or_key(e, "message") or str(e)
                line_no = _get_attr_or_key(e, "line")
                code = _get_attr_or_key(e, "code")
                part = f"  {i}. {msg}"
                if line_no is not None:
                    part += f" (input line {line_no})"
                if code:
                    part += f" [{code}]"
                lines.append(part)
            if len(data) > 20:
                lines.append(f"  ... and {len(data) - 20} more.")
    efile = _get_attr_or_key(batch, "error_file_id")
    if efile:
        lines.append(f"Error file id (per-request errors): {efile}")
        lines.append("Download via OpenAI API or dashboard to inspect failed requests.")
    if (
        _get_attr_or_key(batch, "status") == "failed"
        and "Batch-level errors:" not in "\n".join(lines)
        and not efile
    ):
        lines.append(
            "No error details in response. Check https://platform.openai.com/batches "
            "for validation/input errors or account limits."
        )
    return "\n".join(lines)


def is_token_limit_error(batch_id: str) -> bool:
    """Return True on enqueued token-limit failure."""
    details = get_batch_error_details(batch_id)
    return "token_limit_exceeded" in details or "Enqueued token limit" in details


def download_batch_results(
    batch_id: str,
    output_path: Path | str,
) -> int:
    """Retrieve batch output file and save as JSONL. Returns result line count."""
    client = _get_openai_client()
    batch = client.batches.retrieve(batch_id)
    if batch.status != "completed":
        msg = f"Batch {batch_id} is not completed (status={batch.status})."
        raise RuntimeError(msg)
    if not batch.output_file_id:
        msg = f"Batch {batch_id} has no output_file_id."
        raise RuntimeError(msg)

    content = client.files.content(batch.output_file_id)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    raw: bytes = content.content if hasattr(content, "content") else content.read()
    text = raw.decode("utf-8")
    lines = [line for line in text.strip().split("\n") if line.strip()]
    with out.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")
    return len(lines)


def parse_batch_output_jsonl(path: Path | str) -> list[tuple[str, list[float]]]:
    """Parse batch output JSONL into (custom_id, embedding) pairs. Skips errors."""
    return _parse_batch_output_lines(Path(path))


def _parse_batch_output_lines(path: Path) -> list[tuple[str, list[float]]]:
    """Parse batch output JSONL to (custom_id, embedding) per successful line."""
    if not path.exists():
        return []
    out: list[tuple[str, list[float]]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if not isinstance(row, dict):
                continue
            if row.get("error") is not None:
                continue
            custom_id = row.get("custom_id")
            response = row.get("response", {})
            body = response.get("body", {}) if isinstance(response, dict) else {}
            data = body.get("data") if isinstance(body, dict) else None
            if not isinstance(data, list) or not data:
                continue
            emb = data[0].get("embedding") if isinstance(data[0], dict) else None
            if not isinstance(emb, list):
                continue
            if custom_id is not None:
                out.append((str(custom_id), emb))
    return out


def embed_query_vector(query_text: str) -> list[float]:
    """Embed ``query_text`` with the same OpenAI model as the Chroma collections."""
    client = _get_openai_client()
    q = query_text.strip()
    if not q:
        msg = "Empty query text for embedding."
        raise ValueError(msg)
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=q)
    data0 = resp.data[0]
    emb = getattr(data0, "embedding", None) if data0 is not None else None
    if emb is None:
        msg = "OpenAI embeddings response missing embedding."
        raise RuntimeError(msg)
    return [float(x) for x in emb]
