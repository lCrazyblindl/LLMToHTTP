"""Layer 2 (optional): run each variant through Claude for real.

Bucket accounting (Layer 1) shows what *should* happen. This closes the loop:
it actually gives Claude each variant as real tools and lets it solve the tasks,
measuring (a) total tokens really spent across the agent loop and (b) whether the
task succeeded. The point is to check that compression doesn't quietly trade
tokens for wrong answers - the main risk of the `numbered` scheme.

Off by default (run_bench.py --live). Needs ANTHROPIC_API_KEY and spends model
tokens.

SECURITY NOTE: for `code_exec` this executes model-written Python in a subprocess
sandbox (sandbox.py) with a timeout and restricted builtins, against a throwaway
pet-zoo. Soft isolation - fine for this toy, not a production boundary.
"""

from __future__ import annotations

import os

import query_engine
import sandbox
import spec_source as s
import variants as V
from tasks import Task, _call
from variants.base import dumps

# Cheap by default: the live check measures whether compression hurts *accuracy*,
# for which a small model is fine (the comparison is across variants on the same
# model). Override with BENCH_MODEL=claude-opus-4-8 for the strongest signal.
MODEL = os.environ.get("BENCH_MODEL", "claude-haiku-4-5-20251001")
MAX_TURNS = 8
MAX_TOKENS = 1024

# --quick subset: the most telling variants/tasks, to bound spend.
QUICK_VARIANTS = ("openapi_full", "compact_sig", "code_exec", "odata_query")
QUICK_TASKS = ("T2_count_females", "T5_longest_name")

_OPS = s.list_operations()
_BY_OPNAME = {op.name: op for op in _OPS}
_BY_NUMBER = {str(i + 1): op for i, op in enumerate(_OPS)}


def _tools_for(variant: V.Variant) -> list[dict]:
    """What we register with the API for a variant. Compact/numbered keep their
    descriptions in the system manifest, so their tool schemas are bare."""
    if variant.name in ("openapi_full", "mcp_fastmcp", "code_exec", "odata_query"):
        return variant.definitions().tools
    empty = {"type": "object"}
    if variant.name == "numbered":
        return [{"name": str(i + 1), "description": "", "input_schema": empty} for i in range(len(_OPS))]
    return [{"name": op.name, "description": "", "input_schema": empty} for op in _OPS]


def _exec_tool(variant: V.Variant, name: str, tool_input: dict, client) -> str:
    if name == "run_python":
        return dumps(sandbox.run_in_sandbox(tool_input.get("code", "")))
    if name == "query":
        return dumps(query_engine.run_query(client, tool_input.get("q", {})))
    if variant.name == "numbered":
        op = _BY_NUMBER[name]
    elif variant.name == "mcp_fastmcp":
        op = variant.op_for_name(name)
    else:
        op = _BY_OPNAME[name]
    return dumps(_call(client, op, tool_input))


def _expected(task: Task) -> list[str]:
    if task.expect is not None:  # e.g. writes: check the created name, not the whole echo
        return task.expect
    fv = task.final_value
    return [str(v) for v in fv.values()] if isinstance(fv, dict) else [str(fv)]


def _run_one(anthropic_client, variant: V.Variant, task: Task, model: str = MODEL) -> dict:
    client = s.reset_and_seed()
    system = variant.definitions().text or "Use the provided tools to answer."
    tools = _tools_for(variant)
    messages: list[dict] = [{"role": "user", "content": task.prompt}]
    total = 0
    final_text = ""

    for _ in range(MAX_TURNS):
        resp = anthropic_client.messages.create(
            model=model, max_tokens=MAX_TOKENS, system=system, tools=tools, messages=messages
        )
        total += resp.usage.input_tokens + resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        tool_uses = [b for b in resp.content if getattr(b, "type", None) == "tool_use"]
        final_text = " ".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
        if not tool_uses:
            break

        results = []
        for tu in tool_uses:
            out = _exec_tool(variant, tu.name, tu.input or {}, client)
            results.append({"type": "tool_result", "tool_use_id": tu.id, "content": out})
        messages.append({"role": "user", "content": results})

    ok = all(e.lower() in final_text.lower() for e in _expected(task))
    return {"tokens": total, "ok": ok}


