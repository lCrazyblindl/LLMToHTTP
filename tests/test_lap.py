"""Tests for the `lap` toolkit, using the bundled non-pet-zoo Bookstore spec."""

from pathlib import Path

import pytest

from lap import lint, menu
from lap import openapi_ir as ir
from lap import score as score_mod
from lap import tokens

SPEC_PATH = Path(__file__).resolve().parents[1] / "lap" / "examples" / "bookstore.openapi.json"


@pytest.fixture(scope="module")
def spec() -> dict:
    return ir.load_spec(str(SPEC_PATH))


# --- IR ----------------------------------------------------------------------
def test_operations_parsed(spec):
    ops = {op.name: op for op in ir.operations(spec)}
    assert set(ops) == {
        "list_books", "create_book", "get_book", "update_book", "delete_book", "list_author_books",
    }
    assert ops["list_books"].returns == "Book[]"
    assert ops["delete_book"].returns == "void"
    assert ops["get_book"].path_params == [("book_id", "int")]
    body = {f[0] for f in ops["create_book"].body_fields}
    assert body == {"title", "author", "price", "genre"}


def test_inline_refs_inlines_enum(spec):
    tools, _ = menu.full(spec)
    create = next(t for t in tools if t["name"] == "create_book")
    genre = create["input_schema"]["properties"]["genre"]
    assert genre.get("enum") == ["fiction", "nonfiction", "poetry", "reference"]


# --- menus -------------------------------------------------------------------
def test_full_menu_tools(spec):
    tools, text = menu.full(spec)
    assert text == ""
    assert len(tools) == 6
    assert len({t["name"] for t in tools}) == 6  # unique names
    assert all(t["input_schema"]["type"] == "object" for t in tools)


def test_compact_menu_text(spec):
    _, text = menu.compact(spec)
    assert "type Book =" in text and "type BookCreate =" in text
    assert "create_book(" in text
    assert "-> void" in text  # delete_book


def test_numbered_menu_text(spec):
    _, text = menu.numbered(spec)
    assert "1 = " in text and "GET /books" in text


# --- lint --------------------------------------------------------------------
def test_lint_flags_expected_rules(spec):
    findings = lint.lint(spec)
    rules = {f.rule for f in findings}
    assert {"E1", "R3", "R1", "R2", "W1", "A1"} <= rules
    assert "D3" not in rules  # the bookstore has clean operation names
    # the collection GET /books has no pagination -> R3
    assert any(f.rule == "R3" and f.where == "GET /books" for f in findings)
    # every finding cites a severity we render
    assert all(f.severity in ("warn", "info") for f in findings)


# --- tokens ------------------------------------------------------------------
def test_token_backend_and_counts():
    assert tokens.backend_name() in ("anthropic", "tiktoken-approx")
    assert tokens.count("") == 0
    assert tokens.count("hello world") > 0
    assert tokens.count_tools([]) == 0


# --- score -------------------------------------------------------------------
def test_score_orders_compact_below_full(spec):
    a = score_mod.score(spec)
    assert set(a) == {"openapi_full", "compact_sig", "numbered"}
    assert a["compact_sig"] < a["openapi_full"]
    assert a["numbered"] < a["openapi_full"]


# --- robustness on gnarly OpenAPI 3.1 constructs (Stage 8) -------------------
GNARLY_PATH = Path(__file__).resolve().parents[1] / "lap" / "examples" / "gnarly.openapi.json"


@pytest.fixture(scope="module")
def gnarly() -> dict:
    return ir.load_spec(str(GNARLY_PATH))


def test_gnarly_operations_and_refs(gnarly):
    ops = {op.name: op for op in ir.operations(gnarly)}
    assert set(ops) == {"listPets", "createPet", "getPet"}
    assert ops["getPet"].path_params == [("petId", "int")]  # parameter via $ref
    assert ops["listPets"].returns == "Pet[]"
    assert {"name", "owner"} <= {f[0] for f in ops["createPet"].body_fields}  # requestBody via $ref


def test_gnarly_allof_merge(gnarly):
    fields = {f[0] for f in ir._schema_fields(gnarly, {"$ref": "#/components/schemas/Pet"})}
    assert {"id", "name", "status"} <= fields  # allOf members merged


def test_gnarly_31_and_external_refs(gnarly):
    assert ir._type_str(gnarly, {"type": ["integer", "null"]}) == "int|null"  # 3.1 nullable
    assert ir._type_str(gnarly, {"$ref": "https://x/ext.json#/Owner"}) == "Owner"  # external, no crash


def test_gnarly_score_and_lint_run(gnarly):
    assert set(score_mod.score(gnarly)) == {"openapi_full", "compact_sig", "numbered"}
    findings = lint.lint(gnarly)
    # GET /pets declares `limit` (pagination via a path-item-level param) -> no R3 there
    assert not any(f.rule == "R3" and f.where == "GET /pets" for f in findings)


# --- bucket-C estimate (Stage 9) --------------------------------------------
def test_estimate_list_heavier_than_object(spec):
    from lap import estimate

    ops = {op.name: op for op in ir.operations(spec)}
    kind_list, per, list_c = estimate.estimate(spec, ops["list_books"], page_size=20)
    kind_obj, _, obj_c = estimate.estimate(spec, ops["get_book"], page_size=20)
    assert kind_list == "list" and kind_obj == "object"
    assert list_c > obj_c > 0
    assert list_c >= per * 20  # page multiplies the per-item cost


# --- --json / CI gate (Stage 10) --------------------------------------------
def test_score_gather_shape(spec):
    from types import SimpleNamespace

    res = score_mod.gather(spec, SimpleNamespace(source="x", no_mcp=True, page_size=20, model=None))
    assert {"openapi_full", "compact_sig", "numbered"} <= {m["variant"] for m in res["menu"]}
    assert res["estimated_c"] and res["compaction_pct"] > 0


def test_lint_filter_ignored(spec):
    findings = lint.lint(spec)
    assert any(f.rule == "R2" for f in findings)
    filtered = lint.filter_ignored(findings, {"R2"})
    assert all(f.rule != "R2" for f in filtered) and len(filtered) < len(findings)
