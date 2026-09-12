# Cross-Vendor Model Selection

Choosing the model is part of writing the prompt. A prompt tuned for a frontier model often works on a model a tier down at a fraction of the cost — and a prompt that fails on a small model sometimes just needs a bigger one rather than more instructions.

Sourced: 2026-09-12

Sources:
- https://platform.claude.com/docs/en/about-claude/models/choosing-a-model
- https://platform.claude.com/docs/en/about-claude/pricing
- https://developers.openai.com/api/docs/guides/model-selection
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://docs.z.ai/guides/llm/glm-5.3
- https://developers.openai.com/api/docs/pricing
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing
- https://inference-docs.cerebras.ai/models/choose-a-model
- https://docs.mistral.ai/models/model-selection-guide

---

## The method (both major vendors agree)

**Optimize for accuracy first, then cost and latency.**

1. Set a concrete accuracy target ("90% correct classification"), not a vibe.
2. Build a labeled eval set. This is the highest-value step and the one most often skipped.
3. Implement with a capable model and tune the prompt there.
4. Only then walk down the ladder — smaller model, lower effort, fewer tokens — measuring against the target at each step.

Anthropic offers the mirror-image option: **start efficiency-first** with Haiku 4.5, test thoroughly, and upgrade only where a specific capability gap shows up. Use this when you're prototyping, latency-bound, or running high volume on straightforward tasks.

**Tune effort before switching models.** On Claude 5 and the GPT-5.6/GPT-6 families the effort parameter spans a wider quality-cost range than the gap between adjacent models. Anthropic states this explicitly: "Tuning effort is often a better lever than switching models."

**But re-sweep effort on every model change** — level names are not comparable across models, not even between point releases in the same family. A prompt ported at the same effort level is not a controlled comparison.

### The two long-context cost cliffs

Both are step functions, not gradients, and both are easy to cross without noticing:

| Model | Threshold | Penalty |
|---|---|---|
| `gpt-6-astra` | 272K input tokens | 2× input and cache rates, 1.5× output |
| `gemini-2.5-pro` | 200K tokens | Input $1.25 → $2.50, output $10 → $15 |

Claude bills its 1M window at flat rates — a 900k request costs the same per token as a 9k one. If you are doing long-context work at volume and hovering near either threshold, that flat pricing may beat a cheaper headline rate.

---

## Price comparison (per 1M tokens, input / output)

| Vendor | Model | Input | Output | Notes |
|---|---|---|---|---|
| Anthropic | Claude Fable 5.1 | $10 | $50 | Current top of range; thinking always on; **cache hits bill at 0.025× ($0.25/MTok)**, 4× cheaper than every other Claude model |
| Anthropic | Claude Opus 5 | $5 | $25 | Complex agentic coding, enterprise work |
| Anthropic | Claude Sonnet 5 | $2 | $10 | Best speed-to-intelligence ratio. The scheduled 2026-09-01 rise to $3/$15 was **cancelled** |
| Anthropic | Claude Haiku 4.5 | $1 | $5 | Fastest; 200k context |
| OpenAI | `gpt-6-astra` | $10 | $50 | **Flagship.** 1.05M context. **2× input / 1.5× output above 272K input tokens** |
| OpenAI | `gpt-5.6-cyber` | $12.50 | $75 | Security-focused variant |
| OpenAI | `gpt-5.6-sol` | $4 | $20 | Top of the 5.6 family; `gpt-5.6` alias resolves here |
| OpenAI | `gpt-5.6-terra` | $2 | $12 | OpenAI's documented "smaller option" vs Astra |
| OpenAI | `gpt-5.6-luna` | $0.20 | $1.20 | High-volume, efficient — cheapest OpenAI text model |
| OpenAI | `gpt-5.3-codex` | $1.75 | $14 | Agentic coding harnesses |
| Google | `gemini-3.8-flash` | $0.75 | $3.75 | **Gemini flagship**; long-horizon software engineering |
| Google | `gemini-3.7-flash` | $0.75 | $3.75 | |
| Google | `gemini-3.6-flash` | $0.75 | $3.75 | |
| Google | `gemini-3.5-flash` | $1.50 | $9.00 | Agentic and coding work |
| Google | `gemini-3.1-flash-lite` | $0.25 | $1.50 | |
| Google | `gemini-2.5-flash-lite` | $0.10 | $0.40 | Cheapest listed anywhere here |
| Google | `gemini-2.5-pro` | $1.25 / $2.50 | $10 / $15 | **Price steps above 200k tokens** |
| Mistral | `mistral-medium-3-5` | $1.50 | $7.50 | Modified MIT license |
| Mistral | `mistral-small-2603` | $0.15 | $0.60 | Apache 2.0 |

Cached-input rates run 0.1× (Anthropic, OpenAI) — see `caching-and-cost.md`. Batch processing is 50% off on Anthropic.

⚠️ **Headline rates aren't comparable across vendors** because tokenizers differ. Claude 4.7+ produces ~30% more tokens for the same text than Claude 4.6 did. Compare on *your* content using each vendor's token counter, not on the price table.

---

## Choosing by task shape

