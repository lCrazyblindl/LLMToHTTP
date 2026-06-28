"""A tiny OData/GraphQL-style query engine the `odata_query` variant runs.

The model sends one declarative query; this shim executes it against pet-zoo
(fetch + filter/select/top/count/aggregate) and returns only the small result -
the same end state `code_exec` reaches, but declaratively instead of with code.
pet-zoo itself has no query endpoints, so this layer adds them on top, the way a
GraphQL/OData gateway wraps a plain REST API.

Query shape (read):
    {"resource": "animals"|"<species>",
     "filter": {field: value | {gt|ge|lt|le|ne|eq: value}},
     "select": [field, ...],
     "top": N,                 # adds {"count": total} when it truncates (a la @odata.count)
     "count": true,            # -> {"count": total}
     "group_count": field}     # -> {value: n, ...}
Query shape (write, minimal response):
    {"op": "create", "resource": "<species>", "body": {...}}  # -> {"id": N}
"""

from __future__ import annotations

_OPS = {
    "gt": lambda a, b: a > b,
    "ge": lambda a, b: a >= b,
    "lt": lambda a, b: a < b,
    "le": lambda a, b: a <= b,
    "ne": lambda a, b: a != b,
    "eq": lambda a, b: a == b,
}


def _match(item: dict, field: str, cond) -> bool:
    value = item.get(field)
    if isinstance(cond, dict):
        return all(_OPS[op](value, operand) for op, operand in cond.items())
    return value == cond


def _apply_filter(items: list[dict], filt: dict | None) -> list[dict]:
    if not filt:
        return items
    return [it for it in items if all(_match(it, f, c) for f, c in filt.items())]


def run_query(client, q: dict):
    if q.get("op") == "create":
        created = client.post(f"/{q['resource']}s", json=q["body"]).json()
        return {"id": created["id"]}  # minimal write response (server-generated delta only)

    resource = q["resource"]
    path = "/animals" if resource == "animals" else f"/{resource}s"
    items = _apply_filter(client.get(path).json(), q.get("filter"))
    total = len(items)

    if q.get("count"):
        return {"count": total}

    if q.get("group_count"):
        field = q["group_count"]
        grouped: dict = {}
        for it in items:
            grouped[it[field]] = grouped.get(it[field], 0) + 1
        return grouped

    if q.get("select"):
        items = [{k: it[k] for k in q["select"]} for it in items]

    top = q.get("top")
    if top is not None and top < total:
        # Truncated: signal the full total so the model knows more exist.
        return {"items": items[:top], "count": total}
    return items
