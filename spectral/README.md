# LAP rules for Spectral

Bring [`lap lint`](../lap/README.md)'s token-efficiency checks to any project that
already lints OpenAPI with [**Spectral**](https://github.com/stoplightio/spectral) (or
[vacuum](https://github.com/daveshanley/vacuum), which runs Spectral rulesets). The rules
mirror [`lap/lint.py`](../lap/lint.py) and cite the [LAP profile](../profile/llm-api-profile.md).

## Use it

```bash
npm i -g @stoplight/spectral-cli            # or: npx @stoplight/spectral-cli
spectral lint your-openapi.yaml --ruleset path/to/spectral/lap.spectral.yaml
```

Combine with the standard OpenAPI rules from your own `.spectral.yaml`:

```yaml
extends:
  - spectral:oas
  - ./path/to/spectral/lap.spectral.yaml
```

> **Local only.** These rules use custom JS functions, and Spectral will **not** fetch
> functions over HTTP — so vendor this `spectral/` directory (or install it) and point
> `--ruleset` / `extends` at a **local** path. A URL `extends` works only for
> function-free rulesets.

## Rules

| rule id | LAP | severity | flags |
| --- | --- | --- | --- |
| `lap-d3-readable-operation-id` | D3 | warn | opaque / numeric / too-short `operationId` |
| `lap-r3-collection-pagination` | R3 | warn | array-returning GET with no pagination param |
| `lap-r1-collection-projection` | R1 | info | collection GET with no field projection |
| `lap-r2-collection-filter` | R2 | info | collection GET with no server-side filter |
| `lap-w1-minimal-write` | W1 | info | POST/PUT/PATCH returning a full body by default |
| `lap-e1-error-response` | E1 | warn | operation with no 4xx/5xx response declared |
| `lap-a1-aggregate-endpoint` | A1 | info | no count/aggregate/stats/summary endpoint anywhere |

## Try it on the bundled example

```bash
cd spectral
npm install
npm run lint:example     # lints ../lap/examples/bookstore.openapi.json
```

Expected findings (same set as `python -m lap.lint lap/examples/bookstore.openapi.json`):
**E1 ×6, R3 ×2, R1 ×2, R2 ×2, W1 ×2, A1 ×1**, D3 ×0 — 8 warnings + 7 suggestions. The
project CI runs exactly this to keep the ruleset honest.

## Scope & caveats

- **This lints the static OpenAPI shape** (the "menu"). For the token **numbers** (bucket A
  menu cost, bucket C result estimate, the multi-API leaderboard) use
  [`lap score`](../lap/README.md) / [token-bench](../experiments/token-bench/README.md).
- Targets **OpenAPI 3.x**; basic Swagger 2.0 (`response.schema`) is handled.
- **D3** is only judged when `operationId` is present — Spectral can't see lap's synthesized
  names. (`lap lint` evaluates synthesized names too.)
- Rules run on Spectral's resolved document, so `$ref` parameters/responses are followed.
