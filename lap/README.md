# lap — token-efficiency scorer for agent-facing APIs

`lap` is the open, neutral, standalone toolkit (no pet-zoo dependency) that measures
how many **tokens** an API's definitions cost an LLM. It answers: *is my agent-API
menu efficient, and by how much could it shrink?* — the reproducible number the
agentic-web ecosystem lacks (see [`../docs/LANDSCAPE.md`](../docs/LANDSCAPE.md)).

## Install

```bash
pip install -e .                  # from the repo root (or: pip install lap-score once published)
pip install -e ".[mcp]"           # + real-MCP baseline (fastmcp)
pip install -e ".[faithful]"      # + faithful Anthropic count_tokens
```

Core deps are just `httpx` + `tiktoken` + `pyyaml`; `fastmcp` and `anthropic` are optional extras.
Robust to real specs: `allOf`/`oneOf`/`anyOf`, `$ref` in params/requestBodies/responses,
path-item-level parameters, OpenAPI 3.1 `type` lists, external `$ref`s (left intact), and YAML input.

## Quickstart

```bash
lap score  https://petstore3.swagger.io/api/v3/openapi.json   # menu (bucket A) token cost
lap lint   https://petstore3.swagger.io/api/v3/openapi.json   # flag LAP rule violations
lap score  lap/examples/bookstore.openapi.json

# no install needed, from the repo root:
python -m lap.score lap/examples/bookstore.openapi.json
```

Example output:

```
LAP menu score - Bookstore API
operations: 6   referenced component schemas: 2

  variant       A tokens  saved vs full  form
  openapi_full  418       +0%            6 tool(s)
  compact_sig   205       +51%           manifest text
  numbered      168       +60%           manifest text

Menu efficiency: compact signatures are +51% vs naive OpenAPI->tools (418 -> 205 tokens).
```

When `fastmcp` is installed, the score also includes a **real-MCP baseline**
(`FastMCP.from_openapi`) — what an actual MCP generator emits — plus its
output-schema-inclusive figure (`--no-mcp` to skip). On a real public API
(**Swagger Petstore**, 19 ops) the real MCP server costs **2226** menu tokens
(**3844** with output schemas) vs **415** for compact signatures — an ~81%
reduction. The toy finding holds in the wild: a real MCP generator is *heavier*
than the naive baseline.

The score also includes a lazy **`tool_search`** form (the Anthropic Tool Search /
Cloudflare Code Mode pattern: a fixed 2-tool menu + a name index, schemas loaded on
demand). Because it doesn't preload schemas, its bucket A is ~flat in the number of
operations — on a 120-operation API it collapses the menu ~83% vs full schemas,
beating even compact signatures at scale (Petstore: 1740 → 207, −88%).

- **Faithful counts:** set `ANTHROPIC_API_KEY` (uses the free Anthropic `count_tokens`
  endpoint; tool defs counted via the real `tools=` parameter). Without it, a GPT-style
  `tiktoken` approximation — absolute numbers approximate, **relative ordering robust**.

## CI gate

`--json` makes both commands machine-readable; thresholds set the exit code so LAP can fail a build:

```bash
lap score openapi.json --gate-form compact_sig --max-menu-tokens 800   # exit 1 if the menu is too heavy
lap lint  openapi.json --fail-on warn                                  # exit 1 on any warning
lap lint  openapi.json --ignore R2,A1                                  # suppress rules (or a ./.lapignore file)
```

GitHub Actions:

```yaml
- run: pip install lap-score          # or: pip install -e .
- run: lap score api/openapi.json --gate-form compact_sig --max-menu-tokens 800
- run: lap lint  api/openapi.json --fail-on warn
```

## What it measures (and what it doesn't)

It measures **bucket A** (the definitions/menu the model carries in context) and **estimates
C** (result size, from each response schema + an assumed `--page-size` — a structural lower
bound that captures keys/nesting/types). **B** (the call) still depends on per-API tasks; for a
full measured A/B/C run see
[`../experiments/token-bench`](../experiments/token-bench/README.md). The conventions
behind the compact form are the [LAP profile](../profile/llm-api-profile.md).

## Files

| file | role |
| --- | --- |
| `openapi_ir.py` | load any OpenAPI (file/URL) → normalized operations + `inline_refs` |
| `menu.py` | render the menu forms (openapi_full / compact_sig / numbered) from the IR |
| `mcp_form.py` | real-MCP baseline via `FastMCP.from_openapi` (optional; `--no-mcp` to skip) |
| `estimate.py` | estimates bucket C (result size) from response schemas (`--page-size`) |
| `tokens.py` | token counting (Anthropic endpoint, or tiktoken approx) |
| `score.py` | the `lap score` CLI |
| `lint.py` | the `lap lint` CLI — checks a spec against the LAP profile rules (D3/R1/R2/R3/W1/E1/A1) |
| `examples/` | sample specs: a non-pet-zoo Bookstore API + a gnarly OpenAPI 3.1 (allOf / $ref-params / nullable / external-ref) |
