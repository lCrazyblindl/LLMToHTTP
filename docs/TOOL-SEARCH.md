# Real Tool Search head-to-head (v0.4 · R5)

_By [`experiments/tool_search_real.py`](../experiments/tool_search_real.py), 2026-07-01, model `claude-haiku-4-5-20251001`._

**What this is.** Anthropic's real **Tool Search** (`tool_search_tool_regex_20251119` — GA, no beta header) against our own `tool_search` approximation and the naive full-schema baseline, on a **real, large spec** — live APIs.guru **digitalocean.com** (290 real operations) — not a synthetic corpus. The documented mechanism: mark tools `defer_loading: true` and they're excluded from context/billing until Claude discovers them via search; only a non-deferred search tool need be visible up front.

- tokenizer: **anthropic** _(faithful — a real key was set)_

## A real finding along the way: `count_tokens` can't measure this

The free `messages.count_tokens` endpoint — used for every other menu number in this repo — **rejects** a request containing a server tool: `Error code: 400 - {'type': 'error', 'error': {'type': 'invalid_request_error', 'message': 'Server tools are not supported in the count_tokens endpoint: tool_search_tool_regex_20251119. Use the /v1/messages endpoint instead.'}, 'request_id': 'req_011CcbcX2zJzrsa8LYCFvGpf'}` (confirmed live, not assumed from docs). So real Tool Search's bucket A can only be measured with a **live, billed** call — unlike every other row here, which is free. Ours (naive/compact/our own `tool_search` approximation) stay free via `count_tokens`.

## Bucket A — ours (free) vs real Tool Search (live, billed)

| menu source | kind | measured via | tokens |
| --- | --- | --- | ---: |
| `openapi_full` (naive, ours) | ours | free `count_tokens` | 33140 |
| `compact_sig` (ours) | ours | free `count_tokens` | 6586 |
| `tool_search` (ours: fixed 2-tool + name index) | ours | free `count_tokens` | 3457 |
| **real Tool Search** (`defer_loading: true` on all 290 tools) | **REAL** | live call, billed `usage.input_tokens` | **4789** |
| real Tool Search control (same 290 schemas, **no** `defer_loading`) | REAL | live call, billed `usage.input_tokens` | 50617 |

**Isolating the mechanism:** the control row sends the *identical* 290 real tool schemas as the deferred row, same question, same model — the only difference is the `defer_loading` flag. Both are one-shot live calls (no tool execution against the spec's API), so these are directly comparable billed totals, not estimates.

| form | answer | input_tokens (billed) | output_tokens |
| --- | --- | ---: | ---: |
| real Tool Search (`defer_loading`) | 'droplets_list' | 4789 | 85 |
| control (no `defer_loading`, same schemas) | 'droplets_list' | 50617 | 68 |

**Read.** Real Tool Search's billed input on this single turn is lower than the control (4789 vs 50617) despite identical tool schemas and the same question — `defer_loading` is doing real, measurable work on the real API, on a real 290-operation spec, not just as documented. Our own `tool_search` approximation (3457 tokens, free) is a *fixed* 2-tool-plus-name-index menu — flat regardless of corpus size, but it never reveals a tool's argument schema before calling it (the model must call blind). Real Tool Search auto-expands the *full* schema for every discovered tool - a real capability our static approximation doesn't have. Caveat: one large spec, one question, k=1 on the live check - indicative, not a broad benchmark.
