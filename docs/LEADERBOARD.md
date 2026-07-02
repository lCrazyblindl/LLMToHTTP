# LAP efficiency leaderboard — agent-menu token cost of real public APIs

_Generated 2026-07-02 by [`experiments/leaderboard.py`](../experiments/leaderboard.py) over specs from [APIs.guru](https://apis.guru)._

**How to read it.** Each row is a real public API. **menu (full)** is the bucket-A token cost of the naive OpenAPI→tools menu a generic MCP/OpenAPI bridge emits — what an agent pays, once per session, just to *see* the API. **compact** and **tool_search** are the LAP-style menus (compact signatures; lazy search+execute) generated from the same spec, with the % saved vs full. Sorted by the naive menu cost (heaviest first): the APIs at the top cost agents the most tokens up front and have the most to gain from a leaner menu. **heaviest result (C)** is the largest single response (bucket C) the estimator finds for the API - the *recurring* per-call cost that field projection and pagination (LAP R1/R3) target. It's a structural lower bound at ~20 items/page, envelope-aware: a list wrapped in an envelope (`{data:[...]}`, k8s `items`) is scaled to a full page too, with its sibling fields (counts, cursors, kind/apiVersion, ...) counted once alongside it.

- tokenizer: **tiktoken-approx**  _(approximate — relative ranking is the signal; set `ANTHROPIC_API_KEY` for faithful counts)_
- APIs scored: **50**

| # | API | provider | ops | menu A (full) | compact | save | tool_search | save | heaviest result (C) |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | Xero Accounting API | xero.com | 224 | 4039605 | 7794 | +99% | 1213 | +99% | 15503 |
| 2 | Kubernetes | kubernetes.io | 821 | 2818799 | 45015 | +98% | 8369 | +99% | 7613 |
| 3 | Amazon Elastic Compute Cloud | amazonaws.com | 1182 | 606132 | 63158 | +90% | 8862 | +99% | 652 |
| 4 | Google Sheets API | googleapis.com | 17 | 492618 | 1483 | +99% | 283 | +99% | 5163 |
| 5 | The Jira Cloud platform REST API | atlassian.com | 487 | 345552 | 17996 | +95% | 2401 | +99% | 33565 |
| 6 | Stripe API | stripe.com | 446 | 231586 | 32860 | +86% | 2958 | +99% | 15868 |
| 7 | Bitbucket API | bitbucket.org | 303 | 179049 | 10796 | +94% | 1563 | +99% | 6465 |
| 8 | Adyen Checkout API | adyen.com | 24 | 169292 | 8326 | +95% | 293 | +99% | 1777 |
| 9 | Amazon Relational Database Service | amazonaws.com | 282 | 163827 | 18474 | +89% | 2062 | +99% | 2090 |
| 10 | Amazon DynamoDB | amazonaws.com | 53 | 118053 | 4350 | +96% | 361 | +99% | 260 |
| 11 | GitHub v3 REST API | github.com | 845 | 100181 | 31888 | +68% | 6214 | +94% | 81685 |
| 12 | BigQuery API | googleapis.com | 36 | 98494 | 3563 | +96% | 347 | +99% | 4889 |
| 13 | Zoom API | zoom.us | 373 | 93045 | 7231 | +92% | 1810 | +98% | 9645 |
| 14 | The Plaid API | plaid.com | 198 | 91565 | 25068 | +73% | 1144 | +99% | 4671 |
| 15 | Linode API | linode.com | 350 | 86291 | 11794 | +86% | 1792 | +98% | 2836 |
| 16 | Asana | asana.com | 167 | 83178 | 2285 | +97% | 887 | +99% | 4224 |
| 17 | ComputeManagementClient | azure.com | 109 | 70857 | 4616 | +93% | 886 | +99% | 3269 |
| 18 | YouTube Data API v3 | googleapis.com | 76 | 59373 | 3504 | +94% | 570 | +99% | 9350 |
| 19 | Box Platform API | box.com | 258 | 56468 | 10847 | +81% | 1900 | +97% | 8068 |
| 20 | Drive API | googleapis.com | 48 | 40686 | 3062 | +92% | 372 | +99% | 16860 |
| 21 | Vimeo | vimeo.com | 326 | 39316 | 7675 | +80% | 1794 | +95% | 90105 |
| 22 | Amazon Simple Storage Service | amazonaws.com | 95 | 37807 | 2707 | +93% | 587 | +98% | 82 |
| 23 | Calendar API | googleapis.com | 37 | 36506 | 2263 | +94% | 314 | +99% | 7238 |
| 24 | Gitea API. | gitea.io | 325 | 35067 | 11273 | +68% | 1663 | +95% | 38625 |
| 25 | Email Activity (beta) | sendgrid.com | 334 | 33542 | 8692 | +74% | 2456 | +93% | 2665 |
| 26 | Trello | trello.com | 324 | 28148 | 7884 | +72% | 2730 | +90% | - |
| 27 | AWS Lambda | amazonaws.com | 66 | 27590 | 3788 | +86% | 444 | +98% | 319 |
| 28 | Gitlab | gitlab.com | 358 | 23948 | 9042 | +62% | 3506 | +85% | 697 |
| 29 | Vercel API | vercel.com | 112 | 22188 | 3552 | +84% | 571 | +97% | 24318 |
| 30 | DigitalOcean API | digitalocean.com | 290 | 20991 | 3775 | +82% | 1584 | +92% | 12244 |
| 31 | Amazon Simple Queue Service | amazonaws.com | 40 | 20802 | 1373 | +93% | 342 | +98% | 36 |
| 32 | Gmail API | googleapis.com | 79 | 20429 | 2960 | +86% | 690 | +97% | 1405 |
| 33 | KeyVaultClient | azure.com | 78 | 19066 | 3123 | +84% | 446 | +98% | 1269 |
| 34 | Amazon Simple Notification Service | amazonaws.com | 84 | 17379 | 2477 | +86% | 608 | +97% | 11 |
| 35 | Slack Web API | slack.com | 174 | 14433 | 2378 | +84% | 913 | +94% | 23685 |
| 36 | OpenAI API | openai.com | 28 | 12250 | 2195 | +82% | 247 | +98% | 1852 |
| 37 | LaunchDarkly REST API | launchdarkly.com | 105 | 12086 | 3580 | +70% | 593 | +95% | 3671 |
| 38 | Netlify's API documentation | netlify.com | 120 | 10729 | 3940 | +63% | 656 | +94% | 8465 |
| 39 | StorageManagementClient | azure.com | 19 | 10508 | 1268 | +88% | 247 | +98% | 3769 |
| 40 | Lucidtech API | webflow.com | 81 | 9632 | 4967 | +48% | 423 | +96% | 6129 |
| 41 | Spotify Web API | spotify.com | 88 | 8395 | 2557 | +70% | 698 | +92% | 5184 |
| 42 | Postman API | getpostman.com | 57 | 7521 | 725 | +90% | 352 | +95% | 584 |
| 43 | Firebase Management API | googleapis.com | 21 | 5124 | 1042 | +80% | 272 | +95% | 1150 |
| 44 | Platform API | ably.io | 22 | 4295 | 642 | +85% | 253 | +94% | 1285 |
| 45 | Notion API | notion.com | 13 | 1587 | 168 | +89% | 197 | +88% | 6118 |
| 46 | CircleCI REST API | circleci.com | 22 | 1502 | 801 | +47% | 232 | +85% | 5365 |
| 47 | DVP Data API | docker.com | 8 | 796 | 303 | +62% | 186 | +77% | 333 |
| 48 | Events API | 1password.com | 3 | 123 | 111 | +10% | 158 | -28% | 1693 |
| 49 | clickup20 | clickup.com | 2 | 101 | 43 | +57% | 153 | -51% | - |
| 50 | APOD | nasa.gov | 1 | 36 | 31 | +14% | 148 | -311% | 45 |

**Across all 50 APIs:** the naive menus total **10,426,548 tokens** (bucket A); `compact_sig` saves **+80%** on average and `tool_search` **+82%** (it wins most where operation counts are high). And that's before results come back: **10 of 50** have list endpoints with **no pagination**, so an agent can pull the *whole* collection into context (bucket C), not just a page. These APIs expose OpenAPI, which a generic bridge turns into the naive menu — so for an agent front-end the saving is mostly still on the table.

_Methodology: **A** (menu) is measured; **heaviest result (C)** is estimated from response schemas (structural lower bound; top-level AND envelope-wrapped lists scaled to ~20 items/page). **B** (the call) needs per-API tasks - see [`experiments/token-bench`](../experiments/token-bench/README.md). Regenerate with `python experiments/leaderboard.py`._
