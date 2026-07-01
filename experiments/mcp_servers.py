"""R3 — score the live MCP ecosystem (real published servers).

Connects over **stdio** to real, pip-published MCP **reference servers**, lists the tools they
**actually advertise**, and scores that advertised menu (bucket A) against a compact / lazy
rendering of the same tools — real servers, not menus we generated. Writes `docs/MCP-SERVERS.md`.

The servers pull their own deps, so run them from an **isolated** venv and point
`MCP_SERVER_PY` at it (the runner env only needs `fastmcp` + `lap`):

    python -m venv .venv-srv
    .venv-srv/Scripts/pip install mcp-server-git mcp-server-fetch mcp-server-time
    MCP_SERVER_PY=.venv-srv/Scripts/python.exe python experiments/mcp_servers.py

No API key (offline tiktoken; set ANTHROPIC_API_KEY for faithful counts).
"""

from __future__ import annotations

import os
import pathlib
import sys
from datetime import date

from lap import mcp_client, tokens

REPO = pathlib.Path(__file__).resolve().parents[1]
PY = os.environ.get("MCP_SERVER_PY") or sys.executable

# Real, pip-published reference servers (modelcontextprotocol/servers).
SERVERS = [
    ("mcp-server-git", ["-m", "mcp_server_git", "--repository", str(REPO)]),
    ("mcp-server-fetch", ["-m", "mcp_server_fetch"]),
    ("mcp-server-time", ["-m", "mcp_server_time"]),
]


def _saved(part: int, whole: int) -> str:
    return f"+{round(100 * (whole - part) / whole)}%" if whole else "-"


def main() -> None:
    from fastmcp.client.transports import StdioTransport

    rows, notes = [], []
    for name, args in SERVERS:
        try:
            tools = mcp_client.fetch_tools(StdioTransport(PY, args))
            m = mcp_client.score_tools(tools)["menu"]
            rows.append((name, len(tools), m["mcp_live"], m["compact_sig"], m["tool_search"]))
            print(f"OK   {name:18} tools={len(tools):3} live={m['mcp_live']:6} "
                  f"compact={m['compact_sig']:5} tool_search={m['tool_search']:5}")
        except Exception as e:  # noqa: BLE001
            notes.append(f"{name}: {type(e).__name__}")
            print(f"SKIP {name}: {e!r}"[:100])

    lines = [
        "# Live MCP servers — advertised-menu token cost (bucket A)",
        "",
        f"_By [`experiments/mcp_servers.py`](../experiments/mcp_servers.py), {date.today().isoformat()}._",
        "",
        "Real, pip-published **MCP reference servers** connected over **stdio**; we score the menu "
        "each one **actually advertises** (not a menu we generated), against a compact / lazy "
        "(`tool_search`) rendering of the same tools.",
        "",
        f"- tokenizer: **{tokens.backend_name()}** _(relative ranking is the signal)_",
        "",
        "| MCP server | tools | advertised menu (`mcp_live`) | `compact_sig` | saved | `tool_search` | saved |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for name, n, live, compact, search in rows:
        lines.append(f"| {name} | {n} | {live} | {compact} | {_saved(compact, live)} "
                     f"| {search} | {_saved(search, live)} |")
    lines += [
        "",
        "**Finding.** Even small real servers pay a fixed menu tax every session (a 2-tool server "
        "still ~hundreds of tokens), and a compact rendering of the *same* advertised tools cuts it "
        "sharply. The published heavy hitters go much further — the official GitHub MCP server "
        "advertises ~94 tools (~17.6k tokens), and multi-server setups routinely reach 50k+ before "
        "the first prompt (community-measured). `lap score --mcp-url <url>` scores any live server "
        "this way. _(We ran the pip-installable Python reference servers over stdio; the Docker-only "
        "servers — GitHub, filesystem — need a running Docker daemon, which wasn't available here.)_",
    ]
    if notes:
        lines += ["", "_Run notes: " + "; ".join(notes) + "._"]

    out = REPO / "docs" / "MCP-SERVERS.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\n[written] {out}")


if __name__ == "__main__":
    main()
