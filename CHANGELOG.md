# Changelog

All notable changes to **lap** (PyPI package `lap-score`) are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/); loose semantic
versioning while pre-1.0.

## [0.3.0] — 2026-06-30

First public release of the full toolkit: a **scorer**, a **linter**, the **LAP
profile**, and a reproducible **token benchmark**.

### Added
- **`lap score <openapi>`** — bucket-A (menu) token cost across `openapi_full` /
  `compact_sig` / `numbered` / `tool_search`, a real-MCP baseline (via FastMCP), and a
  bucket-C result-size estimate. `--json`, `--mcp-url <url>`, and a CI gate
  (`--gate-form` + `--max-menu-tokens`).
- **`lap lint <openapi>`** — flags LAP rule violations (D3 / R1 / R2 / R3 / W1 / E1 / A1);
  `--json`, `--ignore` / `.lapignore`, and a `--fail-on` gate.
- **LAP profile v1.0** (`profile/llm-api-profile.md`) with conformance levels L1–L4.
- **token-bench** — 10 tasks across 5 categories (write / aggregate-read / peek-read /
  multi-step / beyond-DSL) with per-category averages, a code-exec sandbox self-check
  (`--check-code`), and an optional live **success-rate matrix** (`--matrix`).
- **`docs/LEADERBOARD.md`** — agent-menu token cost of 20 real public APIs.
- **`experiments/fuzz_corpus.py`** — parser fuzz harness over real APIs.guru specs.
- A composite **GitHub Action** (`action.yml`) to run `lap score` / `lap lint` in CI.
- A **Spectral ruleset** ([`spectral/`](spectral/README.md)) porting the lint rules
  (D3/R1/R2/R3/W1/E1/A1) for teams already linting OpenAPI with Spectral/vacuum; executed and
  asserted in CI on the bundled example.

### Fixed
- Parser now reads **Swagger/OpenAPI 2.0** (response `schema`, `in: body` params,
  type-on-parameter, `#/definitions`) and **non-JSON media types** (`*+json`, form, XML) —
  previously these specs produced empty/void output.
- `tiktoken` no longer crashes on control strings such as `<|endoftext|>` that appear
  verbatim in real specs (e.g. OpenAI's).
- **Bucket-C estimate is envelope-aware**: a list wrapped in an object (Stripe/JSON:API
  `{"data": [...]}`, Kubernetes `{"items": [...]}`, OData `{"value": [...]}`) is now scaled to
  a full page with its sibling fields kept, instead of being scored as a tiny "object" — the
  previous estimate undercounted real, enveloped API responses (15 of 20 leaderboard rows
  changed once this was fixed).

### Validated
- Faithful Anthropic `count_tokens`: same relative ordering as the tiktoken approximation.
- Live success-rate matrix (Claude Haiku, k=3): **compression did not cost accuracy**
  (compact/numbered/code/query ≥ the naive baseline, at far fewer tokens).
- Crash-free across **175+** real APIs.guru specs.
- **Real-tool validation track** (not just our own interface variants): three real
  OpenAPI→MCP generators and three real published MCP servers all emit menus heavier than
  naive and far heavier than compact (`docs/GENERATORS.md`, `docs/MCP-SERVERS.md`); a live
  end-to-end run on the hosted Swagger Petstore found compression **helped** accuracy, not
  just tokens (`experiments/token-bench/validation-real.md`); Anthropic's real **Tool Search**
  cut billed tokens ~90% at real scale, server-enforced regardless of model behavior
  (`docs/TOOL-SEARCH.md`); Anthropic's real **code-execution**, tested the same way, came in
  *heavier* than both naive and our own sandbox on one run — its saving is behavioral, not
  structural (`docs/CODE-EXEC.md`). See `docs/LEADERBOARD.md` for the 20-real-API dataset this
  release ships alongside the code.

[0.3.0]: https://github.com/lCrazyblindl/lap/releases/tag/v0.3.0
