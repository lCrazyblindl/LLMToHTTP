"""Subprocess entry point for the code-execution sandbox.

Reads model-written Python from stdin, runs it against a freshly seeded pet-zoo
with only the generated `zoo` client and a restricted set of builtins in scope,
and prints one JSON line: {"ok": true, "result": ...} or {"ok": false, ...}.

Isolation model: the real boundary is the *process* (the parent enforces a
timeout and reads only this stdout). The restricted builtins are a soft guard,
not a security boundary - CPython in-process sandboxing is escapable. Fine for a
local toy benchmark; a production deployment would use a container or WASM.
"""

from __future__ import annotations

import builtins
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spec_source as s  # noqa: E402
import zoo_client  # noqa: E402

_SAFE_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter", "float",
    "frozenset", "int", "len", "list", "map", "max", "min", "range", "reversed",
    "round", "set", "sorted", "str", "sum", "tuple", "zip",
]
SAFE_BUILTINS = {n: getattr(builtins, n) for n in _SAFE_NAMES if hasattr(builtins, n)}


def main() -> None:
    code = sys.stdin.read()
    client = s.reset_and_seed()

    setup_ns: dict = {}
    exec(zoo_client.generate_client_source(), setup_ns)  # trusted: defines Zoo
    zoo = setup_ns["Zoo"](client)

    run_ns = {"__builtins__": SAFE_BUILTINS, "zoo": zoo}
    try:
        exec(code, run_ns)  # noqa: S102 - sandboxed model code; see module docstring
        print(json.dumps({"ok": True, "result": run_ns.get("result")}, default=str))
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"ok": False, "error": repr(exc)}))


if __name__ == "__main__":
    main()
