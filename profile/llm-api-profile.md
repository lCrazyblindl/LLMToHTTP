# LLM-API Profile (LAP) — v1.0

**Status:** v1.0 — the rules and conformance levels are stable. Each rule is backed by
a measurement from [`experiments/token-bench`](../experiments/token-bench/README.md).
The numbers are **preliminary** but now include a small success-rate check. On Claude's real
tokenizer (faithful `count_tokens`) the relative ordering matches the tiktoken approximation
(~60% higher in absolute terms). On a live **success-rate matrix** (Claude Haiku, one task per
category × 3 repeats, `numbered` included), **compression did not cost accuracy**: `numbered`,
`code_exec` and `odata_query` scored 15/15, `compact_sig` 14/15, and the naive `openapi_full`
baseline came *last* at 13/15 (both misses on the aggregate-count task) — while the compact menu
used ~1.4× and the code/query forms ~3–4× fewer total tokens. **Caveats:** one cheap model, k=3
(noisy at n=3), one toy API (pet-zoo) — indicative, not a broad benchmark; raw table in
[`experiments/token-bench/validation.md`](../experiments/token-bench/validation.md). (Faithful
e.g.: a real MCP menu 2752 tokens vs 634 for compact signatures.)
**Tooling:** `python -m lap.score <openapi>` measures any API's menu cost;
`python -m lap.lint <openapi>` flags violations of the rules below.

**Purpose:** an opinionated convention for exposing an HTTP API so an LLM uses it
with the fewest tokens — *without inventing a new wire format*.

## Not a protocol — a profile

LAP is a set of conventions **on top of HTTP / JSON / OpenAPI** (plus OData and
RFC 7240 idioms). It adds no new wire format. Reason: an LLM's competence is
**distributional** — it is fluent in formats it saw a lot of in pretraining
(HTTP/JSON/REST/SQL) and poor at novel compact encodings. So we ride familiar
standards and constrain *how* they are used, rather than invent a terse dialect
(which loses on reliability and — since tokens ≠ characters — usually on tokens too).

## Principles

1. Optimize **tokens, not characters**.
2. **Ride standards the model already knows** (no cold-start).
3. Spend tokens on the **response, not the request** (the request is the cheapest part).
4. **Minimize round-trips** — each round-trip is a full inference pass.
5. **Minimal by default**, more on explicit opt-in.

## What we optimize: three token buckets

- **A** — definitions / menu in context (paid ~once per session, cacheable).
- **B** — the call the model emits (smallest; do not micro-optimize it).
- **C** — results fed back into context (largest at runtime, un-cacheable).

LAP targets **A** and **C**. (Compressing **B** — e.g. numbering endpoints — is a
measured net loss; see rule D3.)

## Conformance levels

| level | adds | targets |
|---|---|---|
| **L1 Compact** | compact familiar discovery + minimal-by-default writes + uniform errors | A, C (writes) |
| **L2 Shaped reads** | projection + filter + pagination + truncation count signal | C (reads) |
| **L3 Aggregation** | server-side count / group / basic stats | C (compute-over-many) |
| **L4 Escape hatch** | sandboxed code execution for what the query layer can't express | C (arbitrary compute) |

A provider adopts the highest level worth its task distribution.

## Rules

### Discovery — bucket A
- **D1** Describe operations as compact, familiar signatures (TS-like) or trimmed OpenAPI, not full JSON-Schema dumps. *Evidence: 401 vs 1637 tokens (compact_sig vs openapi_full); a real FastMCP server is 1689, or 3762 with output schemas.*
- **D2** When endpoints are many, expose them lazily / searchably (a search-then-fetch step) instead of dumping all definitions up front. *Evidence: industry Tool Search ≈ −85% (vendor-reported); we independently verified this live on a real 290-operation API — Anthropic's real Tool Search cut billed tokens ~90% versus the identical schemas without it, server-enforced regardless of model behavior (`docs/TOOL-SEARCH.md`). Caveat: not worth it below ~10 tools, where the search round-trip itself costs more than it saves.*
- **D3** Do **not** encode operations as opaque codes/numbers. *Evidence: `numbered` total ≥ `compact_sig` total — a net loss, because the codebook still costs bucket A while saving only ~2 tokens of bucket B.*

