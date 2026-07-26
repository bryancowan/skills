# Prompt Caching and Cost Engineering

Caching is a **prompt structure** decision, not just an API flag — which is why it belongs in a prompting skill. Getting the ordering right is usually worth more than any wording change you'll make.

Sourced: 2026-07-26

Sources:
- https://developers.openai.com/api/docs/guides/prompt-caching
- https://developers.openai.com/cookbook/examples/prompt_caching_201
- https://platform.claude.com/docs/en/about-claude/pricing
- https://ai.google.dev/gemini-api/docs/pricing

---

## The one rule

**Static content first, volatile content last.** System instructions, tool definitions, schemas, and reference documents go at the top; user input and dynamic values go at the bottom. Any change in the early tokens invalidates the entire prefix match.

This conflicts with nothing else in prompt design — Anthropic's "long documents at the top, query at the end" advice for long context happens to be exactly cache-optimal too.

---

## OpenAI

**Threshold:** caching activates at **1,024 tokens**. Below that, nothing caches (`cached_tokens: 0`). This creates a genuinely counterintuitive optimization: a 900-token prompt padded to 1,100 tokens with a 50% hit rate is **33% cheaper** than the shorter uncached version.

**TTL:**
- GPT-5.6+: `prompt_cache_options.ttl`, default `30m`.
- Earlier models: `prompt_cache_retention` — `"in_memory"` (5–10 min inactive, 1 hour max) or `"24h"`.

**Explicit vs. automatic:**
- Automatic (default) places breakpoints on the latest message; OpenAI decides what to cache.
- Explicit (`prompt_cache_breakpoint: { "mode": "explicit" }`, GPT-5.6+) caches only what you mark. Max 4 new cache writes per request, 50 breakpoints considered.

**Pricing:** before GPT-5.6, cache writes were free and reads billed at the cached rate. **On GPT-5.6+, writes cost 1.25× the uncached input rate** (`cache_write_tokens`), reads appear as `cached_tokens`. Budget for the write.

**`prompt_cache_key` is the highest-leverage knob.** It improves routing stickiness so requests with the same prefix land on the same engine. One coding customer went from a **60% to 87% hit rate** with it alone. Each prefix+key combination handles roughly **15 requests per minute** — pick granularity (per-user, per-conversation, or bucketed) to match your traffic, since too-fine keys waste the cache and too-coarse ones exceed the per-key rate.

**What breaks caching:**
- Tool or schema changes — **including reordering**
- Any system prompt modification
- Timestamps or dynamic metadata early in the prompt
- Context truncation from conversation management
- Changing the reasoning effort parameter
- Using Chat Completions with reasoning models (chain-of-thought tokens aren't persisted)
- Changing `allowed_tools` — keep the full toolkit static in `tools` instead

**Measured gains:** 7% faster at 1,024 tokens, up to **67% faster time-to-first-token at 150k+ tokens**. Cost reductions of 50–90% depending on model. The **Responses API shows 40–80% better cache utilization than Chat Completions** — this is a strong reason to migrate independent of the reasoning-item argument.

---

## Anthropic

| Operation | Multiplier vs. base input |
|---|---|
| 5-minute cache write | 1.25× |
| 1-hour cache write | 2× |
| Cache read (hit) | 0.1× |

Break-even is **one read** for the 5-minute cache, **two reads** for the 1-hour cache. That's an aggressive payoff — cache almost anything reused.

**Minimum cacheable length dropped to 512 tokens on Opus 5** (from 1,024).

Two modes: **automatic** (one `cache_control` at the top level of the request; the system manages breakpoints as the conversation grows — the recommended default) and **explicit breakpoints** (`cache_control` on individual content blocks).

Multipliers stack with the **Batch API's 50% discount** and with the `inference_geo: "us"` 1.1× data-residency multiplier.

Other Anthropic cost levers:
- **Batch API: 50% off input and output.** Not available with fast mode.
- **The 1M context window bills at standard rates** — a 900k request costs the same per token as a 9k one.
- **Fast mode** (Opus 5 / 4.8, research preview): $10/$50 per MTok for up to 2.5× output speed.
- **Web search: $10 per 1,000 searches.** Web fetch and code execution (when paired with search/fetch) add no charge beyond tokens.
- **Tool definitions cost tokens on every request** — 286–474 tokens of system prompt on Opus 5 / Sonnet 5 just to enable tools, plus your schemas. Pruning unused tools is a real saving, and it also improves accuracy.

⚠️ **Re-baseline your token counts.** Claude 4.7 and later use a tokenizer producing **~30% more tokens for the same text**. Budgets and cost models tuned on 4.6 are wrong.

---

## Google Gemini

Gemini prices caching differently: a **discounted per-token rate plus an hourly storage charge** ($1.00/hr on most models, $4.50/hr on 2.5 Pro). The economics invert relative to the other two vendors — you're renting cache space over time rather than paying a one-time write premium.

Practical consequence: cache only when the content will actually be reused *within* the window you're paying for. Sporadic reuse over hours can cost more than not caching.

Also watch the **200k-token price step on Gemini 2.5 Pro** — input and output rates both jump above that boundary.

---

## Cross-vendor prompt structure for caching

Write the prompt in this order regardless of vendor:

1. System role and standing instructions (never varies)
2. Tool definitions and schemas (never varies, **never reorder**)
3. Reference documents / knowledge base (varies rarely)
4. Few-shot examples (varies rarely)
5. Conversation history
6. Current user input (varies every request)

Then:
- Never inject a timestamp or request ID into 1–4.
- Never reorder the tool array between requests.
- Keep the full tool list static and filter behavior through instructions rather than by changing the array.
- Instrument the cache metrics your vendor exposes and treat hit rate as a monitored production metric, not a one-time setup step.

---

## Beyond caching

- **Model tiering** — route easy work to a small model and hard work to a frontier one. Often a larger saving than any caching work.
- **Effort / reasoning-effort tuning** — on Claude 5 and GPT-5.6, dropping one level frequently holds quality. Test one level below your current setting when migrating.
- **Batch APIs** — 50% off on Anthropic, reduced rates on OpenAI, for anything not latency-sensitive.
- **`N > 1` on Mistral** bills input once for multiple completions, making self-consistency cheap there specifically.
- **Prune the prompt.** OpenAI measured leaner system prompts improving eval scores **10–15%** while cutting tokens **41–66%** and cost **33–67%**. Redundancy costs money *and* quality.
