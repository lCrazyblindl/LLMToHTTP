"""Build `docs/LEADERBOARD.md` — a neutral, reproducible ranking of how many
tokens real public APIs' agent menus (bucket A) cost, and how much a LAP-style
compact menu would save.

For each API (resolved from the APIs.guru directory) we render the naive
OpenAPI->tools menu the way a generic MCP/OpenAPI bridge would, and the LAP
`compact_sig` and `tool_search` forms, and count their tokens. Offline by default
(tiktoken approximation — absolute numbers approximate, ranking is the signal);
set ANTHROPIC_API_KEY for faithful counts.

    python experiments/leaderboard.py            # writes docs/LEADERBOARD.md
"""

from __future__ import annotations

import hashlib
import pathlib
import tempfile
from datetime import date

from lap import openapi_ir as ir, score, tokens, estimate, lint

LIST_URL = "https://api.apis.guru/v2/list.json"
CACHE = pathlib.Path(tempfile.gettempdir()) / "lap-corpus"
MAXBYTES = 16_000_000
PAGE_SIZE = 20  # assumed items/page for the bucket-C (result-size) estimate

# Well-known public APIs (resolved by substring against the APIs.guru directory).
# v0.5 S3: expanded from the original 20-ish (v0.3/v0.4) to 40+ — every entry below was
# verified present in APIs.guru's live directory before being added (unresolvable guesses
# from the first expansion pass were dropped rather than left as silent "skip"s).
CURATED = [
    "stripe.com", "github.com", "slack.com", "digitalocean.com", "box.com", "asana.com",
    "gitlab.com", "atlassian.com:jira", "kubernetes", "adyen.com:CheckoutService",
    "googleapis.com:calendar", "googleapis.com:gmail", "amazonaws.com:ec2",
    "amazonaws.com:dynamodb", "azure.com:compute", "spotify.com", "notion.com",
    "sendgrid.com", "openai.com", "zoom.us", "trello.com",
    # v0.5 S3 additions
    "amazonaws.com:s3", "amazonaws.com:lambda", "amazonaws.com:rds", "amazonaws.com:sns",
    "amazonaws.com:sqs", "googleapis.com:drive", "googleapis.com:sheets",
    "googleapis.com:youtube", "googleapis.com:firebase", "googleapis.com:bigquery",
    "azure.com:storage", "azure.com:keyvault", "vimeo.com", "plaid.com", "nasa.gov",
    "circleci.com", "docker.com", "linode.com", "clickup.com", "netlify.com", "vercel.com",
    "bitbucket.org", "1password.com", "getpostman.com", "xero.com:xero_accounting",
    "webflow.com", "launchdarkly.com", "gitea.io", "ably.io:platform",
]


def _fetch(url: str) -> str:
    import httpx

    CACHE.mkdir(parents=True, exist_ok=True)
    f = CACHE / (hashlib.md5(url.encode()).hexdigest()[:16] + ".spec")
    if f.exists():
        return f.read_text(encoding="utf-8")
    r = httpx.get(url, timeout=60, follow_redirects=True)
    r.raise_for_status()
    f.write_text(r.text, encoding="utf-8")
    return r.text


def _pct(part: int, whole: int) -> int:
    if not whole:
        return 0
    r = round(100 * (whole - part) / whole)
    return 99 if r >= 100 and part > 0 else r  # never imply "free" when tokens remain


def _signed(pct: int) -> str:
    return f"+{pct}%" if pct >= 0 else f"{pct}%"


