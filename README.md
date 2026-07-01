# lap — LLM-API Profile

[![ci](https://github.com/lCrazyblindl/lap/actions/workflows/ci.yml/badge.svg)](https://github.com/lCrazyblindl/lap/actions/workflows/ci.yml) · MIT licensed ([LICENSE](LICENSE))

**Measure and improve the token-efficiency of agent-facing APIs** (OpenAPI & MCP): a scorer (`lap score`), a linter (`lap lint`), a profile, and a benchmark.

Started as a sandbox for token-efficient LLM↔HTTP interaction; now the home of **LAP** — an open, neutral token-efficiency measurement + guidance layer for agent-facing APIs.

## Projects

- [`pet-zoo/`](pet-zoo/README.md) — a small FastAPI zoo management API (CRUD for monkeys, lions, tigers, elephants), JSON file storage, Docker support, Swagger docs. Built first as a plain web server; the testbed for the experiments below.
- [`experiments/token-bench/`](experiments/token-bench/README.md) — measures how many **tokens** different ways of exposing pet-zoo's HTTP API to an LLM actually cost, across three buckets: **A** definitions, **B** the call, **C** the result.
- [`lap/`](lap/README.md) — the standalone, pip-installable **toolkit** (`pip install -e .`): `lap score <openapi-file-or-url>` reports any API's menu (bucket A) token cost (incl. a real-MCP baseline via FastMCP), and `lap lint <openapi>` flags LAP rule violations. The reusable, pet-zoo-free tool.
- [`profile/`](profile/llm-api-profile.md) — **LLM-API Profile (LAP)**, a draft convention (compact discovery + minimal writes + shaped/aggregated reads + a code escape hatch) for token-efficient LLM↔HTTP, with each rule backed by the token-bench numbers. A profile over HTTP/JSON/OpenAPI, not a new protocol.
- [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) — the June-2026 agentic-web landscape (NLWeb, llms.txt, MCP gateways, the token-efficiency tools LAP builds on) and where LAP fits: an open, OpenAPI-native token-efficiency **measurement + linting** layer that complements (doesn't replace) the MCP/NLWeb tooling. See [`ROADMAP.md`](ROADMAP.md) for the staged plan.
- [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) — a ranked, reproducible dataset of the agent-menu (bucket A) token cost of **20 real public APIs** (Kubernetes, EC2, Jira, Stripe, GitHub, OpenAI, …): naive OpenAPI→tools vs the LAP compact/`tool_search` menus. Their naive menus total ~4.9M tokens; `compact_sig` would save ~86% on average (`tool_search` ~96%) — mostly still on the table for agent front-ends today. Built by [`experiments/leaderboard.py`](experiments/leaderboard.py).
- [`spectral/`](spectral/README.md) — the LAP lint rules packaged as a **Spectral ruleset**, so any team already linting OpenAPI gets the token-efficiency checks (D3/R1/R2/R3/W1/E1/A1) in their existing setup, no new tool. CI-validated against the bundled example.

## Findings so far (token-bench)

Two separate channels matter, and conflating them causes most of the confusion:

- **LLM ↔ shim** — measured in **tokens**. The only channel where "efficiency for the LLM" exists. Tokens are the model's I/O alphabet, so you cannot go "binary" here — BPE is tuned for text/code, and for an LLM a human-readable name is *signal*, not waste.
- **shim ↔ site** — bytes/latency. Normal backend work (gRPC, msgpack…). The model never sees it, so it cannot reduce tokens.

On the token channel, four interface variants generated from pet-zoo's OpenAPI compare like this (tiktoken-approx; run with `ANTHROPIC_API_KEY` for faithful counts):

| variant | menu (A) | "count females" task total |
| --- | --- | --- |
| `openapi_full` (naive OpenAPI→tools, baseline) | 1637 | 2809 |
| `mcp_fastmcp` (real MCP server via FastMCP) | 1689 | 2865 |
| `mcp_fastmcp` + output schemas forwarded | 3762 | — |
| `compact_sig` (readable names, dense signatures) | 401 | 1573 |
| `numbered` (endpoint → integer dictionary) | 466 | 1636 |
| `code_exec` (one `run_python` tool + compact client doc) | 183 | **217** |
| `odata_query` (one declarative `query` tool, server-side) | 219 | **239** |

Takeaways:

1. **Numbering endpoints is a net loss.** `numbered` is consistently worse than `compact_sig`: the number-dictionary must still spell out every argument (bucket A), while it only saves ~2 tokens on the call (bucket B) — the cheapest bucket.
2. **The real wins are A and C.** Compact signatures cut the menu ~76% for free; code-execution cuts read/multi-step tasks ~92% because only the small final value re-enters context, not every result body.
3. **The baseline isn't a strawman.** A real OpenAPI→MCP generator (`mcp_fastmcp`, via FastMCP) is slightly heavier than the hand-rolled `openapi_full`, and ~2.3× heavier once per-tool output schemas are forwarded — so the compact/code wins hold against production MCP too.
4. **Declarative queries match code, without running code — up to a point.** An OData/GraphQL-style `query` variant ties `code_exec` on T1–T4 (both collapse the result bucket), with no code sandbox. The wall is T5 (argmax over a *computed* property): the DSL can't express it, so `odata_query` falls back to projecting all rows (C=561) while `code_exec` computes it server-side (C=13). Expressiveness the DSL lacks is where code execution (or a richer protocol) earns its place.

See [`experiments/token-bench/results.md`](experiments/token-bench/results.md) for the full per-task tables and [its README](experiments/token-bench/README.md) for how to run it.
