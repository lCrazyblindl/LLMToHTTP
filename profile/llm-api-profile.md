# LLM-API Profile (LAP) — Draft 0.1

**Status:** draft / hypothesis. Every rule is backed by a measurement from
[`experiments/token-bench`](../experiments/token-bench/README.md) (currently
tiktoken-approx — rerun with a real tokenizer before quoting numbers). Note: LAP
optimizes **token cost**; its effect on **task success** is not yet measured.

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
- **D2** When endpoints are many, expose them lazily / searchably (a search-then-fetch step) instead of dumping all definitions up front. *Evidence: industry Tool Search ≈ −85%.*
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

> The query layer (L2–L3) and the escape hatch (L4) are two points on one spectrum.
> Extending the query DSL covers more tasks but grows its menu (bucket A) toward a
> programming language; at the limit a maximally expressive DSL *is* code execution.
> Pick the point that covers your task distribution at the least A + risk.

## Conformance & scoring

Conformance is **measured, not asserted**. Run
[`token-bench`](../experiments/token-bench/README.md) against the API and report
buckets A/B/C per representative task; the LAP "score" is that profile versus the
naive OpenAPI→tools baseline. Use real-tokenizer mode (`ANTHROPIC_API_KEY`) for
quotable numbers, and `--live` to check that the token savings don't cost accuracy.

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
