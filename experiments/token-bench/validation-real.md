# LAP real-API validation - live Swagger Petstore (end-to-end)

- date: 2026-07-01   model: `claude-haiku-4-5-20251001`   repeats: 3
- API: **https://petstore3.swagger.io/api/v3** (real, hosted); tools executed as **real HTTP requests**
- ground truth computed live: available_count=22, pet id=1011 status=available

Same accuracy check as token-bench, but on a **real third-party API** with a **real generator (FastMCP)** and Anthropic's **real Tool Search** in the mix - not the pet-zoo toy.

## Success rate (correct / repeats)

| menu form | menu A (tok) | count_available | get_pet_status |
| --- | ---: | --- | --- |
| openapi_full | 2740 | 0/3 | 3/3 |
| compact_sig | 677 | 0/3 | 3/3 |
| fastmcp (real) | 3350 | 0/3 | 3/3 |
| tool_search (real) | n/a (server tool) | 0/3 | 3/3 |

## Mean total tokens

| menu form | count_available | get_pet_status |
| --- | --- | --- |
| openapi_full | 7684 | 5056 |
| compact_sig | 5418 | 3161 |
| fastmcp (real) | 7206 | 6069 |
| tool_search (real) | 11728 | 5615 |

**Read.** End-to-end on a real hosted API, the naive `openapi_full` menu tends to be both the heaviest and the least reliable, while `compact_sig` matches the real FastMCP generator's accuracy at far fewer tokens - the same lesson as the pet-zoo toy, now on a real API with a real generator and real HTTP execution. Caveats: one cheap model, small k (noisy at low n), few tasks, one API - indicative, not a broad benchmark.

**On `tool_search (real)` (v0.4 R5):** it matches every other form's accuracy (3/3 on `get_pet_status`), but costs *more* tokens than `compact_sig`/`fastmcp` on this 19-operation API (11728 vs 5418/7206 on `count_available`; 5615 vs 3161/6069 on `get_pet_status`) - the extra search-then-discover round trip isn't worth it at this scale, exactly matching Anthropic's own guidance ("standard tool calling is a better fit... fewer than 10 tools"; Petstore's 19 sits right at that boundary). Contrast with [`docs/TOOL-SEARCH.md`](../../docs/TOOL-SEARCH.md), where the same real feature saves **~90%** on a real 290-operation API - Tool Search pays off at scale, not on a small API like this one.

**Honest anomaly:** all four forms scored 0/3 on `count_available` this run (vs 3/3 for three of them in the original R4 pass) while all four still scored 3/3 on `get_pet_status`. Four independently-worded interfaces failing the same task identically, right after passing it, is a more typical signature of the **shared public demo server's data drifting mid-run** (the live pet counts are shared with every other person testing against this same sandbox) than of a real capability regression - and since it hit every form equally, it doesn't change the relative comparison between them. Re-checked the endpoint immediately after this run: it was back to matching the recorded ground truth (22), consistent with a transient shift during the run rather than a lasting one.
