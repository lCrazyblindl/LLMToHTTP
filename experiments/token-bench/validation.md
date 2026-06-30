# LAP honest validation - live success rates

- date: 2026-06-30
- fixture: 50 animals

## Honest validation - success rate over 3 repeats (model `claude-haiku-4-5-20251001`)

Each cell: correct runs / repeats, for one representative task per category. This is the accuracy check behind the token savings (incl. `numbered`).

| category | task | openapi_full | compact_sig | numbered | code_exec | odata_query |
| --- | --- | --- | --- | --- | --- | --- |
| write | T1_create | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| aggregate-read | T2_count_females | 1/3 | 2/3 | 3/3 | 3/3 | 3/3 |
| multi-step | T3_count_per_species | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| peek-read | T4_peek_one | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |
| beyond-DSL | T5_longest_name | 3/3 | 3/3 | 3/3 | 3/3 | 3/3 |

**Overall correct:** openapi_full 13/15, compact_sig 14/15, numbered 15/15, code_exec 15/15, odata_query 15/15

### Mean total tokens (same runs)

| category | openapi_full | compact_sig | numbered | code_exec | odata_query |
| --- | --- | --- | --- | --- | --- |
| write | 4952 | 3258 | 3337 | 2400 | 1774 |
| aggregate-read | 6121 | 4442 | 4477 | 1636 | 1664 |
| multi-step | 6203 | 4512 | 4534 | 3010 | 1700 |
| peek-read | 5110 | 3421 | 3514 | 1749 | 1747 |
| beyond-DSL | 6192 | 4491 | 4499 | 2481 | 2443 |
