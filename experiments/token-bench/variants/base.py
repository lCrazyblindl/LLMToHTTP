"""Shared variant interface.

A *variant* is one way of exposing pet-zoo's HTTP API to an LLM. Every variant
must be able to, for a given task, produce the three token buckets:

* **A** definitions  - the menu that sits in context (tools and/or manifest text)
* **B** the call(s)  - what the model emits to invoke the action(s)
* **C** the result(s)- what comes back into context

`encode_calls` returns the bucket-B text; `result_payload` returns the object
whose serialization is bucket C. Definitions (A) are task-independent.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

# Compact separators match what Starlette/FastAPI actually puts on the wire, so
# bucket B/C token counts reflect real payloads rather than pretty-printed ones.
COMPACT = (",", ":")


def dumps(obj) -> str:
    return json.dumps(obj, separators=COMPACT, ensure_ascii=False)


@dataclass
class Definitions:
    tools: list = field(default_factory=list)  # Anthropic tool schemas -> count_tools
    text: str = ""  # manifest text -> count


class Variant:
    name: str = "base"

    def definitions(self) -> Definitions:
        raise NotImplementedError

    def encode_calls(self, task) -> str:
        raise NotImplementedError

    def result_payload(self, task):
        raise NotImplementedError


class PerCallVariant(Variant):
    """Variants that invoke one tool per HTTP call. They differ only in how the
    action is *named/described* (A) and referenced (B); the real result bodies
    (C) are identical across them."""

    def call_id(self, op) -> str:
        raise NotImplementedError

    def encode_calls(self, task) -> str:
        # One tool_use per call, in the shape the model actually emits.
        return "\n".join(
            dumps({"name": self.call_id(op), "input": args}) for op, args in task.calls
        )

    def result_payload(self, task):
        return task.bodies  # the real JSON bodies of every call
