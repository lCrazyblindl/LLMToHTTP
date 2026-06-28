"""Benchmark tasks.

Each task fixes the *same* underlying work for every variant:
* `calls`  - the (operation, args) sequence a one-tool-per-call model makes;
* `code`   - the single script a code-execution model writes;
* `query`  - the one declarative query an odata_query model sends;
* `reduce` - turns the real call bodies into the small final answer.

Bodies (bucket C) are produced by actually executing the calls against the
seeded TestClient, so they are real pet-zoo responses. State is reset and
re-seeded before each task, so results are deterministic and order-independent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import query_engine
import spec_source as s

_SPECIES_ORDER = ["monkey", "lion", "tiger", "elephant"]


def _call(client, op: s.Op, args: dict):
    """Execute one operation against the TestClient and return its JSON body."""
    path = op.path
    rest = dict(args)
    for pname, _ in op.path_params:
        path = path.replace("{" + pname + "}", str(rest.pop(pname)))
    body = {f: rest[f] for f, _, _ in op.body_fields if f in rest}
    resp = client.request(op.method, path, json=body if op.body_fields else None)
    if resp.status_code == 204 or not resp.content:
        return None
    return resp.json()


@dataclass
class Task:
    name: str
    prompt: str
    calls: list[tuple[s.Op, dict]]
    code: str
    query: dict
    reduce: Callable[[list], object]
    bodies: list = field(default=None)
    final_value: object = field(default=None)
    query_result: object = field(default=None)

    def materialize(self) -> "Task":
        client = s.reset_and_seed()
        self.bodies = [_call(client, op, args) for op, args in self.calls]
        self.final_value = self.reduce(self.bodies)
        client = s.reset_and_seed()  # fresh state for the declarative query
        self.query_result = query_engine.run_query(client, self.query)
        return self


def build_tasks() -> list[Task]:
    t1 = Task(
        name="T1_create",
        prompt="Add a new monkey named Bobo, age 3, male.",
        calls=[(s.op_by("POST", "/monkeys"), {"name": "Bobo", "age": 3, "gender": "male"})],
        code='result = zoo.create("monkey", {"name": "Bobo", "age": 3, "gender": "male"})',
        query={"op": "create", "resource": "monkey", "body": {"name": "Bobo", "age": 3, "gender": "male"}},
        reduce=lambda bodies: bodies[0],
    )

    t2 = Task(
        name="T2_count_females",
        prompt="How many of all the animals are female?",
        calls=[(s.op_by("GET", "/animals"), {})],
        code=(
            "animals = zoo.list_all()\n"
            'result = {"females": sum(1 for a in animals if a["gender"] == "female")}'
        ),
        query={"resource": "animals", "filter": {"gender": "female"}, "count": True},
        reduce=lambda bodies: {"females": sum(1 for a in bodies[0] if a["gender"] == "female")},
    )

    t3 = Task(
        name="T3_count_per_species",
        prompt="Count how many animals there are of each species.",
        # Models the multi-round-trip pattern: one list call per species.
        calls=[(s.op_by("GET", f"/{sp}s"), {}) for sp in _SPECIES_ORDER],
        code='result = {sp: len(zoo.list(sp)) for sp in ["monkey", "lion", "tiger", "elephant"]}',
        query={"resource": "animals", "group_count": "species"},
        reduce=lambda bodies: {sp: len(b) for sp, b in zip(_SPECIES_ORDER, bodies)},
    )

    t4 = Task(
        name="T4_peek_one",
        prompt="Find one tiger older than 5; give me its name and age.",
        # No filter endpoint in pet-zoo, so per-call must pull the whole list.
        calls=[(s.op_by("GET", "/tigers"), {})],
        code=(
            'tigers = zoo.list("tiger")\n'
            'm = next(t for t in tigers if t["age"] > 5)\n'
            'result = {"name": m["name"], "age": m["age"]}'
        ),
        query={"resource": "tiger", "filter": {"age": {"gt": 5}}, "select": ["name", "age"], "top": 1},
        reduce=lambda bodies: next(
            {"name": t["name"], "age": t["age"]} for t in bodies[0] if t["age"] > 5
        ),
    )

    return [t.materialize() for t in (t1, t2, t3, t4)]
