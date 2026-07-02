# Real Anthropic code-execution head-to-head (v0.4 R6 → v0.5 S1, k=5 repeats)

_By [`experiments/code_exec_real.py`](../experiments/code_exec_real.py), 2026-07-02, model `claude-haiku-4-5-20251001`, 5 repeats (`CODE_EXEC_REPEATS`)._

**What this is.** Anthropic's real server-side **code-execution** tool (`code_execution_20250825` - the version Claude Haiku 4.5 supports; no beta header for the tool itself) against our own local-sandbox `code_exec` variant and the naive full-list baseline, on the exact task Stage 15's live matrix already validated (`T2_count_females`: "How many of all the animals are female?"). **v0.5 S1** repeats the live call 5 times — the original v0.4 R6 run was k=1 and found real code-execution heavier than naive, honestly flagged as "noisy, not a claim it's inherently worse." This is that follow-up.

**The real constraint that shapes this comparison.** Anthropic's code-execution container has **no internet access** - it cannot call a live API itself. Neither can our own local sandbox, which is hard-wired to an in-process pet-zoo client rather than a real network call. So this isn't "who can reach a live API" (neither can, from inside the sandbox) - it's "given the same data, does real code-execution collapse bucket C the same way ours does, without the raw data ever re-entering the model's visible context?" Both mechanisms get the data the same way in spirit: ours via an injected `zoo` object in a local subprocess; Anthropic's via a **Files API upload + `container_upload`** - the documented pattern for handing the sandbox data without it passing through the model's token stream.

- tokenizer / usage: **real, billed** `usage.input_tokens`/`usage.output_tokens` per run for the real code-execution rows; naive and ours are cited from `experiments/token-bench/validation.md (Stage 15 live matrix, k=3 mean, Haiku)` rather than re-spending tokens to re-measure already-real numbers.

## Result

| form | mechanism | total tokens | correct | source |
| --- | --- | ---: | --- | --- |
| `openapi_full` (naive) | full 50-record list re-enters context | 6121 | (validated) | Stage 15 live matrix |
| `code_exec` (ours) | local subprocess sandbox, injected `zoo` client | 1636 | (validated) | Stage 15 live matrix |
| **code-execution (real Anthropic), mean of 5** | server-side sandbox, data via `container_upload` | **17863** (min 15572, max 20400) | 5/5 | this run, live, billed |

### Per-repeat detail

| run | total tokens | input | output | bash exec attempts | had a failed attempt | correct |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 1 | 18152 | 17516 | 636 | 4 | yes | yes — "I'll read the JSON file and count the female animals. Let me use bash to check the file: Let me first check what files are in INPUT_DIR: 24" |
| 2 | 19609 | 19095 | 514 | 3 | yes | yes — "I'll read the animals.json file and count how many records have gender 'female'. Let me check the file first: Now I'll count the records with gender 'female': 24" |
| 3 | 15582 | 15183 | 399 | 2 | yes | yes — "I'll read the JSON file and count the animals with gender 'female'. Now I'll count the animals with gender 'female': Let me fix that by using the correct path: 24" |
| 4 | 15572 | 15173 | 399 | 2 | yes | yes — "I'll help you count the female animals in the JSON file. Now I'll count the female animals: Let me fix that by using the actual path: 24" |
| 5 | 20400 | 19902 | 498 | 3 | yes | yes — "I'll help you count the number of animals with gender 'female' in the JSON file. Now I'll count the animals with gender 'female': Let me check the actual path: Now let me run the Python script correctly: 24" |

**Read.** **Every one of 5 repeats came in above the naive baseline** (6121 tokens) — the original R6 result was not a fluke. Here the direct, verifiable driver is **retried/errored code-execution attempts** (5/5 runs called `bash_code_execution` more than once, 5/5 had a failed attempt — typically the model guessing the wrong file path on its first try, then correcting it), not merely "viewing" the file (5/5 did that): each extra attempt re-sends the growing turn history, which is what actually inflates billed tokens. Across the 5 repeats, mean total was 17863 tokens (above the naive baseline of 6121, and above our own sandbox's 1636), ranging 15572–20400 (**1.3×** spread between the cheapest and most expensive run of the *identical* task against the *identical* data). Both real code-execution and our own sandbox are supposed to collapse the 50-record payload to a single small answer instead of letting it re-enter context — that's the whole thesis behind the `code_exec` LAP form — but real code-execution's delivery on that thesis is **behavioral**: whether it happens depends on the model getting the file path (and its own code) right on the first try, not on anything the mechanism itself enforces. Our own sandbox has no equivalent failure mode: the injected `zoo` client object can't be given a wrong path, because there is no path to get wrong. Caveats: single task, one cheap model (Haiku 4.5), one API (pet-zoo) — indicative, not a broad benchmark; a pricier model may make this specific path-guessing mistake less often, but the structural gap (nothing stops it) remains. Same underlying constraint as `code_exec` everywhere: neither sandbox can call a *live* external API directly - a live-API-backed code-execution comparison (real internet access on both sides) is out of scope here and would need its own security review before extending our own sandbox that way.
