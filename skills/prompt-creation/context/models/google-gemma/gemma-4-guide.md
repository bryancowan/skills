# Gemma 4 Prompting Guide

## Overview

Gemma 4 is Google's open-weight family. Unlike the hosted Gemini models, prompting Gemma often means **writing the chat template yourself** — the control tokens are part of the prompt, and getting them wrong is the most common cause of bad output.

This guide covers the Gemma 4 prompt format, thinking mode, and the hosted `gemma-4-31b` deployment on Cerebras (image inputs and `reasoning_effort`).

Sourced: 2026-07-26

Sources:
- https://ai.google.dev/gemma/docs/core/prompt-formatting-gemma4
- https://ai.google.dev/gemma/docs/capabilities/thinking
- https://inference-docs.cerebras.ai/capabilities/reasoning#gemma-4:-reasoning_effort
- https://inference-docs.cerebras.ai/capabilities/image-inputs

---

## Prompt format

Gemma 4 uses paired control tokens for turn structure:

```
<|turn>system
You are a helpful assistant.<turn|>
<|turn>user
Hello.<turn|>
<|turn>model
Response here<turn|>
```

Roles are `system`, `user`, and `model` (**not** `assistant`).

### Multimodal tokens

| Token pair | Purpose |
|---|---|
| `<|image>` / `<image|>` | Image embeddings |
| `<|audio>` / `<audio|>` | Audio embeddings |
| `<|image|>` | Placeholder marking where an image is inserted |
| `<|audio|>` | Placeholder marking where audio is inserted |

Inline usage: `"Describe this image: <|image|>"`

### Function calling tokens

| Token pair | Purpose |
|---|---|
| `<|tool>` / `<tool|>` | Tool definitions |
| `<|tool_call>` / `<tool_call|>` | The model's tool requests |
| `<|tool_response>` / `<tool_response|>` | Tool execution results |

String values inside structured data are wrapped with `<|"|>`, e.g. `location:<|"|>London<|"|>`.

---

## Thinking mode

Activate by including `<|think|>` in the system instruction, or by passing `enable_thinking=True` to `apply_chat_template()` — the processor inserts the correct tokens for you. Prefer the processor; hand-writing thinking tokens is where most integration bugs come from.

**Output format varies by model size:**
- **E2B / E4B:** thinking wrapped in `<|think|>` tokens within system messages.
- **12B / 26B / 31B:** `<|channel>thought` tags; these models emit *empty* thinking tokens even when thinking is off, to stabilize output shape.

`parse_response()` returns a dict with `role`, `thinking`, `content`, and `tool_calls`.

**Multi-turn rule that matters:** strip generated thoughts from previous turns before passing history back. The exception is function calling *within* a single turn — do **not** strip thoughts between function calls in the same turn.

**No special prompting is required for thinking.** The model already analyzes ambiguous requests, considers multiple interpretations, produces structured reasoning, and self-corrects. Adding "think step by step" is redundant. This holds for both text-only and image+text tasks.

---

## `reasoning_effort` on `gemma-4-31b` (Cerebras)

| Value | Behavior |
|---|---|
| `"none"` | Reasoning disabled — **this is the default** |
| `"low"` / `"medium"` / `"high"` | All enable reasoning |

Important caveat: **the three active levels are currently equivalent.** They exist for cross-model API compatibility, not graduated control. Do not build cost tiers around them the way you would with Claude's `effort` or OpenAI's `reasoning.effort`.

```python
response = client.chat.completions.create(
    model="gemma-4-31b",
    messages=[{"role": "user", "content": "Solve this step by step."}],
    reasoning_effort="medium"
)
```

Gemma 4 does **not** support the `raw`, `hidden`, `clear_thinking`, or `preserve_thinking` reasoning formats.

For comparison on the same platform: GPT-OSS-120B uses low/medium(default)/high with real graduation; GLM 4.7 supports `reasoning_effort="none"` plus a deprecated `disable_reasoning` boolean retiring 2026-07-21.

---

## Image inputs (Cerebras, public preview)

Base64-encode and pass as a data URI in an `image_url` object inside the user message `content` array:

```json
"image_url": { "url": "data:image/png;base64,{base64_image}" }
```

| Limit | Value |
|---|---|
| Formats | PNG, JPEG |
| Max payload per request | 10 MB |
| Images per request | 2 (free trial), 10 (developer/enterprise shared) |
| Max image tokens | **280 per image** |

Token count depends on *processed* dimensions, not file size: images are scaled to ~645,120 pixels and rounded to the nearest multiple of 48. **Small images can cost more tokens than expected** because they get upscaled.

### Security note for image prompts

Text embedded in an image can influence model behavior. Treat image content from untrusted sources as adversarial input — the model may transcribe embedded text verbatim, including instructions or harmful content. Validate before using downstream. See `references/guardrails.md` for the broader injection-hardening pattern.

---

## Practical prompting notes

- **The 280-token image ceiling means Gemma 4 reads images coarsely.** It is fine for scene understanding and classification; do not expect reliable OCR of dense documents.
- **Keep system instructions short.** Gemma models are smaller than the hosted frontier families, and long, layered system prompts degrade instruction following faster.
- **Prefer explicit output schemas over implied ones.** Ask for JSON with named fields rather than "a structured summary."
- **Use few-shot examples liberally.** Unlike GPT-5.6, smaller open-weight models benefit substantially from 2–4 examples.
