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
- [ ] **▶ Stage 4 — Faithful tokens + success check.** Default to Anthropic
  `count_tokens` when `ANTHROPIC_API_KEY` is set; run `--live` for pass/fail.
  _Verify: a task set has faithful token + success numbers._
  **Prep done (no key in env):** the live check now defaults to a cheap model
  (`claude-haiku-4-5`) + a `--quick` subset to bound spend; both token-bench and `lap`
  use faithful `count_tokens` automatically when a key is present. **Remaining (needs a
  key):** set `ANTHROPIC_API_KEY`, then `python experiments/token-bench/run_bench.py
  --live --quick` for real pass/fail, and re-run `lap score` for faithful numbers.
- [ ] **Stage 5 — LAP profile v1.0 + linter.** Promote `profile/llm-api-profile.md`
  to v1 (measured guidance for MCP/NLWeb/OpenAPI authors); add `lap lint` checking
  L1–L4 with measured citations. _Verify: lint flags real violations._
- [ ] **Stage 6 — Package & share.** Quickstart, examples, PyPI/GitHub release, short
  writeup. _Verify: a stranger can `pip install` and score their API._

## Status

**▶ Next: Stage 4** (Faithful tokens + success check). Stages 0–3 done.

## Sources captured for Stage 1 (so it can be done without re-searching)

- llms.txt (state/adoption, 2026): https://codersera.com/blog/llms-txt-complete-guide-2026/ · https://caseyrb.com/blog/state-of-llms-txt-adoption/
- Microsoft NLWeb (agentic web; sites expose `/ask` + `/mcp`): https://news.microsoft.com/source/features/company-news/introducing-nlweb-bringing-conversational-interfaces-directly-to-the-web/
- MCP gateways (OAuth/DCR, open source): AWS https://aws.amazon.com/blogs/opensource/governing-ai-assets-at-scale-with-mcp-gateway-and-registry/ · Hypr https://github.com/hyprmcp/mcp-gateway · atrawog https://github.com/atrawog/mcp-oauth-gateway
- Agent identity standards: NIST AI Agent Standards Initiative https://workos.com/blog/nist-ai-agent-standards-initiative-explained · IETF https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/ · MCP adopted OAuth 2.1 + RFC 9728 (protected-resource metadata)
