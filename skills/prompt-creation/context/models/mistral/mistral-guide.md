# Mistral Prompting Guide

## Overview

Mistral's current lineup is small and purpose-split: one frontier multimodal model, one efficient hybrid, one OCR service. Their prompting guidance is unusually prescriptive about **what not to ask for** — several of the "avoid" items are things people routinely put in prompts to other models.

Sourced: 2026-07-26

Sources:
- https://docs.mistral.ai/models/model-selection-guide
- https://docs.mistral.ai/models/best-practices/prompt-engineering
- https://docs.mistral.ai/models/best-practices/sampling

---

## Model selection

| Model | ID | Profile | Price (in / out per 1M) | License |
|---|---|---|---|---|
| Mistral Medium 3.5 | `mistral-medium-3-5` | Frontier-class multimodal, optimized for agentic and coding use cases. 128B params. | $1.50 / $7.50 | Modified MIT |
| Mistral Small 4 | `mistral-small-2603` | Hybrid model unifying instruct, reasoning, and coding. 119B total / 6.5B active. | $0.15 / $0.60 | Apache 2.0 |
| OCR 4 | `mistral-ocr-4-0` | OCR with paragraph-level bounding boxes and structural block labels | — | — |

Compare on: pricing, performance, features (chat completions, function calling, structured outputs, transcriptions), context size, licensing, and parameter count. The permissive licensing on Small 4 (Apache 2.0) makes it the pick when self-hosting or fine-tuning rights matter more than peak capability.

**OCR 4 is a genuine differentiator** — paragraph-level bounding boxes and structural block labels mean you get document *layout*, not just text. For document-extraction pipelines, running OCR 4 first and prompting a text model over its structured output beats sending page images to a vision model.

---

## Prompting

**Open with role and task:** "You are a [role], your task is to [task]."

**Structure hierarchically.** Divide the prompt into clear sections. The test: it should be clear to someone with no prior context.

**Use Markdown or XML-style tags** — readable, parsable, and familiar to the model from training data.

**Few-shot by conversation history.** Mistral's recommended form is *artificial user/assistant turns* demonstrating the expected behavior, rather than examples embedded in the system prompt.

**Use structured outputs** to enforce a JSON schema when anything downstream parses the result.

If you can't set a system prompt in your integration, concatenating the system and user prompts is explicitly supported.

### What to avoid

| Avoid | Instead |
|---|---|
| Vague language — "too long", "too short", "interesting", "better" | Define the term concretely |
| Contradictory instructions | Use a decision tree |
| Asking the model to count words | Provide character counts as *input* |
| Generating more than you need | Request only the strictly necessary outputs |
| Numeric rating scales | Worded scales: Very Low / Low / Neutral / Good / Very Good |

The word-counting and numeric-scale items are the two most commonly violated. Both are cases where the model produces a confident number that isn't grounded in anything.

### Classification template

Mistral's documented classification pattern (a bank support router) is worth copying wholesale: enumerate the exact category labels, give a few-shot example per ambiguous pair, and close with "only respond with the category, without any explanations or notes."

---

## Sampling

Mistral exposes `temperature`, `top_p`, `N`, `presence_penalty`, and `frequency_penalty`.

- **`N` (multiple completions):** setting `N > 1` returns several responses for one input, and **input tokens are billed only once** regardless of how many completions you request. This makes self-consistency voting unusually cheap on Mistral. Note `mistral-large-2512` does not support N completions.
- **`temperature`:** must be above 0 to get diverse outputs; Mistral's own sample uses `temperature = 1` for diversity. Lower it for deterministic extraction and classification.
- Consult the live docs for the full per-parameter recommendations — the published page is thin on task-specific temperature/top_p tables compared to other vendors.

### Where this differs from other vendors

Mistral still has a full sampling surface, where Claude 5 and GPT-5.6 have removed or de-emphasized it. When porting a prompt *from* Mistral *to* Claude 5, any behavior you were getting from `temperature` or the penalties has to be re-expressed as instructions. When porting *to* Mistral, cheap `N > 1` sampling is a real technique that isn't available elsewhere at the same price.