| Task | Reach for | Why |
|---|---|---|
| Multiday autonomous agent runs | Claude Fable 5 | Built for long-horizon autonomy; sustains parallel subagents |
| Complex agentic coding, large refactors | Claude Opus 5, `gpt-5.6-sol` | Both target this directly |
| High-volume classification / extraction | Haiku 4.5, `gpt-5.6-luna`, `gemini-2.5-flash-lite`, `mistral-small-2603` | 10–50× cheaper, usually sufficient |
| Very long context at volume | Gemini 3.x Flash, Claude (1M at flat rate) | Avoid 2.5 Pro's 200k price step |
| Document OCR with layout | `mistral-ocr-4-0` | Paragraph-level bounding boxes and structural block labels |
| Vision-heavy inspection | Claude Opus 5, GPT-5.6 with `detail: original` | Both strong; give the model a crop tool |
| Image generation with legible text | Nano Banana Pro, `gpt-image-2` | |
| Cheap one-shot image render | Imagen 4 ($0.02–$0.06/image) | |
| Self-consistency voting | Mistral (`N > 1`) | Input billed once for multiple completions |
| Open weights / self-hosting | `mistral-small-2603` (Apache 2.0), Gemma 4, GLM-5.3 (MIT-style) | |
| Latency-critical inference | Cerebras-hosted open models | Speed is the platform's premise |

---

## Open-weight models (Cerebras hosting)

| Tier | Models |
|---|---|
| Large (>200B) | Kimi K2.6, GLM 5.1, GLM 4.7, MiniMax M2.5 |
| Medium (20B–200B) | Gemma 4 31B, Qwen3 32B, GPT OSS 120B |

Cerebras publishes direct substitution mappings for teams leaving closed platforms:

| Coming from | Try |
|---|---|
| Claude Opus | Kimi K2.6, GLM 5.1 |
| Claude Haiku | Gemma 4 31B, GPT OSS 120B |
| GPT 5.5 | Kimi K2.6, GLM 5.1 |
| Gemini Pro | Kimi K2.6, GLM 5.1 |

Treat these as starting points for an eval, not equivalences.

---

## What changes in the prompt when you switch

Switching model families is not a slug change. The things that most often break:

| Difference | Affected |
|---|---|
| **Sampling parameters removed** | Claude 5 / 5.1 and Sonnet 5 reject `temperature`/`top_p`/`top_k` (400 error). Gemini, Mistral, GLM, Qwen all still accept them — though Google now *strongly* recommends leaving them at default on Gemini 3.x. Any behavior you got from temperature must become an instruction. |
| **Prefill removed** | Claude 4.6+ rejects assistant prefill. Use structured outputs. |
| **Few-shot philosophy** | Google says always include few-shot examples; OpenAI's GPT-5.6 guidance says remove examples unless they encode a product requirement. Don't port either belief blindly. |
| **CoT scaffolding** | Actively harmful on reasoning-native models (GPT-6 Astra and GPT-5.6 with reasoning on, Claude with adaptive thinking, GLM-5.3, Qwen3 thinking mode, Gemma 4 thinking). Still a 10–30% lever on non-thinking models. **Cannot be turned off at all** on GPT-6 Astra (no `none`) or GLM-5.3 (thinking mandatory). |
| **Effort semantics** | Claude and OpenAI both have real graduated effort, but **level names don't transfer between models** — re-sweep every time. Defaults differ in direction too: Claude and OpenAI default mid-range and you step up; **GLM-5.3 defaults to `max`** and you step down. **Gemma 4's `low`/`medium`/`high` are currently equivalent** — don't build cost tiers on them. |
| **Verbosity defaults** | Gemini 3 defaults concise (ask for detail); Claude Opus 5 defaults long (ask for brevity). Opposite corrections. |
| **Formatting defaults** | Claude Fable 5.1 *under*-formats in chat — the reverse of every model before it. Anti-bullet rules ported from older prompts make it worse. |
| **History mutability** | Claude Fable 5.1 requires **append-only** conversation history; editing earlier turns returns a 400. Harnesses that inject/remove per-turn reminders or summarize in place must be reworked before porting. |
| **Effort/cache interaction** | Changing effort mid-conversation invalidates the cache on OpenAI **through GPT-5.6**, but **preserves it on GPT-6 Astra**. |
| **Prompt format** | Gemma 4 needs literal control tokens (`<|turn>`, roles `system`/`user`/`model`). Hosted models don't. |
| **Structured output** | Available on all major vendors, but the parameter names differ. Prefer it over prompt-engineering a JSON format wherever it exists. |
| **Tokenizer** | Claude 4.7+ ≈ 30% more tokens. Re-baseline `max_tokens` or expect truncation. |

---

## Sanity check before recommending a model

1. Does the task need frontier capability, or is that an assumption?
2. Has an eval set been built, or is "it seemed better" the evidence?
3. Is effort/reasoning-effort already tuned on the current model?
4. Is caching in place, and is the prompt ordered for it?
5. Would tiering — cheap model first, escalate on low confidence — beat picking one model?
6. Do the licensing or data-residency constraints rule anything out before capability even matters?
