# Document and Multimodal Understanding Tips

## Overview

Prompting for document and image *understanding* — extraction, transcription, chart reading, localization — is mostly **parameter selection**, not wording. OpenAI's own framing: small choices around image detail, verbosity, reasoning effort, and tool usage significantly affect performance.

So when a user's document-extraction prompt is underperforming, check the four settings below **before** rewriting the prompt.

Sourced: 2026-09-12

Sources:
- https://developers.openai.com/cookbook/examples/multimodal/document_and_multimodal_understanding_tips

Companions: `context/models/openai-gpt-5-family/openai-vision-guide.md` (OpenAI vision basics), `context/models/google-gemini/gemini-file-prompting.md` (Gemini file input).

---

## Decision guide

| Symptom | Change |
|---|---|
| Misreads small text, handwriting, dense tables, low-contrast scans, screenshots with fine text | `detail="original"` (default is `"auto"`) |
| Paraphrases when you wanted a faithful transcription | `text={"verbosity": "high"}` |
| Reads each region correctly but combines them wrongly | `reasoning={"effort": "high"}` |
| Needs to inspect a subregion to answer at all | Code Interpreter, or a crop-and-rerun pipeline |

### 1. Image detail

`detail="auto"` is the right default for standard readable pages. Switch to **`detail="original"`** (no downscaling) for handwriting, tiny labels, dense tables, low-contrast scans, and screenshots with fine text.

The cost is real — original-detail images consume substantially more input tokens — so make it conditional on document type rather than global.

### 2. Verbosity for transcription

For **faithful transcription / OCR**, set `text={"verbosity": "high"}`. This preserves layout and minimizes paraphrase. For ordinary question-answering over a clearly readable document, the default is fine.

This is the setting people miss most often: they write "transcribe exactly, do not paraphrase" in the prompt and get paraphrase anyway, because the verbosity default is pulling the other way.

### 3. Reasoning effort for compositional answers

Raise `reasoning={"effort": "high"}` when the answer requires **combining information across multiple regions** — comparing series in a chart, tracing a technical diagram, following a tournament bracket, reading a floorplan. The model can read each part at low effort; assembling them is what needs the reasoning budget.

### 4. Multi-pass inspection

**With Code Interpreter:** let the model zoom, crop, rotate, and inspect subregions before synthesizing an answer. This is the strongest option for dense visual input.

**Without it:** build a narrow crop-and-rerun pipeline — localize the region locally, then run a focused extraction on the cropped image. Two cheap targeted calls usually beat one expensive whole-page call.

---

## Bounding boxes: enforce the coordinate contract

Localization fails silently when the coordinate convention is left implicit. State it:

- Format `[x_min, y_min, x_max, y_max]`
- **Normalized 0–999 space**
- **Top-left origin**

Put the contract in the prompt and require it in the output schema. Without it you get a mix of pixel coordinates, 0–1 floats, and bottom-left origins across a single batch.

---

## Prompt-side rules that still matter

- **Name the operation, not the object.** "Extract every line item with its quantity and unit price" beats "look at this invoice."
- **Extract before interpreting.** Two stages: transcribe the values, then reason over them. Combining both in one instruction produces confident numbers that aren't on the page.
- **Give it a way to say no.** Instruct it to write `unreadable` rather than guess. Absent that, illegible fields get plausible values.
