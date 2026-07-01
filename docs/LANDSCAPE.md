# The Agentic-Web Landscape (June 2026) — and where LAP fits

## Why this doc

LAP is an open, neutral **token-efficiency measurement + guidance** layer for
agent-facing APIs. Before building more, we mapped what already exists, so LAP
**complements** the ecosystem instead of duplicating it. This is that map, with
sources, and an explicit statement of LAP's niche.

## The shared problem

As agents proliferate, two costs dominate: **token/context bloat** (tool definitions
and results eat the model's context — Anthropic has reported tool definitions alone
consuming ~134K tokens before the first question) and the **connective tissue** of
letting an agent reach an arbitrary API at all (discovery, auth, trust). The industry
is attacking both, hard.

## The landscape, by layer

### 1. Discovery — how an agent finds/understands a site's capabilities
- **llms.txt** — a `/llms.txt` file pointing LLMs at a site's key content. ~10% adoption
  (inflated by Shopify auto-enabling it); IDE agents (Claude Code, Cursor, Copilot) read it.
  The first widely-adopted "Business-to-Agent" file. Google declines to support it.
- **Microsoft NLWeb** — an open project/protocol that makes any site conversational and
  **agent-accessible**; each NLWeb instance acts as an MCP server exposing `/ask` + `/mcp`,
  built on Schema.org/RSS/sitemaps. "Agents don't need custom integrations for every site."
  Adopters: Shopify, Tripadvisor, Eventbrite, O'Reilly, Hearst.
- **A2A Agent Cards** — discoverable JSON declaring an agent's auth schemes + capabilities.

### 2. Interface / access — how the agent calls capabilities
- **MCP** — the de-facto standard for exposing tools to LLMs.
- **OpenAPI→MCP generators** — Speakeasy, Stainless, FastMCP, openapi-mcp: one command
  turns an OpenAPI spec into an MCP server.
- **Code execution** — Anthropic "Code execution with MCP" and Cloudflare "Code Mode" let
  the model write code against a typed API in a sandbox instead of many tool calls.
- **GraphQL / OData** — declarative query layers (Apollo MCP, WunderGraph) as the read shape.

