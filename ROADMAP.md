# LAP Roadmap — token-efficiency layer for the agentic web

**What this is:** the staged plan for **LAP**, an open, neutral toolkit that measures
the token cost of agent-facing APIs (A/B/C buckets) and scores them against the LAP
profile. Positioned as the **efficiency-measurement + guidance layer** the ecosystem
lacks — complementary to MCP/NLWeb, **not** a rebuild of gateways/auth/discovery
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
- [ ] **▶ Stage 11 — `tool_search` menu form.** Add the lazy-loading (search+execute) form to
  `lap score` to show the at-scale bucket-A collapse on large APIs. _Done: the form appears with
  its reduction on a large spec._  `[no key]`
- [ ] **Stage 12 — Score live MCP/NLWeb endpoints.** `lap score --mcp-url <url>` connects to a
  running MCP server (MCP client) and scores its advertised tools. _Done: scores ≥1 live MCP
  server._  `[no key]`
- [ ] **Stage 13 (LAST) — Live success + faithful validation.** With `ANTHROPIC_API_KEY`: run
  `run_bench.py --live --quick` for pass/fail + faithful `count_tokens`; sanity-check tiktoken
  vs faithful; update the profile status from "unvalidated" to measured. _Done: real pass/fail
  + faithful numbers recorded._  **[NEEDS API KEY — intentionally last]**

### Further backlog (unscheduled)
Auto-fix patches from lint (emit a compact manifest), `lap score before after` diff mode, a
profile "L0 be-discoverable" rule (llms.txt / .well-known / NLWeb), CONTRIBUTING + issue templates.

## Status

**v0.1 complete (stages 0–6).** On **v0.2** — **▶ Stage 11** (`tool_search` menu form).
Stages 7–10 done (tests/CI/LICENSE; real-spec robustness; estimated bucket C; `--json` + CI
gate). The live-key validation is intentionally **last** (Stage 13). Say "continue LAP" to run
the next stage. (v0.1 owner-only follow-up: publish to PyPI + a GitHub release.)

## Sources captured for Stage 1 (so it can be done without re-searching)

- llms.txt (state/adoption, 2026): https://codersera.com/blog/llms-txt-complete-guide-2026/ · https://caseyrb.com/blog/state-of-llms-txt-adoption/
- Microsoft NLWeb (agentic web; sites expose `/ask` + `/mcp`): https://news.microsoft.com/source/features/company-news/introducing-nlweb-bringing-conversational-interfaces-directly-to-the-web/
- MCP gateways (OAuth/DCR, open source): AWS https://aws.amazon.com/blogs/opensource/governing-ai-assets-at-scale-with-mcp-gateway-and-registry/ · Hypr https://github.com/hyprmcp/mcp-gateway · atrawog https://github.com/atrawog/mcp-oauth-gateway
- Agent identity standards: NIST AI Agent Standards Initiative https://workos.com/blog/nist-ai-agent-standards-initiative-explained · IETF https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/ · MCP adopted OAuth 2.1 + RFC 9728 (protected-resource metadata)
