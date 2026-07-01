# LAP Roadmap — token-efficiency layer for the agentic web

**What this is:** the staged plan for **LAP**, an open, neutral toolkit that measures
the token cost of agent-facing APIs (A/B/C buckets) and scores them against the LAP
profile. Positioned as an open, reproducible **efficiency-measurement + guidance layer** —
complementary to MCP/NLWeb (and to the token-efficiency tools it credits), **not** a rebuild
of gateways/auth/discovery
(those are already covered by Microsoft NLWeb, AWS/Hypr MCP gateways, NIST/IETF auth).

**How to resume (future sessions):** read this file, find the **▶** stage, do it, tick
it `[x]`, move **▶** to the next stage, and update the `lap-roadmap` memory pointer.
Load only the files that stage needs — the user has a limited token budget, so this is
built for stop/resume, one bounded session per stage.

## Reuse (don't rebuild)

`experiments/token-bench/`: `spec_source.py` (the `Op` IR, `list_operations`,
`inline_refs`), `tokens.py` (count backends), `variants/*`
(openapi_full / compact_sig / numbered / code_exec / odata_query / mcp_fastmcp),
`query_engine.py`, `sandbox.py` + `sandbox_runner.py`, `run_bench.py`;
`profile/llm-api-profile.md` (the LAP profile draft). Run with `./.venv/Scripts/python.exe`.

## Stages

- [x] **Stage 0 — Persist the plan.** `ROADMAP.md` + `lap-roadmap` memory pointer +
  repo `CLAUDE.md` link. _Done: a new session resumes from the pointer alone._
- [x] **Stage 1 — Landscape & positioning** → [`docs/LANDSCAPE.md`](docs/LANDSCAPE.md).
  Done: June-2026 landscape (NLWeb, llms.txt, MCP gateways, NIST/IETF auth, efficiency
  patterns) mapped with sources; LAP positioned as the efficiency-measurement niche.
- [x] **Stage 2 — Generalize the scorer beyond pet-zoo.** Done: standalone [`lap/`](lap/)
  toolkit — `python -m lap.score <openapi-file-or-url>` loads any spec, normalizes it
  (`lap/openapi_ir.py`), renders openapi_full / compact_sig / numbered menus
  (`lap/menu.py`) and reports bucket-A tokens + reduction. Verified on a non-pet-zoo
  Bookstore spec (418 → 205 compact). B/C still need per-API tasks (token-bench).
- [x] **Stage 3 — Score real ecosystem targets.** Done: `lap/mcp_form.py` adds a
  real-MCP baseline via `FastMCP.from_openapi`; `lap score` now includes the real MCP
  menu (+ output-schema figure). Verified end-to-end on the **live Swagger Petstore**
  (19 ops): real MCP 2226 (3844 w/ output schemas) vs compact 415 — the toy finding
  holds in the wild (real MCP is heavier than the naive baseline).
- [x] **Stage 4 — Faithful tokens + success check (mechanism only).** The live check
  defaults to a cheap model (`claude-haiku-4-5`) + a `--quick` subset to bound spend;
  both token-bench and `lap` use faithful `count_tokens` automatically when a key is set.
  **Closed by choice:** no API key available (Pro ≠ API), so faithful/live numbers were
  skipped; the budget-safe mechanism is committed and runs anytime via
  `ANTHROPIC_API_KEY=... python experiments/token-bench/run_bench.py --live --quick`.
- [x] **Stage 5 — LAP profile v1.0 + linter.** Done: profile promoted to v1.0;
  `lap/lint.py` + `python -m lap.lint <openapi>` flags D3 / R1 / R2 / R3 / W1 / E1 / A1
  with rule citations — verified on the live Swagger Petstore (6 warnings, 10 suggestions).
