"""Tests for JSONL read/write helpers."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.io.jsonl import (
    append_jsonl_line,
    iter_jsonl_objects,
    load_ids_from_jsonl,
    load_jsonl_as_map,
    write_jsonl,
)


def test_iter_jsonl_objects_empty_file(tmp_path: Path) -> None:
    """An empty or missing file yields nothing."""
    empty = tmp_path / "empty.jsonl"
    empty.touch()
    assert list(iter_jsonl_objects(empty)) == []
    assert list(iter_jsonl_objects(tmp_path / "nonexistent.jsonl")) == []


def test_iter_jsonl_objects_skips_empty_lines_and_invalid_json(tmp_path: Path) -> None:
    """Empty lines and invalid JSON lines are skipped; valid dict lines are yielded."""
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        '{"id": 1}\n\n\n{"id": 2}\nnot json\n{"id": 3}\n',
        encoding="utf-8",
    )
    result = list(iter_jsonl_objects(path))
    assert result == [{"id": 1}, {"id": 2}, {"id": 3}]


def test_iter_jsonl_objects_only_dicts_yielded(tmp_path: Path) -> None:
    """Only dict JSON lines are yielded.

    Arrays or primitive JSON values are skipped.
    """
    path = tmp_path / "types.jsonl"
    path.write_text('[1, 2]\n"string"\n42\n{"id": 1}\n', encoding="utf-8")
    result = list(iter_jsonl_objects(path))
    assert result == [{"id": 1}]


def test_load_ids_from_jsonl(tmp_path: Path) -> None:
    """All integer values for the given id_key are collected into a set."""
    path = tmp_path / "ids.jsonl"
    path.write_text(
        '{"id": 10}\n{"id": 20}\n{"other": 30}\n{"id": "ignored"}\n{"id": 10}\n',
        encoding="utf-8",
    )
    assert load_ids_from_jsonl(path) == {10, 20}
    assert load_ids_from_jsonl(path, id_key="other") == {30}


def test_load_jsonl_as_map_later_overwrites_earlier(tmp_path: Path) -> None:
    """Later lines with the same ID overwrite earlier ones."""
    path = tmp_path / "map.jsonl"
    path.write_text(
        '{"id": 1, "name": "first"}\n{"id": 1, "name": "second"}\n',
        encoding="utf-8",
    )
    result = load_jsonl_as_map(path)
    assert result == {1: {"id": 1, "name": "second"}}


def test_append_jsonl_line_creates_dir_and_appends(tmp_path: Path) -> None:
    """append_jsonl_line creates parent dirs and appends one JSON line."""
    path = tmp_path / "sub" / "out.jsonl"
    append_jsonl_line(path, {"a": 1})
    append_jsonl_line(path, {"a": 2})
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"a": 2}


def test_write_jsonl_writes_one_line_per_object(tmp_path: Path) -> None:
    """write_jsonl writes each object as one JSON line."""
    path = tmp_path / "written.jsonl"
    write_jsonl(path, [{"id": 1}, {"id": 2}])
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    assert [json.loads(ln) for ln in lines] == [{"id": 1}, {"id": 2}]


def test_write_jsonl_creates_parent_directory(tmp_path: Path) -> None:
    """write_jsonl creates the parent directory if needed."""
    path = tmp_path / "nested" / "file.jsonl"
    write_jsonl(path, [{"x": 1}])
    assert path.exists()


def test_load_ids_from_jsonl_skips_non_integer_id(tmp_path: Path) -> None:
    """Non-integer IDs are skipped when collecting IDs."""
    path = tmp_path / "ids.jsonl"
    path.write_text(
        '{"id": 1}\n{"id": "two"}\n{"id": 2.5}\n{"other": 3}\n',
        encoding="utf-8",
    )
    assert load_ids_from_jsonl(path) == {1}
    assert load_ids_from_jsonl(path, id_key="other") == {3}


def test_load_jsonl_as_map_skips_non_integer_id(tmp_path: Path) -> None:
    """Lines whose id_key value is not an int are skipped for the map."""
    path = tmp_path / "map.jsonl"
    path.write_text(
        '{"id": 1, "name": "a"}\n{"id": "x", "name": "b"}\n{"id": 2, "name": "c"}\n',
        encoding="utf-8",
    )
    result = load_jsonl_as_map(path)
    assert result == {1: {"id": 1, "name": "a"}, 2: {"id": 2, "name": "c"}}
