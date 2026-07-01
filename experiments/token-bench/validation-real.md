# LAP real-API validation - live Swagger Petstore (end-to-end)

- date: 2026-07-01   model: `claude-haiku-4-5-20251001`   repeats: 3
- API: **https://petstore3.swagger.io/api/v3** (real, hosted); tools executed as **real HTTP requests**
- ground truth computed live: available_count=7, pet id=4 status=available

Same accuracy check as token-bench, but on a **real third-party API** with a **real generator (FastMCP)** in the mix - not the pet-zoo toy.

## Success rate (correct / repeats)

| menu form | menu A (tok) | count_available | get_pet_status |
| --- | ---: | --- | --- |
| openapi_full | 2740 | 0/3 | 3/3 |
| compact_sig | 677 | 3/3 | 3/3 |
| fastmcp (real) | 3350 | 3/3 | 3/3 |

## Mean total tokens

| menu form | count_available | get_pet_status |
| --- | --- | --- |
| openapi_full | 7708 | 5057 |
| compact_sig | 3683 | 3166 |
| fastmcp (real) | 6595 | 6069 |

**Read.** End-to-end on a real hosted API, the naive `openapi_full` menu was both the heaviest and the least reliable (it missed the count task 0/3), while `compact_sig` matched the real FastMCP generator's accuracy (3/3) at far fewer tokens (~half on the count task) - the same lesson as the pet-zoo toy, now on a real API with a real generator and real HTTP execution. Caveats: one cheap model, k=3 (noisy at low n), 2 tasks, one API - indicative, not a broad benchmark.

_(Bucket-A menu tokens above are faithful `count_tokens` — the run had `ANTHROPIC_API_KEY` set — so ~1.5× the tiktoken figures in [`GENERATORS.md`](../../docs/GENERATORS.md); the ordering is identical.)_
