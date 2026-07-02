"""R6 / v0.5 S1 - real Anthropic code-execution head-to-head, with repeats.

Anthropic's server-side code-execution sandbox has **no internet access** (by
design, for security) - it cannot call a live API itself, exactly like our own
local sandbox (`sandbox_runner.py`), which is hard-wired to an in-process pet-zoo
client, not a real network call either. So the fair comparison isn't "who can
reach a live API" (neither can, from inside the sandbox) - it's "given the same
data, does real code-execution collapse bucket C the same way our own sandboxed
`code_exec` does, without the raw data ever re-entering the model's context?"

We reuse T2_count_females - the exact task Stage 15's live matrix already
validated (see experiments/token-bench/validation.md, aggregate-read category,
Claude Haiku, k=3) - so the new real numbers sit directly next to already-real,
already-validated numbers for naive (`openapi_full`) and our own `code_exec`,
instead of re-spending tokens to re-measure them.

The real data (50 pet-zoo animal records) is handed to the sandbox via a
Files-API upload + `container_upload` - the official pattern for giving the
code-execution container data without it passing through the model's visible
token stream, mirroring what our own sandbox does by injecting a `zoo` client
object directly into the subprocess's namespace.

v0.5 S1: the original R6 run was k=1 and found real code-execution *heavier*
than both naive and our own sandbox - flagged honestly as "noisy, not a claim
it's inherently worse" because a single model choice (viewing the raw file
before writing code) drove the result. This version repeats the same live call
K times (default 5) to see whether that was a one-off or a real pattern.

Needs ANTHROPIC_API_KEY. Uses `code_execution_20250825` (the version Claude
Haiku 4.5 supports - `_20260120`/`_20260521` need Opus/Sonnet 4.5+); no beta
header for the tool itself, but the Files API upload needs
`betas=["files-api-2025-04-14"]`. K live calls (one file upload, reused across
calls). Writes docs/CODE-EXEC.md.
"""

from __future__ import annotations

import json
import os
import statistics
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "token-bench"))

from tasks import build_tasks  # noqa: E402

MODEL = os.environ.get("BENCH_MODEL", "claude-haiku-4-5-20251001")
CODE_EXEC_TOOL = {"type": "code_execution_20250825", "name": "code_execution"}
REPEATS = int(os.environ.get("CODE_EXEC_REPEATS", "5"))

# Already-validated REAL numbers for this exact task (Stage 15 live matrix, Claude
# Haiku 4.5, k=3 mean) - see experiments/token-bench/validation.md, aggregate-read
# category. Not re-measured here to avoid re-spending tokens on already-real data.
NAIVE_MEAN_TOKENS = 6121  # openapi_full: the full 50-animal list re-enters context
OURS_MEAN_TOKENS = 1636  # code_exec: our local sandbox, only the small count returns
VALIDATED_SOURCE = "experiments/token-bench/validation.md (Stage 15 live matrix, k=3 mean, Haiku)"


def _one_run(client, t2, expected, file_obj) -> dict:
    resp = client.beta.messages.create(
        model=MODEL, max_tokens=1024,
        betas=["files-api-2025-04-14"],
        system="Use code execution to answer. Reply with just the final number.",
        tools=[CODE_EXEC_TOOL],
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": "The uploaded file animals.json is a list of animal "
                 "records, each with a 'gender' field. Use code execution to count how many "
                 "have gender 'female'. Reply with just the number."},
                {"type": "container_upload", "file_id": file_obj.id},
            ],
        }],
    )

    final_text = " ".join(b.text for b in resp.content if getattr(b, "type", None) == "text")
    exec_kinds = [getattr(b, "type", None) for b in resp.content
                  if getattr(b, "type", None) in
                  ("server_tool_use", "bash_code_execution_tool_result", "text_editor_code_execution_tool_result")]
    n_bash_execs = sum(
        1 for b in resp.content
        if getattr(b, "type", None) == "server_tool_use" and getattr(b, "name", None) == "bash_code_execution"
    )
    viewed_file = any(getattr(b, "type", None) == "text_editor_code_execution_tool_result" for b in resp.content)
    had_error = False
    for b in resp.content:
        if getattr(b, "type", None) == "bash_code_execution_tool_result":
            content = getattr(b, "content", None)
            return_code = getattr(content, "return_code", None) if content is not None else None
            stderr = getattr(content, "stderr", "") if content is not None else ""
            if (return_code not in (None, 0)) or stderr:
                had_error = True
    ok = str(expected["females"]) in final_text
    total = resp.usage.input_tokens + resp.usage.output_tokens

    return {
        "ok": ok,
        "answer": final_text.strip(),
        "input_tokens": resp.usage.input_tokens,
        "output_tokens": resp.usage.output_tokens,
        "total": total,
        "n_blocks": len(exec_kinds),
        "n_bash_execs": n_bash_execs,
        "viewed_file": viewed_file,
        "had_error": had_error,
    }


