"""The user's variant A: replace endpoint names with integers.

A dictionary maps each operation to a number; the model calls by number and the
"shim" translates back to HTTP. Crucially, the dictionary still has to spell out
every operation's arguments (the model must know them to call correctly), and it
carries method+path too - so the manifest is counted in bucket A, in full. The
only saving versus compact_sig is in bucket B: an integer instead of a readable
name. This variant exists to *measure* whether that trade pays off.
"""

from __future__ import annotations

import spec_source as s

from .base import Definitions, PerCallVariant

# Stable number for every operation (list_operations() has a fixed order).
_NUMBER = {(op.method, op.path): i + 1 for i, op in enumerate(s.list_operations())}


def _args(op: s.Op) -> str:
    parts = [f"{n}:{t}" for n, t in op.path_params]
    parts += [f"{n}:{t}" + (f" {c}" if c else "") for n, t, c in op.body_fields]
    return f" ({', '.join(parts)})" if parts else ""


def _line(op: s.Op) -> str:
    n = _NUMBER[(op.method, op.path)]
    return f"{n} = {op.method} {op.path}{_args(op)} -> {op.returns}"


class Numbered(PerCallVariant):
    name = "numbered"

    def definitions(self) -> Definitions:
        lines = [
            "# Endpoint dictionary. Call by number: {\"name\": \"<n>\", \"input\": {<args>}}.",
            *[_line(op) for op in s.list_operations()],
        ]
        return Definitions(text="\n".join(lines))

    def call_id(self, op: s.Op) -> str:
        return str(_NUMBER[(op.method, op.path)])
