# lap — LLM-API Profile

[![ci](https://github.com/lCrazyblindl/lap/actions/workflows/ci.yml/badge.svg)](https://github.com/lCrazyblindl/lap/actions/workflows/ci.yml) · MIT licensed ([LICENSE](LICENSE)) · [Changelog](CHANGELOG.md) · [Roadmap](ROADMAP.md)

**Measure and improve the token-efficiency of agent-facing APIs** (OpenAPI & MCP) — a free, open, neutral toolkit: a scorer (`lap score`), a linter (`lap lint`), a convention (the **LAP profile**), and a reproducible **benchmark**. Not a product, not a gateway, not a new protocol — a public-good measuring stick for a question nobody else answers with real numbers: *how many tokens does my agent-facing API cost, and how much of that is unnecessary?*

## Table of contents

1. [What we did — TL;DR](#1-what-we-did--tldr)
2. [Why this is useful](#2-why-this-is-useful)
3. [Install & usage](#3-install--usage)
4. [Project map](#4-project-map)
5. [Status, license, contributing](#5-status-license-contributing)

---

## 1. What we did — TL;DR

### The problem, in one paragraph

Every time an agent talks to an API — via OpenAPI-generated tools, an MCP server, or a hand-rolled integration — it pays **tokens**: once per session for the menu of what it *can* call (bucket **A**), a little for each call it makes (bucket **B**), and repeatedly for every result that comes back (bucket **C**). Nobody was publishing real, reproducible numbers for this. Vendors cite their own best-case headline figures on their own setups; nobody scores a random real API and tells you where it stands. **lap does that** — for any OpenAPI spec or live MCP server, in one command, for free.

### The toolkit

| piece | what it does |
| --- | --- |
| **`lap score <api>`** | Reports an API's bucket-A menu cost across four rendering forms (naive OpenAPI→tools, compact signatures, a numbered dictionary, a lazy tool-search form), plus a real-MCP baseline (via FastMCP) and a bucket-C result-size estimate. Works on any OpenAPI file/URL, or a live MCP server (`--mcp-url`). |
| **`lap lint <api>`** | Flags concrete violations of the LAP profile's rules (opaque names, no pagination/filtering/projection, no aggregation, verbose writes, ambiguous errors) — each citing the measurement that justifies it. |
| **The LAP profile** ([`profile/`](profile/llm-api-profile.md)) | A short, opinionated set of conventions **on top of** HTTP/JSON/OpenAPI — not a new wire format — for exposing an API so an agent uses it in the fewest tokens. Every rule is backed by a number, not an opinion. |
| **The benchmark** ([`experiments/token-bench/`](experiments/token-bench/README.md)) | A full A/B/C token accounting across 10 tasks in 5 categories, comparing 6 interface variants (naive, real MCP, compact, numbered, code-execution, declarative query) on a real FastAPI testbed — plus an optional live run against a real model to check that compression doesn't cost accuracy. |

### What we found on our own testbed

Six ways of exposing the same API, measured on identical tasks (tiktoken-approx; faithful Anthropic counts run ~60% higher, same ordering):

| variant | menu (bucket A) | "count females" task total |
| --- | --- | --- |
| `openapi_full` (naive OpenAPI→tools, the baseline) | 1637 | 2809 |
| `mcp_fastmcp` (a **real** MCP server, via FastMCP) | 1689 | 2865 |
| `mcp_fastmcp` + output schemas forwarded | 3762 | — |
| `compact_sig` (readable names, dense signatures) | 401 | 1573 |
| `numbered` (endpoint → integer dictionary) | 466 | 1636 |
| `code_exec` (one `run_python` tool + a compact client doc) | 183 | **217** |
| `odata_query` (one declarative `query` tool, server-side) | 219 | **239** |

**Takeaways:** numbering endpoints is a net loss (the codebook still costs bucket A, while saving ~2 tokens of the cheapest bucket); the real wins are shaping the menu (A) and the result (C); a real MCP generator is *not* a strawman — it's slightly heavier than our hand-rolled naive baseline; and declarative queries match code-execution almost everywhere, until a task needs a computed property the query DSL can't express (then code wins by ~40×). Full tables: [`experiments/token-bench/results.md`](experiments/token-bench/results.md).

A later **live success-rate matrix** (Claude Haiku, k=3 repeats) confirmed this isn't just a token story: **compression didn't cost accuracy** — `numbered`/`code_exec`/`odata_query` scored 15/15, `compact_sig` 14/15, and the naive baseline came in *last* at 13/15, while spending 3–4× more tokens. ([`validation.md`](experiments/token-bench/validation.md))

### What we found when we stopped testing our own code and measured *real* tools

This is the part that makes the numbers worth trusting: instead of only comparing our own interface variants, we pointed the same measurement at **real OpenAPI→MCP generators, real published MCP servers, a real hosted API, and two of Anthropic's own real efficiency features** — live, with real HTTP calls and real billed tokens, not simulated.

| what we tested | result | evidence |
| --- | --- | --- |
| 3 real OpenAPI→MCP generators (FastMCP, `openapi-to-mcp`, `openapi-mcp`) | All three emit a menu **heavier than our naive baseline**, and **5–28× heavier than compact** — none ships the compact form | [`docs/GENERATORS.md`](docs/GENERATORS.md) |
| 3 real published MCP servers (git, fetch, time, over stdio) | Even small reference servers pay a real menu tax; a compact rendering of the *same* advertised tools cuts it **~89%** | [`docs/MCP-SERVERS.md`](docs/MCP-SERVERS.md) |
| End-to-end on the live hosted Swagger Petstore (real HTTP, real model) | The naive menu was both the **heaviest and the least reliable** — it failed a count task 0/3 while compact and a real FastMCP server hit 3/3 | [`validation-real.md`](experiments/token-bench/validation-real.md) |
| Anthropic's real **Tool Search**, live, on a real 290-operation API | Cut **billed** input tokens **~90%** vs. the identical schemas without it — the saving is *structural* (server-enforced) — but cost *more* than a compact menu on a small 19-op API, matching Anthropic's own "10+ tools" guidance | [`docs/TOOL-SEARCH.md`](docs/TOOL-SEARCH.md) |
| Anthropic's real **code-execution** tool, live, repeated 5× on a validated task | Came in **heavier** than both the naive baseline and our own sandbox on **every one of 5 runs** — the model consistently needed 2-4 execution attempts to get the sandboxed file path right; its saving is *behavioral* (it only holds if the model's own code never prints the raw data and doesn't need retries), not guaranteed like Tool Search's | [`docs/CODE-EXEC.md`](docs/CODE-EXEC.md) |
| A parser fuzz pass over **175+ real specs** (APIs.guru) | Zero crashes; found and fixed real bugs (Swagger 2.0 support, non-JSON media types, a `tiktoken` crash on a literal `<|endoftext|>` in OpenAI's own spec) | [`experiments/fuzz_corpus.py`](experiments/fuzz_corpus.py) |
| Bucket-C estimate against real, enveloped API responses (`{"data":[...]}`, Kubernetes `{"items":[...]}`) | Fixed a real undercount — 15 of 20 leaderboard rows changed once envelopes were handled correctly | `lap/estimate.py` |

**We report the two real results that *don't* flatter the thesis as prominently as the ones that do.** Tool Search's saving is enforced by the server regardless of what the model does; code-execution's saving depends on the model's own discipline, and across 5 repeated runs it consistently didn't materialize. That distinction — structural vs. behavioral savings — is now written into the LAP profile itself (rules D2 and X1), not just this README.

### The leaderboard

[**`docs/LEADERBOARD.md`**](docs/LEADERBOARD.md) scores **20 real public APIs** — Kubernetes, EC2, Jira, Stripe, GitHub, OpenAI, Slack, Notion, and more — by what their naive agent menu costs today:

| API | naive menu (bucket A) | LAP compact | saved |
| --- | ---: | ---: | ---: |
| Kubernetes | 2,818,799 | 45,015 | **+98%** |
| Amazon EC2 | 606,132 | 63,158 | **+90%** |
| Jira Cloud | 345,552 | 17,996 | **+95%** |
| Stripe | 231,586 | 32,860 | **+86%** |
| _…16 more_ | | | |

Across all 20, naive menus total **~4.9M tokens**; the compact form would cut **~86%** on average (the lazy `tool_search` form ~96%). None of these APIs ships a compact agent menu today — reproduce it with `python experiments/leaderboard.py`.

---

## 2. Why this is useful

- **If you run an API or MCP server:** `lap score`/`lap lint` tell you, in one command, exactly how many tokens your agent-facing menu costs and which concrete, measured rule violations are driving that cost — not vague advice, a number and a citation. Wire it into CI (`--gate-form`/`--max-menu-tokens`, `--fail-on`) so a schema change that blows up the menu fails the build instead of shipping.
- **If you build agents or pick which APIs to wire up:** the leaderboard and the real-tool findings above are due-diligence data — before you integrate an API or an MCP server, you can know whether its menu is going to eat your context window, without running your own experiment first.
- **If you already lint OpenAPI with Spectral:** the same LAP rules ship as a [Spectral ruleset](spectral/README.md) — one line in your existing setup, no new tool to adopt.
- **If you're deciding between MCP/Tool Search/code-execution/a query DSL:** this is the one place that measured all of them, on the same tasks, with the same accounting, including the vendor features' real behavior (not just their marketing numbers) — see [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) for how LAP sits next to NLWeb, MCP gateways, and the other efficiency tooling that's emerged since 2025, and what it deliberately does *not* rebuild (auth, discovery, hosting).
- **Because it's free and it stays free.** MIT-licensed, no telemetry, no paid tier, no company behind it. The goal is a shared, reproducible number the whole agentic-web ecosystem can use — a public good, not a product.

## 3. Install & usage

### Install

```bash
pip install lap-score                 # PyPI (once published — see CHANGELOG.md for the version)
# or, from a clone of this repo:
pip install -e .                      # editable install for local development
pip install -e ".[mcp]"               # + a real-MCP baseline in `lap score` (needs fastmcp)
pip install -e ".[faithful]"          # + faithful Anthropic token counts (needs an API key)
pip install -e ".[all]"               # both extras
```

Core dependencies are just `httpx` + `tiktoken` + `pyyaml` — `fastmcp` and `anthropic` are optional. `lap` is robust to real-world spec mess: `allOf`/`oneOf`/`anyOf`, `$ref` anywhere, OpenAPI 3.1 nullable types, external refs, YAML input, **Swagger/OpenAPI 2.0**, and non-JSON media types — verified crash-free across 175+ real specs (`experiments/fuzz_corpus.py`).

### Quickstart

```bash
lap score https://petstore3.swagger.io/api/v3/openapi.json    # menu (bucket A) token cost
lap lint  https://petstore3.swagger.io/api/v3/openapi.json    # flag LAP rule violations
lap score --mcp-url http://localhost:8080/mcp                 # score a live MCP server's tools
lap score lap/examples/bookstore.openapi.json                 # a bundled example, no network needed
```

Example `lap score` output:

```
LAP menu score - Bookstore API
operations: 6   referenced component schemas: 2

  variant       A tokens  saved vs full  form
  openapi_full  418       +0%            6 tool(s)
  compact_sig   205       +51%           manifest text
  numbered      168       +60%           manifest text

Menu efficiency: compact signatures are +51% vs naive OpenAPI->tools (418 -> 205 tokens).
```

With `fastmcp` installed, the score adds a **real-MCP baseline** (what an actual MCP generator emits) — on the live Swagger Petstore, that's **2226** menu tokens (**3844** with output schemas) vs **415** for compact signatures. With `ANTHROPIC_API_KEY` set, counts switch from a `tiktoken` approximation to Anthropic's real, free `count_tokens` endpoint — absolute numbers change (~60% higher), relative ordering doesn't.

### Lint output

```bash
lap lint api/openapi.json
```

Flags rule violations (opaque operation names, missing pagination/filtering/projection, no server-side aggregation, verbose write responses, ambiguous error handling) with a plain-language message and a citation into the [LAP profile](profile/llm-api-profile.md), e.g. `[WARN R3] collection GET has no pagination (limit/offset/cursor) — agents pull the whole list`.

### CI gate

`--json` makes both commands machine-readable; thresholds turn them into a build gate:

```bash
lap score openapi.json --gate-form compact_sig --max-menu-tokens 800   # exit 1 if the menu is too heavy
lap lint  openapi.json --fail-on warn                                  # exit 1 on any warning
lap lint  openapi.json --ignore R2,A1                                  # suppress specific rules (or a ./.lapignore file)
```

As a raw GitHub Actions step:

```yaml
- run: pip install lap-score
- run: lap score api/openapi.json --gate-form compact_sig --max-menu-tokens 800
- run: lap lint  api/openapi.json --fail-on warn
```

…or the bundled composite **Action** (one step, no manual install):

```yaml
- uses: lCrazyblindl/lap@v0.3.0
  with:
    spec: api/openapi.json
    max-menu-tokens: "800"     # gate the compact_sig menu (omit = report only)
    fail-on: warn              # fail on any lint warning (omit = report only)
```

### Already using Spectral?

The same rules ship as a **Spectral ruleset** — no new tool, one line in your existing lint config:

```yaml
extends:
  - spectral:oas
  - ./path/to/spectral/lap.spectral.yaml
```

See [`spectral/README.md`](spectral/README.md) (custom-function rulesets must be referenced locally, not by URL).

### What `lap score` measures (and doesn't)

It measures **bucket A** (the definitions/menu the model carries in context) and **estimates C** (result size, from each response schema — a structural lower bound, envelope-aware for patterns like `{"data": [...]}`). **B** (the call itself) needs per-API tasks; for a full measured A/B/C run with real accuracy checks, see [`experiments/token-bench`](experiments/token-bench/README.md).

---

## 4. Project map

- [`lap/`](lap/README.md) — the standalone, pip-installable **toolkit** (`lap score`, `lap lint`). Start here for day-to-day use.
- [`profile/`](profile/llm-api-profile.md) — the **LAP profile**: the conventions, with every rule backed by a measurement.
- [`experiments/token-bench/`](experiments/token-bench/README.md) — the full A/B/C benchmark on a real FastAPI testbed ([`pet-zoo/`](pet-zoo/README.md)), 10 tasks across 5 categories, an optional live accuracy check.
- [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) — 20 real public APIs ranked by agent-menu token cost. `experiments/leaderboard.py` regenerates it.
- [`docs/GENERATORS.md`](docs/GENERATORS.md) · [`docs/MCP-SERVERS.md`](docs/MCP-SERVERS.md) · [`docs/TOOL-SEARCH.md`](docs/TOOL-SEARCH.md) · [`docs/CODE-EXEC.md`](docs/CODE-EXEC.md) — the real-tool validation track: real generators, real MCP servers, and two of Anthropic's real efficiency features, tested live.
- [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md) — where LAP sits in the June-2026 agentic-web landscape (NLWeb, llms.txt, MCP gateways, the token-efficiency tools LAP builds on and credits), and what it deliberately doesn't rebuild.
- [`spectral/`](spectral/README.md) — the LAP lint rules as a Spectral ruleset.
- [`pet-zoo/`](pet-zoo/README.md) — the small FastAPI zoo-management API used as the benchmark's testbed.
- [`ROADMAP.md`](ROADMAP.md) — the full staged history of how this was built, stop/resume friendly.

## 5. Status, license, contributing

**v0.3.0**, pre-1.0, actively maintained. MIT licensed ([LICENSE](LICENSE)) — use it, fork it, ship its rules in your own linter, no attribution required (though a star or a mention helps the public-good goal). See [`CHANGELOG.md`](CHANGELOG.md) for release history and [`RELEASING.md`](RELEASING.md) for the release process. Issues and PRs welcome — there's no formal contributing guide yet; open an issue to discuss before a large change.
