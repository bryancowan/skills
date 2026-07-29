# Gemini File Prompting Guide

## Overview

How to prompt Gemini with files as input — images, video, audio, and documents — via the Files API.

Sourced: 2026-07-26

Source: https://ai.google.dev/gemini-api/docs/files

---

## Files API limits

| Limit | Value |
|---|---|
| Max file size | 2 GB (**PDFs: 50 MB**) |
| Total storage per project | 20 GB |
| Retention | **48 hours** |
| Cost | Free in all regions |

The 48-hour retention is the one that bites in production — re-upload rather than assuming a stored `file_id` persists across a longer pipeline.

---

## Prompting strategies

**1. Be specific about the operation, not the object.**

Weak: "describe this airport board."
Strong: "parse the time and city from the airport board shown in this image into a list."

Craft instructions that leave minimal room for misinterpretation. Name the fields, the structure, and what to do with anything that doesn't fit.

**2. Give few-shot image/response pairs.** Sample pairs demonstrating the output format and style transfer to new inputs better than a format description alone.

**3. Decompose the task.** Divide complex work into sub-goals and walk the model through them. This matters most for math, diagram reasoning, and multi-part extraction.

**4. Specify the output format** — JSON, Markdown, HTML — whenever anything downstream will parse the result.

**5. Put a single image *before* the text prompt.** Order is flexible, but image-then-text tends to perform better for single-image prompts.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Vague or generic response | Ask the model to describe the file first, then answer the question |
| Missing a detail that's plainly there | Point at it: "Use the weight shown on the box to determine the child's age" |
| Wrong answer, unclear why | Ask the model to explain its reasoning — this localizes where interpretation broke |
| Hallucinated details | Lower temperature, or request a shorter description; long free-form descriptions invite invention |

---

## Cross-modality notes

- **Video:** ask for timestamped observations rather than a summary when you need to locate events. Gemini 3.1 Flash can also generate images from a YouTube URL or uploaded video.
- **Audio:** state whether you want a verbatim transcript, a diarized transcript, or a summary — these produce very different outputs from the same prompt.
- **Documents:** for PDFs over 50 MB, split before upload. For structured extraction, supply the schema and an instruction for illegible fields ("write `unreadable` rather than guessing").
