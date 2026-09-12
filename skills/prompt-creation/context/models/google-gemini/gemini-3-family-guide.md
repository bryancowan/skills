# Gemini 3 Family Guide

## Overview

Google's current text lineup is the **Gemini 3.x Flash** family. The flagship is **`gemini-3.8-flash`** — Google's "most intelligent Flash model, engineered for long-horizon software engineering." There is still no Gemini 3 Pro *text* model in the stable list; `gemini-2.5-pro` remains the only Pro entry, and it is now more expensive than the entire 3.x Flash line. Image, video, audio, and music each have their own model families.

Sourced: 2026-09-12

Sources:
- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing

Companion files: `gemini-prompting-strategies.md` (how to write the prompt), `gemini-file-prompting.md` (images/video/audio/docs as input), `../../image-generation/google-image-models-guide.md` (image output).

---

## Text models

| Model | Input / Output per 1M tokens | Cache | Pick it for |
|---|---|---|---|
| `gemini-3.8-flash` | $0.75 / $3.75 | $0.15 + $1.00/hr storage | **Flagship. Default choice.** Most intelligent Flash model; built for long-horizon software engineering |
| `gemini-3.7-flash` | $0.75 / $3.75 | $0.15 + $1.00/hr | Prior release at the same price — no reason to pick it over 3.8 for new work |
| `gemini-3.6-flash` | $0.75 / $3.75 | $0.15 + $1.00/hr | Balanced |
| `gemini-3.5-flash` | $1.50 / $9.00 | $0.15 + $1.00/hr | Agentic and coding work — note it costs **2× the 3.8 rate**; verify the gap on your evals before paying it |
| `gemini-3.5-flash-lite` | $0.30 / $2.50 | $0.03 + $1.00/hr | Fast, cost-effective |
| `gemini-3.1-flash-lite` | $0.25 / $1.50 | — | Frontier performance at low cost |
| `gemini-2.5-pro` | $1.25 / $10.00 (≤200k); $2.50 / $15.00 (>200k) | $0.125–$0.25 + $4.50/hr | Most advanced reasoning; note the long-context price step |
| `gemini-2.5-flash` | $0.30 / $2.50 | $0.03 + $1.00/hr | Price-performance on reasoning tasks |
| `gemini-2.5-flash-lite` | $0.10 / $0.40 | $0.01 + $1.00/hr | Cheapest, fastest |

**Watch the 200k boundary on 2.5 Pro** — input and output rates both jump. And note the headline comparison has now inverted: at $0.75/$3.75, `gemini-3.8-flash` is **cheaper than 2.5 Pro at every context length**, with flat pricing. The old "pay more for Flash to get flat pricing" trade no longer exists — 3.x Flash is simply cheaper.

The current 3.x Flash prices are promotional **through 2026-12-31**. Re-check before quoting them for a long-lived budget.

Gemini context caching is billed as a **storage rate per hour** on top of a discounted token rate, unlike Anthropic's and OpenAI's write-once multipliers. Cache only if the content will be reused within the storage window you're paying for.

## Other modalities

| Family | Models | Price |
|---|---|---|
| Image generation | Nano Banana 2 (`gemini-3.1-flash-image`), Nano Banana 2 Lite (`gemini-3.1-flash-lite-image`), Nano Banana Pro (`gemini-3-pro-image`), Nano Banana (2.5 family), Imagen 4 | NB2 $0.067/1K image; NB2 Lite $0.0336/1K; NB Pro $0.134/1K–2K; Imagen 4 $0.02–$0.06 per image |
| Video generation | **Veo 3.1**, Veo 3.1 Lite, Gemini Omni Flash (preview, conversational video gen/editing) | $0.05–$0.60 per second |
| Audio / speech | Gemini 3.1 Flash Live (`gemini-3.1-flash-live-preview`, audio-to-audio), Gemini 3.1 Flash TTS (`gemini-3.1-flash-tts-preview`), **Gemini 3.5 Transcribe (`gemini-3.5-transcribe`)**, Gemini 2.5 Flash Live, Gemini 2.5 Flash TTS | TTS $0.50 text in / $10.00 audio out per 1M |
| Music | Lyria 3 Pro, Lyria 3 Clip, Lyria RealTime | — |
| Embeddings | Gemini Embedding 2 (multimodal), Gemini Embedding | Text $0.20, image $0.45, audio $6.50, video $12.00 per 1M |

> The Veo guide in `context/video-generation/google-veo-prompt-guide.md` predates Veo 3.1 — its craft advice (shot language, camera moves, audio cues) still holds, but verify model names and parameters against current docs.

---

## Gemini 3 prompting behavior

These are the model-family behaviors that change how you write the prompt. Full technique detail is in `gemini-prompting-strategies.md`.

- **Gemini 3 defaults to concise output.** If you want detail or a conversational register, ask for it explicitly — this is the opposite of the tuning most Gemini 2.x prompts needed.
- **Use direct language.** Persuasive framing and hedged phrasing ("it would be great if you could…") measurably underperform a plain statement of the goal.
- **Structure with XML tags or Markdown headings, consistently:** `<context>`, `<task>`, `<constraints>`.
- **Put critical instructions first** — role definitions, behavioral constraints, and format requirements belong at the top or in system instructions.
- **Long context: all context first, question last**, with a bridging phrase like "Based on the information above…".
- **Define ambiguous terms explicitly.** The model will not ask what you meant by "recent" or "high quality."
- **Multimodal inputs are equal-class.** Text, image, audio, and video can be interleaved; reference each one clearly rather than saying "the image."
- **Few-shot examples are strongly recommended**, and this is a genuine difference from Claude and GPT guidance: Google's docs say prompts without few-shot examples "are likely to be less effective." Use 2–4 varied examples with consistent formatting.

### Gemini 3 Flash specifics

Two clauses worth adding when factual currency matters:

```text
Remember it is 2026 this year.
```
```text
Your knowledge cutoff date is January 2025.
```

For retrieval-grounded assistants, use a strictly-grounded instruction that limits responses to the provided context only.

### Sampling parameters

Unlike the current Claude and GPT families, **Gemini still accepts sampling parameters**: `temperature`, `top_k`, `top_p` (default 0.95), `max_output_tokens`, and stop sequences.

But Google's current wording is stronger than "recommends": they **strongly recommend keeping them at their default values for Gemini 3.x**, and warn that changing them can cause unexpected behavior. Treat Gemini 3.x as effectively parameter-free like Claude and GPT-6 unless you have an eval showing otherwise — the fact that the knobs still exist is not an invitation. Roughly 4 characters per token; 100 tokens ≈ 60–80 words.

If a safety filter produces a fallback response, raising temperature sometimes yields a substantive answer.

### Tools

Enable **Google Search grounding** for current or obscure facts, and **code execution** for arithmetic and calculation — Gemini's arithmetic is materially more reliable through code execution than in-context.

### Agentic system instructions

Google frames agent steering along three axes; set each explicitly in system instructions rather than leaving them to default:

- **Reasoning and strategy** — decomposition depth, diagnosis thoroughness, how exhaustive information gathering should be
- **Execution and reliability** — adaptability to new data, persistence and error recovery, risk assessment for read vs. write operations
- **Interaction and output** — how to handle ambiguity and permission, verbosity, precision requirements
