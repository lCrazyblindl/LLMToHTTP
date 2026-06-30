"""Fuzz the `lap` parser over a corpus of real-world OpenAPI specs.

Runs the whole `lap` surface (operations IR, all menu forms via `lap score`,
`lap lint`, and the bucket-C estimate) over many real specs from APIs.guru and
asserts no crashes + non-degenerate output. This is how the parser's robustness
is verified against the messy long-tail (Swagger 2.0, `discriminator`, webhooks,
deep nesting, non-JSON media types). Network, opt-in; not part of the unit suite.

    python experiments/fuzz_corpus.py                  # curated gnarly set (~12 specs)
    python experiments/fuzz_corpus.py --sample 100     # + 100 random APIs.guru specs
    python experiments/fuzz_corpus.py --sample 60 --seed 17

Exit code is non-zero if any spec crashes, so it can gate CI if ever wanted.
"""

from __future__ import annotations

import argparse
import hashlib
import pathlib
import random
import tempfile
import traceback

from lap import openapi_ir as ir, score, lint, estimate

LIST_URL = "https://api.apis.guru/v2/list.json"
CACHE = pathlib.Path(tempfile.gettempdir()) / "lap-corpus"
MAXBYTES = 40_000_000

# Deliberately gnarly, well-known specs (resolved by substring against the
# APIs.guru directory) — Swagger 2.0, discriminator, webhooks, 1000+ operations.
CURATED = ["stripe.com", "github.com", "kubernetes", "digitalocean", "googleapis.com:compute",
           "azure.com:compute", "box.com", "slack.com", "atlassian.com:jira",
           "amazonaws.com:ec2", "twilio.com:twilio_api", "asana"]


def _fetch(url: str, timeout: float = 60) -> str:
    import httpx

    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.md5(url.encode()).hexdigest()[:16] + ".spec")
    if f.exists():
        return f.read_text(encoding="utf-8")
    r = httpx.get(url, timeout=timeout, follow_redirects=True)
    r.raise_for_status()
    f.write_text(r.text, encoding="utf-8")
    return r.text


def _run_lap(spec: dict) -> tuple[int, int, int]:
    """Exercise every parser entry point; raise on any crash."""
    ops = ir.operations(spec)
    sc = score.score(spec)  # openapi_full / compact_sig / numbered / tool_search
    findings = lint.lint(spec)
    for op in ops:
        estimate.estimate(spec, op, 20)
    ir.referenced_component_names(spec)
    assert all(isinstance(v, int) and v >= 0 for v in sc.values()), sc
    return len(ops), sc["compact_sig"], len(findings)


def _targets(args) -> list[tuple[str, str]]:
    import httpx

    directory = httpx.get(LIST_URL, timeout=60).json()

    def url_of(key: str) -> str | None:
        vers = directory.get(key, {}).get("versions", {})
        ver = directory.get(key, {}).get("preferred") or (next(iter(vers)) if vers else None)
        return (vers.get(ver) or {}).get("swaggerUrl") if ver else None

    out: list[tuple[str, str]] = []
    for want in CURATED:
        key = next((k for k in directory if want in k), None)
        url = url_of(key) if key else None
        if url:
            out.append((key, url))
    if args.sample:
        pool = [(k, url_of(k)) for k in directory]
        pool = [(k, u) for k, u in pool if u]
        random.Random(args.seed).shuffle(pool)
        out += pool[:args.sample]
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Fuzz lap over real OpenAPI specs (APIs.guru).")
    ap.add_argument("--sample", type=int, default=0, help="also test N random specs from the directory")
    ap.add_argument("--seed", type=int, default=17, help="sampling seed (reproducible)")
    args = ap.parse_args()

    fails = []
    ok = skipped = 0
    for name, url in _targets(args):
        try:
            text = _fetch(url)
        except Exception as e:  # noqa: BLE001
            skipped += 1
            print(f"DL-SKIP {name}: {repr(e)[:90]}")
            continue
        if len(text) > MAXBYTES:
            skipped += 1
            print(f"BIG-SKIP {name}: {len(text)} bytes")
            continue
        try:
            spec = ir._parse(text)
            if not isinstance(spec, dict):
                raise TypeError(f"top-level is {type(spec).__name__}, not a mapping")
            ver = spec.get("openapi") or ("swagger" + str(spec.get("swagger", "?")))
            nops, compact, nf = _run_lap(spec)
            ok += 1
            print(f"OK   {ver:8} {name:40} ops={nops:4} compact={compact:6} findings={nf}")
        except Exception as e:  # noqa: BLE001
            fails.append((name, type(e).__name__, str(e), traceback.format_exc()))
            print(f"FAIL {name:40} {type(e).__name__}: {str(e)[:90]}")

    print(f"\n==== ok={ok} fail={len(fails)} skipped={skipped} ====")
    for name, etype, emsg, tb in fails:
        print(f"\n### {name}  ({etype}: {emsg})\n{tb[-1200:]}")
    raise SystemExit(1 if fails else 0)


if __name__ == "__main__":
    main()