# The accuracy question (does compression cost correctness?) compares interface
# *shapes*, so we skip the real-MCP variant (a menu-cost row, not an accuracy one)
# and keep the five shapes that differ in how the model is asked to act.
MATRIX_VARIANTS = ("openapi_full", "compact_sig", "numbered", "code_exec", "odata_query")


def run_matrix(tasks: list[Task], repeats: int = 3, model: str | None = None,
               variant_names=MATRIX_VARIANTS) -> str:
    """Honest validation: per category × variant, run each task `repeats` times and
    report a success *rate* (not one OK/FAIL), plus the mean total tokens. One
    representative task per category keeps spend bounded; `numbered` is included so
    its accuracy is on the record next to its (measured) token cost."""
    from anthropic import Anthropic

    client = Anthropic()
    mdl = model or MODEL
    variants = [V.BY_NAME[n] for n in variant_names]

    by_cat: dict[str, list[Task]] = {}
    for t in tasks:
        by_cat.setdefault(t.category, []).append(t)
    chosen = [(cat, ts[0]) for cat, ts in by_cat.items()]  # first task per category

    succ: dict[tuple, int] = {}
    toks: dict[tuple, int] = {}
    for cat, task in chosen:
        for v in variants:
            s_ok = t_sum = 0
            for _ in range(repeats):
                r = _run_one(client, v, task, model=mdl)
                s_ok += int(r["ok"])
                t_sum += r["tokens"]
            succ[(cat, v.name)] = s_ok
            toks[(cat, v.name)] = round(t_sum / repeats)
            print(f"[matrix] {cat:14} {v.name:13} {s_ok}/{repeats}  (~{toks[(cat, v.name)]} tok)",
                  file=__import__("sys").stderr, flush=True)

    vnames = [v.name for v in variants]
    out = [f"## Honest validation - success rate over {repeats} repeats (model `{mdl}`)", "",
           "Each cell: correct runs / repeats, for one representative task per category. "
           "This is the accuracy check behind the token savings (incl. `numbered`).", "",
           "| category | task | " + " | ".join(vnames) + " |",
           "| --- | --- | " + " | ".join("---" for _ in vnames) + " |"]
    for cat, task in chosen:
        cells = [f"{succ[(cat, vn)]}/{repeats}" for vn in vnames]
        out.append(f"| {cat} | {task.name} | " + " | ".join(cells) + " |")

    totals = {vn: sum(succ[(cat, vn)] for cat, _ in chosen) for vn in vnames}
    denom = len(chosen) * repeats
    out += ["", f"**Overall correct:** " + ", ".join(f"{vn} {totals[vn]}/{denom}" for vn in vnames), ""]

    out += ["### Mean total tokens (same runs)", "",
            "| category | " + " | ".join(vnames) + " |",
            "| --- | " + " | ".join("---" for _ in vnames) + " |"]
    for cat, _task in chosen:
        cells = [str(toks[(cat, vn)]) for vn in vnames]
        out.append(f"| {cat} | " + " | ".join(cells) + " |")
    return "\n".join(out)


def run(tasks: list[Task], quick: bool = False) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    variants = [V.BY_NAME[n] for n in QUICK_VARIANTS] if quick else V.ALL
    used = [t for t in tasks if t.name in QUICK_TASKS] if quick else tasks
    headers = ["variant"] + [t.name for t in used]
    rows = []
    for v in variants:
        cells = []
        for t in used:
            r = _run_one(client, v, t)
            cells.append(f"{r['tokens']} {'OK' if r['ok'] else 'FAIL'}")
        rows.append([v.name] + cells)

    out = [f"## Live runs (real Claude, total tokens + success) - model `{MODEL}`"
           + (" - quick subset" if quick else ""), ""]
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)
