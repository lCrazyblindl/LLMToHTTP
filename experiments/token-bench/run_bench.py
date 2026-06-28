"""Token benchmark for LLM<->HTTP interface variants on pet-zoo.

For every (variant x task) it computes the three token buckets:
  A = definitions (the menu in context)   B = the call(s)   C = the result(s)
and prints comparison tables + writes results.md.

Run:
  python experiments/token-bench/run_bench.py           # offline, tiktoken-approx
  ANTHROPIC_API_KEY=... python .../run_bench.py          # faithful count_tokens
  python experiments/token-bench/run_bench.py --live     # + real Claude runs (Layer 2)
"""

from __future__ import annotations

import argparse
import os
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")  # silence starlette's httpx TestClient deprecation
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec_source as s  # noqa: E402
import tokens as tk  # noqa: E402
import variants as V  # noqa: E402
from tasks import build_tasks  # noqa: E402
from variants.base import dumps  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def bucket_a(variant: V.Variant) -> int:
    d = variant.definitions()
    return tk.count_tools(d.tools) + tk.count(d.text)


def definitions_form(variant: V.Variant) -> str:
    d = variant.definitions()
    parts = []
    if d.tools:
        parts.append(f"{len(d.tools)} tool(s)")
    if d.text:
        parts.append("manifest text")
    return " + ".join(parts)


def md_table(headers: list[str], rows: list[list]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)


def pct(part: int, whole: int) -> str:
    if not whole:
        return "-"
    return f"{100 * (whole - part) / whole:+.0f}%"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true", help="also run each variant through Claude (needs key)")
    ap.add_argument("--out", default=os.path.join(HERE, "results.md"))
    args = ap.parse_args()

    backend = tk.backend_name()
    tasks = build_tasks()
    a_cost = {v.name: bucket_a(v) for v in V.ALL}
    base = V.ALL[0].name  # openapi_full is the baseline

    blocks: list[str] = []
    fixture = ", ".join(f"{k}:{v}" for k, v in s._FIXTURE_COUNTS.items())
    header = [
        "# LLM<->HTTP token benchmark (pet-zoo)",
        "",
        f"- date: {date.today().isoformat()}",
        f"- tokenizer backend: **{backend}**"
        + ("  _(approximate - GPT-style BPE, not Claude's; relative ordering is the signal)_" if backend != "anthropic" else ""),
        f"- source of truth: pet-zoo OpenAPI ({len(s.list_operations())} operations)",
        f"- fixture: {sum(s._FIXTURE_COUNTS.values())} animals ({fixture})",
        "",
        "Buckets: **A** = definitions in context, **B** = the call(s), **C** = the result(s).",
        "",
    ]
    blocks.append("\n".join(header))

    # --- Table 1: the menu cost (bucket A), task-independent --------------------
    a_rows = [
        [v.name, a_cost[v.name], pct(a_cost[v.name], a_cost[base]), definitions_form(v)]
        for v in V.ALL
    ]
    blocks.append("## Bucket A - menu cost (paid ~once per session)\n\n"
                  + md_table(["variant", "A tokens", "saved vs base", "form"], a_rows))

    # --- Per-task tables: A / B / C / total ------------------------------------
    for task in tasks:
        rows = []
        base_total = None
        for v in V.ALL:
            A = a_cost[v.name]
            B = tk.count(v.encode_calls(task))
            C = tk.count(dumps(v.result_payload(task)))
            total = A + B + C
            if v.name == base:
                base_total = total
            rows.append([v.name, A, B, C, total, pct(total, base_total) if base_total else "-"])
        # fix the vs-baseline column now that base_total is known
        for r in rows:
            r[5] = pct(r[4], base_total)
        blocks.append(
            f"## {task.name} - \"{task.prompt}\"\n\n"
            + md_table(["variant", "A", "B call", "C result", "total", "saved vs base"], rows)
        )

    if args.live:
        try:
            import live_runs

            blocks.append(live_runs.run(tasks))
        except Exception as exc:  # noqa: BLE001
            blocks.append(f"## Live runs\n\n_Skipped: {exc!r}_")

    report = "\n\n".join(blocks) + "\n"
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(report)

    print(report)
    print(f"[written] {args.out}")


if __name__ == "__main__":
    main()
