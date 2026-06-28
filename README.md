# LLMToHTTP
LLM TO HTTP Improvement

Sandbox repo for experimenting with exposing tools over HTTP, including MCP.

## Projects

- [`pet-zoo/`](pet-zoo/README.md) — a small FastAPI zoo management API (CRUD for monkeys, lions, tigers, elephants), JSON file storage, Docker support, Swagger docs. Built first as a plain web server; the testbed for the experiments below.
- [`experiments/token-bench/`](experiments/token-bench/README.md) — measures how many **tokens** different ways of exposing pet-zoo's HTTP API to an LLM actually cost, across three buckets: **A** definitions, **B** the call, **C** the result.

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

Takeaways:

1. **Numbering endpoints is a net loss.** `numbered` is consistently worse than `compact_sig`: the number-dictionary must still spell out every argument (bucket A), while it only saves ~2 tokens on the call (bucket B) — the cheapest bucket.
2. **The real wins are A and C.** Compact signatures cut the menu ~76% for free; code-execution cuts read/multi-step tasks ~92% because only the small final value re-enters context, not every result body.
3. **The baseline isn't a strawman.** A real OpenAPI→MCP generator (`mcp_fastmcp`, via FastMCP) is slightly heavier than the hand-rolled `openapi_full`, and ~2.3× heavier once per-tool output schemas are forwarded — so the compact/code wins hold against production MCP too.

See [`experiments/token-bench/results.md`](experiments/token-bench/results.md) for the full per-task tables and [its README](experiments/token-bench/README.md) for how to run it.
