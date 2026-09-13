# GPT-5.5 Prompting Guide

## Overview

GPT-5.5 (`gpt-5.5`, $5 / $0.50 cached / $30 per 1M tokens; `gpt-5.5-pro` at $30 / $180) sits between GPT-5.4 and GPT-5.6. OpenAI's guidance is to treat it as a **new model family, not a drop-in replacement** — prompts tuned on GPT-5.4 typically need edits, mostly deletions.

Use `gpt-5-6-guide.md` for anything new. This guide covers GPT-5.5 specifics and the 5.4 → 5.5 migration.

Sourced: 2026-07-26

Sources:
- https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5
- https://developers.openai.com/api/docs/pricing

---

## Parameters

**`reasoning.effort`** — options `none`, `low`, `medium`, `high`, `xhigh`. The default is now **`medium`** (balanced quality, latency, and cost). Reserve `none` for latency-critical tasks that don't need reasoning.

**`text.verbosity`** — defaults to `medium`. Use `low` for more concise responses.

**Image detail** — `auto`/unset now behaves as `original`, preserving detail up to **10.2M pixels**. Explicit `high` preserves up to 2.5M pixels; `low` resizes more aggressively for context efficiency. Unset is therefore *more* expensive than it used to be on large images — set `low` deliberately when context budget matters more than fidelity.

---

## Prompting guidance

### Prompt for outcomes, not procedure

GPT-5.5 responds better to outcome-first prompts than to step-by-step process guidance. Describe:

> what good looks like, what constraints matter, what evidence is available, and what the final answer should contain.

Then let the model choose the path. Remove the process scaffolding you wrote for GPT-5.4.

### Give it a stopping condition

For research and multi-step tool work, state the check that ends the loop:

```text
After each result, ask: "Can I answer the user's core request now with useful evidence and citations?"
```

### Push tool guidance into tool descriptions

> Put most tool-specific guidance in the tool descriptions themselves: what the tool does, when to use it, required inputs, side effects, retry safety.

This keeps the system prompt lean and makes the guidance available exactly when the model is choosing a tool.

---

## What changed from GPT-5.4

- **More efficient reasoning** — reaches the same quality with fewer tokens.
- **Better with outcome-first prompts**, worse served by step-by-step instructions.
- **More precise tool use on large tool surfaces.**
- **Tone is more polished but can be more direct** — re-check style prompts if your product has a specific voice.
- **Stricter literal instruction interpretation** — it will not generously reinterpret an instruction that says something slightly different from what you meant.

---

## Migration checklist

- [ ] Update the model slug to `gpt-5.5`.
- [ ] Use the **Responses API** for reasoning and tool-calling workflows.
- [ ] Remove unnecessary step-by-step process guidance; restate the prompt in outcome terms.
- [ ] **Drop the current date from your prompt** — the model is UTC-aware.
- [ ] Re-tune `reasoning.effort` from the new `medium` default rather than carrying over a 5.4 value.
- [ ] Decide `image detail` explicitly if you send large images.
- [ ] Re-check tone-sensitive prompts against the new baseline.
