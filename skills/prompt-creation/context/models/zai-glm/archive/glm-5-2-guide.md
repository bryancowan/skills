# GLM-5.2 Prompting Guide

## Overview

`glm-5.2` is Z.ai's current flagship — positioned as their strongest coding model, built for long-horizon work with a **1M token context and 128K max output**. The prompting style Z.ai documents is distinctive: rather than generic instructions, they recommend **task-shaped, deliverable-listing requests** that enumerate exactly what artifacts the model should produce.

Sourced: 2026-07-26

Sources:
- https://docs.z.ai/guides/llm/glm-5.2
- https://docs.z.ai/guides/overview/migrate-to-glm-new

Endpoint: `https://api.z.ai/api/paas/v4/chat/completions`

---

## Parameters

| Parameter | Values | Notes |
|---|---|---|
| `thinking` | `{"type": "enabled"}` / `{"type": "disabled"}` | **Enabled by default.** Unlike GLM-4.7's forced thinking, GLM-5.2 *decides whether to think* when enabled. |
| `reasoning_effort` | `high`, `max` | New in 5.2. `max` (deep reasoning) is the default. |
| `temperature` | 0.6–1.0, **default 1.0** | Raised from prior versions |
| `top_p` | default 0.95 | |
| `max_tokens` | up to 128K | Examples show 4096 |
| `stream` | bool | Yields `delta.reasoning_content` and `delta.content` |
| `tool_stream` | bool | New — streams tool-call arguments in real time; concatenate `delta.tool_calls[*].function.arguments` |

**Do not tune `temperature` and `top_p` at the same time** — Z.ai's guidance is to pick one.

Also supported: function calling, context caching for long conversations, structured JSON output, and MCP tool integration.

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

Supply team standards up front (lint rules, build commands, testing requirements) in a `CLAUDE.md` or `Agent.md`-style file; GLM-5.2 performs best on production-grade work when those constraints are in context rather than discovered.

---

## Migrating from GLM-4.7 / 5.1

- Update the model ID to `glm-5.2`.
- Re-baseline `temperature` — the default moved to 1.0.
- Replace forced-thinking assumptions: thinking is enabled by default but the model now decides when to use it. Set `reasoning_effort` (`high` or `max`) instead of trying to force reasoning through the prompt.
- Adopt `tool_stream=True` if you surface tool arguments in a UI.
- Raise `max_tokens` budgets — 128K output and 1M context are both much larger than prior limits.
- On Cerebras, GLM 4.7's `disable_reasoning` boolean is deprecated and retires 2026-07-21; use `reasoning_effort="none"`.
- Give clearer instructions and tighter constraints — Z.ai's stated migration advice is that the stronger model rewards precision, not more verbosity.
