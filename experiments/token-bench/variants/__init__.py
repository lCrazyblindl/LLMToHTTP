"""Registry of interface variants, in display order."""

from __future__ import annotations

from .base import Definitions, PerCallVariant, Variant
from .code_exec import CodeExec
from .compact_sig import CompactSig
from .mcp_fastmcp import McpFastMCP
from .numbered import Numbered
from .odata_query import ODataQuery
from .openapi_full import OpenApiFull

ALL: list[Variant] = [OpenApiFull(), McpFastMCP(), CompactSig(), Numbered(), CodeExec(), ODataQuery()]
BY_NAME = {v.name: v for v in ALL}

__all__ = ["ALL", "BY_NAME", "Variant", "PerCallVariant", "Definitions"]
