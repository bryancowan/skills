# OpenAI Sora Video Prompting Guide

## Overview

OpenAI's video generation runs on the Sora models through the Videos API. Renders are **asynchronous** — you submit a job, poll or receive a webhook, then download.

⚠️ **Deprecation:** the Sora 2 models and the Videos API are scheduled to shut down **September 24, 2026**. Check for a successor model before building anything long-lived on this API.

For Google's video models (Veo 3.1 / Veo 3.1 Lite), see `google-veo-prompt-guide.md` in this folder.

Sourced: 2026-07-26

Source: https://developers.openai.com/api/docs/guides/video-generation

---

## Models and cost

| Model | Use for | Price |
|---|---|---|
| `sora-2` | Fast iteration: exploration, social media, rough cuts | $0.10 / second at 720p |
| `sora-2-pro` | Production-quality cinematic footage, 1080p exports | from $0.30 / second |

## Parameters

- **Duration:** 8, 16, or 20 seconds.
- **Size:** 1280×720, 1920×1080, 1080×1920 (vertical), plus 480p/720p options.
- **`input_reference`:** an image that acts as the **first frame** of the video. Must match the target video resolution. Use it to lock in brand assets or a specific environment.
- **Characters:** reusable non-human subjects uploaded as short MP4 clips; up to two per video.

## Operations

| Operation | Endpoint | Notes |
|---|---|---|
| Create | `POST /v1/videos` | Starts an async render job |
| Extend | `POST /v1/videos/extensions` | Continues a scene; max 6 extensions → 120s total |
| Edit | `POST /v1/videos/edits` | Targeted adjustments to an existing video |
| Monitor | `GET /videos/{video_id}` | Or use webhooks |
| Download | `GET /v1/videos/{video_id}/content` | MP4, thumbnail, or spritesheet |

Batch renders go through the Batch API in JSON — upload assets first and reference them by `file_id` or `image_url`.

---

## Prompting

The documented core: specify **shot type, subject, action, setting, and lighting**. Naming all five is what prevents the model from inventing details you didn't ask for.

A workable template:

```
[Shot type + lens feel] of [subject, described concretely] [action, one clear beat].
Setting: [place, time of day, weather, notable background elements].
Lighting: [source, quality, direction, color temperature].
Camera: [static / slow push in / handheld drift / orbit], [speed].
Mood: [two or three adjectives].
```

Practical rules:

- **One action beat per generation.** Multi-beat prompts ("she walks in, sits down, then opens the laptop") produce mush at 8–20 seconds. Chain beats with the extend endpoint instead.
- **Describe the camera, not just the scene.** Absent camera direction, the model picks its own movement, which is the most common source of "it looks wrong but I can't say why."
- **Lock continuity across extends** by repeating the subject and lighting description verbatim in each extension prompt — the same preserve-list discipline that works for image edits.
- **Use `input_reference` instead of describing a look you already have.** A first-frame image is far more reliable than adjectives for brand color, wardrobe, or set dressing.
- **State exclusions explicitly** ("no on-screen text", "no lens flare", "no camera shake").
- **Iterate at `sora-2` and 720p, then re-render the winning prompt at `sora-2-pro`.** Cost per iteration is 3× different.

---

## Content restrictions

Enforced by the API, so build them into the prompt rather than discovering them at render time:

- Content must be suitable for audiences under 18
- No copyrighted characters or music
- No real people or public figures
- Human likeness in character uploads is blocked by default
