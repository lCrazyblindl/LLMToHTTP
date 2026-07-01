# Real OpenAPI→MCP generator shoot-out (bucket A) — Swagger Petstore

_By [`experiments/generators.py`](../experiments/generators.py) on the **live**
`https://petstore3.swagger.io/api/v3/openapi.json` (19 operations), 2026-07-01._

**What this is (v0.4 · R2).** The same real OpenAPI spec, run through several **real**
OpenAPI→MCP generators; we count the **menu** each one emits — bucket A, the tool definitions
an agent carries in context every session. Our synthetic `compact_sig` / `tool_search` are
shown only for reference. The point: measure what *real tools* produce, not only our own
generators.

- tokenizer: **tiktoken-approx** _(relative ranking is the signal)_

| menu source | kind | tools | menu tokens (A) | vs naive |
| --- | --- | ---: | ---: | ---: |
| `openapi_full` (ours: naive `$ref`-inlined) | ours | 19 | 1740 | +0% |
| `compact_sig` (ours) | ours | 19 | 415 | **+76%** |
| `tool_search` (ours: lazy) | ours | 2 | 207 | **+88%** |
| **openapi-to-mcp** (`convert_to_mcp`) | REAL | 19 | 2130 | −22% |
| **FastMCP** (`from_openapi`) | REAL | 19 | 2226 | −28% |
| **FastMCP** + output schemas | REAL | 19 | 3844 | −121% |
| **openapi-mcp** (`create_mcp_server`) | REAL | 19 | 4274 | −146% |
| **openapi-mcp** + full response schema | REAL | 19 | 11756 | −576% |

**Finding.** All **three** real generators emit a base menu of **2,130–4,274 tokens** for the
same 19-operation API — every one **heavier** than the naive `$ref`-inlined baseline (1,740),
and **5–28× heavier than a compact menu** (415). Turning on response/output schemas pushes them
to **3,844–11,756**. So "just run a real OpenAPI→MCP generator" typically makes the agent menu
*worse*, not better; none ships the compact form. The token savings LAP measures are, in
practice, **left unclaimed by the real generator ecosystem** — which is exactly the gap a
neutral measurement + a compact convention are meant to close. (This mirrors, on real tools,
the earlier "real MCP is heavier than the naive baseline" result — now across *three* real
generators, not one.)

## How this was measured (honest note)

The three generators have **conflicting pinned dependencies** (they downgrade
`fastapi`/`starlette`), so they can't all live in one environment — itself a small finding
about the ecosystem's fragility. FastMCP's row was measured in the main venv (where
`lap.mcp_form` targets `fastmcp==3.4.x`); the `openapi-mcp` / `openapi-to-mcp` rows in a
throwaway venv. [`experiments/generators.py`](../experiments/generators.py) reproduces whichever
generators are importable in the venv it runs in (it **skips with a note** any that aren't), so
each number is reproducible — just not all in a single install. Extraction is apples-to-apples:
each generator's real tool defs are normalized to `{name, description, input_schema}` and counted
by the same `lap.tokens.count_tools` (openapi-to-mcp emits OpenAI-function format; openapi-mcp's
real wire schema comes from its async `list_tools()`).

## Reproduce

```bash
python -m venv .venv-gen
.venv-gen/Scripts/pip install httpx tiktoken pyyaml fastmcp        # FastMCP row + ours
PYTHONPATH=. .venv-gen/Scripts/python experiments/generators.py
# then, in a SEPARATE throwaway venv (they conflict with the above):
#   pip install httpx tiktoken pyyaml openapi-mcp openapi-to-mcp
#   PYTHONPATH=. python experiments/generators.py
```