- [x] **Stage 6 — Package & share.** Done: `pyproject.toml` (core deps httpx+tiktoken,
  extras `[mcp]`/`[faithful]`) + `lap/cli.py` console script — `pip install -e .` gives a
  `lap` command; `lap score` / `lap lint` verified as installed commands. **Remaining manual
  step (owner's):** publish to PyPI + a GitHub release to make it `pip install lap-score`.

## Stages — v0.2 (planned improvements; same stop/resume model)

Ordered: trust foundation → robustness → value features → (last) the key-needing live
validation. Each is one bounded session. `[no key]` = doable without an API key.

- [x] **Stage 7 — Tests + CI + LICENSE.** Done: `tests/test_lap.py` (8 tests, green) over
  IR / menu / lint / tokens / score on the bookstore spec; `.github/workflows/ci.yml` (pytest +
  smoke `lap lint`); MIT `LICENSE`; `dev` extra + CI badge in README.  `[no key]`
- [x] **Stage 8 — Robustness on real specs.** Done: rewrote `lap/openapi_ir.py` to handle
  `allOf`/`oneOf`/`anyOf`, `$ref` in params/requestBodies/responses, path-item-level
  parameters, OpenAPI 3.1 `type` lists, external `$ref`s (left intact), and YAML input. Added
  `lap/examples/gnarly.openapi.json` (3.1) + 4 regression tests (now 12 passing); live Petstore
  unregressed.  `[no key]`
- [x] **Stage 9 — Estimate bucket C from response schemas.** Done: `lap/estimate.py` synthesizes
  an instance from each success-response schema, counts its tokens, and (for arrays) multiplies
  by `--page-size`; `lap score` now prints an "Estimated result size (bucket C)" table flagging
  heavy lists (Petstore `GET /pet/findByStatus` ~785 tok/page vs ~39 for objects). +1 test (13).  `[no key]`
- [x] **Stage 10 — `--json` output + CI gate.** Done: `lap score`/`lap lint` take `--json`
  (structured output); `lap score --gate-form F --max-menu-tokens N` and `lap lint --fail-on
  warn` set a non-zero exit code; rule suppression via `--ignore R2,A1` or a `./.lapignore`
  file; GH Action snippet in the README. Exit codes verified; +2 tests (15).  `[no key]`
- [x] **Stage 11 — `tool_search` menu form.** Done: `lap/menu.py` `tool_search` (fixed
  `search_tools`+`call_tool` + name index; schemas on demand) added to `lap score`. Its bucket A
  is ~flat in #ops: Petstore 1740→207 (−88%), a synthetic 120-op API 3722→624 (−83%), beating
  even compact at scale. +1 test (16). `[no key]`
- [x] **Stage 12 — Score live MCP/NLWeb endpoints.** Done: `lap/mcp_client.py` + `lap score
  --mcp-url <url>` connects via a FastMCP MCP client, lists advertised tools, and reports
  mcp_live vs compact/tool_search. Verified end to end against a local HTTP MCP server (6 tools,
  mcp_live 422 → compact 69 / tool_search 149) + an in-memory test. +1 test (17).  `[no key]`
- [x] **Stage 13 (LAST) — Live success + faithful validation.** Done with a real API key:
  faithful `count_tokens` (anthropic backend) reran token-bench — **same ordering** as the
  tiktoken approximation, ~60% higher absolute (e.g. openapi_full 2665, compact 634, real MCP
  2752/6418, code 555). `--live --quick` on Claude Haiku: **every variant answered correctly**
  (compression doesn't cost accuracy) while compact/code/query spent ~3–4× fewer total tokens;
  the T5 DSL-gap shows live (odata 2995 vs code 1735). Also fixed a latent empty-content bug in
  token-bench `tokens.py` that the faithful run surfaced. `results.md` now holds faithful+live.

## Stages — v0.3 (post-validation hardening + reach)

Same stop/resume model. `[key]` = needs `ANTHROPIC_API_KEY` (read the User-scope value into the
command, or restart Claude Code so all tools inherit it).

- [x] **Stage 14 — Rename + rebrand to `lap`.** _(Done 2026-06-30 — owner renamed the repo on
  GitHub; agent pointed `origin`, the CI badge, and `pyproject` `[project.urls]` at `/lap`.)_
  README title/tagline + `CLAUDE.md` were already rebranded to `lap` (LLM-API Profile). The local
  folder stays `LLMToHTTP`; GitHub auto-redirects the old URL.  `[no key]`
  - **To let the agent do the rename itself, the owner provides ONE of:** (a) install GitHub CLI
    + `gh auth login` (one-time, interactive; then the agent runs `gh repo rename lap` + `gh repo
    edit --description ...`); (b) a GitHub token in env `GH_TOKEN` at User scope (classic `repo`
    scope, or fine-grained Administration: write) — never pasted in chat — then restart so the
    process inherits it, and the agent renames via the REST API. Probed 2026-06-30: `gh` absent,
    no `GH_TOKEN`/`GITHUB_TOKEN`. Zero-credential fallback: owner renames in the web UI and the
    agent flips the refs (no auth needed for that part).
  - **Naming decision (owner asked to record):** keep the repo name **`lap`** — the umbrella
    *toolkit*, not any one part — and let the **description enumerate all four deliverables incl.
    the benchmark**, so the name matches the full implementation (not `lap-profile`/`lap-bench`,
    which would privilege one part). Canonical description to apply at rename: **"lap — measure &
    improve the token-efficiency of agent-facing APIs (OpenAPI & MCP): scorer, linter, the LAP
    profile, and a reproducible token benchmark."** README tagline already lists all four.
- [x] **Stage 15 — Honest validation.** Done. (a) The profile no longer says "validated" — it
  reports a measured success rate with caveats. (b) Ran a live **success-rate matrix** (new
  `run_bench.py --matrix` / `live_runs.run_matrix`): Claude Haiku, one task per category × **k=3
  repeats**, `numbered` included → [`validation.md`](experiments/token-bench/validation.md).
  **Compression did not cost accuracy:** `numbered`/`code_exec`/`odata_query` 15/15, `compact_sig`
  14/15, naive `openapi_full` *last* at 13/15 (both misses on the aggregate-count task), while the
  compact/code/query forms used ~1.4–4× fewer total tokens. Profile updated with this evidence +
  caveats (one cheap model, k=3 noisy at n=3, toy API). The key was read from User scope per-command
  (process didn't inherit it). _sonnet pass + ≥2 tasks/category left as cheap follow-ups._  `[key]`
- [x] **Stage 16 — Grouped, ≥2-per-category benchmark tasks.** Done: `tasks.py` now carries a
  `category` per task and has **10 tasks across the 5 categories** (write / aggregate-read /
  peek-read / multi-step / beyond-DSL), ≥2 each; `run_bench` prints a **per-category averages**
  table (mean A+B+C vs baseline) ahead of the per-task tables; `results.md` regenerated (the prior
  faithful+live run kept as `results-faithful.md`). +4 bench tests (`test_bench_tasks.py`, guarded
  by `importorskip("fastapi")` so package CI skips it) — full suite 21 passing. The DSL gap holds
  as a category average: code_exec ~92% on beyond-DSL vs odata_query ~78% (it must project all
  rows for avg/argmax over a computed property).  `[no key]`
- [x] **Stage 17 — Fuzz on a real-spec corpus.** Done: `experiments/fuzz_corpus.py` runs the whole
  parser surface (IR + all menus via `score` + `lint` + bucket-C estimate) over APIs.guru. **175+
  real specs across two random seeds + a curated gnarly set (Stripe, GitHub 845 ops, Kubernetes,
  EC2 1182 ops, Jira, Azure, googleapis compute) → zero crashes** — the named long-tail
  (`discriminator`, webhooks, deep nesting, 1000+ ops) was already crash-robust (Stage 8). The real
  gap was **degenerate output, not crashes**: Swagger/OpenAPI **2.0** specs (~25% of the corpus, e.g.
  kubernetes/azure) reported every op as `returns=void`, empty body, no W1/R* — because 2.0 puts the
  response schema under `response.schema` (not `content`) and the body in an `in: body` param; some
  3.0 specs (EC2) were void too (responses are `text/xml`, not `application/json`). Fixed in
  `openapi_ir.py` (additive, 3.x unchanged): a JSON-ish **media-type fallback** (`*+json`/form/xml),
  **2.0 response `schema`**, **2.0 `in: body` params**, type-on-parameter, and `#/definitions` type
  blocks. Regression sample `lap/examples/swagger2.json` + 4 tests (25 passing); k8s went from 0
  findings to 284, EC2 returns 0→1070.  `[no key]`
- [x] **Stage 18 — Efficiency leaderboard.** Done: `experiments/leaderboard.py` scores real public
  APIs from APIs.guru and writes [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md) — **20 APIs** ranked by
  naive agent-menu (bucket A) cost: Kubernetes 2.82M tokens, EC2 606k, Jira 346k, Stripe 232k, …;
  naive menus total ~4.9M, `compact_sig` saves ~86% on average and `tool_search` ~96% (mostly
  still on the table for agent front-ends). Surfaced + fixed a real crash on the way: tiktoken
  raised on the literal `<|endoftext|>`
  in OpenAI's spec — `lap/tokens.py` now encodes with `disallowed_special=()` (+regression test, 25
  passing).  `[no key]`
- [x] **Stage 19 — Ship it (artifacts ready; owner publishes).** Done by the agent:
  `CHANGELOG.md` (0.3.0), version bump `pyproject` `0.1.0 → 0.3.0` + classifiers + Changelog/
  Leaderboard urls, a composite marketplace **GitHub Action** (`action.yml`, used as
  `uses: lCrazyblindl/lap@v0.3.0`; README snippet), and [`RELEASING.md`](RELEASING.md) with the
  owner's exact publish steps. **Remaining (owner, needs credentials):** `python -m build` →
  `twine upload` to PyPI + `gh release create v0.3.0` (and "Publish this Action to the
  Marketplace"). See `RELEASING.md`.  `[owner action]`

### Further backlog (unscheduled, key-free)
**Shipped after the v0.3 stages:** the LAP rules as a **Spectral ruleset**
([`spectral/`](spectral/README.md), executed + asserted in CI). Still open: a short
**Related work / credit** note in the README,
estimate-C realism (use schema `examples`; configurable string length), caching economics
(first-call vs amortized A), bucket-B estimate, NLWeb endpoint scoring, lint auto-fix (emit a
compact manifest), `lap score before after` diff mode, profile L0 "be-discoverable" rule
(llms.txt / .well-known / NLWeb), CONTRIBUTING + issue templates.

## Status

**v0.3 complete (stages 0–19) — all agent work done.** v0.3 delivered: finished the rename to
`lap` (14); honest validation incl. a live **success-rate matrix** where compression didn't cost
accuracy (15); grouped **≥2-per-category** benchmark tasks (16); a real-spec **fuzz corpus** +
Swagger-2.0 / media-type parser fixes (17); the **20-API efficiency leaderboard** (18); and
**release artifacts** — CHANGELOG, version `0.3.0`, a marketplace GitHub Action, `RELEASING.md`
(19). **Only owner publish steps remain:** `python -m build` → `twine upload` to PyPI +
`gh release create v0.3.0` (see [`RELEASING.md`](RELEASING.md)). Remaining open work is the
key-free **backlog** below (estimate-C realism, caching economics, bucket-B estimate, NLWeb
scoring, lint auto-fix, `score before after` diff, L0 "be-discoverable" rule, CONTRIBUTING) plus a
**broader 15(b) matrix** (more models/tasks/repeats). Say "continue LAP" to pick one.

## Sources captured for Stage 1 (so it can be done without re-searching)

- llms.txt (state/adoption, 2026): https://codersera.com/blog/llms-txt-complete-guide-2026/ · https://caseyrb.com/blog/state-of-llms-txt-adoption/
- Microsoft NLWeb (agentic web; sites expose `/ask` + `/mcp`): https://news.microsoft.com/source/features/company-news/introducing-nlweb-bringing-conversational-interfaces-directly-to-the-web/
- MCP gateways (OAuth/DCR, open source): AWS https://aws.amazon.com/blogs/opensource/governing-ai-assets-at-scale-with-mcp-gateway-and-registry/ · Hypr https://github.com/hyprmcp/mcp-gateway · atrawog https://github.com/atrawog/mcp-oauth-gateway
- Agent identity standards: NIST AI Agent Standards Initiative https://workos.com/blog/nist-ai-agent-standards-initiative-explained · IETF https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/ · MCP adopted OAuth 2.1 + RFC 9728 (protected-resource metadata)
