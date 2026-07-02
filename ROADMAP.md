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
- [x] **Stage 19 — Ship it. FULLY RELEASED, 2026-07-01.** Artifacts: `CHANGELOG.md` (0.3.0,
  folded in the v0.4 real-tool findings before cutting the release), version bump `pyproject`
  `0.1.0 → 0.3.0` + classifiers + Changelog/Leaderboard urls, a composite marketplace **GitHub
  Action** (`action.yml`), and [`RELEASING.md`](RELEASING.md). **PyPI:** `python -m build` →
  `twine check` (both PASSED) → `twine upload` — **`lap-score` 0.3.0 is live**:
  https://pypi.org/project/lap-score/0.3.0/, verified for real in a fresh throwaway venv (`pip
  install lap-score` + `lap score <spec>` worked exactly as documented). **GitHub:** tag `v0.3.0`
  pushed; `gh release create v0.3.0` published (both dist files attached) at
  https://github.com/lCrazyblindl/lap/releases/tag/v0.3.0 — unblocked mid-session when the owner
  ran `gh auth login` themselves (the agent's shell had a stale PATH cached from before `gh` was
  installed; refreshing `$env:Path` from the registry inside the command found it). Also fixed the
  repo's GitHub description to the canonical one now that `gh repo edit` was available. **Only
  remaining, optional, UI-only step:** "Publish this Action to the Marketplace" from the release
  page (owner action — no `gh` command for this one).  `[owner action, optional]`

## Stages — v0.4 (measure real tools, not our own)

New direction (owner's push): a benchmark should measure **real, third-party artifacts**, not
only our own interface generators. Reproducible scope = **OSS tools + real Anthropic API
features** (we have a key); commercial hosted products (Speakeasy Gram, Stainless, StackOne,
Cloudflare Code Mode) are **cited, not run**. Our own variants stay as a controlled demo of the
*principle*; this track shows it holds against real tools. Same stop/resume model. Inventory of
candidates: [`docs/REAL-TOOLS.md`](docs/REAL-TOOLS.md).

- [x] **R1 — Inventory the reproducible real tools.** Done: [`docs/REAL-TOOLS.md`](docs/REAL-TOOLS.md)
  maps OSS OpenAPI→MCP generators (FastMCP + `openapi-to-mcp` / `openapi-mcp` / cnoe
  `openapi-mcp-codegen`), a real OSS optimizer (**Atlassian `mcp-compressor`**), locally-runnable
  real MCP servers (`uvx` reference servers; Docker `github`/`filesystem`), and the real Anthropic
  features (Tool Search, code execution) — with an explicit account-gated exclusion list.  `[no key]`
- [x] **R2 — Real generator shoot-out (bucket A).** Done: [`docs/GENERATORS.md`](docs/GENERATORS.md)
  + [`experiments/generators.py`](experiments/generators.py) score **three real** OpenAPI→MCP
  generators on the live Swagger Petstore (19 ops): openapi-to-mcp **2130**, FastMCP **2226**,
  openapi-mcp **4274** (→ **11756** with response schemas) — **every one heavier than the naive
  baseline (1740), and 5–28× heavier than a compact menu (415)**. No real generator ships the
  compact form → the savings are unclaimed by the ecosystem (mirrors "real MCP is heavier", now
  across 3 real tools). Honest caveat: the generators have conflicting pinned deps, so they were
  measured across two venvs (they broke pet-zoo once; env restored, 25 tests green); `generators.py`
  skips absent generators with a note.  `[no key]`
- [x] **R3 — Score the live MCP ecosystem.** Done: [`experiments/mcp_servers.py`](experiments/mcp_servers.py)
  connects over **stdio** to three real published reference servers and scores their advertised menus
  → [`docs/MCP-SERVERS.md`](docs/MCP-SERVERS.md): mcp-server-git 12 tools **1418**→153 (−89%),
  mcp-server-fetch **290**→28 (−90%), mcp-server-time **283**→31 (−89%). Even reference servers pay a
  fixed menu tax a compact rendering cuts ~89%; cites the official GitHub MCP (~94 tools/~17.6k) as
  the heavy real example (Docker daemon was down, so Docker-only servers weren't run). Servers ran
  from an isolated venv (`MCP_SERVER_PY`).  `[no key / Docker]`
- [x] **R4 — End-to-end on a real live API.** Done: [`experiments/real_api_matrix.py`]
  (experiments/real_api_matrix.py) runs the live matrix on the **hosted Swagger Petstore** — real
  HTTP execution, Claude Haiku, k=3 — comparing our naive/compact menus and the **real FastMCP**
  menu → [`validation-real.md`](experiments/token-bench/validation-real.md). **Compression didn't
  cost accuracy — it helped:** naive `openapi_full` *failed* the count task **0/3** (heaviest +
  least reliable), while `compact_sig` and **real FastMCP** were **3/3**, and compact used ~half the
  tokens of naive. Closes the pet-zoo toy gap. Caveats: 1 cheap model, k=3 (noisy), 2 tasks, 1 API.  `[key]`
- [x] **R5 — Real Tool Search head-to-head.** Done, no beta header needed (GA feature) —
  [`experiments/tool_search_real.py`](experiments/tool_search_real.py) →
  [`docs/TOOL-SEARCH.md`](docs/TOOL-SEARCH.md), plus a 4th form added to the Petstore live matrix
  ([`experiments/real_api_matrix.py`](experiments/real_api_matrix.py) →
  [`validation-real.md`](experiments/token-bench/validation-real.md)). **At real scale (live
  DigitalOcean, 290 real ops): real Tool Search billed 4789 input tokens vs 50617 for the identical
  schemas without `defer_loading` — a real, live, ~90% cut**, isolating just the mechanism (same
  question, same model, same tool schemas). **At small scale (live Petstore, 19 ops): real Tool
  Search cost *more* than `compact_sig`/real FastMCP** (11728 vs 5418/7206 on one task) — matches
  Anthropic's own "10+ tools" guidance, now empirically confirmed both ways on real APIs. Real find:
  the free `count_tokens` endpoint **rejects any request containing a server tool** (400) — real
  Tool Search's bucket A can only be measured via a live, billed call, unlike every other row in
  this repo. Also real: Kubernetes (821 ops) was tried first and rejected — its naive $ref-inlined
  schema is ~4.2M faithful tokens, and since *every* tool's full definition (deferred or not) must
  still be sent in the request, even `defer_loading` can't get an oversized corpus under a model's
  context window (Haiku 4.5: 200K) — a real, useful limit, not just a documented one.  `[key]`
- [x] **R6 — Real code-execution head-to-head.** Done, no beta header for the tool itself (only
  Files API needs `betas=["files-api-2025-04-14"]`) —
  [`experiments/code_exec_real.py`](experiments/code_exec_real.py) →
  [`docs/CODE-EXEC.md`](docs/CODE-EXEC.md). Used `code_execution_20250825` (the version Haiku 4.5
  supports) on the exact task Stage 15 already validated, so the new real number sits beside
  already-real naive (6121 tok) and our own `code_exec` (1636 tok) numbers. **A genuinely humbling,
  honest result:** real code-execution totaled **15613 tokens** — *heavier* than both. The
  content-block trace shows why: the model **viewed the uploaded file first** (re-entering the raw
  data into context, same as a naive fetch), then needed a retry to get the right path. This is a
  real, structural finding: **Tool Search's saving is enforced by the server** (`defer_loading`
  worked regardless of model behavior, R5) while **code-execution's saving is only behavioral** —
  it holds only if the model's own code never prints the raw data; our sandbox enforces that
  structurally (only `result` can leave the subprocess), real code-execution doesn't. Caveat: k=1,
  one model, one task — noisy, not a claim that real code-execution is inherently worse.  `[key]`
  Neither sandbox can call a *live* external API (no internet in Anthropic's container; ours is
  hard-wired to an in-process client) — a live-API-backed comparison is out of scope, would need
  its own security review to extend our sandbox's network access.
- [x] **R7 — Envelope-aware bucket C.** Done: `lap/estimate.py` detects a list wrapped in an
  envelope object (`_find_envelope_key` — Stripe/JSON:API `{"data":[...]}`, k8s `{"items":[...]}`,
  OData `{"value":[...]}`, preferring conventional names deterministically) and scales it to a
  full page **with its sibling fields kept**, instead of scoring it as a tiny "object". Regenerated
  [`docs/LEADERBOARD.md`](docs/LEADERBOARD.md): **15 of 20** real APIs' heaviest-result estimate
  changed, several substantially (Kubernetes 1303→**7613**, Stripe 1588→**15868**, DigitalOcean
  616→**12244**, Notion 412→**6118**) — the previous numbers were undercounting real, enveloped
  responses. +4 tests (29 passing).  `[no key]`
- [x] **R8 — Reframe the story honestly.** Done. `profile/llm-api-profile.md`: rule **D2** (Tool
  Search) now cites our own real ~90% verification alongside the vendor number, and explicitly
  notes it's *server-enforced*; rule **X1** (code-execution escape hatch) now carries an explicit
  caveat that its saving is **behavioral, not structural** — cites the real R6 counter-example
  (cost more than naive on one run) and contrasts it with D2's server-enforced guarantee.
  `docs/LANDSCAPE.md` §5 (Efficiency patterns): added that we tested two of Anthropic's own
  features live rather than only citing headline numbers — Tool Search held up, code-execution
  didn't on one run — with the general lesson (structural vs behavioral savings). README's v0.4
  bullet already stated the R6 counter-example plainly (done in the R6 commit); left as-is.
  _Done: docs updated, "ours vs real" kept explicit, the R6 counter-example is not buried._  `[no key]`

Recommended order: **R1 → R2 → R4 → R3 → R7 → R5 → R6 → R8**. **All of v0.4's numbered stages
(R1–R8) are now done.**

## Stages — v0.5 (deepen the real-tool track; finish the toolkit backlog)

Post-release (0.3.0 is live on PyPI + GitHub). Same stop/resume model. `[key]` = needs
`ANTHROPIC_API_KEY`; `[no key]` = doable without one.

- [x] **S1 — Re-run R6 (code-execution) with repeats.** Done. Re-ran
  `experiments/code_exec_real.py` with k=5 against Claude Haiku 4.5, and instrumented each run
  for exec-attempt count + failed-attempt detection (not just "did it view the file", which
  turned out not to be the real driver). **Result: not a fluke — a confirmed pattern.** All 5/5
  repeats came in above the naive baseline (mean 17863 vs. naive 6121, ours 1636), 5/5 correct.
  The verified mechanism: every run needed 2–4 `bash_code_execution` attempts because the model
  guessed the wrong sandboxed file path on its first try and had to retry — each retry re-sends
  the growing turn history, which is what inflates billed tokens. Our own sandbox has no
  equivalent failure mode (an injected client object can't be given a wrong path). Updated
  `docs/CODE-EXEC.md`, `profile/llm-api-profile.md` (rule X1), `docs/LANDSCAPE.md` §5, and
  `README.md`'s real-tool table to state "5/5, confirmed pattern" instead of "k=1, noisy."
  `[key]`
- [x] **S2 — Test `mcp-compressor` (Atlassian), a third real compression mechanism.** Done.
  Wrapped two of R3's real reference servers with the real, published (PyPI `mcp-compressor`,
  Rust-backed) stdio proxy at all 4 compression levels: `mcp-server-time` (2 tools, small) and
  `mcp-server-git` (12 tools, mid-size). **Scale amplifies the win** — our own tokenizer measured
  real savings at both scales (+12% small, +67% big at `medium`), bigger menus compressing more.
  **Genuine cross-check discrepancy found:** the tool's own self-reported startup-banner
  percentage disagreed with us on the small server — it claimed `medium` cost *more* than
  original (103.8%) where our bucket-A count of that exact same output measured a real, if
  modest, saving (+12%). Flagged honestly rather than smoothed over (likely a different internal
  metric, e.g. raw bytes vs our tokenizer — not confirmed). Wrote `docs/MCP-COMPRESSOR.md`;
  updated `docs/REAL-TOOLS.md` and README's real-tool table/links.  `[no key]`
- [x] **S3 — Leaderboard expansion, 20 → 40+ real APIs.** Done. Extended
  `experiments/leaderboard.py`'s `CURATED` list to 50 candidates, each verified present in
  APIs.guru's live directory first (dropped unresolvable guesses rather than leaving silent
  skips); all 50 scored cleanly. New heaviest entry: Xero Accounting (4,039,605 naive tokens,
  even heavier than Kubernetes). Totals across 50: **10,426,548 naive tokens**; `compact_sig`
  **+80%** avg saved, `tool_search` **+82%** avg (and, now visible at this scale, genuinely
  *negative* on 1-3-op APIs like NASA APOD/ClickUp/1Password — tool_search costing more than
  naive — a live illustration of the "not worth it below ~10 tools" caveat). Fixed a cosmetic
  bug the expansion surfaced: negative `save_search`/`save_compact` percentages rendered as
  `+-51%` (double sign) in the table; added a `_signed()` helper. Updated README's leaderboard
  sample table/count/totals.  `[no key]`
- [x] **S4 — `lap score before after` diff mode.** Done. Added `score.diff(before, after)`:
  menu (bucket A) token delta per interface form (`openapi_full`/`compact_sig`/`numbered`/
  `tool_search`), plus which LAP lint findings were newly introduced or fixed — matched by
  `(rule, where)` so wording changes don't count as a different finding. Wired into the CLI as
  `lap score --diff <before> <after>` (human + `--json`), and a CI gate `--max-growth` (reuses
  `--gate-form`; exit 1 if that form's menu grew by more than N tokens). +3 tests (32 passing).
  This is real, shipped-package code (not just docs/experiments) — added an `[Unreleased]`
  section to `CHANGELOG.md` for it since 0.3.0 is already tagged. Updated `lap/README.md`.
  `[no key]`
- [x] **S5 — estimate-C realism.** Done. `example_instance()` now checks a schema for a real
  `example` (OpenAPI 3.0) or `examples[0]` (JSON Schema 2020-12 / OpenAPI 3.1) value first,
  before any synthetic placeholder or even `enum`/`allOf`/`oneOf` handling — real data an API
  author wrote down beats a guess, unconditionally. The synthetic string placeholder's length is
  now a `string_len` parameter (`estimate()`/`example_instance()`) and a CLI flag
  (`lap score --string-len N`, default 6 = unchanged, since there's no universally "correct"
  default). +5 tests (37 passing). **Real, substantial leaderboard impact**: of 48 comparable
  rows, **41 grew, 1 shrank (EC2 - its `enum[0]` was longer than its real `example`), 6 were
  unchanged** (no examples in those schemas); the leaderboard's total heaviest-result estimate
  rose **~41%** (482,795 → 681,830 tokens) — the placeholder-only estimate had been undercounting
  real payload sizes wherever specs actually documented example values. Regenerated
  `docs/LEADERBOARD.md`, updated its methodology note, `CHANGELOG.md` `[Unreleased]`, and
  `lap/README.md`.  `[no key]`
- [ ] **▶ S6 — Broader validation matrix.** Extend Stage 15(b)'s live success-rate matrix: add
  Sonnet alongside Haiku, ≥2 tasks/category (reusing R16's grouped tasks), more repeats (k≈5).
  _Done: an expanded `validation.md`._  `[key]`
- [ ] **S7 — CONTRIBUTING.md + issue templates.** Now that the repo is public and released,
  outside issues/PRs are actually possible — a short contributing guide + a bug-report /
  feature-request issue template. _Done: `CONTRIBUTING.md` + `.github/ISSUE_TEMPLATE/`._  `[no key]`
- [ ] **S8 — Profile L0 "be-discoverable" rule + NLWeb endpoint scoring.** Add a lightweight LAP
  rule for exposing `llms.txt` / `.well-known` / an NLWeb `/mcp` endpoint, and extend `lap score
  --mcp-url` (or a sibling flag) to also score a live NLWeb `/ask` endpoint — ties the real-tool
  track to another real ecosystem player. _Done: rule + one real NLWeb site scored._  `[no key]`

Recommended order: **S1 → S2 → S3 → S4 → S5 → S6 → S7 → S8** (roughly: cheapest real-tool
follow-ups first, then toolkit features, then the more involved validation/housekeeping work).

### Further backlog (unscheduled, key-free)
**Shipped after the v0.3 stages:** the LAP rules as a **Spectral ruleset**
([`spectral/`](spectral/README.md), executed + asserted in CI, verified locally on Spectral
6.11.0 = same 15 findings as `lap lint`); the leaderboard gained a **bucket-C** (heaviest
result) column. _(The two honest gaps that surfaced — real-API end-to-end validation, and
envelope-aware bucket C — became v0.4 **R4** and **R7**, both now done.)_
Still open, unscheduled: a short **Related work / credit** note in the README; caching economics
(first-call vs amortized A); a bucket-B estimate in `lap score` (currently only measured in
token-bench); lint auto-fix (emit a suggested compact manifest); GitHub's official MCP server
(~94 tools/~17.6k, cited in R3 but never scored — Docker daemon was down; revisit if it comes
up); a second real API for Tool Search/code-execution to check R5/R6 generalize beyond
DigitalOcean/pet-zoo.

## Status

**v0.3 complete (stages 0–19); v0.4 COMPLETE (R1–R8); v0.3.0 FULLY RELEASED 2026-07-01; v0.5 IN
PROGRESS.** `lap-score` 0.3.0 is live on PyPI (https://pypi.org/project/lap-score/0.3.0/,
verified via a fresh-venv install) and the GitHub release is published
(https://github.com/lCrazyblindl/lap/releases/tag/v0.3.0, both dist files attached). The only
release step left is optional and UI-only: listing the Action on the GitHub Marketplace. **v0.5
S1 done** — repeating R6's code-execution comparison 5× confirmed "heavier than naive" is a real
pattern (5/5), driven by retried execution attempts from wrong sandboxed file-path guesses, not
noise. **v0.5 S2 done** — real `mcp-compressor` (Atlassian) on 2 real MCP servers at 2 scales:
scale amplifies the win (+12% small server, +67% big server, our own tokenizer), and a genuine
cross-check discrepancy surfaced — the tool's own self-reported percentage disagreed with us on
the small server. **v0.5 S3 done** — leaderboard expanded 20 → 50 real APIs (10.4M naive tokens
total, +80%/+82% avg saved); also caught and fixed a cosmetic double-sign bug the expansion
surfaced. **v0.5 S4 done** — `lap score --diff <before> <after>`: real, shipped-package code
(menu-token delta per form + added/removed lint findings), a `--max-growth` CI gate, +3 tests;
first v0.5 change to actually land in `lap/`, tracked in `CHANGELOG.md`'s new `[Unreleased]`
section. **v0.5 S5 done** — bucket-C estimate now prefers real schema `example`/`examples` over
synthetic placeholders, plus a configurable `--string-len`; leaderboard's total heaviest-result
estimate rose ~41% (482,795 → 681,830 tokens) once real examples were honored. **▶ v0.5 S6**
(broader validation matrix: +Sonnet, more repeats) is the current stage; order after: S6 → S7 →
S8. Say "continue LAP" to keep going once a stage
completes. v0.4 pivoted the benchmark from our own interface variants to real third-party
artifacts —
real generators, a real live API, real servers, real Anthropic features — and found the compact/
efficient story holds **most, not all**, of the time:

- **Real generators & servers leave savings unclaimed.** Three real OpenAPI→MCP generators
  ([`docs/GENERATORS.md`](docs/GENERATORS.md)) and three real published MCP servers
  ([`docs/MCP-SERVERS.md`](docs/MCP-SERVERS.md)) all emit menus heavier than naive and far heavier
  than compact (5–28× and ~89% respectively) — nobody in the ecosystem ships the compact form.
- **Compression didn't cost accuracy on a real live API — it helped.** End-to-end on the hosted
  Swagger Petstore ([`validation-real.md`](experiments/token-bench/validation-real.md)): the naive
  menu was both the heaviest *and* the least reliable (failed a count task 0/3 while compact/real
  FastMCP hit 3/3).
- **Envelope-aware bucket C** made result-size estimates honest on real APIs — 15 of 20 leaderboard
  rows changed, several substantially (Kubernetes 1303→7613, Stripe 1588→15868).
- **Two of Anthropic's own real efficiency features, tested live, cut two different ways.** Real
  **Tool Search** ([`docs/TOOL-SEARCH.md`](docs/TOOL-SEARCH.md)) held up: ~90% real, billed saving
  at scale (290 real ops), *server-enforced* regardless of model behavior — though it cost more
  than compact at small scale (19 ops), matching Anthropic's own "10+ tools" guidance. Real
  **code-execution** ([`docs/CODE-EXEC.md`](docs/CODE-EXEC.md)) did **not** hold up on one run: it
  cost *more* than both naive and our own sandbox, because the model viewed the raw uploaded data
  before writing code to avoid reprinting it — its saving is *behavioral*, not structural, and
  nothing stops a model from re-materializing the very payload the hatch exists to avoid.
- **R8 reframed the story honestly** — the profile's D2 (Tool Search) and X1 (code-execution) rules
  and `docs/LANDSCAPE.md` §5 now say plainly which savings are server-enforced vs behavior-dependent,
  instead of only citing vendor headline numbers.

A key-free **backlog** remains below (unscheduled, pick anytime); a broader Stage 15(b) matrix
(more models/tasks/repeats) is also open, key-needed. Say "continue LAP" to pick one.

## Sources captured for Stage 1 (so it can be done without re-searching)

- llms.txt (state/adoption, 2026): https://codersera.com/blog/llms-txt-complete-guide-2026/ · https://caseyrb.com/blog/state-of-llms-txt-adoption/
- Microsoft NLWeb (agentic web; sites expose `/ask` + `/mcp`): https://news.microsoft.com/source/features/company-news/introducing-nlweb-bringing-conversational-interfaces-directly-to-the-web/
- MCP gateways (OAuth/DCR, open source): AWS https://aws.amazon.com/blogs/opensource/governing-ai-assets-at-scale-with-mcp-gateway-and-registry/ · Hypr https://github.com/hyprmcp/mcp-gateway · atrawog https://github.com/atrawog/mcp-oauth-gateway
- Agent identity standards: NIST AI Agent Standards Initiative https://workos.com/blog/nist-ai-agent-standards-initiative-explained · IETF https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/ · MCP adopted OAuth 2.1 + RFC 9728 (protected-resource metadata)
