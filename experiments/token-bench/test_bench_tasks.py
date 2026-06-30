"""Tests for the grouped benchmark tasks (categories, >=2 each).

These exercise pet-zoo through the bench, so they need its deps (FastAPI). The
package CI installs only lap's deps, so the module skips itself there via
`importorskip`; it runs in the bench venv (`./.venv/Scripts/python.exe -m pytest`).
"""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
pytest.importorskip("fastapi")  # pet-zoo (and thus the whole bench) needs FastAPI

import sandbox  # noqa: E402
from tasks import build_tasks  # noqa: E402

CATEGORIES = {"write", "aggregate-read", "peek-read", "multi-step", "beyond-DSL"}


@pytest.fixture(scope="module")
def tasks():
    return build_tasks()


def test_every_category_has_at_least_two_tasks(tasks):
    by_cat: dict[str, int] = {}
    for t in tasks:
        by_cat[t.category] = by_cat.get(t.category, 0) + 1
    assert set(by_cat) == CATEGORIES, by_cat
    assert all(n >= 2 for n in by_cat.values()), by_cat


def test_tasks_materialized(tasks):
    for t in tasks:
        assert t.final_value is not None, t.name
        assert t.query_result is not None, t.name
        # The per-call path's reduce is the reference answer by construction.
        assert t.reduce(t.bodies) == t.final_value, t.name


def test_code_exec_matches_final_value(tasks):
    # Strongest cross-variant check: the code path returns the same small answer
    # the per-call path computes, in the real sandbox, offline (no API key).
    for t in tasks:
        out = sandbox.run_in_sandbox(t.code)
        assert out.get("ok"), (t.name, out)
        assert out["result"] == t.final_value, (t.name, out["result"], t.final_value)


def test_writes_declare_expected_name(tasks):
    # Writes echo the whole created object; the live check must look for the name,
    # so write tasks must set `expect` explicitly (not derive it from final_value).
    for t in tasks:
        if t.category == "write":
            assert t.expect, t.name
