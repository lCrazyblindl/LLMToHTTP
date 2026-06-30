"""Generic OpenAPI -> normalized operations.

The reusable, app-agnostic parsing the `lap` toolkit builds on. Takes any OpenAPI
spec (file path or http[s] URL; JSON or YAML) and yields a normalized operation
list. Hardened for the constructs real specs use: `allOf`/`oneOf`/`anyOf`, `$ref`
in parameters / requestBodies / responses, path-item-level parameters, OpenAPI 3.1
`type: [..., "null"]`, and external `$ref`s (left intact, never crash). Also reads
Swagger/OpenAPI 2.0 shapes (response `schema`, `in: body` params, type keywords on
the parameter, `#/definitions`) and non-JSON media types (`*+json`, form, XML), so
2.0 and XML/form APIs yield real returns/bodies instead of looking empty.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass, field


def load_spec(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        import httpx

        resp = httpx.get(source, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        return _parse(resp.text)
    with open(source, "r", encoding="utf-8") as f:
        return _parse(f.read())


def _parse(text: str) -> dict:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        import yaml  # optional; only needed for YAML specs

        return yaml.safe_load(text)


@dataclass
class Op:
    method: str
    path: str
    summary: str
    path_params: list[tuple[str, str]]
    body_fields: list[tuple[str, str, str]]
    returns: str
    name: str
    params: list[dict]  # merged + deref'd parameter objects (path-item + operation)
    raw: dict = field(default_factory=dict)


# --- $ref handling (local-only; external/broken refs degrade gracefully) -----
def _local(ref) -> bool:
    return isinstance(ref, str) and ref.startswith("#/")


def _resolve_ref(spec: dict, ref: str) -> dict:
    if not _local(ref):
        return {}
    node = spec
    try:
        for part in ref.lstrip("#/").split("/"):
            node = node[part]
    except (KeyError, TypeError, IndexError):
        return {}
    return node if isinstance(node, dict) else {}


def _deref(spec: dict, node):
    """One-level deref of a possible {$ref}. External/broken refs -> the node's
    non-ref siblings only (never crash)."""
    if isinstance(node, dict) and "$ref" in node:
        resolved = _resolve_ref(spec, node["$ref"])
        siblings = {k: v for k, v in node.items() if k != "$ref"}
        return {**resolved, **siblings}
    return node if isinstance(node, dict) else {}


# --- type / field rendering --------------------------------------------------
_SCALARS = {"integer": "int", "number": "float", "boolean": "bool", "string": "string", "null": "null"}


def _scalar(t) -> str:
    return _SCALARS.get(t, str(t))


def _num(x) -> str:
    return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)


def _type_str(spec: dict, schema) -> str:
    if not isinstance(schema, dict):
        return "any"
    if "$ref" in schema:
        if _local(schema["$ref"]):
            target = _resolve_ref(spec, schema["$ref"])
            if "enum" in target:
                return "|".join(f'"{v}"' for v in target["enum"])
        return schema["$ref"].rsplit("/", 1)[-1] or "ref"  # local object or external -> use name
    for comb in ("oneOf", "anyOf"):
        if comb in schema:
            return "|".join(_type_str(spec, m) for m in schema[comb]) or "any"
    if "allOf" in schema:
        return "object"
    if "enum" in schema:
        return "|".join(f'"{v}"' for v in schema["enum"])
    t = schema.get("type", "any")
    if isinstance(t, list):  # OpenAPI 3.1 nullable: ["string", "null"]
        return "|".join(_scalar(x) for x in t)
    if t == "array":
        return _type_str(spec, schema.get("items", {})) + "[]"
    return _scalar(t)


def _constraint_str(schema: dict) -> str:
    bits = []
    if "minimum" in schema:
        bits.append(f">={_num(schema['minimum'])}")
    if "maximum" in schema:
        bits.append(f"<={_num(schema['maximum'])}")
    if "minLength" in schema:
        bits.append(f"len>={_num(schema['minLength'])}")
    if "maxLength" in schema:
        bits.append(f"len<={_num(schema['maxLength'])}")
    return ",".join(bits)


def _collect_properties(spec: dict, schema, depth: int = 0) -> dict:
    """Merged properties of an object schema, following $ref and allOf (and
    best-effort the first oneOf/anyOf member). Depth-guarded against cycles."""
    if not isinstance(schema, dict) or depth > 8:
        return {}
    if "$ref" in schema:
        return _collect_properties(spec, _resolve_ref(spec, schema["$ref"]), depth + 1)
    props = dict(schema.get("properties", {}))
    for member in schema.get("allOf", []):
        props.update(_collect_properties(spec, member, depth + 1))
    if not props:
        for comb in ("oneOf", "anyOf"):
            for member in schema.get(comb, []):
                p = _collect_properties(spec, member, depth + 1)
                if p:
                    return p
    return props


def _schema_fields(spec: dict, schema) -> list[tuple[str, str, str]]:
    out = []
    for fname, prop in _collect_properties(spec, schema).items():
        out.append((fname, _type_str(spec, prop), _constraint_str(_deref(spec, prop))))
    return out


def _content_schema(node) -> dict | None:
    """Pick a schema out of an OpenAPI 3 `content` map. Prefers `application/json`,
    then any `*+json`/`*json` media type, then the first media type with a schema —
    so JSON-ish APIs (`application/hal+json`, `application/problem+json`) and even
    XML-only ones still yield a structural schema instead of looking empty."""
    content = node.get("content") if isinstance(node, dict) else None
    if not isinstance(content, dict):
        return None
    sch = content.get("application/json", {})
    if isinstance(sch, dict) and isinstance(sch.get("schema"), dict):
        return sch["schema"]
    for mt, mobj in content.items():
        if isinstance(mt, str) and mt.endswith("json") and isinstance(mobj, dict) \
                and isinstance(mobj.get("schema"), dict):
            return mobj["schema"]
    for mobj in content.values():
        if isinstance(mobj, dict) and isinstance(mobj.get("schema"), dict):
            return mobj["schema"]
    return None


def _json_body_schema(spec: dict, operation: dict) -> dict | None:
    rb = operation.get("requestBody")
    if isinstance(rb, dict):
        sch = _content_schema(_deref(spec, rb))  # requestBody may itself be a $ref
        if isinstance(sch, dict):
            return sch
    # Swagger/OpenAPI 2.0: the body is a parameter with `in: body` (+ a schema).
    for p in operation.get("parameters", []):
        if isinstance(p, dict) and "$ref" in p:
            p = _deref(spec, p)
        if isinstance(p, dict) and p.get("in") == "body" and isinstance(p.get("schema"), dict):
            return p["schema"]
    return None


def _response_schema(spec: dict, operation: dict) -> dict | None:
    """Success-response schema for an operation, across OpenAPI 3 (`content`) and
    2.0 (`schema` directly on the response)."""
    responses = operation.get("responses", {})
    for code in ("200", "201", "202"):
        resp = _deref(spec, responses.get(code, {}))  # response may be a $ref
        sch = _content_schema(resp)
        if isinstance(sch, dict):
            return sch
        if isinstance(resp.get("schema"), dict):  # Swagger 2.0
            return resp["schema"]
    return None


def _returns_str(spec: dict, operation: dict) -> str:
    schema = _response_schema(spec, operation)
    if not isinstance(schema, dict):
        return "void"
    if schema.get("type") == "array":
        items = schema.get("items", {})
        ref = items.get("$ref", "") if isinstance(items, dict) else ""
        return f"{ref.rsplit('/', 1)[-1] or _type_str(spec, items)}[]"
    ref = schema.get("$ref", "")
    return ref.rsplit("/", 1)[-1] if ref else _type_str(spec, schema)


def _synth_name(method: str, path: str) -> str:
    segments = [p for p in path.strip("/").split("/") if not p.startswith("{")]
    resource = segments[-1] if segments else "root"
    singular = resource[:-1] if resource.endswith("s") else resource
    has_id = "{" in path
    verb = {"GET": "get" if has_id else "list", "POST": "create",
            "PUT": "update", "PATCH": "patch", "DELETE": "delete"}.get(method, method.lower())
    noun = singular if (has_id or method in ("POST", "PUT", "PATCH", "DELETE")) else resource
    return f"{verb}_{noun}"


_PARAM_SCHEMA_KEYS = ("type", "format", "enum", "items", "minimum", "maximum",
                      "minLength", "maxLength", "pattern", "default")


def _param_schema(p: dict) -> dict:
    """The schema of a parameter, across OpenAPI 3 (a nested `schema`) and 2.0
    (the type keywords live directly on the parameter object)."""
    if isinstance(p, dict) and isinstance(p.get("schema"), dict):
        return p["schema"]
    return {k: p[k] for k in _PARAM_SCHEMA_KEYS if isinstance(p, dict) and k in p}


def _resolved_parameters(spec: dict, path_item: dict, operation: dict) -> list[dict]:
    """Path-item-level + operation-level parameters, with $refs resolved."""
    out: list[dict] = []
    for p in list(path_item.get("parameters", [])) + list(operation.get("parameters", [])):
        if isinstance(p, dict) and "$ref" in p:
            p = _deref(spec, p)
        if isinstance(p, dict) and "name" in p:
            out.append(p)
    return out


def operations(spec: dict) -> list[Op]:
    """All operations in a stable order. Names prefer operationId, else a
    synthesized name; collisions are de-duplicated with a numeric suffix."""
    ops: list[Op] = []
    seen: dict[str, int] = {}
    for path in sorted(spec.get("paths", {})):
        path_item = spec["paths"][path]
        if not isinstance(path_item, dict):
            continue
        for method in ("get", "post", "put", "patch", "delete"):
            operation = path_item.get(method)
            if not isinstance(operation, dict):
                continue
            params = _resolved_parameters(spec, path_item, operation)
            path_params = [(p["name"], _type_str(spec, _param_schema(p)))
                           for p in params if p.get("in") == "path"]
            body_schema = _json_body_schema(spec, operation)
            body_fields = _schema_fields(spec, body_schema) if body_schema else []
            name = operation.get("operationId") or _synth_name(method.upper(), path)
            if name in seen:
                seen[name] += 1
                name = f"{name}_{seen[name]}"
            else:
                seen[name] = 1
            ops.append(Op(
                method=method.upper(), path=path, summary=operation.get("summary", ""),
                path_params=path_params, body_fields=body_fields,
                returns=_returns_str(spec, operation), name=name, params=params, raw=operation,
            ))
    return ops


def inline_refs(spec: dict, node):
    """Deep-copy `node` with every *local* $ref recursively inlined; external
    refs and cycles are left intact."""

    def _walk(n, stack: frozenset):
        if isinstance(n, dict):
            if "$ref" in n:
                ref = n["$ref"]
                if not _local(ref) or ref in stack:
                    return {"$ref": ref}  # external or cycle: leave as-is
                resolved = _resolve_ref(spec, ref)
                siblings = {k: v for k, v in n.items() if k != "$ref"}
                return _walk({**resolved, **siblings}, stack | {ref})
            return {k: _walk(v, stack) for k, v in n.items()}
        if isinstance(n, list):
            return [_walk(x, stack) for x in n]
        return n

    return _walk(copy.deepcopy(node), frozenset())


def referenced_component_names(spec: dict) -> list[str]:
    """Component schema names referenced by operation bodies/returns, in order of
    first appearance — used to render shared type blocks in compact menus."""
    names: list[str] = []

    def visit(schema):
        if not isinstance(schema, dict):
            return
        ref = schema.get("$ref") or (schema.get("items", {}) or {}).get("$ref")
        if ref and _local(ref):
            name = ref.rsplit("/", 1)[-1]
            if name not in names:
                names.append(name)

    for op in operations(spec):
        visit(_json_body_schema(spec, op.raw))
        visit(_response_schema(spec, op.raw))
    return names


def schema_ref(spec: dict, name: str) -> str:
    """The `$ref` that resolves component schema `name` in this spec — OpenAPI 3
    (`#/components/schemas/`) or 2.0 (`#/definitions/`)."""
    if name in (spec.get("components", {}) or {}).get("schemas", {}):
        return f"#/components/schemas/{name}"
    if name in (spec.get("definitions", {}) or {}):
        return f"#/definitions/{name}"
    return f"#/components/schemas/{name}"
