# GPT Image Models Prompting Guide

## Overview

OpenAI's `gpt-image` family generates and edits production-quality visuals: photorealism, text-in-image, infographics, UI mockups, logos, ads, compositing, and identity-sensitive edits. This guide covers model selection, settings, prompt structure, and condensed use-case patterns. For the full source with worked Python examples for every use case, see `gpt-image-models-full-guide.md` in this folder.

`gpt-image-2` is the recommended default for new builds. Its `low` quality setting is strong for latency-sensitive, high-volume work; `medium`/`high` are for maximum fidelity.

---

## Key Principles

1. **Structure the prompt in a consistent order**: background/scene → subject → key details → constraints. State the intended use (ad, UI mock, infographic) to set the "mode" and level of polish. For complex requests, use short labeled segments or line breaks instead of one long paragraph.
2. **Separate what changes from what stays.** For edits, say "change only X" + "keep everything else the same," and **restate the preserve list on every iteration** to prevent drift.
3. **Be concrete about materials, medium, and composition.** Vague aesthetic words ("beautiful," "professional," "modern") underperform concrete descriptors (medium, era, lighting, lens, texture).
4. **Iterate instead of overloading.** Start from a clean base prompt and refine with small single-change follow-ups ("make lighting warmer," "remove the extra tree").
5. **Match quality to the task.** Use `high` whenever the image must render legible/dense text or fine material detail.

---

## Model Selection

As of April 21, 2026:

| Model | `outputQuality` | `input_fidelity` | Resolutions | Use for |
|---|---|---|---|---|
| `gpt-image-2` | low/medium/high | Disabled — output is already high-fidelity by default | Flexible (see constraints below) | **Default for new builds.** Highest-quality generation/editing, text-heavy images, photorealism, compositing, identity-sensitive edits. |
| `gpt-image-1.5` | low/medium/high | low/high | 1024×1024, 1024×1536, 1536×1024, auto | Keep for existing validated workflows during migration. |
| `gpt-image-1` | low/medium/high | low/high | same as 1.5 | Legacy compatibility only. |
| `gpt-image-1-mini` | low/medium/high | low/high | same as 1.5 | Cost/throughput priority: large batches, rapid ideation, previews, drafts. |

**Choosing:** Default to `gpt-image-2`. For speed/unit-economics, try `gpt-image-2` at `quality: "low"` first (often as good as `gpt-image-1-mini`). Keep `gpt-image-1.5`/`gpt-image-1` only for backward compatibility while validating migrations.

**Upgrade path:** Move customer-facing, photorealistic, editing-heavy, brand-sensitive, and text-in-image work to `gpt-image-2`. During migration keep prompts largely the same, then retune after comparing quality, latency, and retry rates on your real workload.

### Quality & fidelity
- `quality`: `low` (latency/volume), `medium` (balanced), `high` (small/dense text, close-up portraits, identity-sensitive edits, high-res).
- `input_fidelity` (only on `gpt-image-1.5`/`-1`/`-mini`): use `high` to preserve likeness during larger scene edits. On `gpt-image-2` it is disabled — fidelity is already high.

### gpt-image-2 sizing
Any `size` is allowed if **all** hold: both edges multiples of 16; max edge < 3840px; long:short ratio ≤ 3:1; total pixels between 655,360 and 8,294,400. Treat output above 2560×1440 (2K) as experimental — variability rises.

| Label | Resolution |
|---|---|
| HD portrait | 1024×1536 |
| HD landscape | 1536×1024 |
| Square (default) | 1024×1024 |
| 2K / QHD (reliability ceiling) | 2560×1440 |
| 4K / UHD (experimental) | 3824×2144 (rounded under the <3840 edge rule) |

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
| Object removal | "Remove X. Do not change anything else"; `input_fidelity: "high"` where supported |
| Person compositing | Grounded photographic look (natural light, no cinematic grading); lock subject likeness; higher input fidelity for larger edits |
| Interior swap | Swap one object; preserve camera angle, room lighting, floor shadows, surrounding objects; photorealistic contact shadows |
| Character consistency | Establish a reusable "character anchor" (appearance, proportions, outfit, tone); reuse via edit for each new scene; "do not redesign the character" |

---

## Common Failure Modes

| Problem | Fix |
|---|---|
| Text in image is blurry or misspelled | Switch to `quality: "high"`; put text in quotes; spell tricky words letter-by-letter |
| Identity drifts across edits | State "Preserve [specific features] exactly" in **every** follow-up; use higher `input_fidelity` where supported |
| Composition changes unexpectedly | Name what must stay the same before describing what should change |
| Fine textures look flat | Add material descriptor ("hand-stitched," "brushed," "matte"); consider `quality: "high"` |
| Result looks generic | Replace vague terms ("professional," "modern") with concrete references (medium, era, lighting setup) |
| Prompt too tangled to debug | Start from a clean base prompt and refine with small, single-change follow-ups |
