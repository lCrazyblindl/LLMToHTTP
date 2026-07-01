"""R6 - real Anthropic code-execution head-to-head.

Anthropic's server-side code-execution sandbox has **no internet access** (by
design, for security) - it cannot call a live API itself, exactly like our own
local sandbox (`sandbox_runner.py`), which is hard-wired to an in-process pet-zoo
client, not a real network call either. So the fair comparison isn't "who can
reach a live API" (neither can, from inside the sandbox) - it's "given the same
data, does real code-execution collapse bucket C the same way our own sandboxed
`code_exec` does, without the raw data ever re-entering the model's context?"

We reuse T2_count_females - the exact task Stage 15's live matrix already
validated (see experiments/token-bench/validation.md, aggregate-read category,
Claude Haiku, k=3) - so the new real number sits directly next to already-real,
already-validated numbers for naive (`openapi_full`) and our own `code_exec`,
instead of re-spending tokens to re-measure them.

The real data (50 pet-zoo animal records) is handed to the sandbox via a
Files-API upload + `container_upload` - the official pattern for giving the
code-execution container data without it passing through the model's visible
token stream, mirroring what our own sandbox does by injecting a `zoo` client
object directly into the subprocess's namespace.

Needs ANTHROPIC_API_KEY. Uses `code_execution_20250825` (the version Claude
Haiku 4.5 supports - `_20260120`/`_20260521` need Opus/Sonnet 4.5+); no beta
header for the tool itself, but the Files API upload needs
`betas=["files-api-2025-04-14"]`. One live call. Writes docs/CODE-EXEC.md.
"""

from __future__ import annotations

import json
import os
import sys
import warnings
from datetime import date

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "token-bench"))

from tasks import build_tasks  # noqa: E402

MODEL = os.environ.get("BENCH_MODEL", "claude-haiku-4-5-20251001")
CODE_EXEC_TOOL = {"type": "code_execution_20250825", "name": "code_execution"}

# Already-validated REAL numbers for this exact task (Stage 15 live matrix, Claude
# Haiku 4.5, k=3 mean) - see experiments/token-bench/validation.md, aggregate-read
# category. Not re-measured here to avoid re-spending tokens on already-real data.
NAIVE_MEAN_TOKENS = 6121  # openapi_full: the full 50-animal list re-enters context
OURS_MEAN_TOKENS = 1636  # code_exec: our local sandbox, only the small count returns
VALIDATED_SOURCE = "experiments/token-bench/validation.md (Stage 15 live matrix, k=3 mean, Haiku)"


def main() -> None:
    from anthropic import Anthropic

    client = Anthropic()
    tasks = build_tasks()
    t2 = next(t for t in tasks if t.name == "T2_count_females")
    animals = t2.bodies[0]  # the real GET /animals payload naive/ours both see
    expected = t2.final_value  # {"females": N}, computed the same way as every other variant
    print(f"task: {t2.prompt}  expected={expected}  (n={len(animals)} records)")

    payload = json.dumps(animals).encode("utf-8")
    file_obj = client.beta.files.upload(
        file=("animals.json", payload, "application/json"),
        betas=["files-api-2025-04-14"],
    )
    print(f"uploaded {len(payload)} bytes as file {file_obj.id}")

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
    stu = getattr(resp.usage, "server_tool_use", None)
    n_requests = getattr(stu, "code_execution_requests", None) if stu else None
    ok = str(expected["females"]) in final_text

    print(f"answer={final_text.strip()!r}  ok={ok}")
    print(f"usage: input_tokens={resp.usage.input_tokens} output_tokens={resp.usage.output_tokens} "
          f"code_execution_requests={n_requests}")
    print(f"content block kinds seen: {exec_kinds}")

    real_total = resp.usage.input_tokens + resp.usage.output_tokens

    lines = [
        "# Real Anthropic code-execution head-to-head (v0.4 · R6)",
        "",
        f"_By [`experiments/code_exec_real.py`](../experiments/code_exec_real.py), "
        f"{date.today().isoformat()}, model `{MODEL}`._",
        "",
        "**What this is.** Anthropic's real server-side **code-execution** tool "
        "(`code_execution_20250825` - the version Claude Haiku 4.5 supports; no beta header for "
        "the tool itself) against our own local-sandbox `code_exec` variant and the naive "
        "full-list baseline, on the exact task Stage 15's live matrix already validated "
        f"(`{t2.name}`: \"{t2.prompt}\").",
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
        f"- tokenizer / usage: **real, billed** `usage.input_tokens`/`usage.output_tokens` for the "
        f"real code-execution row; naive and ours are cited from `{VALIDATED_SOURCE}` rather than "
        "re-spending tokens to re-measure already-real numbers.",
        "",
        "## Result",
        "",
        "| form | mechanism | total tokens | correct | source |",
        "| --- | --- | ---: | --- | --- |",
        f"| `openapi_full` (naive) | full 50-record list re-enters context | {NAIVE_MEAN_TOKENS} | (validated) | Stage 15 live matrix |",
        f"| `code_exec` (ours) | local subprocess sandbox, injected `zoo` client | {OURS_MEAN_TOKENS} | (validated) | Stage 15 live matrix |",
        f"| **code-execution (real Anthropic)** | server-side sandbox, data via `container_upload` | **{real_total}** | {'yes' if ok else 'no'} — {final_text.strip()!r} | this run, live, billed |",
        "",
        f"**Read.** Real code-execution's total ({real_total} tokens: {resp.usage.input_tokens} in "
        f"+ {resp.usage.output_tokens} out) sits "
        f"{'below' if real_total < NAIVE_MEAN_TOKENS else 'above'} the naive baseline "
        f"({NAIVE_MEAN_TOKENS}) and "
        f"{'close to' if abs(real_total - OURS_MEAN_TOKENS) < 800 else ('below' if real_total < OURS_MEAN_TOKENS else 'above')} "
        f"our own local sandbox's number ({OURS_MEAN_TOKENS}) — both mechanisms collapse the "
        "50-record payload to a single small answer instead of letting it re-enter context, which "
        "is the whole thesis behind the `code_exec` LAP form. The gap between them (if any) is "
        "mostly Anthropic's own container-execution overhead (file upload metadata, the server "
        f"tool's own turn structure — {len(exec_kinds)} exec-related content block(s) this run) "
        "versus our minimal one-shot `run_python` framing. Caveat: k=1 for the real row (one live "
        "call), single task, one model - indicative, not a broad benchmark. Same underlying "
        "constraint as `code_exec` everywhere: neither sandbox can call a *live* external API "
        "directly - a live-API-backed code-execution comparison (real internet access on both "
        "sides) is out of scope here and would need its own security review before extending our "
        "own sandbox that way.",
    ]

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "CODE-EXEC.md")
    out = os.path.abspath(out)
    with open(out, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
