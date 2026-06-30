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


def _longest(items: list[dict]) -> dict:
    m = max(items, key=lambda a: len(a["name"]))
    return {"name": m["name"], "species": m["species"]}


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
    category: str  # write | aggregate-read | peek-read | multi-step | beyond-DSL
    expect: list | None = None  # live-run success tokens; None -> derive from final_value
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
    # Tasks are grouped into categories with >=2 each, so no conclusion rests on a
    # single task (run_bench averages per category):
    #   write          - a single create; tests the minimal-write response (W1).
    #   aggregate-read  - compute-over-many -> small result (count/group); tests A1.
    #   peek-read       - retrieve one small item via filter/projection (R1/R2).
    #   multi-step      - naive needs many round-trips; the DSL collapses them.
    #   beyond-DSL      - the query layer can't express it (argmax/avg over a
    #                     computed property), so only code returns a small result.

    # --- write ---------------------------------------------------------------
    t1 = Task(
        name="T1_create",
        prompt="Add a new monkey named Bobo, age 3, male.",
        calls=[(s.op_by("POST", "/monkeys"), {"name": "Bobo", "age": 3, "gender": "male"})],
        code='result = zoo.create("monkey", {"name": "Bobo", "age": 3, "gender": "male"})',
        query={"op": "create", "resource": "monkey", "body": {"name": "Bobo", "age": 3, "gender": "male"}},
        reduce=lambda bodies: bodies[0],
        category="write",
        expect=["Bobo"],
    )

    t1b = Task(
        name="T1b_create_lion",
        prompt="Register a new lion named Zuri, age 4, female.",
        calls=[(s.op_by("POST", "/lions"), {"name": "Zuri", "age": 4, "gender": "female"})],
        code='result = zoo.create("lion", {"name": "Zuri", "age": 4, "gender": "female"})',
        query={"op": "create", "resource": "lion", "body": {"name": "Zuri", "age": 4, "gender": "female"}},
        reduce=lambda bodies: bodies[0],
        category="write",
        expect=["Zuri"],
    )

    # --- aggregate-read ------------------------------------------------------
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
        category="aggregate-read",
    )

    t2b = Task(
        name="T2b_count_old_lions",
        prompt="How many lions are older than 8?",
        calls=[(s.op_by("GET", "/lions"), {})],
        code=(
            'lions = zoo.list("lion")\n'
            'result = {"older_than_8": sum(1 for a in lions if a["age"] > 8)}'
        ),
        query={"resource": "lion", "filter": {"age": {"gt": 8}}, "count": True},
        reduce=lambda bodies: {"older_than_8": sum(1 for a in bodies[0] if a["age"] > 8)},
        category="aggregate-read",
    )

    # --- multi-step (naive = one round-trip per species; the DSL does it in one) -
    t3 = Task(
        name="T3_count_per_species",
        prompt="Count how many animals there are of each species.",
        calls=[(s.op_by("GET", f"/{sp}s"), {}) for sp in _SPECIES_ORDER],
        code='result = {sp: len(zoo.list(sp)) for sp in ["monkey", "lion", "tiger", "elephant"]}',
        query={"resource": "animals", "group_count": "species"},
        reduce=lambda bodies: {sp: len(b) for sp, b in zip(_SPECIES_ORDER, bodies)},
        category="multi-step",
    )

    t3b = Task(
        name="T3b_males_per_species",
        prompt="Count how many male animals there are of each species.",
        calls=[(s.op_by("GET", f"/{sp}s"), {}) for sp in _SPECIES_ORDER],
        code=(
            'result = {sp: sum(1 for a in zoo.list(sp) if a["gender"] == "male") '
            'for sp in ["monkey", "lion", "tiger", "elephant"]}'
        ),
        query={"resource": "animals", "filter": {"gender": "male"}, "group_count": "species"},
        reduce=lambda bodies: {
            sp: sum(1 for a in b if a["gender"] == "male") for sp, b in zip(_SPECIES_ORDER, bodies)
        },
        category="multi-step",
    )

    # --- peek-read -----------------------------------------------------------
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
        category="peek-read",
    )

    t4b = Task(
        name="T4b_peek_female_monkey",
        prompt="Find one female monkey older than 4; give me its name and age.",
        calls=[(s.op_by("GET", "/monkeys"), {})],
        code=(
            'monkeys = zoo.list("monkey")\n'
            'm = next(a for a in monkeys if a["gender"] == "female" and a["age"] > 4)\n'
            'result = {"name": m["name"], "age": m["age"]}'
        ),
        query={
            "resource": "monkey",
            "filter": {"gender": "female", "age": {"gt": 4}},
            "select": ["name", "age"],
            "top": 1,
        },
        reduce=lambda bodies: next(
            {"name": a["name"], "age": a["age"]}
            for a in bodies[0]
            if a["gender"] == "female" and a["age"] > 4
        ),
        category="peek-read",
    )

    # --- beyond-DSL (the query layer can't express it; only code stays small) -
    t5 = Task(
        name="T5_longest_name",
        prompt="Which animal has the longest name? Give its name and species.",
        calls=[(s.op_by("GET", "/animals"), {})],
        code=(
            "animals = zoo.list_all()\n"
            'm = max(animals, key=lambda a: len(a["name"]))\n'
            'result = {"name": m["name"], "species": m["species"]}'
        ),
        # The DSL can't express "argmax by len(name)" - a computed property. Best
        # effort is to project the needed fields; the model still gets all rows and
        # must compute the max itself. This is where the query approach hits its wall.
        query={"resource": "animals", "select": ["name", "species"]},
        reduce=lambda bodies: _longest(bodies[0]),
        category="beyond-DSL",
    )

    t5b = Task(
        name="T5b_avg_age",
        prompt="What is the average age of all the animals? Round to one decimal place.",
        calls=[(s.op_by("GET", "/animals"), {})],
        code=(
            "animals = zoo.list_all()\n"
            'result = {"avg_age": round(sum(a["age"] for a in animals) / len(animals), 1)}'
        ),
        # No average aggregate in the DSL either: best effort projects the one needed
        # field over every row, and the model must compute the mean itself.
        query={"resource": "animals", "select": ["age"]},
        reduce=lambda bodies: {"avg_age": round(sum(a["age"] for a in bodies[0]) / len(bodies[0]), 1)},
        category="beyond-DSL",
    )

    ordered = (t1, t1b, t2, t2b, t3, t3b, t4, t4b, t5, t5b)
    return [t.materialize() for t in ordered]
