"""`lap lint <openapi>` - check an API against the LAP profile rules.

Static, advisory checks over an OpenAPI spec for the LAP conventions that are
detectable without runtime: opaque names (D3), read shaping on collections
(projection R1 / filter R2 / pagination R3), aggregation (A1), minimal writes
(W1), and uniform errors (E1). Heuristic by nature - it flags likely token/clarity
costs for a human to confirm, each tied to a profile rule.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from . import openapi_ir as ir

PAGINATION = {"limit", "offset", "page", "page_size", "pagesize", "per_page", "perpage",
              "cursor", "top", "skip", "$top", "$skip"}
PROJECTION = {"fields", "field", "select", "$select", "include", "expand", "$expand"}
FILTER_HINTS = {"filter", "$filter", "q", "query", "where", "search"}


@dataclass
class Finding:
    rule: str
    severity: str  # "warn" | "info"
    where: str
    message: str


def _query_names(op: ir.Op) -> set[str]:
    return {p["name"].lower() for p in op.params if p.get("in") == "query"}


def _error_codes(op: ir.Op) -> list[str]:
    return [c for c in op.raw.get("responses", {}) if c[:1] in ("4", "5")]


def lint(spec: dict) -> list[Finding]:
    ops = ir.operations(spec)
    out: list[Finding] = []

    for op in ops:
        where = f"{op.method} {op.path}"

        # D3 - opaque operation name
        if re.fullmatch(r"\d+", op.name) or not re.search(r"[A-Za-z]", op.name) or len(op.name) < 3:
            out.append(Finding("D3", "warn", where,
                               f"opaque operation name '{op.name}' - LLMs ground on readable names"))

        # Read shaping on collection (array-returning) GETs
        if op.method == "GET" and op.returns.endswith("[]"):
            q = _query_names(op)
            if not (q & PAGINATION):
                out.append(Finding("R3", "warn", where,
                                   "collection GET has no pagination (limit/offset/cursor) - agents pull the whole list (big bucket C)"))
            if not (q & PROJECTION):
                out.append(Finding("R1", "info", where,
                                   "no field projection (fields/select) - responses carry every field"))
            if not (q & (FILTER_HINTS | (q - PAGINATION - PROJECTION))):
                out.append(Finding("R2", "info", where,
                                   "no server-side filter params - agents fetch then filter in-context"))

        # W1 - writes returning a full representation by default
        if op.method in ("POST", "PUT", "PATCH") and op.returns not in ("void", ""):
            out.append(Finding("W1", "info", where,
                               f"write returns a full representation ({op.returns}) by default - consider Prefer: return=minimal (server-generated fields only)"))

        # E1 - no error responses declared
        if not _error_codes(op):
            out.append(Finding("E1", "warn", where,
                               "no 4xx/5xx error response declared - agents can't distinguish success/empty/error"))

    # A1 - no aggregate/count endpoint anywhere
    if not any(re.search(r"count|aggregate|stats|summary", op.name + op.path, re.I) for op in ops):
        out.append(Finding("A1", "info", "(global)",
                           "no aggregate/count endpoint - 'how many...' questions force pulling the full list"))

    return out


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Lint an OpenAPI against the LAP profile rules.")
    ap.add_argument("source", help="OpenAPI spec: file path or http(s) URL")
    args = ap.parse_args()

    spec = ir.load_spec(args.source)
    findings = lint(spec)
    title = spec.get("info", {}).get("title", "(untitled API)")
    print(f"\nLAP lint - {title}\nsource: {args.source}\n")

    if not findings:
        print("  No LAP rule violations detected. ✓\n")
        return

    order = {"warn": 0, "info": 1}
    by_rule: dict[str, list[Finding]] = {}
    for f in sorted(findings, key=lambda f: (order[f.severity], f.rule)):
        by_rule.setdefault(f"{f.severity.upper()} {f.rule}", []).append(f)

    for header, items in by_rule.items():
        print(f"  [{header}] {items[0].message.split(' - ')[0]}")
        for f in items[:6]:
            print(f"      {f.where}")
        if len(items) > 6:
            print(f"      ... +{len(items) - 6} more")
        print()

    warns = sum(1 for f in findings if f.severity == "warn")
    infos = len(findings) - warns
    print(f"  {warns} warning(s), {infos} suggestion(s). See profile/llm-api-profile.md for the rules.\n")


if __name__ == "__main__":
    main()
