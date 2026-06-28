"""The strong lever: tools-as-code.

Instead of one tool call per HTTP request (each dumping a full result into
context), the model gets a single `run_python` tool plus a compact client doc,
writes one script that does the calls + filtering + aggregation server-side, and
returns only the small final value. This collapses round-trips and - decisively
- shrinks bucket C: only the answer re-enters context, not every intermediate
body.
"""

from __future__ import annotations

from .base import Definitions, Variant

_CLIENT_DOC = """\
# Tool: run_python(code). A `zoo` client is in scope. Put the answer in `result`.
zoo.list(species) -> Animal[]      # species: "monkey"|"lion"|"tiger"|"elephant"
zoo.list_all() -> Animal[]
zoo.get(species, id) -> Animal
zoo.create(species, {name, age, gender}) -> Animal
zoo.update(species, id, {name, age, gender}) -> Animal
zoo.delete(species, id) -> None
# Animal = {id, species, name, age, gender}"""

_RUN_PYTHON_TOOL = {
    "name": "run_python",
    "description": "Execute Python against the zoo and return `result`.",
    "input_schema": {
        "type": "object",
        "properties": {"code": {"type": "string"}},
        "required": ["code"],
    },
}


class CodeExec(Variant):
    name = "code_exec"

    def definitions(self) -> Definitions:
        return Definitions(tools=[_RUN_PYTHON_TOOL], text=_CLIENT_DOC)

    def encode_calls(self, task) -> str:
        # One script for the whole task (bucket B is the code the model writes).
        return task.code

    def result_payload(self, task):
        # Only the reduced answer re-enters context (bucket C).
        return task.final_value
