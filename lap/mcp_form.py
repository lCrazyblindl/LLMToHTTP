"""Real-MCP menu form: what an actual MCP generator emits for a spec.

Builds a real MCP server from any OpenAPI via `FastMCP.from_openapi` and returns
its actual tool schemas, so the score includes a *real* ecosystem baseline rather
than only our hand-rolled `openapi_full`. Optional: gracefully unavailable if
`fastmcp` isn't installed.

We return the Anthropic `tools=` shape (name + description + input_schema), and
separately the per-tool output schemas — which FastMCP emits by default and many
clients forward into context (counted as an extra figure, as in the token-bench).
"""

from __future__ import annotations

import asyncio


def available() -> bool:
    try:
        import fastmcp  # noqa: F401
        import httpx  # noqa: F401
    except ImportError:
        return False
    return True


async def _build(spec: dict):
    import httpx
    from fastmcp import FastMCP

    async with httpx.AsyncClient(base_url="http://lap.invalid") as client:
        mcp = FastMCP.from_openapi(openapi_spec=spec, client=client)
        mcp_tools = [t.to_mcp_tool() for t in await mcp.list_tools()]

    inputs = [
        {"name": m.name, "description": m.description or "", "input_schema": m.inputSchema}
        for m in mcp_tools
    ]
    outputs = [m.outputSchema for m in mcp_tools if m.outputSchema]
    return inputs, outputs


def build(spec: dict) -> tuple[list[dict], list[dict]]:
    """Returns (input_tools, output_schemas) for the spec's real MCP server."""
    return asyncio.run(_build(spec))
