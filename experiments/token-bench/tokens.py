"""Token-counting backend.

Two backends, auto-selected:

* **anthropic** (faithful) - when ANTHROPIC_API_KEY is set. Uses the free
  `messages.count_tokens` endpoint (no generation, no token spend). Tool
  definitions are counted via the real `tools=` parameter, so bucket A reflects
  how tools are actually serialized into the prompt. Plain text is counted
  *marginally* (full request minus a fixed framing baseline) so we get the cost
  of the text itself, not of the surrounding message envelope.

* **tiktoken-approx** (zero-setup fallback) - GPT-style cl100k BPE. NOT Claude's
  tokenizer, so absolute numbers are approximate; clearly labelled. The relative
  ordering between variants - which is the point of this benchmark - is robust
  under it.
"""

from __future__ import annotations

import functools
import json
import os

MODEL = os.environ.get("BENCH_MODEL", "claude-opus-4-8")
_FRAME = [{"role": "user", "content": "."}]  # minimal request used as a baseline

_backend: str | None = None
_anthropic_client = None
_tiktoken_enc = None


def _init() -> str:
    """Pick a backend once and memoize the choice."""
    global _backend, _anthropic_client, _tiktoken_enc
    if _backend is not None:
        return _backend

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            from anthropic import Anthropic

            _anthropic_client = Anthropic()
            # Probe once so a bad key / no network falls back instead of crashing mid-run.
            _anthropic_client.messages.count_tokens(model=MODEL, messages=_FRAME)
            _backend = "anthropic"
            return _backend
        except Exception as exc:  # noqa: BLE001 - any failure -> approx fallback
            print(f"[tokens] anthropic backend unavailable ({exc!r}); using tiktoken-approx")

    import tiktoken

    _tiktoken_enc = tiktoken.get_encoding("cl100k_base")
    _backend = "tiktoken-approx"
    return _backend


def backend_name() -> str:
    return _init()


@functools.lru_cache(maxsize=4096)
def count(text: str) -> int:
    """Tokens contributed by `text` itself."""
    backend = _init()
    if backend == "anthropic":
        if not text:
            return 0  # the API rejects empty message content
        full = _anthropic_client.messages.count_tokens(
            model=MODEL, messages=[{"role": "user", "content": text}]
        ).input_tokens
        return max(0, full - _frame_overhead())
    return len(_tiktoken_enc.encode(text))


def count_tools(tools: list[dict]) -> int:
    """Marginal tokens added by a block of tool definitions (bucket A)."""
    if not tools:
        return 0
    backend = _init()
    if backend == "anthropic":
        with_tools = _anthropic_client.messages.count_tokens(
            model=MODEL, messages=_FRAME, tools=tools
        ).input_tokens
        return max(0, with_tools - _frame_tokens())
    # approx: count the serialized schema as text
    return len(_tiktoken_enc.encode(json.dumps(tools)))


@functools.lru_cache(maxsize=1)
def _frame_tokens() -> int:
    return _anthropic_client.messages.count_tokens(model=MODEL, messages=_FRAME).input_tokens


@functools.lru_cache(maxsize=1)
def _frame_overhead() -> int:
    # The frame's content is "." (one token), so the envelope overhead is
    # everything else. Subtracting it makes count(text) return the size of the
    # content alone, not of the surrounding message.
    return _frame_tokens() - 1
