"""Score a *live* MCP server's advertised tools (lap score --mcp-url <url>).

Connects to a running MCP server with an MCP client, lists the tools it actually
advertises, and reports their menu (bucket A) token cost plus what a compact or
lazy (`tool_search`) menu would cost instead. Meets the ecosystem where it's
deployed, rather than only scoring a static OpenAPI file. Optional: needs fastmcp.

`fetch_tools(target)` accepts either a URL string (real server) or a FastMCP
server object (in-memory transport, used by the tests).
"""

from __future__ import annotations

import asyncio


def available() -> bool:
    try:
        import fastmcp  # noqa: F401
    except ImportError:
        return False
    return True


async def _fetch(target):
    from fastmcp import Client

    async with Client(target) as client:
        tools = await client.list_tools()
    return [
        {"name": t.name, "description": t.description or "", "input_schema": (t.inputSchema or {})}
        for t in tools
    ]


def fetch_tools(target) -> list[dict]:
    return asyncio.run(_fetch(target))


def _ptype(prop) -> str:
    t = prop.get("type") if isinstance(prop, dict) else None
    if isinstance(t, list):
        t = next((x for x in t if x != "null"), t[0] if t else None)
    return t or "any"


def _compact(tools: list[dict]) -> str:
    lines = ["# tools (compact, from MCP inputSchemas)"]
    for t in tools:
        props = (t["input_schema"] or {}).get("properties", {})
        params = ", ".join(f"{k}:{_ptype(v)}" for k, v in props.items())
        lines.append(f"{t['name']}({params})")
    return "\n".join(lines)


def score_tools(tools: list[dict]) -> dict:
    from . import menu, tokens

    live = tokens.count_tools(tools)
    compact = tokens.count(_compact(tools))
    search = tokens.count_tools([menu._SEARCH_TOOL, menu._CALL_TOOL]) + tokens.count(
        "# Lazy: search_tools(query)+call_tool(name,input). operations: "
        + ", ".join(t["name"] for t in tools)
    )
    return {"tools": len(tools), "menu": {"mcp_live": live, "compact_sig": compact, "tool_search": search}}
