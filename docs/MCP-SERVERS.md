# Live MCP servers — advertised-menu token cost (bucket A)

_By [`experiments/mcp_servers.py`](../experiments/mcp_servers.py), 2026-07-01._

Real, pip-published **MCP reference servers** connected over **stdio**; we score the menu each one **actually advertises** (not a menu we generated), against a compact / lazy (`tool_search`) rendering of the same tools.

- tokenizer: **tiktoken-approx** _(relative ranking is the signal)_

| MCP server | tools | advertised menu (`mcp_live`) | `compact_sig` | saved | `tool_search` | saved |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| mcp-server-git | 12 | 1418 | 153 | +89% | 172 | +88% |
| mcp-server-fetch | 1 | 290 | 28 | +90% | 132 | +54% |
| mcp-server-time | 2 | 283 | 31 | +89% | 137 | +52% |

**Finding.** Even small real servers pay a fixed menu tax every session (a 2-tool server still ~hundreds of tokens), and a compact rendering of the *same* advertised tools cuts it sharply. The published heavy hitters go much further — the official GitHub MCP server advertises ~94 tools (~17.6k tokens), and multi-server setups routinely reach 50k+ before the first prompt (community-measured). `lap score --mcp-url <url>` scores any live server this way. _(We ran the pip-installable Python reference servers over stdio; the Docker-only servers — GitHub, filesystem — need a running Docker daemon, which wasn't available here.)_
