"""Single source of truth for the benchmark.

Loads the *real* pet-zoo FastAPI app as a library (no server, no network),
exposes its auto-generated OpenAPI spec, a normalized list of operations that
every interface variant is generated from, and a TestClient seeded with a
deterministic fixture so result bodies (bucket C) are real, not invented.

pet-zoo is never modified. Its storage is redirected to a throwaway temp file
so the user's real data/zoo.json is left untouched.
"""

from __future__ import annotations

import atexit
import copy
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

# --- make pet-zoo importable (its modules import `from app...`) --------------
REPO_ROOT = Path(__file__).resolve().parents[2]
PETZOO_DIR = REPO_ROOT / "pet-zoo"
if str(PETZOO_DIR) not in sys.path:
    sys.path.insert(0, str(PETZOO_DIR))

from app import storage  # noqa: E402
from app.main import app  # noqa: E402
from app.models import AnimalSpecies  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

SPECIES = [s.value for s in AnimalSpecies]  # ['monkey', 'lion', 'tiger', 'elephant']

# --- redirect storage to a temp file so real data is untouched ---------------
_TMP_DIR = Path(tempfile.mkdtemp(prefix="petzoo-bench-"))
storage.DATA_PATH = _TMP_DIR / "zoo.json"
atexit.register(lambda: shutil.rmtree(_TMP_DIR, ignore_errors=True))

# Deterministic fixture: 50 animals across the four species.
_FIXTURE_COUNTS = {"monkey": 15, "lion": 12, "tiger": 13, "elephant": 10}

_client: TestClient | None = None
_spec: dict | None = None


def get_client() -> TestClient:
    global _client
    if _client is None:
        _client = TestClient(app)
    return _client


def reset_and_seed() -> TestClient:
    """Wipe the temp store and re-seed the fixed fixture. Deterministic, so
    every task starts from the same 50-animal state regardless of run order."""
    storage._save(storage._empty_state())
    client = get_client()
    for sp in SPECIES:
        for i in range(_FIXTURE_COUNTS[sp]):
            client.post(
                f"/{sp}s",
                json={
                    "name": f"{sp.capitalize()}-{i + 1:02d}",
                    "age": i % 18,
                    "gender": "male" if i % 2 == 0 else "female",
                },
            )
    return client


def get_spec() -> dict:
    global _spec
    if _spec is None:
        _spec = app.openapi()
    return _spec


# --- normalized operation model ---------------------------------------------
@dataclass
class Op:
    method: str  # GET / POST / PUT / DELETE
    path: str  # /monkeys/{animal_id}
    summary: str
    path_params: list[tuple[str, str]]  # [(name, type_str)]
    body_fields: list[tuple[str, str, str]]  # [(name, type_str, constraint_str)]
    returns: str  # 'Animal' | 'Animal[]' | 'void'
    raw: dict  # raw OpenAPI operation object

    @property
    def name(self) -> str:
        return tool_name(self)


def _resolve_ref(spec: dict, ref: str) -> dict:
    node: dict = spec
    for part in ref.lstrip("#/").split("/"):
        node = node[part]
    return node


def _type_str(spec: dict, schema: dict) -> str:
    if "$ref" in schema:
        target = _resolve_ref(spec, schema["$ref"])
        if "enum" in target:
            return "|".join(f'"{v}"' for v in target["enum"])
        schema = target
    if "enum" in schema:
        return "|".join(f'"{v}"' for v in schema["enum"])
    t = schema.get("type", "any")
    return {"integer": "int", "number": "float", "boolean": "bool", "string": "string"}.get(t, t)


def _num(x) -> str:
    return str(int(x)) if isinstance(x, float) and x.is_integer() else str(x)


def _constraint_str(schema: dict) -> str:
    bits = []
    if "minimum" in schema:
        bits.append(f">={_num(schema['minimum'])}")
    if "maximum" in schema:
        bits.append(f"<={_num(schema['maximum'])}")
    if "minLength" in schema:
        bits.append(f"len>={_num(schema['minLength'])}")
    if "maxLength" in schema:
        bits.append(f"len<={_num(schema['maxLength'])}")
    return ",".join(bits)