### Reads — bucket C
- **R1** Support field projection (`?fields=` / OData `$select`). Default to a small curated field set; full object on opt-in.
- **R2** Support server-side filtering (OData `$filter`-style).
- **R3** Support pagination; default to a **sane page size, not 1** (a default that is almost always insufficient guarantees an extra round-trip).
- **R4** When a response is truncated, include the **total count and a continuation cursor** (`@odata.count` / `nextLink`) so the model knows more exists — otherwise minimal defaults cause silent-truncation wrong answers.

### Aggregation — bucket C
- **A1** Support server-side aggregates (count, group-by-count, basic stats) so "compute over many" returns a small result instead of the whole list. *Evidence: T2/T3 result bucket ≈ 5–19 tokens vs ≈ 1161 for the full list.*

### Writes — bucket C
- **W1** Default to a **minimal response** (`Prefer: return=minimal`): status plus only server-generated fields (e.g. the new `id`); full representation on opt-in. *Evidence: T1 result 5 vs 22 tokens.*

### Errors — reliability
- **E1** Uniform, explicit outcomes: success-with-data, success-empty, and error must be unambiguously distinguishable (an empty body must not mean two different things).

### Escape hatch — bucket C, arbitrary compute
- **X1** For computations the query layer can't express, offer a **sandboxed code-execution** endpoint that returns only the final value. *Evidence: T5 (argmax over a computed property) — result 13 (code) vs 561 (query projection) vs 1161 (full list).*
  > **A real-world caveat, not just theory:** unlike R1/R3/A1 (enforced by the endpoint's own shape — the model can't opt back into a bigger response), X1's saving is **behavioral, not structural**. We tested Anthropic's own real code-execution tool live (`docs/CODE-EXEC.md`): on one run it cost *more* tokens than both the naive baseline and our own hand-rolled sandbox, because the model chose to view the raw uploaded data before writing the code that would have avoided reprinting it. Offering the escape hatch is necessary but not sufficient — nothing stops a calling agent from re-materializing the very payload the hatch exists to avoid. (Contrast with D2's Tool Search, `docs/TOOL-SEARCH.md`, which *is* server-enforced and held up at ~90% real savings regardless of model behavior.)

> The query layer (L2–L3) and the escape hatch (L4) are two points on one spectrum.
> Extending the query DSL covers more tasks but grows its menu (bucket A) toward a
> programming language; at the limit a maximally expressive DSL *is* code execution.
> Pick the point that covers your task distribution at the least A + risk.

## Conformance & scoring

Conformance is **measured, not asserted**. For a quick check on any spec,
`python -m lap.score <openapi>` reports the menu (bucket A) cost (incl. a real-MCP
baseline) and `python -m lap.lint <openapi>` flags rule violations (D3 / R1 / R2 / R3 /
W1 / E1 / A1). For a full A/B/C run with tasks, use
[`token-bench`](../experiments/token-bench/README.md); the LAP "score" is that profile
versus the naive OpenAPI→tools baseline. Use real-tokenizer mode (`ANTHROPIC_API_KEY`)
for quotable numbers, and `--live` to check that the savings don't cost accuracy.

## Non-goals (explicitly out of scope)

LAP addresses only the **token-efficiency of the interface shape**. It does **not**
solve — and these, not interface shape, are the main reasons universal LLM↔site
access lags today:

- **authentication / authorization / secrets** (per-provider, irreducible);
- **discovery / trust** (which endpoint, and is it legit);
- **hosting / secure operation** of the code escape hatch;
- **task success / correctness** (LAP optimizes tokens; success must be measured separately).

## References

MCP; MCP SEP-1576 (token bloat); Anthropic *Code execution with MCP*; Anthropic
*Tool Search*; Cloudflare *Code Mode*; OData (`$select`/`$filter`/`$top`/`$count`/`$apply`);
RFC 7240 (`Prefer: return=minimal`); GraphQL; OpenAPI.
