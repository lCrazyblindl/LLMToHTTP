# LAP efficiency leaderboard — agent-menu token cost of real public APIs

_Generated 2026-06-30 by [`experiments/leaderboard.py`](../experiments/leaderboard.py) over specs from [APIs.guru](https://apis.guru)._

**How to read it.** Each row is a real public API. **menu (full)** is the bucket-A token cost of the naive OpenAPI→tools menu a generic MCP/OpenAPI bridge emits — what an agent pays, once per session, just to *see* the API. **compact** and **tool_search** are the LAP-style menus (compact signatures; lazy search+execute) generated from the same spec, with the % saved vs full. Sorted by the naive menu cost (heaviest first): the APIs at the top cost agents the most tokens up front and have the most to gain from a leaner menu.

- tokenizer: **tiktoken-approx**  _(approximate — relative ranking is the signal; set `ANTHROPIC_API_KEY` for faithful counts)_
- APIs scored: **20**

| # | API | provider | ops | menu (full) | compact | save | tool_search | save |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Kubernetes | kubernetes.io | 821 | 2818799 | 45015 | +98% | 8369 | +99% |
| 2 | Amazon Elastic Compute Cloud | amazonaws.com | 1182 | 606132 | 63158 | +90% | 8862 | +99% |
| 3 | The Jira Cloud platform REST API | atlassian.com | 487 | 345552 | 17996 | +95% | 2401 | +99% |
| 4 | Stripe API | stripe.com | 446 | 231586 | 32860 | +86% | 2958 | +99% |
| 5 | Adyen Checkout API | adyen.com | 24 | 169292 | 8326 | +95% | 293 | +99% |
| 6 | Amazon DynamoDB | amazonaws.com | 53 | 118053 | 4350 | +96% | 361 | +99% |
| 7 | GitHub v3 REST API | github.com | 845 | 100181 | 31888 | +68% | 6214 | +94% |
| 8 | Zoom API | zoom.us | 373 | 93045 | 7231 | +92% | 1810 | +98% |
| 9 | Asana | asana.com | 167 | 83178 | 2285 | +97% | 887 | +99% |
| 10 | ComputeManagementClient | azure.com | 109 | 70857 | 4616 | +93% | 886 | +99% |
| 11 | Box Platform API | box.com | 258 | 56468 | 10847 | +81% | 1900 | +97% |
| 12 | Calendar API | googleapis.com | 37 | 36506 | 2263 | +94% | 314 | +99% |
| 13 | Email Activity (beta) | sendgrid.com | 334 | 33542 | 8692 | +74% | 2456 | +93% |
| 14 | Gitlab | gitlab.com | 358 | 23948 | 9042 | +62% | 3506 | +85% |
| 15 | DigitalOcean API | digitalocean.com | 290 | 20991 | 3775 | +82% | 1584 | +92% |
| 16 | Gmail API | googleapis.com | 79 | 20429 | 2960 | +86% | 690 | +97% |
| 17 | Slack Web API | slack.com | 174 | 14433 | 2378 | +84% | 913 | +94% |
| 18 | OpenAI API | openai.com | 28 | 12250 | 2195 | +82% | 247 | +98% |
| 19 | Spotify Web API | spotify.com | 88 | 8395 | 2557 | +70% | 698 | +92% |
| 20 | Notion API | notion.com | 13 | 1587 | 168 | +89% | 197 | +88% |

**Across all 20 APIs:** the naive menus total **4,865,224 tokens**; `compact_sig` saves **+86%** on average and `tool_search` **+96%** (it wins most where operation counts are high). These APIs expose OpenAPI, which a generic bridge turns into the naive menu — so for an agent front-end that saving is mostly still on the table.

_Methodology: bucket A only (the menu in context). B (the call) and C (results) need per-API tasks — see [`experiments/token-bench`](../experiments/token-bench/README.md). Regenerate with `python experiments/leaderboard.py`._
