# ComfyUI Prompting Guide

## Overview
ComfyUI is a node-based workflow tool — not a single prompt box. Output is always two separate blocks: Positive Prompt and Negative Prompt. Syntax and token limits depend on the loaded checkpoint, so always ask which model is loaded before writing.

## Ask first if not stated
"Which checkpoint model are you using? (SD 1.5, SDXL, Flux, or other)"

## Model-specific notes
- **SD 1.5**: shorter prompts work better, under 75 tokens per block, use `(word:weight)` syntax for emphasis.
- **SDXL**: handles longer prompts, supports more natural language alongside weighted syntax.
- **Flux**: natural language works well, less reliance on weighted syntax, very responsive to style descriptions.

## Template

```
POSITIVE PROMPT:
[subject], [style], [mood], [lighting], [composition], [quality boosters: highly detailed, sharp focus, 8k]

NEGATIVE PROMPT:
[exclusions: blurry, low quality, watermark, extra limbs, bad anatomy, distorted, oversaturated, extra fingers]

CHECKPOINT: [model name]
SAMPLER: Euler a (recommended starting point)
CFG SCALE: 7 (increase for stricter prompt adherence)
STEPS: 20-30 for drafts, 40-50 for finals
RESOLUTION: [width x height — must be divisible by 64]
```

## Example (SDXL)
```
POSITIVE PROMPT:
portrait of an elderly fisherman, weathered face, deep wrinkles, salt-and-pepper beard, wearing a worn yellow raincoat, standing on a wooden dock at golden hour, cinematic lighting, shallow depth of field, photorealistic, 8k, sharp focus

NEGATIVE PROMPT:
blurry, low quality, watermark, signature, text, extra fingers, deformed hands, plastic skin, cartoon, anime, oversaturated, harsh flash

CHECKPOINT: sd_xl_base_1.0.safetensors
SAMPLER: DPM++ 2M Karras
CFG SCALE: 7
STEPS: 30
RESOLUTION: 1024x1024
```

## Anti-patterns
- Single combined prompt → ComfyUI needs Positive and Negative as separate blocks
- No negative prompt → low-quality artifacts dominate output
- Ignoring checkpoint syntax differences (SD1.5 vs Flux) → wasted compute, off-target output
- Resolution not divisible by 64 → workflow errors