### 3. Gateways + auth — who brokers access, credentials, policy
- **Open-source MCP gateways:** AWS MCP Gateway & Registry (OAuth DCR, biweekly releases),
  Hypr (1-click OAuth + DCR), atrawog/mcp-oauth-gateway ("OAuth 2.1 for any MCP server, no
  code changes"). They wrap auth + policy + discovery for you.
- MCP adopted **OAuth 2.1 + RFC 9728** (protected-resource metadata) so agents discover auth
  requirements dynamically.

### 4. Identity standards — who is this agent, on whose behalf
- **NIST AI Agent Standards Initiative** (Feb 2026); **IETF draft-klrc-aiagent-auth**; built
  on OAuth/OIDC/SPIFFE/WIMSE. Open problem: **multi-hop delegation** (A→B→C).

### 5. Efficiency patterns — making the above cheap in tokens
- Anthropic **code execution** (~98.7% token cut on a workflow), **Tool Search** (~85% via
  lazy tool loading), Cloudflare **Code Mode** (~99.9% on a 2,500-endpoint API), MCP
  **SEP-1576** (token-bloat mitigation: schema dedup, embedding tool-select, progressive
  disclosure).

### 6. Token-efficiency tooling — the closest neighbors to LAP

The measure/optimize space filled in fast through 2025–2026. An honest map of what already
exists (LAP builds on, credits, and overlaps some of these — it is **not first or only**):
- **Live MCP token counters** — e.g. the browser-based *MCP Token Counter*: paste a server
  URL, get per-tool token counts ranked largest-first. Measures bucket A for a **live MCP
  server**; doesn't work offline from OpenAPI, doesn't lint, estimate results (C), gate CI, or
  compare multiple APIs.
- **Vendor benchmarks & guides** — StackOne "4 approaches compared", Speakeasy "dynamic
  toolsets (−100×)", Pydantic "engineering MCP tools for token efficiency", Apollo GraphQL MCP.
  Strong decision frameworks and product numbers — articles/products, not a reusable neutral
  measure.
- **Runtime gateways / proxies** — StackOne, Speakeasy, getmaxim, Atlassian `mcp-compressor`:
  compress/filter tool schemas and responses at request time. (The "gateway" layer LAP
  deliberately does **not** rebuild.)
- **OpenAPI minifiers for LLMs** — e.g. `LLM-OpenAPI-minifier`: shrink a spec's *characters*
  for prompt-stuffing. (LAP optimizes *tokens*, and keeps readable names as signal.)
- **General API linters** — Spectral / vacuum: the de-facto OpenAPI linters with CI + custom
  rulesets, but **no token-efficiency ruleset** ships with them — so LAP also publishes its rules
  as a Spectral ruleset ([`../spectral/`](../spectral/README.md)) to ride that distribution.
- **Token/agent leaderboards** — Tokscale, llm-stats, Artificial Analysis rank **models and
  coding agents** by token use, not the token cost of specific **APIs'** agent menus.

## Where LAP fits (not first, not only — a different combination)

The neighbors in §6 each measure or optimize *pieces*: a live-MCP token counter (bucket A
only), vendor benchmarks (articles on their own setups), runtime gateways (the layer LAP
doesn't rebuild), minifiers (characters, not tokens), Spectral/vacuum (linting, but no
token-efficiency ruleset). What no single one offers is the **open, OpenAPI-native,
CI-friendly combination**: score the menu (A) *and* estimate the result (C) from a static spec
or a live MCP server, **lint** it against measured rules, gate a build, and publish a
**standing, reproducible leaderboard of real APIs**. LAP aims to be that shared yardstick —
complementary to everything above, crediting the techniques it builds on.

| layer | well-covered by | LAP |
|---|---|---|
| discovery | NLWeb, llms.txt, A2A | references, doesn't rebuild |
| interface / access | MCP, generators, code-exec, GraphQL | references, doesn't rebuild |
| gateways + auth | AWS / Hypr / atrawog, OAuth 2.1 + DCR | references, doesn't rebuild |
| identity | NIST, IETF, A2A | references, doesn't rebuild |
| **efficiency measurement + linting** | partial: live-MCP counters, vendor benchmarks, Spectral (no token rules) | **the open, OpenAPI-native, CI + leaderboard combination ← LAP** |

## LAP's niche

LAP is the open **measurement + guidance** layer:
- **`lap score`** — bucket-A menu cost (+ a real-MCP baseline, + a bucket-C result-size
  estimate) for any OpenAPI file/URL or a live MCP server, across naive / compact / numbered /
  tool_search forms; `--json` + a CI gate.
- **`lap lint`** — flags violations of measured rules (D3 / R1 / R2 / R3 / W1 / E1 / A1) with
  citations.
- **token-bench** — the full A/B/C run with tasks + a live success-rate check.
- **the LAP profile** ([`../profile/llm-api-profile.md`](../profile/llm-api-profile.md)) —
  measured, opinionated conventions for token-efficient APIs.
- **[`LEADERBOARD.md`](LEADERBOARD.md)** — a standing, reproducible ranking of real public
  APIs' menu cost.

**Explicit non-goals:** LAP does not build auth brokers, gateways, discovery registries,
hosting, or agent identity — those are covered above. LAP measures and guides; it cites the rest.

## Why it helps everyone

Anyone building on MCP/NLWeb wants their agent-API fast and cheap. Plenty of good tools and
posts help (§6); LAP's contribution is an **open, reproducible, vendor-neutral** way to measure
and lint it in CI, plus a public dataset — a public good, not a product. We stand on the
techniques above and credit them.

## Sources

- llms.txt (2026 state/adoption): https://codersera.com/blog/llms-txt-complete-guide-2026/ · https://caseyrb.com/blog/state-of-llms-txt-adoption/
- Microsoft NLWeb: https://news.microsoft.com/source/features/company-news/introducing-nlweb-bringing-conversational-interfaces-directly-to-the-web/
- MCP gateways: AWS https://aws.amazon.com/blogs/opensource/governing-ai-assets-at-scale-with-mcp-gateway-and-registry/ · Hypr https://github.com/hyprmcp/mcp-gateway · atrawog https://github.com/atrawog/mcp-oauth-gateway
- Agent identity: NIST https://workos.com/blog/nist-ai-agent-standards-initiative-explained · IETF https://datatracker.ietf.org/doc/draft-klrc-aiagent-auth/
- Efficiency: Anthropic code-exec https://www.anthropic.com/engineering/code-execution-with-mcp · Cloudflare Code Mode https://blog.cloudflare.com/code-mode-mcp/ · MCP SEP-1576 https://github.com/modelcontextprotocol/modelcontextprotocol/issues/1576
- OpenAPI→MCP: Speakeasy https://www.speakeasy.com/blog/generate-mcp-from-openapi · FastMCP https://gofastmcp.com/integrations/openapi
- GraphQL for agents: Apollo https://www.apollographql.com/blog/building-efficient-ai-agents-with-graphql-and-apollo-mcp-server
- Token-efficiency neighbors (§6): MCP Token Counter https://mcpplaygroundonline.com/blog/mcp-token-counter-optimize-context-window · StackOne https://www.stackone.com/blog/mcp-token-optimization/ · Speakeasy dynamic toolsets https://www.speakeasy.com/blog/how-we-reduced-token-usage-by-100x-dynamic-toolsets-v2 · Pydantic https://pydantic.dev/articles/engineering-mcp-tools-for-token-efficiency · LLM-OpenAPI-minifier https://github.com/ShelbyJenkins/LLM-OpenAPI-minifier · Spectral https://github.com/stoplightio/spectral · vacuum https://github.com/daveshanley/vacuum · Tokscale https://github.com/junhoyeo/tokscale
