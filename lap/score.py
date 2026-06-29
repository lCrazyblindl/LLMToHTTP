"""`lap score <openapi>` - measure an API's menu (bucket A) token cost.

Given any OpenAPI spec (file path or http[s] URL), report how many tokens its
definitions cost an LLM under three interface forms, and how much the compact
form would save versus the naive OpenAPI->tools baseline. This is the neutral,
reproducible "is my agent-API menu efficient?" number the ecosystem lacks.

Usage:
    python -m lap.score path/to/openapi.json
    python -m lap.score https://petstore3.swagger.io/api/v3/openapi.json
    ANTHROPIC_API_KEY=... python -m lap.score spec.json   # faithful counts
"""

from __future__ import annotations

import argparse
import json

from . import mcp_form
from . import menu
from . import openapi_ir as ir
from . import tokens


def _pct_saved(part: int, whole: int) -> str:
    if not whole:
        return "-"
    return f"{100 * (whole - part) / whole:+.0f}%"


def score(spec: dict) -> dict[str, int]:
    out = {}
    for name, gen in menu.MENUS.items():
        tools, text = gen(spec)
        out[name] = tokens.count_tools(tools) + tokens.count(text)
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure an OpenAPI's menu (bucket A) token cost.")
    ap.add_argument("source", help="OpenAPI spec: file path or http(s) URL")
    ap.add_argument("--model", help="model id for faithful count_tokens (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--no-mcp", action="store_true", help="skip the real-MCP (FastMCP) baseline row")
    args = ap.parse_args()

    if args.model:
        tokens.MODEL = args.model

    spec = ir.load_spec(args.source)
    ops = ir.operations(spec)
    components = ir.referenced_component_names(spec)
    a_cost = score(spec)
    base = "openapi_full"

    title = spec.get("info", {}).get("title", "(untitled API)")
    print(f"\nLAP menu score - {title}")
    print(f"source: {args.source}")
    print(f"tokenizer: {tokens.backend_name()}"
          + ("  (approx - GPT-style BPE, not Claude's)" if tokens.backend_name() != "anthropic" else ""))
    print(f"operations: {len(ops)}   referenced component schemas: {len(components)}\n")

    base_a = a_cost[base]
    entries = [("openapi_full", a_cost["openapi_full"], f"{len(ops)} tool(s)")]
    if not args.no_mcp and mcp_form.available():
        try:
            inp, outs = mcp_form.build(spec)
            a_in = tokens.count_tools(inp)
            entries.append(("mcp_fastmcp", a_in, f"{len(inp)} MCP tool(s)"))
            a_out = a_in + tokens.count(json.dumps(outs, separators=(",", ":")))
            entries.append(("mcp_fastmcp (+outputSchema)", a_out, "MCP tools + output schemas"))
        except Exception as exc:  # noqa: BLE001
            print(f"  [mcp_fastmcp skipped: {exc!r}]")
    entries.append(("compact_sig", a_cost["compact_sig"], "manifest text"))
    entries.append(("numbered", a_cost["numbered"], "manifest text"))

    rows = [("variant", "A tokens", "saved vs full", "form")]
    for name, a, form in entries:
        rows.append((name, str(a), _pct_saved(a, base_a), form))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    for r in rows:
        print("  " + "  ".join(r[i].ljust(widths[i]) for i in range(4)))

    full, compact = a_cost["openapi_full"], a_cost["compact_sig"]
    print(f"\nMenu efficiency: compact signatures are {_pct_saved(compact, full)} vs naive "
          f"OpenAPI->tools ({full} -> {compact} tokens).")
    print("Note: this scores bucket A (the menu) only. B (the call) and C (results) need "
          "per-API tasks - see experiments/token-bench for a full A/B/C run.\n")


if __name__ == "__main__":
    main()