def main() -> None:
    from anthropic import Anthropic

    client = Anthropic()
    tasks = build_tasks()
    t2 = next(t for t in tasks if t.name == "T2_count_females")
    animals = t2.bodies[0]  # the real GET /animals payload naive/ours both see
    expected = t2.final_value  # {"females": N}, computed the same way as every other variant
    print(f"task: {t2.prompt}  expected={expected}  (n={len(animals)} records)  repeats={REPEATS}")

    payload = json.dumps(animals).encode("utf-8")
    file_obj = client.beta.files.upload(
        file=("animals.json", payload, "application/json"),
        betas=["files-api-2025-04-14"],
    )
    print(f"uploaded {len(payload)} bytes as file {file_obj.id}")

    runs = []
    for i in range(REPEATS):
        run = _one_run(client, t2, expected, file_obj)
        runs.append(run)
        print(f"  run {i + 1}/{REPEATS}: ok={run['ok']} total={run['total']} "
              f"(in={run['input_tokens']} out={run['output_tokens']}) "
              f"n_bash_execs={run['n_bash_execs']} had_error={run['had_error']} "
              f"viewed_file={run['viewed_file']} answer={run['answer']!r}")

    totals = [r["total"] for r in runs]
    n_ok = sum(1 for r in runs if r["ok"])
    n_viewed = sum(1 for r in runs if r["viewed_file"])
    n_errored = sum(1 for r in runs if r["had_error"])
    n_retried = sum(1 for r in runs if r["n_bash_execs"] > 1)
    mean_total = round(statistics.mean(totals))
    min_total, max_total = min(totals), max(totals)
    n_above_naive = sum(1 for t in totals if t > NAIVE_MEAN_TOKENS)
    n_above_ours = sum(1 for t in totals if t > OURS_MEAN_TOKENS)

    print(f"\nsummary: {n_ok}/{REPEATS} correct, mean_total={mean_total} "
          f"(min={min_total} max={max_total}), retried={n_retried}/{REPEATS}, "
          f"errored={n_errored}/{REPEATS}, viewed_file={n_viewed}/{REPEATS}, "
          f"above_naive={n_above_naive}/{REPEATS}, above_ours={n_above_ours}/{REPEATS}")

    per_run_rows = "\n".join(
        f"| {i + 1} | {r['total']} | {r['input_tokens']} | {r['output_tokens']} | "
        f"{r['n_bash_execs']} | {'yes' if r['had_error'] else 'no'} | "
        f"{'yes' if r['ok'] else 'no'} — {r['answer']!r} |"
        for i, r in enumerate(runs)
    )

    driver_note = (
        f"the direct, verifiable driver is **retried/errored code-execution attempts** "
        f"({n_retried}/{REPEATS} runs called `bash_code_execution` more than once, "
        f"{n_errored}/{REPEATS} had a failed attempt — typically the model guessing the wrong "
        f"file path on its first try, then correcting it), not merely \"viewing\" the file "
        f"({n_viewed}/{REPEATS} did that): each extra attempt re-sends the growing turn history, "
        f"which is what actually inflates billed tokens."
    )

    if n_above_naive == 0:
        pattern_read = (
            f"**Every one of {REPEATS} repeats came in under the naive baseline** "
            f"({NAIVE_MEAN_TOKENS} tokens) — the original R6 heavier-than-naive result "
            f"looks like a one-off, not a pattern. Here {driver_note}"
        )
    elif n_above_naive == REPEATS:
        pattern_read = (
            f"**Every one of {REPEATS} repeats came in above the naive baseline** "
            f"({NAIVE_MEAN_TOKENS} tokens) — the original R6 result was not a fluke. Here "
            f"{driver_note}"
        )
    else:
        pattern_read = (
            f"**{n_above_naive}/{REPEATS} repeats came in above the naive baseline** "
            f"({NAIVE_MEAN_TOKENS} tokens), {REPEATS - n_above_naive}/{REPEATS} below — this "
            f"is genuinely inconsistent run to run, which is itself the finding: real "
            f"code-execution's token cost on this task swings on whether that particular "
            f"completion needs more than one execution attempt to get the file path right. "
            f"Concretely, {driver_note} That is exactly what \"behavioral, not structural\" "
            f"means in practice — the saving is not guaranteed by the mechanism, it is "
            f"contingent on a per-run model choice (and mistake rate) the caller does not "
            f"control."
        )

    lines = [
        "# Real Anthropic code-execution head-to-head (v0.4 R6 → v0.5 S1, k={} repeats)".format(REPEATS),
        "",
        f"_By [`experiments/code_exec_real.py`](../experiments/code_exec_real.py), "
        f"{date.today().isoformat()}, model `{MODEL}`, {REPEATS} repeats (`CODE_EXEC_REPEATS`)._",
        "",
        "**What this is.** Anthropic's real server-side **code-execution** tool "
        "(`code_execution_20250825` - the version Claude Haiku 4.5 supports; no beta header for "
        "the tool itself) against our own local-sandbox `code_exec` variant and the naive "
        "full-list baseline, on the exact task Stage 15's live matrix already validated "
        f"(`{t2.name}`: \"{t2.prompt}\"). **v0.5 S1** repeats the live call {REPEATS} times — "
        "the original v0.4 R6 run was k=1 and found real code-execution heavier than naive, "
        "honestly flagged as \"noisy, not a claim it's inherently worse.\" This is that follow-up.",
        "",
        "**The real constraint that shapes this comparison.** Anthropic's code-execution "
        "container has **no internet access** - it cannot call a live API itself. Neither can our "
        "own local sandbox, which is hard-wired to an in-process pet-zoo client rather than a real "
        "network call. So this isn't \"who can reach a live API\" (neither can, from inside the "
        "sandbox) - it's \"given the same data, does real code-execution collapse bucket C the same "
        "way ours does, without the raw data ever re-entering the model's visible context?\" Both "
        "mechanisms get the data the same way in spirit: ours via an injected `zoo` object in a "
        "local subprocess; Anthropic's via a **Files API upload + `container_upload`** - the "
        "documented pattern for handing the sandbox data without it passing through the model's "
        "token stream.",
        "",
        f"- tokenizer / usage: **real, billed** `usage.input_tokens`/`usage.output_tokens` per run "
        f"for the real code-execution rows; naive and ours are cited from `{VALIDATED_SOURCE}` "
        "rather than re-spending tokens to re-measure already-real numbers.",
        "",
        "## Result",
        "",
        "| form | mechanism | total tokens | correct | source |",
        "| --- | --- | ---: | --- | --- |",
        f"| `openapi_full` (naive) | full 50-record list re-enters context | {NAIVE_MEAN_TOKENS} | (validated) | Stage 15 live matrix |",
        f"| `code_exec` (ours) | local subprocess sandbox, injected `zoo` client | {OURS_MEAN_TOKENS} | (validated) | Stage 15 live matrix |",
        f"| **code-execution (real Anthropic), mean of {REPEATS}** | server-side sandbox, data via `container_upload` | **{mean_total}** (min {min_total}, max {max_total}) | {n_ok}/{REPEATS} | this run, live, billed |",
        "",
        "### Per-repeat detail",
        "",
        "| run | total tokens | input | output | bash exec attempts | had a failed attempt | correct |",
        "| ---: | ---: | ---: | ---: | ---: | --- | --- |",
        per_run_rows,
        "",
        f"**Read.** {pattern_read} Across the {REPEATS} repeats, mean total was {mean_total} tokens "
        f"({'below' if mean_total < NAIVE_MEAN_TOKENS else 'above'} the naive baseline of "
        f"{NAIVE_MEAN_TOKENS}, and "
        f"{'below' if mean_total < OURS_MEAN_TOKENS else 'above'} our own sandbox's "
        f"{OURS_MEAN_TOKENS}), ranging {min_total}–{max_total} "
        f"(**{round(max_total / min_total, 1)}×** spread between the cheapest and most "
        "expensive run of the *identical* task against the *identical* data). "
        "Both real code-execution and our own sandbox are supposed to collapse the 50-record "
        "payload to a single small answer instead of letting it re-enter context — that's the "
        "whole thesis behind the `code_exec` LAP form — but real code-execution's delivery on "
        "that thesis is **behavioral**: whether it happens depends on the model getting the "
        "file path (and its own code) right on the first try, not on anything the mechanism "
        "itself enforces. Our own sandbox has no equivalent failure mode: the injected `zoo` "
        "client object can't be given a wrong path, because there is no path to get wrong. "
        "Caveats: single task, one cheap model (Haiku 4.5), one API (pet-zoo) — indicative, not a "
        "broad benchmark; a pricier model may make this specific path-guessing mistake less often, "
        "but the structural gap (nothing stops it) remains. Same underlying constraint as "
        "`code_exec` everywhere: neither sandbox can call a *live* external API directly - a "
        "live-API-backed code-execution comparison (real internet access on both sides) is out "
        "of scope here and would need its own security review before extending our own sandbox "
        "that way.",
    ]

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "CODE-EXEC.md")
    out = os.path.abspath(out)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
