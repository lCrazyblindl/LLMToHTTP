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

MODEL = os.environ.get("BENCH_MODEL", "claude-opus-4-8")
MAX_TURNS = 8
MAX_TOKENS = 1024

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
    if task.name.startswith("T1"):
        return ["Bobo"]
    fv = task.final_value
    return [str(v) for v in fv.values()] if isinstance(fv, dict) else [str(fv)]


def _run_one(anthropic_client, variant: V.Variant, task: Task) -> dict:
    client = s.reset_and_seed()
    system = variant.definitions().text or "Use the provided tools to answer."
    tools = _tools_for(variant)
    messages: list[dict] = [{"role": "user", "content": task.prompt}]
    total = 0
    final_text = ""

    for _ in range(MAX_TURNS):
        resp = anthropic_client.messages.create(
            model=MODEL, max_tokens=MAX_TOKENS, system=system, tools=tools, messages=messages
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


def run(tasks: list[Task]) -> str:
    from anthropic import Anthropic

    client = Anthropic()
    headers = ["variant"] + [t.name for t in tasks]
    rows = []
    for v in V.ALL:
        cells = []
        for t in tasks:
            r = _run_one(client, v, t)
            cells.append(f"{r['tokens']} {'OK' if r['ok'] else 'FAIL'}")
        rows.append([v.name] + cells)

    out = ["## Live runs (real Claude, total tokens + success)", ""]
    out.append("| " + " | ".join(headers) + " |")
    out.append("| " + " | ".join("---" for _ in headers) + " |")
    for r in rows:
        out.append("| " + " | ".join(str(c) for c in r) + " |")
    return "\n".join(out)
