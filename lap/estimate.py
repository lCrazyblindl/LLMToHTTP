"""Estimate bucket C (result tokens) from response schemas - no runtime needed.

For each operation we synthesize a representative instance from its success
response schema, serialize it compactly, and count tokens. For array (collection)
responses we multiply the per-item cost by an assumed page size. Values are a
*structural lower bound* - they capture keys + nesting + types (which dominate
repeated-JSON cost), not real string lengths, so a live payload is >= this.

v0.5 S5: when a schema carries a real `example` (OpenAPI 3.0) or `examples`
(JSON Schema 2020-12 / OpenAPI 3.1) value, that's used verbatim instead of a
synthetic placeholder - it's real data the API author wrote down, so it's a
strictly better estimate than a guess. Where no example exists, the synthetic
`string` placeholder's length is configurable (`string_len`, default 6, same
as the literal word "string") so callers who want a more conservative /
realistic floor for un-exampled string fields can raise it explicitly - there's
no universally "correct" default, so this stays an opt-in knob, not a silent
behavior change.
"""

from __future__ import annotations

import json

from . import openapi_ir as ir
from . import tokens

_NON_STRING_PLACEHOLDER = {"integer": 0, "number": 0, "boolean": True, "null": None}

# Common envelope keys real APIs wrap a list in, preferred in this order when
# more than one array-typed property is present (rare, but pick deterministically).
_ENVELOPE_KEYS = ("data", "items", "results", "value", "values", "content", "entries", "records")


def _placeholder(t: str, string_len: int):
    if t == "string":
        return "x" * string_len
    return _NON_STRING_PLACEHOLDER.get(t, "x")


def example_instance(spec: dict, schema, stack: frozenset = frozenset(), depth: int = 0,
                     string_len: int = 6):
    if not isinstance(schema, dict) or depth > 6:
        return None
    if "example" in schema:
        return schema["example"]
    if isinstance(schema.get("examples"), list) and schema["examples"]:
        return schema["examples"][0]
    if "$ref" in schema:
        ref = schema["$ref"]
        if not ir._local(ref) or ref in stack:
            return "ref"
        return example_instance(spec, ir._resolve_ref(spec, ref), stack | {ref}, depth + 1, string_len)
    if "allOf" in schema:
        return {
            fname: example_instance(spec, prop, stack, depth + 1, string_len)
            for fname, prop in ir._collect_properties(spec, schema).items()
        }
    for comb in ("oneOf", "anyOf"):
        if schema.get(comb):
            return example_instance(spec, schema[comb][0], stack, depth + 1, string_len)
    if "enum" in schema:
        return schema["enum"][0]
    t = schema.get("type")
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), "string")
    if t == "object" or "properties" in schema:
        return {
            k: example_instance(spec, v, stack, depth + 1, string_len)
            for k, v in schema.get("properties", {}).items()
        }
    if t == "array":
        return [example_instance(spec, schema.get("items", {}), stack, depth + 1, string_len)]
    return _placeholder(t, string_len)


def _success_schema(spec: dict, op: ir.Op):
    # OpenAPI 3 (`content`) and 2.0 (`schema`), JSON-ish media types — see ir._response_schema.
    return ir._response_schema(spec, op.raw)


def _dumps(value) -> str:
    return json.dumps(value, separators=(",", ":"), default=str, ensure_ascii=False)


def _is_array_schema(spec: dict, schema) -> bool:
    if not isinstance(schema, dict):
        return False
    deref = ir._deref(spec, schema)
    return deref.get("type") == "array" or "items" in deref


def _find_envelope_key(spec: dict, schema: dict) -> str | None:
    """If `schema` is an object with an array-typed property - a common
    `{"data": [...]}` / k8s `{"items": [...]}` / OData `{"value": [...]}` envelope -
    return that property's name. Real APIs almost always wrap collections this
    way; without this, an enveloped list scores as a tiny "object" (one item deep
    in the envelope) and bucket C is badly undercounted."""
    props = ir._collect_properties(spec, schema)
    candidates = [fname for fname, prop in props.items() if _is_array_schema(spec, prop)]
    if not candidates:
        return None
    for key in _ENVELOPE_KEYS:
        if key in candidates:
            return key
    return candidates[0]


def estimate(spec: dict, op: ir.Op, page_size: int = 20, string_len: int = 6) -> tuple[str, int, int]:
    """Returns (kind, per_unit_tokens, estimated_C_tokens) for an operation's
    success response. kind in {"void", "object", "list"}.

    A bare top-level array is scaled by `page_size` directly. A list wrapped in
    an envelope object (`{"data": [...], "total_count": ...}`, k8s `{"items": [...],
    "kind": ..., "metadata": ...}`) is detected too: the sibling fields are kept
    (counted once) and the array property is scaled to `page_size` items, so the
    *whole* envelope at a page is what's estimated - not just one wrapped item.

    `string_len` sizes the synthetic placeholder used for un-exampled string
    fields (real `example`/`examples` values in the schema always win over any
    placeholder, regardless of this setting)."""
    schema = _success_schema(spec, op)
    if not isinstance(schema, dict):
        return ("void", 0, 0)
    deref = ir._deref(spec, schema)
    if schema.get("type") == "array" or "items" in deref:
        per = tokens.count(_dumps(example_instance(spec, deref.get("items", {}), string_len=string_len)))
        return ("list", per, per * page_size + 5)  # +5 for the array brackets/commas

    envelope_key = _find_envelope_key(spec, schema)
    if envelope_key:
        instance = example_instance(spec, schema, string_len=string_len)
        arr = instance.get(envelope_key) if isinstance(instance, dict) else None
        if isinstance(arr, list) and arr:
            item = arr[0]
            per = tokens.count(_dumps(item))
            instance[envelope_key] = [item] * page_size
            return ("list", per, tokens.count(_dumps(instance)))

    per = tokens.count(_dumps(example_instance(spec, schema, string_len=string_len)))
    return ("object", per, per)
