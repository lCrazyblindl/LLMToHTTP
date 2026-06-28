"""Declarative query variant (OData/GraphQL-style), the alternative to code.

The model sends one `query` with projection/filter/aggregation; the shim's query
engine runs it server-side and returns only the small result. Same end state as
`code_exec` (tiny bucket C), but declarative instead of imperative - so the bench
can compare "query language vs writing code" head to head on the same tasks.

Bundles the response-side ideas we settled on: minimal write responses (create
returns just `{id}`) and a `count` signal when a read is truncated by `top`.
"""

from __future__ import annotations

import spec_source as s

from .base import Definitions, Variant, dumps

_QUERY_TOOL = {
    "name": "query",
    "description": "Run one declarative query server-side; only the result returns.",
    "input_schema": {"type": "object", "properties": {"q": {"type": "object"}}, "required": ["q"]},
}


def _doc() -> str:
    species = "|".join(f'"{x}"' for x in s.SPECIES)
    return (
        "# Tool: query(q). One declarative query; the server runs it, only the result returns.\n"
        "# read:  q = {resource, filter?, select?, top?, count?, group_count?}\n"
        f"#   resource: \"animals\" | {species}\n"
        "#   filter: {field: value} or {field: {gt|ge|lt|le|ne: value}}\n"
        "#   select: [field,...]   top: N (response adds {count} when truncated)\n"
        "#   count: true -> {count}    group_count: field -> {value: n}\n"
        "# write: q = {op:\"create\", resource, body:{...}} -> {id}\n"
        "# Animal fields: id, species, name, age, gender"
    )


class ODataQuery(Variant):
    name = "odata_query"

    def definitions(self) -> Definitions:
        return Definitions(tools=[_QUERY_TOOL], text=_doc())

    def encode_calls(self, task) -> str:
        return dumps(task.query)

    def result_payload(self, task):
        return task.query_result
