"""`lap score <openapi>` - measure an API's menu (bucket A) token cost.

Given any OpenAPI spec (file path or http[s] URL), report how many tokens its
definitions cost an LLM under several interface forms, plus an estimate of the
result size (bucket C). `--json` emits machine-readable output and
`--max-menu-tokens` turns it into a CI gate (non-zero exit if exceeded).

Usage:
    python -m lap.score path/to/openapi.json
    python -m lap.score https://petstore3.swagger.io/api/v3/openapi.json --json
    python -m lap.score spec.json --gate-form compact_sig --max-menu-tokens 800
"""

from __future__ import annotations

import argparse
import json
import sys

from . import estimate
from . import mcp_form
from . import menu
from . import openapi_ir as ir
from . import tokens


def _pct_saved(part: int, whole: int) -> str:
    return "-" if not whole else f"{100 * (whole - part) / whole:+.0f}%"


def _pct_int(part: int, whole: int) -> int:
    return round(100 * (whole - part) / whole) if whole else 0


def score(spec: dict) -> dict[str, int]:
    out = {}
    for name, gen in menu.MENUS.items():
        tools, text = gen(spec)
        out[name] = tokens.count_tools(tools) + tokens.count(text)
    return out


def gather(spec: dict, args) -> dict:
    ops = ir.operations(spec)
    a_cost = score(spec)
    menu_list = [("openapi_full", a_cost["openapi_full"], f"{len(ops)} tool(s)")]
    mcp_error = None
    if not args.no_mcp and mcp_form.available():
        try:
            inp, outs = mcp_form.build(spec)
            a_in = tokens.count_tools(inp)
            menu_list.append(("mcp_fastmcp", a_in, f"{len(inp)} MCP tool(s)"))
            a_out = a_in + tokens.count(json.dumps(outs, separators=(",", ":")))
            menu_list.append(("mcp_fastmcp (+outputSchema)", a_out, "MCP tools + output schemas"))
        except Exception as exc:  # noqa: BLE001
            mcp_error = repr(exc)
    menu_list.append(("compact_sig", a_cost["compact_sig"], "manifest text"))
    menu_list.append(("numbered", a_cost["numbered"], "manifest text"))
    menu_list.append(("tool_search", a_cost["tool_search"], "2 lazy tools + name index"))

    ests = []
    for op in ops:
        kind, _per, est = estimate.estimate(spec, op, args.page_size)
        if kind != "void":
            ests.append({"where": f"{op.method} {op.path}", "kind": kind, "tokens": est})
    ests.sort(key=lambda e: e["tokens"], reverse=True)

    return {
        "api": spec.get("info", {}).get("title", "(untitled API)"),
        "source": args.source,
        "tokenizer": tokens.backend_name(),
        "operations": len(ops),
        "components": len(ir.referenced_component_names(spec)),
        "page_size": args.page_size,
        "menu": [{"variant": n, "a_tokens": a, "form": f} for n, a, f in menu_list],
        "compaction_pct": _pct_int(a_cost["compact_sig"], a_cost["openapi_full"]),
        "estimated_c": ests,
        "mcp_error": mcp_error,
        "_a_cost": a_cost,  # internal, for gating; stripped from JSON
    }


def _print_human(res: dict) -> None:
    approx = "  (approx - GPT-style BPE, not Claude's)" if res["tokenizer"] != "anthropic" else ""
    print(f"\nLAP menu score - {res['api']}")
    print(f"source: {res['source']}")
    print(f"tokenizer: {res['tokenizer']}{approx}")
    print(f"operations: {res['operations']}   referenced component schemas: {res['components']}\n")
    if res["mcp_error"]:
        print(f"  [mcp_fastmcp skipped: {res['mcp_error']}]")
    base_a = res["_a_cost"]["openapi_full"]
    rows = [("variant", "A tokens", "saved vs full", "form")]
    for m in res["menu"]:
        rows.append((m["variant"], str(m["a_tokens"]), _pct_saved(m["a_tokens"], base_a), m["form"]))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    for r in rows:
        print("  " + "  ".join(r[i].ljust(widths[i]) for i in range(4)))

    full, compact = res["_a_cost"]["openapi_full"], res["_a_cost"]["compact_sig"]
    print(f"\nMenu efficiency: compact signatures are {_pct_saved(compact, full)} vs naive "
          f"OpenAPI->tools ({full} -> {compact} tokens).")
    if res["estimated_c"]:
        print(f"\nEstimated result size (bucket C, ~{res['page_size']} items/page; structural lower bound):")
        for e in res["estimated_c"][:8]:
            tag = "   <- heavy list" if e["kind"] == "list" else ""
            print(f"  {e['where']:34} ~{e['tokens']:>5} tokens ({e['kind']}){tag}")
        print("  Field projection (R1) and pagination (R3) cut list cost - see `lap lint`.")
    print("\nNote: A (menu) is measured and C (results) is estimated above; B (the call) needs "
          "per-API tasks - see experiments/token-bench for a full A/B/C run.\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure an OpenAPI's menu (bucket A) token cost.")
    ap.add_argument("source", help="OpenAPI spec: file path or http(s) URL")
    ap.add_argument("--model", help="model id for faithful count_tokens (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--no-mcp", action="store_true", help="skip the real-MCP (FastMCP) baseline row")
    ap.add_argument("--page-size", type=int, default=20,
                    help="assumed page size for the estimated result-size (bucket C)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--gate-form", choices=["openapi_full", "compact_sig", "numbered", "tool_search"],
                    default="openapi_full", help="which menu form --max-menu-tokens checks")
    ap.add_argument("--max-menu-tokens", type=int,
                    help="CI gate: exit 1 if the gate-form menu exceeds this many tokens")
    args = ap.parse_args()

    if args.model:
        tokens.MODEL = args.model

    res = gather(ir.load_spec(args.source), args)
    if args.json:
        print(json.dumps({k: v for k, v in res.items() if not k.startswith("_")}, indent=2))
    else:
        _print_human(res)

    if args.max_menu_tokens is not None:
        got = res["_a_cost"][args.gate_form]
        if got > args.max_menu_tokens:
            print(f"FAIL: {args.gate_form} menu {got} > --max-menu-tokens {args.max_menu_tokens}",
                  file=sys.stderr)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
