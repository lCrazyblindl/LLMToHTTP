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

from lap import openapi_ir as ir, score, tokens

LIST_URL = "https://api.apis.guru/v2/list.json"
CACHE = pathlib.Path(tempfile.gettempdir()) / "lap-corpus"
MAXBYTES = 16_000_000

# Well-known public APIs (resolved by substring against the APIs.guru directory).
CURATED = [
    "stripe.com", "github.com", "slack.com", "twilio.com:twilio_api", "digitalocean.com",
    "box.com", "asana.com", "gitlab.com", "atlassian.com:jira", "kubernetes",
    "adyen.com:CheckoutService", "googleapis.com:calendar", "googleapis.com:gmail",
    "amazonaws.com:ec2", "amazonaws.com:dynamodb", "azure.com:compute", "spotify.com",
    "notion.com", "discord.com", "shopify.com", "sendgrid.com", "mailchimp.com",
    "openai.com", "zoom.us", "bigcommerce.com",
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
            title = spec.get("info", {}).get("title", key)[:36]
            rows.append({
                "api": title, "provider": key.split(":")[0], "ops": len(ops),
                "full": a["openapi_full"], "compact": a["compact_sig"],
                "tool_search": a["tool_search"],
                "save_compact": _pct(a["compact_sig"], a["openapi_full"]),
                "save_search": _pct(a["tool_search"], a["openapi_full"]),
            })
            print(f"OK {key:34} ops={len(ops):4} full={a['openapi_full']:6} compact={a['compact_sig']:6}")
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
        "top cost agents the most tokens up front and have the most to gain from a leaner menu.",
        "",
        f"- tokenizer: **{backend}**" + ("  _(approximate — relative ranking is the signal; set "
        "`ANTHROPIC_API_KEY` for faithful counts)_" if approx else "  _(faithful)_"),
        f"- APIs scored: **{len(rows)}**",
        "",
        "| # | API | provider | ops | menu (full) | compact | save | tool_search | save |",
        "| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for i, r in enumerate(rows, 1):
        lines.append(
            f"| {i} | {r['api']} | {r['provider']} | {r['ops']} | {r['full']} | {r['compact']} | "
            f"+{r['save_compact']}% | {r['tool_search']} | +{r['save_search']}% |"
        )

    if rows:
        avg_compact = round(sum(r["save_compact"] for r in rows) / len(rows))
        avg_search = round(sum(r["save_search"] for r in rows) / len(rows))
        total_full = sum(r["full"] for r in rows)
        lines += [
            "",
            f"**Across all {len(rows)} APIs:** the naive menus total **{total_full:,} tokens**; "
            f"`compact_sig` saves **+{avg_compact}%** on average and `tool_search` **+{avg_search}%** "
            "(it wins most where operation counts are high). These APIs expose OpenAPI, which a "
            "generic bridge turns into the naive menu — so for an agent front-end that saving is "
            "mostly still on the table.",
            "",
            "_Methodology: bucket A only (the menu in context). B (the call) and C (results) need "
            "per-API tasks — see [`experiments/token-bench`](../experiments/token-bench/README.md). "
            "Regenerate with `python experiments/leaderboard.py`._",
        ]

    out = pathlib.Path(__file__).resolve().parents[1] / "docs" / "LEADERBOARD.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[written] {out}  ({len(rows)} APIs)")


if __name__ == "__main__":
    main()
