# Google Image Model Prompting Guide (Nano Banana + Imagen)

## Overview

Google has two image families with genuinely different prompting styles:

- **Nano Banana** (the Gemini image models) — conversational, multi-turn, reference-image-heavy, and capable of legible text. Prompt it in full sentences describing a scene.
- **Imagen** — a classic text-to-image model. Prompt it with subject + context + style, plus photography/art modifiers. Shorter, more keyword-tolerant, 480-token prompt ceiling.

Reach for Nano Banana by default; reach for Imagen when you want a straightforward one-shot render at low cost.

For OpenAI's `gpt-image` family see `gpt-image-prompting-guide.md` in this folder. The deep Nano Banana source clipping lives at `../models/google-nano-banana/nano-banana-2.md`.

Sourced: 2026-07-26

Sources:
- https://ai.google.dev/gemini-api/docs/image-generation#prompt-guide
- https://ai.google.dev/gemini-api/docs/imagen#imagen-prompt-guide
- https://ai.google.dev/gemini-api/docs/pricing

---

## Nano Banana model selection

| Model | ID | Max resolution | Use for | Price |
|---|---|---|---|---|
| Nano Banana 2 Lite | `gemini-3.1-flash-lite-image` | 1K only | Fastest/cheapest, high volume, drafts | $0.0336 / 1K image |
| Nano Banana 2 | `gemini-3.1-flash-image` | up to 4K | **Default workhorse** | $0.067 / 1K image |
| Nano Banana Pro | `gemini-3-pro-image` | up to 4K | Complex compositions, legible styled text, interleaved text+image output | $0.134 / 1K–2K |
| Nano Banana (2.5) | `gemini-2.5-flash-image` | — | Legacy | — |

**Resolutions:** 512px (0.5K), 1K, 2K, 4K.
**Aspect ratios:** 1:1, 3:2, 2:3, 3:4, 4:3, 4:5, 5:4, 9:16, 16:9, 21:9.

Capabilities that change what you can prompt for:

- **Up to 14 reference images** (specs vary by model) — the main lever for character and brand consistency.
- **Video-to-image** on Gemini 3.1 Flash: generate stills from a YouTube URL or uploaded video.
- **Thinking is on by default** for complex prompts; interim reasoning images are generated but not billed. Gemini 3.1 Flash exposes `minimal` and `high` thinking levels to trade quality against latency.
- **Interleaved output** on Gemini 3 Pro Image: mixed text-and-image storytelling in one response.
- **Google Search grounding** works for image prompts about current events — e.g. "Make a simple but stylish graphic of last night's Arsenal game."

---

## Nano Banana prompt patterns

Write **descriptive scenes in prose**, not keyword soup. Each use case wants a specific set of elements named:

| Use case | Name these elements |
|---|---|
| **Photorealistic scene** | Shot type, subject details, setting, lighting, camera angle, lens type. *"A photorealistic wide-angle shot of a vibrant coral reef teeming with tropical fish."* |
| **Stylized illustration / sticker** | Artistic style, subject details, visual qualities (bold outlines, cel-shading), color palette, background handling |
| **Text in image** | Image type, brand or concept, the exact text, font style described in words, design aesthetic, color scheme. Use Nano Banana Pro when the text must be legible and styled. |
| **Product mockup / commercial** | Studio setup, lighting configuration (e.g. "three-point softbox setup"), camera angle, surface material (e.g. "polished concrete surface"), focus point |
| **Minimalist / negative space** | Subject placement, background color and texture, where the negative space is and why (usually for overlay text), subtle lighting |
| **Sequential art / storyboard** | Panel count, art style ("gritty, noir art style"), character placement, per-panel scene description. Pass reference images for character consistency. |

---

## Imagen prompt structure

Three foundational elements, in this order:

1. **Subject** — the object, person, animal, or scenery.
2. **Context / background** — where it is and what surrounds it.
3. **Style** — medium, movement, or aesthetic.

Prompt ceiling is **480 tokens**. Start with the core concept and expand across successive attempts rather than writing one maximal prompt.

**Aspect ratios:** 1:1, 4:3, 3:4, 16:9, 9:16.

### Photography modifiers

- **Camera proximity:** close-up, zoomed out
- **Camera position:** aerial, low-angle
- **Lighting:** natural, dramatic, warm, cold
- **Camera settings:** motion blur, soft focus, bokeh, portrait mode
- **Lens:** 35mm, 50mm, fisheye, wide-angle, macro
- **Film:** black and white, Polaroid

### Art and illustration

Name the medium and technique — "a technical pencil drawing", "a charcoal drawing" — or the movement: impressionism, renaissance, pop art.

### Quality keywords

`4K`, `HDR`, `Studio Photo` for photographs; `by a professional`, `detailed` for illustrations.

### Text in Imagen

- Keep embedded text to **25 characters or fewer**.
- Try **two or three distinct phrases** rather than one long string.
- Specify font style **generally** — don't expect precise typeface replication.

---

## Choosing between them

| If you need… | Use |
|---|---|
| Legible, styled text in the image | Nano Banana Pro |
| Character or product consistency across many images | Nano Banana 2 with reference images |
| Multi-turn conversational refinement | Nano Banana (any) |
| 4K output | Nano Banana 2 or Pro |
| A cheap single-shot render from a short prompt | Imagen 4 ($0.02–$0.06/image) |
| Current-events imagery | Nano Banana with Search grounding |
