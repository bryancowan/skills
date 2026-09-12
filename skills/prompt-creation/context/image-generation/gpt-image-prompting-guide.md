# GPT Image Models Prompting Guide

## Overview

OpenAI's `gpt-image` family generates and edits production-quality visuals: photorealism, text-in-image, infographics, UI mockups, logos, ads, compositing, and identity-sensitive edits. This guide covers model selection, settings, prompt structure, and condensed use-case patterns. For the full source with worked Python examples for every use case, see `context/image-generation/gpt-image-models-full-guide.md`.

**`gpt-image-2.5` is the recommended default for new builds**, in two variants: `gpt-image-2.5-flare` (speed) and `gpt-image-2.5-sunburst` (quality). Both improve on `gpt-image-2` in **precise editing and subject preservation**, add `xhigh`/`max` quality, add **transparent background support** (which `gpt-image-2` lacks), and raise the resolution ceiling to 3840px per edge.

---

## Key Principles

1. **Define the result first, then structure the prompt in labeled sections**: `scene` → `subject` → `details` → `constraints`. Name the subject and its intended use (product photograph, advertisement, diagram) — that sets the mode and level of polish — then specify composition, aspect ratio, and placement constraints.
   **The format is your choice.** Short prompts, descriptive paragraphs, JSON-like structures, instruction lists, and tags all express the same intent to these models. OpenAI's guidance is to optimize for *maintainability and readability*, not for special syntax. Pick one shape and keep it consistent across a prompt library.
2. **Separate what changes from what stays.** For edits, say "change only X" + "keep everything else the same," and **restate the preserve list on every iteration** to prevent drift.
3. **Be concrete about materials, medium, and composition.** Vague aesthetic words ("beautiful," "professional," "modern") underperform concrete descriptors (medium, era, lighting, lens, texture).
4. **Iterate instead of overloading.** Start from a clean base prompt and refine with small single-change follow-ups ("make lighting warmer," "remove the extra tree").
5. **Match quality to the task.** Use `medium` or above whenever the image must render small text, dense information, or multiple fonts; `high` and above for fine material detail and identity-sensitive edits.
6. **Know the hard limit on edits.** Repeated edits still alter details you didn't ask to change, on 2.5 as on 2. Prompting reduces drift; it does not eliminate it. **If a region must be pixel-identical, composite it back in — don't prompt for it.**

---

Sourced: 2026-09-12

Sources:
- https://developers.openai.com/api/docs/guides/image-prompting?model=gpt-image-2.5
- https://developers.openai.com/api/docs/guides/image-prompting?model=gpt-image-2
- https://developers.openai.com/api/docs/models/gpt-image-2.5-sunburst
- https://developers.openai.com/api/docs/guides/image-generation
- https://developers.openai.com/api/docs/guides/tools-image-generation
- https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide
- https://developers.openai.com/api/docs/pricing

For Google's image models (Imagen, Nano Banana 2 / Pro / Lite), see `google-image-models-guide.md` in this folder.

---

## Model Selection

Verified current 2026-09-12:

| Model | Quality levels | Resolutions | Use for |
|---|---|---|---|
| **`gpt-image-2.5-sunburst`** | low/medium/high/**xhigh**/**max**/auto | Up to 3840px/edge (see constraints) | **Default for demanding work.** Highest quality; best precise editing and subject preservation. |
| **`gpt-image-2.5-flare`** | low/medium/high/xhigh/max/auto | same | **Default when speed matters.** Quality comparable to `gpt-image-2` at lower latency. |
| `gpt-image-2` | low/medium/high/auto | Up to 3840px/edge | Existing integrations. Superseded but supported. **No transparency.** |
| `gpt-image-1.5` | low/medium/high | 1024×1024, 1024×1536, 1536×1024, auto | Existing validated workflows during migration. |
| `gpt-image-1` | low/medium/high | same as 1.5 | Legacy compatibility only. |
| `gpt-image-1-mini` | low/medium/high | same as 1.5 | Cost/throughput priority: large batches, previews, drafts. |

**Choosing between the 2.5 variants** — OpenAI's stated order: start with **Sunburst** when quality requirements are demanding; start with **Flare** when speed is the priority. If Sunburst succeeds and latency is the remaining problem, *then* test Flare on the same prompt. Don't start at Flare and work up — you won't know whether a failure is the prompt or the model.

**Migrating from `gpt-image-2`:** keep prompts as they are and re-measure quality, latency, and retry rates first. Two things change materially: `xhigh`/`max` are newly available above `high`, and transparency now works without dropping back to the 1.x family.

