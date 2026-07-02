"""`lap score <openapi>` - measure an API's menu (bucket A) token cost.

Given any OpenAPI spec (file path or http[s] URL), report how many tokens its
definitions cost an LLM under several interface forms, plus an estimate of the
result size (bucket C). `--json` emits machine-readable output and
`--max-menu-tokens` turns it into a CI gate (non-zero exit if exceeded).

`--diff <before> <after>` compares two versions of a spec instead: the menu
token delta per form, plus which LAP lint findings were added or fixed - "did
this PR make the API worse for agents?" `--max-growth` turns that into a gate.

Usage:
    python -m lap.score path/to/openapi.json
    python -m lap.score https://petstore3.swagger.io/api/v3/openapi.json --json
    python -m lap.score spec.json --gate-form compact_sig --max-menu-tokens 800
    python -m lap.score --diff old_spec.json new_spec.json
    python -m lap.score --diff old_spec.json new_spec.json --max-growth 500
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


def diff(before: dict, after: dict) -> dict:
    """Compare two versions of an OpenAPI spec: menu (bucket A) token delta per
    form, plus which LAP lint findings were added or fixed. Findings are matched
    by (rule, where) - message/severity text isn't part of the identity, so a
    finding at the same operation for the same rule is treated as unchanged even
    if its wording shifts."""
    from . import lint as lint_mod

    b_cost, a_cost = score(before), score(after)
    forms = []
    for name in b_cost:
        b, a = b_cost[name], a_cost.get(name, 0)
        pct = round(100 * (a - b) / b) if b else (100 if a else 0)
        forms.append({"variant": name, "before": b, "after": a, "delta": a - b, "pct": pct})

    b_findings = {(f.rule, f.where) for f in lint_mod.lint(before)}
    a_findings = {(f.rule, f.where) for f in lint_mod.lint(after)}
    added = sorted(a_findings - b_findings)
    removed = sorted(b_findings - a_findings)

    return {
        "before_operations": len(ir.operations(before)),
        "after_operations": len(ir.operations(after)),
        "forms": forms,
        "findings_added": [{"rule": r, "where": w} for r, w in added],
        "findings_removed": [{"rule": r, "where": w} for r, w in removed],
    }


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


def _print_diff(res: dict, before_src: str, after_src: str) -> None:
    print(f"\nLAP diff - {before_src} -> {after_src}")
    print(f"operations: {res['before_operations']} -> {res['after_operations']}\n")
    rows = [("variant", "before", "after", "delta")]
    for f in res["forms"]:
        sign = "+" if f["delta"] >= 0 else ""
        rows.append((f["variant"], str(f["before"]), str(f["after"]),
                     f"{sign}{f['delta']} ({sign}{f['pct']}%)"))
    widths = [max(len(r[i]) for r in rows) for i in range(4)]
    for r in rows:
        print("  " + "  ".join(r[i].ljust(widths[i]) for i in range(4)))

    added, removed = res["findings_added"], res["findings_removed"]
    if added:
        print(f"\n  {len(added)} new lint finding(s):")
        for f in added[:10]:
            print(f"      [{f['rule']}] {f['where']}")
        if len(added) > 10:
            print(f"      ... +{len(added) - 10} more")
    if removed:
        print(f"\n  {len(removed)} lint finding(s) fixed:")
        for f in removed[:10]:
            print(f"      [{f['rule']}] {f['where']}")
        if len(removed) > 10:
            print(f"      ... +{len(removed) - 10} more")
    if not added and not removed:
        print("\n  No lint finding changes.")
    print()


def _print_mcp(res: dict) -> None:
    approx = "  (approx)" if res["tokenizer"] != "anthropic" else ""
    print(f"\nLAP MCP score - {res['source']}")
    print(f"tokenizer: {res['tokenizer']}{approx}")
    print(f"advertised tools: {res['tools']}\n")
    live = res["menu"]["mcp_live"]
    rows = [("form", "A tokens", "saved vs live")]
    for name in ("mcp_live", "compact_sig", "tool_search"):
        rows.append((name, str(res["menu"][name]), _pct_saved(res["menu"][name], live)))
    widths = [max(len(r[i]) for r in rows) for i in range(3)]
    for r in rows:
        print("  " + "  ".join(r[i].ljust(widths[i]) for i in range(3)))
    print("\nmcp_live = the server's advertised menu; compact_sig / tool_search = a leaner menu's cost.\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Measure an OpenAPI's menu (bucket A) token cost.")
    ap.add_argument("source", nargs="?", help="OpenAPI spec: file path or http(s) URL (omit if --mcp-url)")
    ap.add_argument("after", nargs="?",
                    help="second OpenAPI spec, only with --diff: 'source' is scored as before, "
                    "'after' as after")
    ap.add_argument("--diff", action="store_true",
                    help="compare two spec versions instead of scoring one: "
                    "lap score --diff <before> <after>")
    ap.add_argument("--mcp-url", help="score a live MCP server's advertised tools instead of an OpenAPI spec")
    ap.add_argument("--model", help="model id for faithful count_tokens (needs ANTHROPIC_API_KEY)")
    ap.add_argument("--no-mcp", action="store_true", help="skip the real-MCP (FastMCP) baseline row")
    ap.add_argument("--page-size", type=int, default=20,
                    help="assumed page size for the estimated result-size (bucket C)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    ap.add_argument("--gate-form", choices=["openapi_full", "compact_sig", "numbered", "tool_search"],
                    default="openapi_full", help="which menu form --max-menu-tokens/--max-growth checks")
    ap.add_argument("--max-menu-tokens", type=int,
                    help="CI gate: exit 1 if the gate-form menu exceeds this many tokens")
    ap.add_argument("--max-growth", type=int,
                    help="--diff CI gate: exit 1 if the gate-form menu grew by more than this many "
                    "tokens (before -> after)")
    args = ap.parse_args()

    if args.model:
        tokens.MODEL = args.model

    if args.diff:
        if not args.source or not args.after:
            ap.error("--diff needs two sources: lap score --diff <before> <after>")
        before, after = ir.load_spec(args.source), ir.load_spec(args.after)
        res = diff(before, after)
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            _print_diff(res, args.source, args.after)
        if args.max_growth is not None:
            grown = next(f["delta"] for f in res["forms"] if f["variant"] == args.gate_form)
            if grown > args.max_growth:
                print(f"FAIL: {args.gate_form} menu grew by {grown} tokens > --max-growth "
                      f"{args.max_growth}", file=sys.stderr)
                raise SystemExit(1)
        return

    if args.mcp_url:
        from . import mcp_client

        if not mcp_client.available():
            print("--mcp-url needs fastmcp: pip install 'lap-score[mcp]'", file=sys.stderr)
            raise SystemExit(2)
        res = {"source": args.mcp_url, "tokenizer": tokens.backend_name(),
               **mcp_client.score_tools(mcp_client.fetch_tools(args.mcp_url))}
        if args.json:
            print(json.dumps(res, indent=2))
        else:
            _print_mcp(res)
        live = res["menu"]["mcp_live"]
        if args.max_menu_tokens is not None and live > args.max_menu_tokens:
            print(f"FAIL: mcp_live menu {live} > --max-menu-tokens {args.max_menu_tokens}", file=sys.stderr)
            raise SystemExit(1)
        return

    if not args.source:
        ap.error("provide an OpenAPI source or --mcp-url")

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