def main() -> None:
    import httpx

    directory = httpx.get(LIST_URL, timeout=60).json()

    def url_of(key: str) -> str | None:
        vers = directory.get(key, {}).get("versions", {})
        ver = directory.get(key, {}).get("preferred") or (next(iter(vers)) if vers else None)
        return (vers.get(ver) or {}).get("swaggerUrl") if ver else None

    rows = []
    for want in CURATED:
        key = next((k for k in directory if want in k), None)
        url = url_of(key) if key else None
        if not url:
            print(f"skip (not found): {want}")
            continue
        try:
            text = _fetch(url)
            if len(text) > MAXBYTES:
                print(f"skip (too big): {key}")
                continue
            spec = ir._parse(text)
            ops = ir.operations(spec)
            if not ops:
                print(f"skip (no ops): {key}")
                continue
            a = score.score(spec)
            result_cs = [est_c for op in ops
                         for kind, _per, est_c in [estimate.estimate(spec, op, page_size=PAGE_SIZE)]
                         if kind != "void"]
            c_max = max(result_cs) if result_cs else 0
            unpaged = sum(1 for f in lint.lint(spec) if f.rule == "R3")
            title = spec.get("info", {}).get("title", key)[:36]
            rows.append({
                "api": title, "provider": key.split(":")[0], "ops": len(ops),
                "full": a["openapi_full"], "compact": a["compact_sig"],
                "tool_search": a["tool_search"],
                "save_compact": _pct(a["compact_sig"], a["openapi_full"]),
                "save_search": _pct(a["tool_search"], a["openapi_full"]),
                "c_max": c_max, "unpaged": unpaged,
            })
            print(f"OK {key:34} ops={len(ops):4} full={a['openapi_full']:6} "
                  f"compact={a['compact_sig']:6} Cmax={c_max}")
        except Exception as e:  # noqa: BLE001
            print(f"FAIL {key}: {type(e).__name__}: {str(e)[:80]}")

    rows.sort(key=lambda r: r["full"], reverse=True)

    backend = tokens.backend_name()
    approx = backend != "anthropic"
    lines = [
        "# LAP efficiency leaderboard — agent-menu token cost of real public APIs",
        "",
        f"_Generated {date.today().isoformat()} by [`experiments/leaderboard.py`]"
        "(../experiments/leaderboard.py) over specs from [APIs.guru](https://apis.guru)._",
        "",
        f"**How to read it.** Each row is a real public API. **menu (full)** is the bucket-A token "
        "cost of the naive OpenAPI→tools menu a generic MCP/OpenAPI bridge emits — what an agent "
        "pays, once per session, just to *see* the API. **compact** and **tool_search** are the "
        "LAP-style menus (compact signatures; lazy search+execute) generated from the same spec, "
        "with the % saved vs full. Sorted by the naive menu cost (heaviest first): the APIs at the "
        "top cost agents the most tokens up front and have the most to gain from a leaner menu. "
        "**heaviest result (C)** is the largest single response (bucket C) the estimator finds for "
        "the API - the *recurring* per-call cost that field projection and pagination (LAP R1/R3) "
        f"target. It's a structural lower bound at ~{PAGE_SIZE} items/page, envelope-aware: a list "
        "wrapped in an envelope (`{data:[...]}`, k8s `items`) is scaled to a full page too, with its "
        "sibling fields (counts, cursors, kind/apiVersion, ...) counted once alongside it. Where a "
        "schema carries a real `example`/`examples` value, that's used instead of a synthetic "
        "placeholder - real data an API author wrote down beats a guess.",
        "",
        f"- tokenizer: **{backend}**" + ("  _(approximate — relative ranking is the signal; set "
        "`ANTHROPIC_API_KEY` for faithful counts)_" if approx else "  _(faithful)_"),
        f"- APIs scored: **{len(rows)}**",
        "",
        "| # | API | provider | ops | menu A (full) | compact | save | tool_search | save | heaviest result (C) |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['api']} | {r['provider']} | {r['ops']} | {r['full']} | {r['compact']} | "
            f"{_signed(r['save_compact'])} | {r['tool_search']} | {_signed(r['save_search'])} | {r['c_max'] or '-'} |"
        )

    if rows:
        avg_compact = round(sum(r["save_compact"] for r in rows) / len(rows))
        avg_search = round(sum(r["save_search"] for r in rows) / len(rows))
        total_full = sum(r["full"] for r in rows)
        n_unpaged = sum(1 for r in rows if r["unpaged"])
        lines += [
            "",
            f"**Across all {len(rows)} APIs:** the naive menus total **{total_full:,} tokens** (bucket "
            f"A); `compact_sig` saves **+{avg_compact}%** on average and `tool_search` **+{avg_search}%** "
            "(it wins most where operation counts are high). And that's before results come back: "
            f"**{n_unpaged} of {len(rows)}** have list endpoints with **no pagination**, so an agent can "
            "pull the *whole* collection into context (bucket C), not just a page. These APIs expose "
            "OpenAPI, which a generic bridge turns into the naive menu — so for an agent front-end the "
            "saving is mostly still on the table.",
            "",
            "_Methodology: **A** (menu) is measured; **heaviest result (C)** is estimated from response "
            f"schemas (structural lower bound; top-level AND envelope-wrapped lists scaled to "
            f"~{PAGE_SIZE} items/page; real schema `example`/`examples` values preferred over the "
            "6-char synthetic placeholder where present - `--string-len` on `lap score` raises the "
            "placeholder for un-exampled fields). **B** (the call) needs per-API tasks - see "
            "[`experiments/token-bench`](../experiments/token-bench/README.md). Regenerate with "
            "`python experiments/leaderboard.py`._",
        ]

    out = pathlib.Path(__file__).resolve().parents[1] / "docs" / "LEADERBOARD.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[written] {out}  ({len(rows)} APIs)")


if __name__ == "__main__":
    main()
