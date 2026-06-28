"""Registry of interface variants, in display order."""

from __future__ import annotations

from .base import Definitions, PerCallVariant, Variant
from .code_exec import CodeExec
from .compact_sig import CompactSig
from .numbered import Numbered
from .openapi_full import OpenApiFull

ALL: list[Variant] = [OpenApiFull(), CompactSig(), Numbered(), CodeExec()]
BY_NAME = {v.name: v for v in ALL}

__all__ = ["ALL", "BY_NAME", "Variant", "PerCallVariant", "Definitions"]
