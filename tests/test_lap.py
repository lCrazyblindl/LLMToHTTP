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
    # tiktoken control strings that appear verbatim in real specs (e.g. OpenAI's
    # "<|endoftext|>") must be counted as text, not crash the encoder.
    assert tokens.count("ends with <|endoftext|> token") > 0


# --- score -------------------------------------------------------------------
def test_score_orders_compact_below_full(spec):
    a = score_mod.score(spec)
    assert {"openapi_full", "compact_sig", "numbered", "tool_search"} == set(a)
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
    assert {"openapi_full", "compact_sig", "numbered", "tool_search"} <= set(score_mod.score(gnarly))
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


# --- envelope-aware bucket C (v0.4 R7) ---------------------------------------
def _envelope_spec(list_key: str, extra_props: dict) -> dict:
    item_schema = {"type": "object", "properties": {
        "id": {"type": "integer"}, "name": {"type": "string"},
    }}
    resp_schema = {"type": "object", "properties": {
        list_key: {"type": "array", "items": item_schema}, **extra_props,
    }}
    return {
        "openapi": "3.0.0", "info": {"title": "Enveloped"},
        "paths": {"/things": {"get": {
            "operationId": "listThings",
            "responses": {"200": {"content": {"application/json": {"schema": resp_schema}}}},
        }}},
    }


def test_estimate_envelope_data_key():
    # Stripe/JSON:API-style {"data": [...], "total_count": ...} - a real list, not
    # a lone wrapped item. Without envelope detection this scored as "object".
    from lap import estimate

    spec = _envelope_spec("data", {"total_count": {"type": "integer"}})
    op = ir.operations(spec)[0]
    kind, per, c = estimate.estimate(spec, op, page_size=20)
    assert kind == "list"
    assert per > 0
    assert c > per * 15  # scaled to ~page_size items, not one wrapped item


def test_estimate_envelope_items_key_k8s_style():
    # Kubernetes-style {"items": [...], "kind": ..., "apiVersion": ...}.
    from lap import estimate

    spec = _envelope_spec("items", {"kind": {"type": "string"}, "apiVersion": {"type": "string"}})
    op = ir.operations(spec)[0]
    kind, per, c = estimate.estimate(spec, op, page_size=10)
    assert kind == "list" and c > per * 8


def test_estimate_envelope_prefers_conventional_key_when_ambiguous():
    # Two array-typed properties: the conventional name wins deterministically.
    from lap.estimate import _find_envelope_key

    schema = {"type": "object", "properties": {
        "weird_list_name": {"type": "array", "items": {"type": "string"}},
        "data": {"type": "array", "items": {"type": "string"}},
    }}
    assert _find_envelope_key({}, schema) == "data"


def test_estimate_no_envelope_for_plain_object():
    # A plain object with no array-typed property must stay "object", not "list".
    from lap import estimate

    spec = {
        "openapi": "3.0.0", "info": {"title": "Plain"},
        "paths": {"/thing": {"get": {
            "operationId": "getThing",
            "responses": {"200": {"content": {"application/json": {"schema": {
                "type": "object",
                "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
            }}}}},
        }}},
    }
    op = ir.operations(spec)[0]
    kind, _per, _c = estimate.estimate(spec, op, page_size=20)
    assert kind == "object"


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


# --- tool_search collapses bucket A at scale (Stage 11) ---------------------
def _big_spec(n: int) -> dict:
    paths = {
        f"/things{i}": {"get": {"operationId": f"listThings{i}", "responses": {"200": {
            "content": {"application/json": {"schema": {
                "type": "array", "items": {"$ref": "#/components/schemas/Thing"}}}}}}}}
        for i in range(n)
    }
    return {"openapi": "3.0.0", "info": {"title": "Big"}, "paths": paths,
            "components": {"schemas": {"Thing": {"type": "object", "properties": {
                "id": {"type": "integer"}, "name": {"type": "string"},
                "description": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}}}}}


def test_tool_search_collapses_at_scale():
    a = score_mod.score(_big_spec(120))
    assert a["tool_search"] < a["openapi_full"]
    assert a["tool_search"] < a["compact_sig"]  # at scale, lazy beats even compact signatures


# --- Swagger/OpenAPI 2.0 + media-type fallback: sane output (Stage 17) -------
SWAGGER2_PATH = Path(__file__).resolve().parents[1] / "lap" / "examples" / "swagger2.json"


@pytest.fixture(scope="module")
def swagger2() -> dict:
    return ir.load_spec(str(SWAGGER2_PATH))


def test_swagger2_returns_and_body(swagger2):
    # 2.0 puts the response schema under `response.schema` and the body in an
    # `in: body` parameter; the IR must read both (not report void / empty body).
    ops = {op.name: op for op in ir.operations(swagger2)}
    assert ops["listPets"].returns == "Pet[]"  # 2.0 array response
    assert ops["getPet"].returns == "Pet"
    assert ops["getPet"].path_params == [("petId", "int")]
    assert ops["createPet"].returns == "Pet"  # not "void"
    assert {"name", "status"} <= {f[0] for f in ops["createPet"].body_fields}  # in: body schema


def test_swagger2_type_block_resolves_definitions(swagger2):
    _, text = menu.compact(swagger2)
    assert "type Pet = {" in text
    assert "id:" in text and "status:" in text  # #/definitions/... resolved, block not empty


def test_swagger2_lint_and_estimate(swagger2):
    from lap import estimate

    findings = lint.lint(swagger2)
    rules = {f.rule for f in findings}
    assert "W1" in rules  # createPet returns the full Pet representation
    assert any(f.rule == "R3" and f.where == "GET /pets" for f in findings)  # collection, no paging
    ops = {op.name: op for op in ir.operations(swagger2)}
    kind, _per, c = estimate.estimate(swagger2, ops["listPets"], page_size=20)
    assert kind == "list" and c > 0  # bucket-C estimate works on 2.0 now


def test_content_media_type_fallback():
    # Non-application/json media types (form body, vnd.api+json response) must
    # still yield a schema, so JSON-ish and XML/form APIs aren't seen as empty.
    spec = {
        "openapi": "3.0.0", "info": {"title": "Media"},
        "paths": {"/things": {"post": {
            "operationId": "makeThing",
            "requestBody": {"content": {"application/x-www-form-urlencoded": {
                "schema": {"type": "object", "properties": {"q": {"type": "string"}}}}}},
            "responses": {"201": {"content": {"application/vnd.api+json": {
                "schema": {"$ref": "#/components/schemas/Thing"}}}}},
        }}},
        "components": {"schemas": {"Thing": {"type": "object",
                                             "properties": {"id": {"type": "integer"}}}}},
    }
    op = ir.operations(spec)[0]
    assert op.returns == "Thing"  # */*+json response picked up
    assert {"q"} <= {f[0] for f in op.body_fields}  # form-encoded body picked up


# --- score a live MCP server's advertised tools (Stage 12) ------------------
def test_mcp_client_scores_live_server():
    pytest.importorskip("fastmcp")
    import httpx
    from fastmcp import FastMCP

    from lap import mcp_client

    spec = ir.load_spec(str(SPEC_PATH))
    server = FastMCP.from_openapi(openapi_spec=spec, client=httpx.AsyncClient(base_url="http://lap.invalid"))
    tools = mcp_client.fetch_tools(server)  # in-memory MCP transport (real client protocol)
    assert len(tools) == 6
    res = mcp_client.score_tools(tools)
    assert res["menu"]["tool_search"] < res["menu"]["mcp_live"]
