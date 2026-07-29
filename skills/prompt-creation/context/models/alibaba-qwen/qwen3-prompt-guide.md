# Qwen3 Prompting Guide

## Overview

Distilled guidance for Alibaba's Qwen3 family. The full raw source (with extended examples) is archived at `archive/qwen-Text-to-text prompt guide.md` in this folder.

Sourced: 2026-07-26

Source: https://qwen3lm.com/prompt/

---

## Model variants

Qwen 3.6 (newest), Qwen 3.5, Qwen 3.4, plus the specialized line: **Qwen-Max**, **Qwen-Turbo**, **Qwen-Plus**, **Qwen-VL** (vision), **Qwen-Audio**, **Qwen-Math**, **Qwen-Coder**.

Pick the specialist when the task matches one — Qwen-Math and Qwen-Coder outperform the general models in their domains at lower cost than Qwen-Max.

## Thinking mode

- **Qwen 3.6** has built-in thinking mode, activated with `thinking: true` in the API call.
- Earlier versions: structure step-by-step reasoning with explicit `<thinking>` and `<answer>` XML tags.
- Chat interfaces support `/think` and `/no_think` commands.

When thinking is on, **do not add chain-of-thought scaffolding to the prompt** — the reasoning is internal. When it's off (or on an older variant), "Let's think step by step" is a real 10–30% accuracy lever on reasoning tasks.

## Sampling

| Use case | Temperature | Top-P |
|---|---|---|
| Deterministic — code, math, extraction | 0.0–0.3 | 0.9 |
| Balanced default — chat, analysis | 0.5–0.7 | 0.9 |
| Creative — brainstorming, marketing | 0.8–1.0 | 0.9 |

Set `max_tokens` deliberately every time; leaving it open invites rambling.

---

## Best practices

1. **System prompts are the highest-leverage surface.** Structure them as: role → goal → numbered constraints → output format.
2. **Be specific.** Replace "good" with concrete specs: length, audience, tone, format.
3. **Few-shot beats rules for nuanced patterns.** 2–3 examples is enough.
4. **Chain-of-thought raises accuracy 10–30% on reasoning tasks** when thinking mode is off.
5. **Use delimiters** — XML tags or `---` — to separate instructions from data, especially with long documents.
6. **Run any prompt 3–5 times before judging it.** Single-sample evaluation at nonzero temperature is noise.

## Mistakes to avoid

- Stacking negatives instead of stating the positive action
- Burying the actual task in a long preamble
- Mixing instructions and data without a clear boundary
- Leaving temperature at default for deterministic tasks
- Judging a prompt on a single failure

## Task templates

**Summarization** — specify the artifact list and the limits:
> 1 headline (max 12 words), 3 key takeaways (one sentence each), and a 60-word executive summary.

**Classification** — suppress commentary explicitly:
> Respond with only the label name. No explanation.

**Rewriting** — bound the drift:
> Preserve all facts. Stay within ±15% of the original word count.
