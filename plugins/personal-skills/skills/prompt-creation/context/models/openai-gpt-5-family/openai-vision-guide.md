# OpenAI Vision & Image-Input Prompting Guide

## Overview

This covers **images going in** (vision, document understanding, screenshots, charts). For images coming out, see `context/image-generation/`.

The change that matters most in the GPT-5.6 generation: **`detail` now defaults to `original`**, meaning images are no longer downscaled by default. Fidelity is better; token counts and latency are higher. On image-heavy workloads this is a cost decision you should make deliberately rather than inherit.

Sourced: 2026-07-26

Sources:
- https://developers.openai.com/api/docs/guides/images-vision
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/guides/latest-model?model=gpt-5.5

---

## Passing images

Three methods: a fully qualified **URL**, **base64** data URL, or a **file ID** from the Files API created with `purpose: "vision"`.

Limits: up to **1,500 image inputs per request**, **512 MB total payload**. Formats: PNG, JPEG, WEBP, non-animated GIF. Images must have no watermarks or logos, no NSFW content, and be clear enough for a human to understand.

## `detail` levels

| Value | Behavior |
|---|---|
| `low` | 512×512 — fastest and cheapest |
| `high` | Standard high-fidelity understanding (preserves up to ~2.5M pixels on GPT-5.5) |
| `original` | Full resolution, for large, dense, or spatially sensitive images (GPT-5.6 family; up to ~10.2M pixels on GPT-5.5) |
| `auto` | Automatic — **equals `original` on GPT-5.6 models** |

Practical rule: use `low` when the model only needs to *recognize* what's in the image, `high` or `original` when it needs to *read* the image (small text, dense tables, schematics, UI inspection).

## Token cost model

- **Patch-based models** (GPT-5.5, GPT-5.4): the image is divided into 32×32px patches; cost is patch count × a model-specific multiplier (1.62–2.46×).
- **Tile-based models** (GPT-4o, GPT-4.1, o-series): a base charge (70–85 tokens) plus per-512px-tile cost (140–170 tokens per tile).

Use OpenAI's pricing calculator for exact numbers — the multiplier differences between models are large enough to change which model is cheapest for a vision-heavy workload.

---

## Known weak spots

Prompt defensively around these; they are documented limitations, not prompt failures:

- Medical imaging analysis
- Non-Latin script text
- Small text at low `detail`
- Rotated or flipped content
- Spatial reasoning tasks
- Panoramic and fisheye images
- Precise object counting
- CAPTCHAs (blocked for safety)
- Graphs with unusual color or style conventions — the model may misread the encoding

---

## Prompting patterns for vision tasks

**Ask for extraction before interpretation.** On dense documents and charts, have the model transcribe the relevant region first, then reason over the transcription. This catches misreads before they propagate into conclusions.

**Name the region.** "In the top-right panel…" or "the third row of the table" beats "in the image" when several things compete for attention.

**State the schema for extraction tasks.** Structured outputs or an explicit JSON schema is far more reliable than asking for "the data from this table."

**Give the model a crop or zoom tool when accuracy matters.** Iterative crop-and-verify consistently outperforms a single high-detail pass on fine-grained visual work, and is usually cheaper than raising `detail` across the board.

**Ask for uncertainty explicitly.** "If a value is illegible, write `unreadable` rather than guessing" is the single most effective anti-hallucination instruction for document extraction.

**For counting, ask for an enumeration, not a number.** "List each item you see with a short description, then give the total" is more accurate than "how many items are there?"

**Send images at a resolution matched to the task.** For computer-use style screenshot work, 1080p is the documented sweet spot for performance vs. cost; 720p or 1366×768 for cost-sensitive workloads.
