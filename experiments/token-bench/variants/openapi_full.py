"""Baseline: the naive "OpenAPI -> tools" bridge.

Every operation becomes a tool whose input_schema is the real, $ref-inlined
JSON Schema (path params + request body merged). This is what most automatic
OpenAPI/MCP bridges emit, and it is deliberately verbose - it shows how
expensive bucket A is when you ship full schemas.
"""

from __future__ import annotations

import spec_source as s

from .base import Definitions, PerCallVariant


def _input_schema(op: s.Op) -> dict:
    props: dict = {}
    required: list[str] = []
    for param in op.raw.get("parameters", []):
        if param.get("in") == "path":
            props[param["name"]] = s.inline_refs(param.get("schema", {}))
            if param.get("required", True):
                required.append(param["name"])
    rb = op.raw.get("requestBody")
    if rb:
        body = s.inline_refs(rb["content"]["application/json"]["schema"])
        props.update(body.get("properties", {}))
        required.extend(body.get("required", []))
    return {"type": "object", "properties": props, "required": required}


class OpenApiFull(PerCallVariant):
    name = "openapi_full"

    def definitions(self) -> Definitions:
        tools = [
            {
                "name": op.name,
                "description": op.summary,
                "input_schema": _input_schema(op),
            }
            for op in s.list_operations()
        ]
        return Definitions(tools=tools)

    def call_id(self, op: s.Op) -> str:
        return op.name