`input_fidelity` is a no-op on `gpt-image-2` and 2.5 — image inputs are always processed at high fidelity. Omit it. It still functions on `gpt-image-1.5`/`-1`/`-mini`.

### Quality
- `low` — latency and volume.
- `medium` — balanced; minimum for small or dense text.
- `high` — close-up portraits, identity-sensitive edits, dense text, fine material detail.
- `xhigh` / `max` — **2.5 only.** Reach for these on the hardest renders, then verify the gain is real; as with reasoning effort, more is not automatically better.
- `auto` — default; lets the model pick.

### Sizing (gpt-image-2 and 2.5)
Any `size` is allowed if **all** hold: both edges multiples of 16; max edge ≤ 3840px; long:short ratio ≤ 3:1; total pixels between 655,360 and 8,294,400.

| Label | Resolution |
|---|---|
| Square (default) | 1024×1024 |
| HD portrait | 1024×1536 |
| HD landscape | 1536×1024 |
| Large square | 2048×2048 |
| Wide | 2048×1152 |
| 2K / QHD (reliability ceiling) | 2560×1440 |
| 4K / UHD (experimental) | 3840×2160 / 2160×3840 |

**Above 2560×1440 (3,686,400 px) is explicitly experimental** — variability rises. Don't ship 4K output without checking a real sample set.

### Output format and background
`PNG` (default), `JPEG`, or `WebP`; for JPEG/WebP set `output_compression` (0–100).

`background`: `auto`, `opaque`, or `transparent`. **Transparency works on `gpt-image-2.5` (both variants)** with PNG or WebP — this is new. `gpt-image-2` does **not** support transparency; on that model you must fall back to `gpt-image-1.5`/`-1`/`-mini`.

### Cost
`gpt-image-2.5` token rates **match `gpt-image-2`**: text input $5.00 / 1M ($1.25 cached), image input $8.00 / 1M ($2.00 cached), image output $30.00 / 1M. Note that OpenAI's GPT Image 2 token calculator does **not** estimate 2.5 consumption — measure it. Image *inputs* on the GPT-5.6 family default to `original` detail (no downscaling), which raises token counts on large references — set `detail: "low"` when the reference only needs to be recognized, not read.

---

## Images API vs. the `image_generation` tool

Two ways to reach the same models:

