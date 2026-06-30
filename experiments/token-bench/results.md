# LLM<->HTTP token benchmark (pet-zoo)

- date: 2026-06-30
- tokenizer backend: **tiktoken-approx**  _(approximate - GPT-style BPE, not Claude's; relative ordering is the signal)_
- source of truth: pet-zoo OpenAPI (21 operations)
- fixture: 50 animals (monkey:15, lion:12, tiger:13, elephant:10)

Buckets: **A** = definitions in context, **B** = the call(s), **C** = the result(s).


## Bucket A - menu cost (paid ~once per session)

| variant | A tokens | saved vs base | form |
| --- | --- | --- | --- |
| openapi_full | 1637 | +0% | 21 tool(s) |
| mcp_fastmcp | 1689 | -3% | 21 tool(s) |
| mcp_fastmcp (+outputSchema) | 3762 | -130% | 21 tool(s) + manifest text |
| compact_sig | 401 | +76% | manifest text |
| numbered | 466 | +72% | manifest text |
| code_exec | 183 | +89% | 1 tool(s) + manifest text |
| odata_query | 219 | +87% | 1 tool(s) + manifest text |

## Per-category averages - mean total tokens over each category's tasks

Each cell is the mean A+B+C total across that category's tasks, with the saving vs the `openapi_full` baseline. Averaging >=2 tasks per category keeps any single task from carrying a conclusion.

| category | openapi_full | mcp_fastmcp | compact_sig | numbered | code_exec | odata_query |
| --- | --- | --- | --- | --- | --- | --- |
| write (n=2) | 1683 (+0%) | 1738 (-3%) | 447 (+73%) | 510 (+70%) | 231 (+86%) | 248 (+85%) |
| aggregate-read (n=2) | 2368 (+0%) | 2424 (-2%) | 1132 (+52%) | 1195 (+50%) | 220 (+91%) | 240 (+90%) |
| multi-step (n=2) | 2848 (+0%) | 2912 (-2%) | 1612 (+43%) | 1669 (+41%) | 236 (+92%) | 251 (+91%) |
| peek-read (n=2) | 1972 (+0%) | 2027 (-3%) | 736 (+63%) | 799 (+59%) | 241 (+88%) | 264 (+87%) |
| beyond-DSL (n=2) | 2809 (+0%) | 2865 (-2%) | 1573 (+44%) | 1636 (+42%) | 228 (+92%) | 610 (+78%) |

## T1_create - "Add a new monkey named Bobo, age 3, male."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 22 | 24 | 1683 | +0% |
| mcp_fastmcp | 1689 | 25 | 24 | 1738 | -3% |
| compact_sig | 401 | 22 | 24 | 447 | +73% |
| numbered | 466 | 20 | 24 | 510 | +70% |
| code_exec | 183 | 26 | 22 | 231 | +86% |
| odata_query | 219 | 24 | 5 | 248 | +85% |

## T1b_create_lion - "Register a new lion named Zuri, age 4, female."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 22 | 24 | 1683 | +0% |
| mcp_fastmcp | 1689 | 25 | 24 | 1738 | -3% |
| compact_sig | 401 | 22 | 24 | 447 | +73% |
| numbered | 466 | 20 | 24 | 510 | +70% |
| code_exec | 183 | 26 | 22 | 231 | +86% |
| odata_query | 219 | 24 | 5 | 248 | +85% |

## T2_count_females - "How many of all the animals are female?"

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 1161 | 2809 | +0% |
| mcp_fastmcp | 1689 | 15 | 1161 | 2865 | -2% |
| compact_sig | 401 | 11 | 1161 | 1573 | +44% |
| numbered | 466 | 9 | 1161 | 1636 | +42% |
| code_exec | 183 | 28 | 6 | 217 | +92% |
| odata_query | 219 | 15 | 5 | 239 | +91% |

## T2b_count_old_lions - "How many lions are older than 8?"

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 279 | 1927 | +0% |
| mcp_fastmcp | 1689 | 14 | 279 | 1982 | -3% |
| compact_sig | 401 | 11 | 279 | 691 | +64% |
| numbered | 466 | 9 | 279 | 754 | +61% |
| code_exec | 183 | 32 | 8 | 223 | +88% |
| odata_query | 219 | 18 | 5 | 242 | +87% |

## T3_count_per_species - "Count how many animals there are of each species."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 44 | 1167 | 2848 | +0% |
| mcp_fastmcp | 1689 | 56 | 1167 | 2912 | -2% |
| compact_sig | 401 | 44 | 1167 | 1612 | +43% |
| numbered | 466 | 36 | 1167 | 1669 | +41% |
| code_exec | 183 | 28 | 19 | 230 | +92% |
| odata_query | 219 | 10 | 19 | 248 | +91% |

## T3b_males_per_species - "Count how many male animals there are of each species."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 44 | 1167 | 2848 | +0% |
| mcp_fastmcp | 1689 | 56 | 1167 | 2912 | -2% |
| compact_sig | 401 | 44 | 1167 | 1612 | +43% |
| numbered | 466 | 36 | 1167 | 1669 | +41% |
| code_exec | 183 | 41 | 19 | 243 | +91% |
| odata_query | 219 | 16 | 19 | 254 | +91% |

## T4_peek_one - "Find one tiger older than 5; give me its name and age."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 315 | 1963 | +0% |
| mcp_fastmcp | 1689 | 14 | 315 | 2018 | -3% |
| compact_sig | 401 | 11 | 315 | 727 | +63% |
| numbered | 466 | 9 | 315 | 790 | +60% |
| code_exec | 183 | 43 | 12 | 238 | +88% |
| odata_query | 219 | 25 | 19 | 263 | +87% |

## T4b_peek_female_monkey - "Find one female monkey older than 4; give me its name and age."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 333 | 1981 | +0% |
| mcp_fastmcp | 1689 | 14 | 333 | 2036 | -3% |
| compact_sig | 401 | 11 | 333 | 745 | +62% |
| numbered | 466 | 9 | 333 | 808 | +59% |
| code_exec | 183 | 50 | 11 | 244 | +88% |
| odata_query | 219 | 28 | 18 | 265 | +87% |

## T5_longest_name - "Which animal has the longest name? Give its name and species."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 1161 | 2809 | +0% |
| mcp_fastmcp | 1689 | 15 | 1161 | 2865 | -2% |
| compact_sig | 401 | 11 | 1161 | 1573 | +44% |
| numbered | 466 | 9 | 1161 | 1636 | +42% |
| code_exec | 183 | 37 | 13 | 233 | +92% |
| odata_query | 219 | 11 | 561 | 791 | +72% |

## T5b_avg_age - "What is the average age of all the animals? Round to one decimal place."

| variant | A | B call | C result | total | saved vs base |
| --- | --- | --- | --- | --- | --- |
| openapi_full | 1637 | 11 | 1161 | 2809 | +0% |
| mcp_fastmcp | 1689 | 15 | 1161 | 2865 | -2% |
| compact_sig | 401 | 11 | 1161 | 1573 | +44% |
| numbered | 466 | 9 | 1161 | 1636 | +42% |
| code_exec | 183 | 31 | 8 | 222 | +92% |
| odata_query | 219 | 9 | 202 | 430 | +85% |
