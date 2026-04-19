"""Tests for batch_api module (pure parsing logic, no OpenAI calls)."""

from __future__ import annotations

import json
from pathlib import Path

from music_review.pipeline.retrieval.batch_api import (
    _get_attr_or_key,
    _parse_batch_output_lines,
    parse_batch_output_jsonl,
)


class TestGetAttrOrKey:
    def test_attribute_access(self) -> None:
        class Obj:
            name = "Alice"

        assert _get_attr_or_key(Obj(), "name") == "Alice"

    def test_dict_key_access(self) -> None:
        assert _get_attr_or_key({"name": "Bob"}, "name") == "Bob"

    def test_default_on_missing(self) -> None:
        assert _get_attr_or_key({}, "missing", "fallback") == "fallback"

    def test_none_object_returns_default(self) -> None:
        assert _get_attr_or_key(None, "key") is None
        assert _get_attr_or_key(None, "key", 42) == 42

    def test_attribute_preferred_over_dict(self) -> None:
        class DictLike(dict):  # type: ignore[type-arg]
            foo = "from_attr"

        obj = DictLike(foo="from_dict")
        assert _get_attr_or_key(obj, "foo") == "from_attr"


class TestParseBatchOutputLines:
    def test_valid_row(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        row = {
            "custom_id": "review_42",
            "response": {
                "body": {"data": [{"embedding": [0.1, 0.2, 0.3]}]},
            },
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = _parse_batch_output_lines(path)
        assert result == [("review_42", [0.1, 0.2, 0.3])]

    def test_skips_error_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        lines = [
            json.dumps(
                {
                    "custom_id": "ok",
                    "response": {"body": {"data": [{"embedding": [1.0]}]}},
                }
            ),
            json.dumps({"custom_id": "bad", "error": {"message": "fail"}}),
        ]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        result = _parse_batch_output_lines(path)
        assert len(result) == 1
        assert result[0][0] == "ok"

    def test_skips_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        path.write_text("not-json\n", encoding="utf-8")
        assert _parse_batch_output_lines(path) == []

    def test_skips_missing_embedding(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        row = {"custom_id": "x", "response": {"body": {"data": [{}]}}}
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        assert _parse_batch_output_lines(path) == []

    def test_nonexistent_file_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "nope.jsonl"
        assert _parse_batch_output_lines(path) == []

    def test_empty_file_returns_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "empty.jsonl"
        path.write_text("", encoding="utf-8")
        assert _parse_batch_output_lines(path) == []

    def test_multiple_valid_rows(self, tmp_path: Path) -> None:
        path = tmp_path / "multi.jsonl"
        rows = []
        for i in range(3):
            rows.append(
                json.dumps(
                    {
                        "custom_id": f"id_{i}",
                        "response": {"body": {"data": [{"embedding": [float(i)]}]}},
                    }
                )
            )
        path.write_text("\n".join(rows) + "\n", encoding="utf-8")
        result = _parse_batch_output_lines(path)
        assert len(result) == 3
        assert [r[0] for r in result] == ["id_0", "id_1", "id_2"]

    def test_skips_row_without_custom_id(self, tmp_path: Path) -> None:
        path = tmp_path / "no_id.jsonl"
        row = {"response": {"body": {"data": [{"embedding": [1.0]}]}}}
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        assert _parse_batch_output_lines(path) == []

    def test_skips_row_with_empty_data(self, tmp_path: Path) -> None:
        path = tmp_path / "empty_data.jsonl"
        row = {"custom_id": "x", "response": {"body": {"data": []}}}
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        assert _parse_batch_output_lines(path) == []


class TestParseBatchOutputJsonl:
    def test_delegates_to_parse_lines(self, tmp_path: Path) -> None:
        path = tmp_path / "out.jsonl"
        row = {
            "custom_id": "abc",
            "response": {"body": {"data": [{"embedding": [9.9]}]}},
        }
        path.write_text(json.dumps(row) + "\n", encoding="utf-8")
        result = parse_batch_output_jsonl(path)
        assert result == [("abc", [9.9])]
