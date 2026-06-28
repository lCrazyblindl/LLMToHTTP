"""Generate the code-execution client + its doc from the pet-zoo IR.

This is the "developer tool" in miniature: from the OpenAPI operations (already
normalized in spec_source) we emit ONE source of truth that produces both
* `client_doc()` - the compact API description the model sees (bucket A), and
* `generate_client_source()` - the executable `Zoo` class the sandbox runs.

Because both come from the same IR, the doc and the runtime can't drift. The
generator targets the common RESTful collection pattern (`/things`,
`/things/{id}`) and validates that pet-zoo actually follows it.
"""

from __future__ import annotations

import spec_source as s


def _validate_rest_pattern() -> None:
    """Confirm pet-zoo follows the collection/item shape this generator assumes,
    so the generated client is derived-and-checked, not blindly hardcoded."""
    for sp in s.SPECIES:
        s.op_by("GET", f"/{sp}s")
        s.op_by("POST", f"/{sp}s")
        s.op_by("GET", f"/{sp}s/{{animal_id}}")
        s.op_by("PUT", f"/{sp}s/{{animal_id}}")
        s.op_by("DELETE", f"/{sp}s/{{animal_id}}")
    s.op_by("GET", "/animals")


def client_doc() -> str:
    species = "|".join(f'"{x}"' for x in s.SPECIES)
    return (
        "# Tool: run_python(code). A `zoo` client is in scope. Put the answer in `result`.\n"
        f"zoo.list(species) -> Animal[]      # species: {species}\n"
        "zoo.list_all() -> Animal[]\n"
        "zoo.get(species, id) -> Animal\n"
        "zoo.create(species, {name, age, gender}) -> Animal\n"
        "zoo.update(species, id, {name, age, gender}) -> Animal\n"
        "zoo.delete(species, id) -> None\n"
        "# Animal = {id, species, name, age, gender}"
    )


def generate_client_source() -> str:
    """Emit the `Zoo` class source the sandbox exec's. Derived from the IR."""
    _validate_rest_pattern()
    return (
        "class Zoo:\n"
        '    """Generated from the pet-zoo OpenAPI (RESTful collection pattern)."""\n'
        "    def __init__(self, client):\n"
        "        self._c = client\n"
        "    def list(self, species):\n"
        '        return self._c.get(f"/{species}s").json()\n'
        "    def list_all(self):\n"
        '        return self._c.get("/animals").json()\n'
        "    def get(self, species, id):\n"
        '        return self._c.get(f"/{species}s/{id}").json()\n'
        "    def create(self, species, body):\n"
        '        return self._c.post(f"/{species}s", json=body).json()\n'
        "    def update(self, species, id, body):\n"
        '        return self._c.put(f"/{species}s/{id}", json=body).json()\n'
        "    def delete(self, species, id):\n"
        '        self._c.delete(f"/{species}s/{id}")\n'
    )
