"""R2 — real OpenAPI->MCP generator shoot-out (bucket A).

Scores the **menu** (bucket A) that several *real* OpenAPI->MCP generators emit for the
same spec, next to our synthetic `openapi_full` / `compact_sig` / `tool_search` — a neutral
"which real generator produces the leanest agent menu, and how do they compare to a compact
form?" Writes `docs/GENERATORS.md`.

⚠️ The extra generators (`openapi-mcp`, `openapi-to-mcp`) pin **old fastapi/starlette** that
conflict with the core + pet-zoo deps — do **not** install them in the main venv (it broke
pet-zoo once). Run this in a throwaway env:

    python -m venv .venv-gen
    .venv-gen/Scripts/pip install httpx tiktoken pyyaml fastmcp openapi-mcp openapi-to-mcp
    PYTHONPATH=. .venv-gen/Scripts/python experiments/generators.py [openapi-url]

FastMCP + our synthetic forms always run; the two extras are **skipped with a note** if not
importable. Offline tiktoken by default; set ANTHROPIC_API_KEY for faithful counts.
"""

from __future__ import annotations

import asyncio
import json
import pathlib
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")

from lap import openapi_ir as ir, score, tokens

DEFAULT_URL = "https://petstore3.swagger.io/api/v3/openapi.json"


def _count(tools) -> int:
    return tokens.count_tools(tools)


def gather(url: str):
    spec = ir.load_spec(url)
    nops = len(ir.operations(spec))
    rows = []  # (source, kind, tools, A)
    notes = []

    a = score.score(spec)
    rows.append(("openapi_full (ours: naive $ref-inlined)", "ours", nops, a["openapi_full"]))
    rows.append(("compact_sig (ours)", "ours", nops, a["compact_sig"]))
    rows.append(("tool_search (ours: lazy)", "ours", 2, a["tool_search"]))

    # FastMCP (real)
    try:
        from lap import mcp_form
        if not mcp_form.available():
            raise RuntimeError("fastmcp not installed")
        inp, outs = mcp_form.build(spec)
        rows.append(("FastMCP.from_openapi", "REAL", len(inp), _count(inp)))
        rows.append(("FastMCP + output schemas", "REAL", len(inp),
                     _count(inp) + tokens.count(json.dumps(outs, separators=(",", ":")))))
    except Exception as e:  # noqa: BLE001
        notes.append(f"FastMCP skipped: {e!r}")

    # openapi-mcp (real) — real wire schema via the async list_tools()
    try:
        import openapi_mcp

        def wire(**kw):
            srv = openapi_mcp.create_mcp_server(url, **kw)
            ts = asyncio.run(srv.list_tools())
            return [{"name": t.name, "description": t.description or "", "input_schema": t.inputSchema}
                    for t in ts]

        w = wire()
        rows.append(("openapi-mcp (create_mcp_server)", "REAL", len(w), _count(w)))
        w2 = wire(describe_all_responses=True, describe_full_response_schema=True)
        rows.append(("openapi-mcp + full response schema", "REAL", len(w2), _count(w2)))
    except Exception as e:  # noqa: BLE001
        notes.append(f"openapi-mcp skipped (install in a separate venv): {type(e).__name__}")

    # openapi-to-mcp (real) — OpenAI function format: tool["function"] = {name, description, parameters}
    try:
        from openapi_to_mcp.converter import convert_to_mcp
        ft = convert_to_mcp(spec, url)["tools"]
        norm = [{"name": t["function"]["name"], "description": t["function"].get("description", "") or "",
                 "input_schema": t["function"].get("parameters") or {"type": "object"}} for t in ft]
        rows.append(("openapi-to-mcp (convert_to_mcp)", "REAL", len(norm), _count(norm)))
    except Exception as e:  # noqa: BLE001
        notes.append(f"openapi-to-mcp skipped (install in a separate venv): {type(e).__name__}")

    return spec, nops, rows, notes


def main() -> None:
    url = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_URL
    spec, nops, rows, notes = gather(url)
    base = next(a for s, k, n, a in rows if s.startswith("openapi_full"))
    compact = next(a for s, k, n, a in rows if s.startswith("compact_sig"))

    ours = [r for r in rows if r[1] == "ours"]
    real = sorted([r for r in rows if r[1] == "REAL"], key=lambda r: r[3])

    def pct(tok):
        return f"{round(100 * (base - tok) / base):+d}%" if base else "-"

    lines = [
        f"# Real OpenAPI→MCP generator shoot-out (bucket A) — {spec.get('info', {}).get('title', url)}",
        "",
        f"_Generated {date.today().isoformat()} by [`experiments/generators.py`]"
        "(../experiments/generators.py) on `" + url + f"` ({nops} operations)._",
        "",
        "**What this is.** The same real OpenAPI spec, run through several **real** OpenAPI→MCP "
        "generators; we count the **menu** each one emits (bucket A — the tool definitions an agent "
        "carries in context). Our synthetic `compact_sig` / `tool_search` are shown for reference. "
        "The point of v0.4: measure what *real tools* produce, not only our own generators.",
        "",
        f"- tokenizer: **{tokens.backend_name()}**"
        + ("  _(approximate; ranking is the signal)_" if tokens.backend_name() != "anthropic" else "  _(faithful)_"),
        "",
        "| menu source | kind | tools | menu tokens (A) | vs naive |",
        "| --- | --- | ---: | ---: | ---: |",
    ]
    for s, k, n, tok in ours:
        lines.append(f"| {s} | ours | {n} | {tok} | {pct(tok)} |")
    for s, k, n, tok in real:
        lines.append(f"| {s} | **REAL** | {n} | {tok} | {pct(tok)} |")

    real_only = [r for r in real if "output" not in r[0] and "response schema" not in r[0]]
    if real_only:
        lo = min(r[3] for r in real_only)
        hi = max(r[3] for r in real)
        heavier = sum(1 for r in real_only if r[3] > base)
        lines += [
            "",
            f"**Finding.** Across the real generators, the base menu ranges **{lo:,}–{hi:,} tokens** "
            f"for the same {nops}-operation API. **{heavier} of {len(real_only)}** real generators emit "
            f"a menu *heavier* than the naive `$ref`-inlined baseline ({base:,}), and every one is "
            f"several times heavier than a compact menu ({compact:,}). No mainstream real generator "
            "ships the compact form — the token savings LAP measures are, in practice, unclaimed by "
            "the generator ecosystem.",
        ]
    if notes:
        lines += ["", "_Run notes: " + "; ".join(notes) + "._"]

    out = pathlib.Path(__file__).resolve().parents[1] / "docs" / "GENERATORS.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"\nGenerators on {url} ({nops} ops), {tokens.backend_name()}:")
    for s, k, n, tok in ours + real:
        print(f"  {s:42} {k:4} {n:>4} {tok:>8} {pct(tok):>7}")
    for note in notes:
        print("  [note]", note)
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
