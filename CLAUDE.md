# lap — LLM-API Profile

Open, neutral toolkit to **measure and improve the token-efficiency of agent-facing APIs**
(OpenAPI & MCP): a scorer (`lap score`), a linter (`lap lint`), the LAP profile, and a
benchmark. (GitHub repo: `lap`; local folder is still `LLMToHTTP`.)

## Layout
- `pet-zoo/` — small FastAPI CRUD service used as the testbed.
- `experiments/token-bench/` — measures the token cost of interface variants across
  three buckets: **A** definitions / **B** call / **C** result. Run:
  `./.venv/Scripts/python.exe experiments/token-bench/run_bench.py`.
- `profile/llm-api-profile.md` — the LAP profile (draft): conventions for token-efficient agent APIs.
- `ROADMAP.md` — **the active staged plan and source of truth for ongoing work.**

## Working notes
- **Ongoing work follows `ROADMAP.md`** — built for stop/resume (the user has a limited
  token budget). On "continue", read `ROADMAP.md`, do the **▶** stage, tick it, advance
  the marker, and load only that stage's files. The `lap-roadmap` memory mirrors the pointer.
- Dependencies live in a gitignored `.venv`; use `./.venv/Scripts/python.exe`.
- Positioning: LAP **complements** MCP/NLWeb; it does **not** rebuild gateways/auth/discovery
  (those are covered by Microsoft NLWeb, AWS/Hypr MCP gateways, NIST/IETF auth).