- **Images API** — you call the endpoint directly. Use when image generation is the whole job and you control every parameter.
- **`image_generation` tool in the Responses API** — the model decides when and how to generate or edit images as part of a conversation. The support list last verified (2026-07) was `gpt-5.5`, `gpt-5.4-mini`, `gpt-5.2`, `gpt-5`, `o3`, `gpt-4.1`, `gpt-4o`, `gpt-4o-mini`. **Whether `gpt-6-astra` and the GPT-5.6 family carry the tool was not re-verified in the 2026-09 refresh — check the current docs before promising it.** (Astra's own model page does list image generation among its supported hosted tools, which suggests the list above is simply stale.)

Tool-specific behavior worth prompting around:

- **Parameters** mirror the Images API (`size`, `quality`, `format`, `compression`, `background`) plus `action`: `auto`, `generate`, or `edit`. `auto` lets the model pick based on the prompt.
- **Multi-turn editing** works by referencing `previous_response_id` or an image ID in the input array — so "now make it look realistic" refines the prior image instead of starting over.
- **`partial_images`** (1–3) streams intermediate renders for perceived latency.
- **Use action-oriented verbs.** "Draw…" and "edit…" outperform general directives. To combine images, frame it as an edit: *"edit the first image by adding this element from the second image."*
- The tool auto-optimizes your prompt text (a "revised prompt"), so extremely terse prompts still work — but explicit constraints still beat letting it guess.

---

## Specific Techniques

- **Photorealism:** Include the word **"photorealistic"** to engage the model's photorealistic mode. Phrases like "real photograph," "taken on a real camera," "iPhone photo" also help. Use photography language (lens, lighting, framing) and ask for real texture (pores, wrinkles, fabric wear). Avoid words implying studio polish/staging. Detailed camera specs are interpreted loosely — use for look/composition, not exact simulation. Use `quality: "high"` when detail matters.
- **Text in images:** Put literal text in **quotes** or **ALL CAPS**; specify font style, size, color, placement as constraints. For brand names / uncommon spellings, spell letter-by-letter. Use `medium`/`high` for small or dense text.
- **Composition:** Specify framing/viewpoint (close-up, wide, top-down), angle (eye-level, low-angle), and lighting/mood. Call out placement ("logo top-right," "subject centered with negative space on left"). For wide/cinematic/low-light/neon scenes, add scale, atmosphere, and color so the model doesn't trade mood for surface realism.
- **People:** Describe scale, body framing, gaze, and object interactions ("full body, feet included," "looking down at the book, not the camera," "hands gripping the handlebars").
- **Multi-image inputs:** Reference each input by **index and description** ("Image 1: product… Image 2: style reference…") and how they interact ("apply Image 2's style to Image 1"; "put the bird from Image 1 on the elephant in Image 2").
- **Surgical edits:** When an edit must be precise, also forbid drift in saturation, contrast, layout, arrows, labels, camera angle, and surrounding objects.
- **Variations:** Set `n` to generate multiple options in one call (useful for logos).

---

## Use-Case Patterns

**Generate (text → image):**

| Use case | Prompt approach | Quality |
|---|---|---|
| Infographic | Describe the flow/components and intended audience; "technically and visually" | high for dense layouts |
| Translation in image | "Translate the text to X. Do not change any other aspect"; preserve typography/layout | medium |
| Photorealism | Prompt as a real photo being captured; lens/lighting/framing + real texture; no glamorization | medium–high |
| World knowledge | Give place + date and let the model infer context (e.g., Bethel NY, Aug 1969 → Woodstock) | medium |
| Logo | Brand personality + use case; "clean, original, strong silhouette, balanced negative space, scalable"; plain bg, no watermark; use `n=4` | medium |
| Ad / creative | Write a creative brief: brand, audience, concept, composition, exact tagline (quoted); let the model make taste decisions | medium |
| Comic strip | Define narrative as one clear visual beat per panel; concrete, action-focused | medium |
| UI mockup | Describe the product as if it already exists: layout, hierarchy, spacing, real elements; avoid concept-art language; optional device frame | medium |
| Scientific / educational | Instructional-design brief: audience, objective, required labels, constraints; flat icon system, clear arrows, white space; list required components | high |
| Slides / charts | Artifact spec: name deliverable, define canvas/hierarchy, supply real numbers/labels; readable type, no clutter; landscape | high |

**Edit (text + image → image):**

| Use case | Prompt approach |
|---|---|
| Style transfer | State what stays (palette, texture, brushwork) and what changes (new subject); hard constraints to prevent drift |
| Virtual try-on | Lock face/body/pose/hair/expression; change **only** garments; realistic fit + matched lighting/shadows; no added accessories/text |
| Sketch → render | "Preserve exact layout, proportions, perspective"; add plausible materials/lighting; "do not add new elements or text" |
| Product mockup | Extract to plain opaque background; crisp silhouette, no halos; preserve geometry + label legibility; light polish + subtle contact shadow only |
| In-image marketing text | Exact copy in quotes, verbatim, no extra characters; placement + font style; ensure text appears once and legible |
| Lighting / weather | Change only environmental conditions (light, shadows, atmosphere, precipitation, wetness); preserve identity/geometry/camera/placement |
| Object removal | "Remove X. Do not change anything else." On `gpt-image-2`/2.5 that is the whole lever — `input_fidelity` does nothing there. On the 1.x family, add `input_fidelity: "high"`. |
| Person compositing | Grounded photographic look (natural light, no cinematic grading); lock subject likeness; higher input fidelity for larger edits |
| Interior swap | Swap one object; preserve camera angle, room lighting, floor shadows, surrounding objects; photorealistic contact shadows |
| Character consistency | Establish a reusable "character anchor" (appearance, proportions, outfit, tone); reuse via edit for each new scene; "do not redesign the character" |

---

## Common Failure Modes

| Problem | Fix |
|---|---|
| Text in image is blurry or misspelled | Switch to `quality: "high"`; put text in quotes; spell tricky words letter-by-letter |
| Identity drifts across edits | State "Preserve [specific features] exactly" in **every** follow-up. `gpt-image-2.5` improves subject preservation over `gpt-image-2`, so switching model helps more than any parameter; `input_fidelity: "high"` applies only to the 1.x family. If a region must be pixel-identical, composite it. |
| Composition changes unexpectedly | Name what must stay the same before describing what should change |
| Fine textures look flat | Add material descriptor ("hand-stitched," "brushed," "matte"); consider `quality: "high"` |
| Result looks generic | Replace vague terms ("professional," "modern") with concrete references (medium, era, lighting setup) |
| Prompt too tangled to debug | Start from a clean base prompt and refine with small, single-change follow-ups |
