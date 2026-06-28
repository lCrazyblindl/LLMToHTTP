"""Run model-written code in a process-isolated sandbox with a timeout.

Spawns sandbox_runner.py with the same interpreter, pipes the code in on stdin,
and parses the single JSON result line. A runaway script (infinite loop, etc.)
is killed by the timeout instead of hanging the benchmark.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

_RUNNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sandbox_runner.py")


def run_in_sandbox(code: str, timeout: float = 10.0) -> dict:
    try:
        proc = subprocess.run(
            [sys.executable, _RUNNER],
            input=code,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"timeout after {timeout}s"}

    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or "nonzero exit").strip()[-500:]}

    out = proc.stdout.strip().splitlines()
    if not out:
        return {"ok": False, "error": f"no sandbox output; stderr={proc.stderr.strip()[-300:]!r}"}
    try:
        return json.loads(out[-1])
    except json.JSONDecodeError:
        return {"ok": False, "error": f"bad sandbox output: {out[-1][:200]!r}"}
