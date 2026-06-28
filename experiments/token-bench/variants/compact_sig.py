"""Compact TypeScript-like signatures.

The "healthy half" of the user's idea: keep human-readable names (which the
model grounds on) but drop verbose JSON Schema for dense signatures plus one
shared type block. Same calls and same results as the baseline - only bucket A
shrinks. The gap A(openapi_full) - A(compact_sig) is the pure schema-verbosity
tax.
"""

from __future__ import annotations

import spec_source as s

from .base import Definitions, PerCallVariant


def _field(name: str, type_str: str, constraint: str = "") -> str:
    return f"{name}:{type_str}" + (f" {constraint}" if constraint else "")


def _animal_type() -> str:
    fields = s._schema_fields(s.get_spec(), {"$ref": "#/components/schemas/Animal"})
    body = ", ".join(_field(n, t, c) for n, t, c in fields)
    return f"type Animal = {{ {body} }}"


def _signature(op: s.Op) -> str:
    params = [_field(n, t) for n, t in op.path_params]
    params += [_field(n, t, c) for n, t, c in op.body_fields]
    return f"{op.name}({', '.join(params)}) -> {op.returns}"


class CompactSig(PerCallVariant):
    name = "compact_sig"

    def definitions(self) -> Definitions:
        lines = [
            "# pet-zoo tools. Call as a tool: {\"name\": <fn>, \"input\": {<args>}}.",
            _animal_type(),
            "",
            *[_signature(op) for op in s.list_operations()],
        ]
        return Definitions(text="\n".join(lines))

    def call_id(self, op: s.Op) -> str:
        return op.name
