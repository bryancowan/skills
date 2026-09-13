# GLM-5.3 Prompting Guide

## Overview

`glm-5.3` is Z.ai's current flagship — their strongest coding model, built for long-horizon work with a **1M token context and 128K max output**. `glm-5.3-flash` is the multimodal (VLM) sibling: same context and output ceiling, image/video/file input, text output.

Two things to know before writing anything:

1. **Reasoning is now mandatory.** `thinking.type` must be `"enabled"`; `"disabled"` is no longer supported. This is a **breaking migration** from GLM-5.2 — see below.
2. **The prompting style Z.ai documents is distinctive.** Rather than generic instructions, they recommend **task-shaped, deliverable-enumerating requests** that name exactly which artifacts the model should produce. This carries over unchanged from 5.2 and is still the highest-leverage thing to get right.

Sourced: 2026-09-12

Sources:
- https://docs.z.ai/guides/llm/glm-5.3
- https://docs.z.ai/guides/vlm/glm-5.3-flash
- https://docs.z.ai/guides/overview/migrate-to-glm-new

Endpoint: `https://api.z.ai/api/paas/v4/chat/completions`
Superseded: `context/models/zai-glm/archive/glm-5-2-guide.md`, `context/models/zai-glm/archive/glm-4.7`.

---

## Models

| Model | ID | Profile | Context / Max output |
|---|---|---|---|
| GLM-5.3 | `glm-5.3` | Flagship coding and agentic model. ~50% gain over GLM-5.2 on Z.ai Code Bench. Cybersecurity/exploitation benchmark scores over 2× GLM-5.2's. Better token efficiency at higher performance. | 1M / 128K |
| GLM-5.3-Flash | `glm-5.3-flash` | VLM. 320B total / 18B activated params. Input: **text, image, video, file**. Output: text only. | 1M / 128K |

`glm-5.3-flash` is positioned at $0.045 per task on the Artificial Analysis Intelligence Index. The GLM Coding Plan gives it 3× the quota of `glm-5.3` and 50% point consumption off-peak and at weekends — so for high-volume visual-loop work, Flash is the cost-sane default even where 5.3 would also work.

---

## Parameters

| Parameter | Values | Notes |
|---|---|---|
| `thinking.type` | `"enabled"` — **required** | Disabling is no longer supported. |
| `reasoning_effort` | `low`, `high`, `max` | **Default `max`.** Z.ai recommends `max` for complex tasks like coding. Use `low` as the replacement for what used to be `thinking: disabled`. |
| `temperature` | default 1.0 | |
| `max_tokens` | up to 128K | Examples show 4096 — raise it deliberately. |
| `stream` | bool | Yields `delta.reasoning_content` and `delta.content` |
| `tool_stream` | bool | Streams tool-call arguments in real time; concatenate `delta.tool_calls[*].function.arguments` |

Also supported: function calling, context caching for long conversations, structured JSON output, MCP tool integration.

> **`reasoning_effort` defaults to `max` here — the opposite of most vendors.** On Claude and OpenAI the default sits mid-range and you step up. On GLM-5.3 you are paying for maximum reasoning unless you step *down*. For short, well-scoped, latency-sensitive calls, set `low` explicitly.

---

## Prompting style: enumerate the deliverables

The pattern running through every documented example is that the prompt **lists the artifacts it wants back**, rather than describing a goal and hoping. Adapt these shapes:

**Project-level context building**
```text
Please read the current project and output a system architecture map, core module responsibilities, key API contracts, major data flows, core call chains, potential technical debt, and engineering constraints.
```

**Long-horizon refactoring** — note the plan-before-execute structure and the explicit invariants:
```text
Complete the decoupling and refactoring of the current module without changing business logic, API signatures, or runtime behavior. First provide the execution plan, impact scope, risk boundaries, and verification method.
```

**Engineering standards compliance**
```text
Strictly follow engineering standards. Do not introduce new dependencies, modify API contracts, or commit changes proactively. Run build, lint, and tests; report verification results and uncovered risks.
```

**Platform-targeted implementation** — name the device/debug loop, not just the feature list:
```text
Implement a native Android client in Kotlin connecting to existing server APIs, supporting multi-session conversations, streaming messages, voice input, notifications, and reconnection. Install on real device using ADB; debug with logcat and screenshots.
```

**Migration with platform constraints**
```text
Migrate all features into a WeChat Mini Program using [native/Taro/uni-app]. Analyze page structure, core user paths, API contracts, and platform constraints including package size, domain allowlists, and HTTPS requirements.
```

**Research reproduction**
```text
Reproduce experiments from this paper and dataset. Build model architecture and loss functions using PyTorch. Construct data pipeline and training/inference scripts ensuring consistency. Autonomously identify and fix runtime issues; verify metrics align with paper.
```

### What these share

1. **Named deliverables**, comma-separated, in the order you want them.
2. **Explicit invariants** — what must not change (business logic, API signatures, runtime behavior).
3. **A verification step baked into the request** — "run build, lint, and tests; report verification results."
4. **Autonomy granted explicitly** — "autonomously identify and fix runtime issues."
5. **Plan first on large tasks** — "First provide the execution plan, impact scope, risk boundaries, and verification method."

Supply team standards up front (lint rules, build commands, testing requirements) in a `CLAUDE.md` or `Agent.md`-style file; GLM performs best on production-grade work when those constraints are in context rather than discovered.

---

## GLM-5.3-Flash: prompt the visual loop, not the output

Z.ai's documented best practice for the VLM is not a prompt template — it's a **closed loop**. In every domain they cover, the pattern is `act → render → inspect → refine`, with the model looking at its own output as an image and comparing it against a reference. Build the loop into the prompt explicitly; the model will not assume it.

| Domain | The loop |
|---|---|
| **UI coding** | Supply a set of page screenshots; ask for a high-fidelity reproduction; have the model re-screenshot its build and refine against the references until they match. |
| **Office documents** | Have it render and inspect each page, fixing text overflow, image cropping, element overlap, and alignment. |
| **Video editing** | Use its ability to identify speakers and match visuals to spoken content. |
| **3D / Blender** | Repeated render → inspect → refine from **fixed camera positions** (fixed cameras are what make successive renders comparable). |
| **Game development** | Test the gameplay loop, comparing captures against reference art. |
| **Computer use** | Observe → implement → test cycles for UI reproduction. |

Prompt shape:
```text
Reproduce the attached screenshots as [framework] components. After each build, take a screenshot of your output, compare it against reference image [N], and list the specific differences you see. Fix them and repeat until the differences are cosmetic only. Do not declare it done without a final side-by-side comparison.
```

The instruction that matters most is the last one — without an explicit stopping criterion tied to a comparison, the model exits the loop after one pass.

---

## Migrating from GLM-5.2

- Update the model ID to `glm-5.3`.
- **Breaking:** any caller sending `thinking: {"type": "disabled"}` must change to `{"type": "enabled"}` with `reasoning_effort: "low"` before migrating. There is no way to turn reasoning off.
- Re-baseline cost expectations: `reasoning_effort` defaults to `max`, and 5.2's "the model decides whether to think" behavior is gone.
- Token efficiency improved, so budgets tuned on 5.2 are likely conservative — but verify rather than assuming, since default `max` effort pushes the other way.
- Adopt `tool_stream=True` if you surface tool arguments in a UI.
- Z.ai's standing migration advice still holds: **the stronger model rewards precision, not more verbosity.** Tighten constraints; don't pad.
