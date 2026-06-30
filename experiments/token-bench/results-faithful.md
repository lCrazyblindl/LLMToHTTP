# LLM<->HTTP token benchmark (pet-zoo) — faithful + live snapshot

> **Snapshot.** This is the faithful (`anthropic` `count_tokens`) + live (Claude Haiku)
> run over the **original 5-task** set (T1–T5), kept for provenance. The current task
> set has 10 tasks across 5 categories; `results.md` is regenerated from it (offline by
> default). A faithful + live re-run over the new set is the next key-needing step.

- date: 2026-06-30
- tokenizer backend: **anthropic**
- source of truth: pet-zoo OpenAPI (21 operations)
- fixture: 50 animals (monkey:15, lion:12, tiger:13, elephant:10)

Buckets: **A** = definitions in context, **B** = the call(s), **C** = the result(s).


## Bucket A - menu cost (paid ~once per session)

| variant | A tokens | saved vs base | form |
| --- | --- | --- | --- |
| openapi_full | 2665 | +0% | 21 tool(s) |
| mcp_fastmcp | 2752 | -3% | 21 tool(s) |
| mcp_fastmcp (+outputSchema) | 6418 | -141% | 21 tool(s) + manifest text |
| compact_sig | 634 | +76% | manifest text |
| numbered | 747 | +72% | manifest text |
| code_exec | 555 | +79% | 1 tool(s) + manifest text |
| odata_query | 582 | +78% | 1 tool(s) + manifest text |

## T1_create - "Add a new monkey named Bobo, age 3, male."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 2665 | 36 | 36 | 2737 | +0% |
| mcp_fastmcp | 2752 | 42 | 36 | 2830 | -3% |
| compact_sig | 634 | 36 | 36 | 706 | +74% |
| numbered | 747 | 32 | 36 | 815 | +70% |
| code_exec | 555 | 36 | 34 | 625 | +77% |
| odata_query | 582 | 40 | 6 | 628 | +77% |

## T2_count_females - "How many of all the animals are female?"

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 2665 | 15 | 1780 | 4460 | +0% |
| mcp_fastmcp | 2752 | 22 | 1780 | 4554 | -2% |
| compact_sig | 634 | 15 | 1780 | 2429 | +46% |
| numbered | 747 | 12 | 1780 | 2539 | +43% |
| code_exec | 555 | 40 | 6 | 601 | +87% |
| odata_query | 582 | 26 | 6 | 614 | +86% |

## T3_count_per_species - "Count how many animals there are of each species."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 2665 | 67 | 1786 | 4518 | +0% |
| mcp_fastmcp | 2752 | 87 | 1786 | 4625 | -2% |
| compact_sig | 634 | 67 | 1786 | 2487 | +45% |
| numbered | 747 | 51 | 1786 | 2584 | +43% |
| code_exec | 555 | 44 | 28 | 627 | +86% |
| odata_query | 582 | 17 | 28 | 627 | +86% |

## T4_peek_one - "Find one tiger older than 5; give me its name and age."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 2665 | 16 | 472 | 3153 | +0% |
| mcp_fastmcp | 2752 | 21 | 472 | 3245 | -3% |
| compact_sig | 634 | 16 | 472 | 1122 | +64% |
| numbered | 747 | 12 | 472 | 1231 | +61% |
| code_exec | 555 | 57 | 16 | 628 | +80% |
| odata_query | 582 | 39 | 27 | 648 | +79% |

## T5_longest_name - "Which animal has the longest name? Give its name and species."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 2665 | 15 | 1780 | 4460 | +0% |
| mcp_fastmcp | 2752 | 22 | 1780 | 4554 | -2% |
| compact_sig | 634 | 15 | 1780 | 2429 | +46% |
| numbered | 747 | 12 | 1780 | 2539 | +43% |
| code_exec | 555 | 55 | 20 | 630 | +86% |
| odata_query | 582 | 18 | 978 | 1578 | +65% |

## Live runs (real Claude, total tokens + success) — model `claude-haiku-4-5-20251001` — quick subset

| variant | T2_count_females | T5_longest_name |
| --- | --- | --- |
| openapi_full | 6098 OK | 6148 OK |
| compact_sig | 4439 OK | 4464 OK |
| code_exec | 1625 OK | 1735 OK |
| odata_query | 1662 OK | 2995 OK |
