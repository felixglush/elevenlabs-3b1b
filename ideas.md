# Ideas inbox

Paste raw ideas here, one per line. When one is ready to become a video:

```bash
explainer draft "Design a distributed rate limiter" --kind system_design   # Claude writes topics/<slug>.yaml
# or
explainer new rate-limiter --kind system_design                            # blank template to fill by hand
```

Kinds: `system_design`, `agentic`, `neetcode`.

## System design
- Distributed rate limiter
- URL shortener
- News feed / timeline
- Notification service (email, push, SMS) with retries
- Shopify B2B order sync (webhooks, idempotency, backfills)

## Agentic
- Customer support agent with RAG over help docs
- Coding agent that opens PRs
- Deep research agent (multi-agent fan-out)

## NeetCode
- Two Sum
- Longest Substring Without Repeating Characters
- LRU Cache
- Course Schedule (topological sort)

## Done
- [x] agentic-wholesale-order-agent
- [x] neetcode-top-k-frequent