def _schema_fields(spec: dict, schema: dict) -> list[tuple[str, str, str]]:
    if "$ref" in schema:
        schema = _resolve_ref(spec, schema["$ref"])
    out = []
    for fname, prop in schema.get("properties", {}).items():
        resolved = _resolve_ref(spec, prop["$ref"]) if "$ref" in prop else prop
        out.append((fname, _type_str(spec, prop), _constraint_str(resolved)))
    return out


def _returns_str(spec: dict, operation: dict) -> str:
    for code in ("200", "201"):
        resp = operation.get("responses", {}).get(code)
        if not resp:
            continue
        schema = resp.get("content", {}).get("application/json", {}).get("schema")
        if not schema:
            continue
        if schema.get("type") == "array":
            item = schema["items"]
            ref = item.get("$ref", "")
            return f"{ref.rsplit('/', 1)[-1] or 'object'}[]"
        ref = schema.get("$ref", "")
        return ref.rsplit("/", 1)[-1] or "object"
    return "void"


def tool_name(op: Op) -> str:
    """Synthesize a human-readable tool name (the thing the `numbered` variant
    tries to replace with an integer): list_monkeys, get_monkey, create_monkey…"""
    segments = [p for p in op.path.strip("/").split("/") if not p.startswith("{")]
    resource = segments[-1] if segments else "root"
    singular = resource[:-1] if resource.endswith("s") else resource
    has_id = "{" in op.path
    verb = {"GET": "get" if has_id else "list", "POST": "create", "PUT": "update", "DELETE": "delete"}[op.method]
    noun = singular if (has_id or op.method in ("POST", "PUT", "DELETE")) else resource
    return f"{verb}_{noun}"


_operations: list[Op] | None = None


def list_operations() -> list[Op]:
    """All pet-zoo operations in a stable order (also defines `numbered` ids)."""
    global _operations
    if _operations is not None:
        return _operations
    spec = get_spec()
    ops: list[Op] = []
    for path in sorted(spec["paths"]):
        methods = spec["paths"][path]
        for method in ("get", "post", "put", "delete"):
            if method not in methods:
                continue
            operation = methods[method]
            path_params = [
                (p["name"], _type_str(spec, p.get("schema", {})))
                for p in operation.get("parameters", [])
                if p.get("in") == "path"
            ]
            body_fields: list[tuple[str, str, str]] = []
            rb = operation.get("requestBody")
            if rb:
                body_fields = _schema_fields(spec, rb["content"]["application/json"]["schema"])
            ops.append(
                Op(
                    method=method.upper(),
                    path=path,
                    summary=operation.get("summary", ""),
                    path_params=path_params,
                    body_fields=body_fields,
                    returns=_returns_str(spec, operation),
                    raw=operation,
                )
            )
    _operations = ops
    return ops


def op_by(method: str, path: str) -> Op:
    for op in list_operations():
        if op.method == method.upper() and op.path == path:
            return op
    raise KeyError(f"{method} {path}")


def inline_refs(node):
    """Deep-copy `node` with every $ref recursively inlined, producing a
    self-contained JSON Schema. This is what a naive OpenAPI->tools bridge emits
    (and what makes those tool schemas verbose). pet-zoo has no recursive
    schemas, so this always terminates."""
    spec = get_spec()

    def _walk(n):
        if isinstance(n, dict):
            if "$ref" in n:
                resolved = _resolve_ref(spec, n["$ref"])
                siblings = {k: v for k, v in n.items() if k != "$ref"}
                return _walk({**resolved, **siblings})
            return {k: _walk(v) for k, v in n.items()}
        if isinstance(n, list):
            return [_walk(x) for x in n]
        return n

    return _walk(copy.deepcopy(node))
