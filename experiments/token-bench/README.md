# token-bench

Measures, on the real [`pet-zoo`](../../pet-zoo/README.md) API, how many **tokens**
different ways of exposing an HTTP API to an LLM actually cost. It answers a
concrete question: *can you beat a naive "MCP-style" tool bridge on token
efficiency, and does replacing endpoint names with numbers help?*

## The idea being tested

LLM↔API interaction has two separate channels:

- **LLM ↔ shim** — measured in **tokens**. The only channel where "efficiency for
  the LLM" exists.
- **shim ↔ site** — measured in bytes/latency. Normal backend work (gRPC, msgpack…);
  the model never sees it, so it can't save tokens. Out of scope here.

On the token channel, cost lives in three buckets:

| bucket | what | who pays |
| --- | --- | --- |
| **A** | tool/menu definitions sitting in context | ~once per session (cacheable) |
| **B** | the call the model emits | tiny |
| **C** | the result fed back into context | every turn, un-cacheable |

The "give every endpoint a number" idea targets **B** — the cheapest bucket — and
still needs the arg spec in **A**. The strong levers target **A** (compact
definitions) and **C** (return only what's needed). This benchmark puts numbers on
all of that.

## Variants compared

All four are generated from one source of truth: `pet-zoo`'s auto OpenAPI spec.

| variant | what it is |
| --- | --- |
| `openapi_full` | baseline: each operation → a tool with full $ref-inlined JSON Schema (what naive OpenAPI/MCP bridges emit) |
| `compact_sig` | human-readable names, but dense TS-like signatures + one shared `Animal` type |
| `numbered` | the user's idea: a `number → endpoint` dictionary; model calls by number |
| `code_exec` | one `run_python` tool + a compact client doc; model writes one script, only the small final value returns |

`numbered`'s dictionary is counted **in full** in bucket A — it has to spell out
every argument (the model needs them to call correctly), so the comparison is
fair: its only saving is an integer instead of a name in bucket B.

## Run it

```bash
pip install -r experiments/token-bench/requirements.txt   # also covers pet-zoo
python experiments/token-bench/run_bench.py               # offline, approx tokenizer
```

- **Faithful counts:** set `ANTHROPIC_API_KEY`. The benchmark then uses Anthropic's
  free `messages.count_tokens` endpoint (no generation, no spend); bucket A is
  measured through the real `tools=` parameter. Without a key it falls back to a
  GPT-style BPE (`tiktoken`) — absolute numbers are approximate but the **relative
  ordering** (the whole point) holds.
- **Optional Layer 2** (`--live`, needs key, spends tokens): actually runs each
  variant through Claude on the tasks and reports total tokens + whether the answer
  was correct — a check that compression doesn't trade tokens for wrong answers.
  Note: `code_exec` executes model-written Python locally against the throwaway
  TestClient; only run on this sandbox.

Output goes to stdout and `results.md`.

## How to read it

- `A` for `compact_sig`/`code_exec` ≪ `openapi_full`: most of the baseline cost is
  verbose schema, not anything the model needs.
- `numbered` total ≥ `compact_sig` total: numbering the calls doesn't pay — the
  dictionary costs more (A) than the integer saves (B).
- `code_exec` wins big on the read-heavy / multi-step tasks: bucket C collapses
  because only the answer re-enters context, not every body.

## Files

| file | role |
| --- | --- |
| `spec_source.py` | loads pet-zoo as a library; OpenAPI → normalized ops; seeded TestClient |
| `tokens.py` | token counting (Anthropic endpoint, or tiktoken approx) |
| `variants/` | the four interface generators |
| `tasks.py` | T1 create / T2 count-females / T3 count-per-species, with real bodies |
| `run_bench.py` | orchestrates A/B/C accounting, prints tables, writes `results.md` |
| `live_runs.py` | optional real-Claude Layer 2 |
