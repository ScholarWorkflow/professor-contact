"""Shared readers for the issue #67 professor-local Stage-4 machine contract.

The filename deliberately does not match the unittest discovery pattern
(``test_*.py``), so this module is never collected as a test.

Issue #67 moved Stage-4 authority to one transaction per canonical
``professor_dir``: ``stage4-finalize`` prints exactly one aggregate object and
every professor-scoped outcome (``ok`` / ``needs_refresh`` / ``error``, plus the
absolute ``selection_file`` / ``email_pack`` paths) lives in ``results[]``.
"""

import json
from pathlib import Path


def stage4_rows(payload: dict) -> list:
    rows = payload.get("results")
    if not isinstance(rows, list):
        raise AssertionError(f"Stage-4 result carries no results[]: {payload!r}")
    return rows


def stage4_row(payload: dict, index: int = 0) -> dict:
    """One professor's machine row, for single-professor fixtures."""
    rows = stage4_rows(payload)
    if len(rows) <= index:
        raise AssertionError(f"expected a results[{index}] row, got {payload!r}")
    return rows[index]


def read_local_selection(row: dict) -> dict:
    """The professor-local 套磁选择.json named by one committed row."""
    assert row["status"] == "ok", row
    return json.loads(Path(row["selection_file"]).read_text(encoding="utf-8"))


def read_local_pack(row: dict) -> dict:
    """The professor-local 邮件输入.json named by one committed row."""
    assert row["status"] == "ok", row
    return json.loads(Path(row["email_pack"]).read_text(encoding="utf-8"))
