# GPT-5.6 Prompting Guide

## Overview

GPT-5.6 is OpenAI's current flagship family and introduces a **new naming scheme**: three named variants instead of size suffixes. It also adds programmatic tool calling, a multi-agent beta, explicit prompt caching, persisted reasoning, `pro` mode, and a `max` reasoning effort level.

The headline prompting finding: **lean prompts win.** OpenAI's internal testing found leaner system prompts improved eval scores by roughly **10–15% while cutting total tokens 41–66% and cost 33–67%**. If you are migrating a prompt from GPT-5.x, deleting redundancy is the highest-value edit you can make.

Sourced: 2026-07-26

Sources:
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/guides/model-selection
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/guides/prompting/migrate-from-prompt-object
- https://developers.openai.com/api/docs/guides/prompt-engineering
- https://developers.openai.com/api/docs/guides/reasoning-best-practices

---

## Variants and pricing

| Model ID | Role | Input / Cached / Output per 1M tokens |
|---|---|---|
| `gpt-5.6-sol` | Flagship capability (what the `gpt-5.6` alias resolves to) | $5.00 / $0.50 / $30.00 |
| `gpt-5.6-terra` | Strong performance at lower cost | $2.50 / $0.25 / $15.00 |
| `gpt-5.6-luna` | Efficient, high-volume workloads | $1.00 / $0.10 / $6.00 |

For reference: `gpt-5.5` $5/$0.50/$30, `gpt-5.5-pro` $30/–/$180, `gpt-5.4` $2.50/$0.25/$15, `gpt-5.4-mini` $0.75/$0.075/$4.50, `gpt-5.4-nano` $0.20/$0.02/$1.25.

**Selection method** (OpenAI's stated framework): optimize for accuracy first — set a concrete accuracy target, build a labeled eval set, start with the most capable model (`gpt-5.6`) — and only then pursue the cheapest, fastest model that still hits the target. Collect prompt/completion pairs along the way so a smaller variant can be tested zero-shot, few-shot, or fine-tuned.

---

## Parameters

### `reasoning.effort`
Levels: `none`, `low`, `medium`, `high`, `xhigh`, `max`.

- `medium` — balanced starting point.
- `low` — latency-sensitive workloads.
- `none` — reserve for latency-critical tasks that genuinely don't need reasoning.
- `max` — new highest setting, for demanding quality-first tasks that need extensive exploration.

When migrating, start from your GPT-5.5/5.4 setting and **test one level lower** — GPT-5.6 reaches frontier performance with fewer output tokens.

### `reasoning.mode: "pro"`
Applies additional model work on difficult tasks before returning a single final answer. Increases latency and token usage, billed at standard rates. Independent of effort level. Compare standard vs. pro on representative tasks before adopting it broadly.

### `reasoning.context` (persisted reasoning)
Reuses reasoning across conversation turns. Link turns with `previous_response_id`.

| Value | Behavior |
|---|---|
| `auto` (default) | Model decides what stays relevant |
| `all_turns` | Preserve reasoning when goals stay stable across the conversation |
| `current_turn` | Reset when prior reasoning becomes irrelevant |

### `text.verbosity`
`low` / `medium` / `high` — sets the default detail level of responses. Use it as the coarse control and prompt for the fine control (see "Response length" below).

### `prompt_cache_options`
Explicit caching: `prompt_cache_options.mode: "explicit"` lets you mark reusable prefixes. Cache writes bill at **1.25× the uncached input rate**; reads bill at the discounted cached rate. `prompt_cache_retention` is replaced by `prompt_cache_options.ttl`. Track `cached_tokens` and `cache_write_tokens` in the response to verify you're actually hitting cache.

### Programmatic tool calling
Add the `programmatic_tool_calling` tool, mark eligible tools with `allowed_callers`, and handle `program` items, function calls, and `program_output` items. The model orchestrates tools with JavaScript inside a hosted runtime.

**Match the calling method to task shape.** Reserve programmatic tool calling for *bounded* workflows that return multiple results needing processing. It is not a general upgrade over ordinary function calling — benchmark it before adopting.

### Multi-agent (beta)
Coordinates multiple subagents in parallel to cut latency on complex tasks.

### Image input detail
GPT-5.6 preserves original image dimensions instead of resizing. This improves fidelity but can increase tokens and latency — budget accordingly on image-heavy workloads.

---

## Prompting guidance

### 1. Strip redundancy — this is the big one

- **State each instruction once.** Repeating a rule in the system prompt, the tool description, and the user message costs tokens and does not increase compliance.
- **Expose only the tools relevant to the task**, with concise, precise descriptions.
- **Remove examples** unless they encode a specific product requirement. GPT-5.6 does not need few-shot examples to infer ordinary formats.
- **Monitor context growth** in long sessions — accumulated context is the silent version of the same problem.

### 2. Define autonomy boundaries, not per-action approval

Instead of making the model ask before every step, state which classes of work it may proceed on:

```text
For requests to answer, explain, review, diagnose, or plan: inspect the relevant materials and report the result. Do not implement changes unless the request also asks for them.

For requests to change, build, or fix: make the requested in-scope local changes and validate them.

Require confirmation for external writes, destructive actions, purchases, or a material expansion of scope.
```

Name the specific safe actions explicitly, and don't repeat approval instructions elsewhere in the prompt.

### 3. Specify what brevity must preserve

Pair `text.verbosity` with a prompt that says what survives the cut, rather than just "be concise":

```text
Lead with the conclusion. Include the evidence needed to support it, any material caveats, and the next action. Omit secondary detail and repetition.
```

### 4. Describe tone as concrete writing choices

Abstract labels ("be friendly", "be professional") underperform. Name the behaviors:

```text
State answers directly. Acknowledge specific problems rather than generalities. Use reassurance only when it is relevant to what the user asked.
```

### 5. Put tool guidance in the tool description

What the tool does, when to use it, required inputs, side effects, retry safety — these belong in the tool's own description, not scattered through the system prompt.

---

## Structure

OpenAI's recommended prompt order:

1. **Identity** — purpose, communication style, high-level goals
2. **Instructions** — rules, required behaviors, prohibitions
3. **Examples** — diverse input/output pairs (only if needed)
4. **Context** — supporting data, proprietary information, reference material

Message roles form a chain of command: **developer** messages carry high-priority application instructions, **user** messages are lower priority. The `instructions` parameter grants developer-level authority and takes priority over user input in the same request.

Combine **markdown for hierarchy** (headers, lists) with **XML tags for boundaries** (where content starts and stops, with attributes for metadata).

**Put frequently reused content at the beginning of the prompt** so prompt caching can hit it.

---

## Migration checklist

- [ ] Update the model slug; decide between `sol`, `terra`, and `luna` on your evals rather than defaulting to the alias.
- [ ] Drop reasoning effort one level from your GPT-5.5/5.4 setting and measure.
- [ ] Use the **Responses API** for reasoning and tool workflows (Chat Completions never includes reasoning items in context, degrading multi-function-call performance and raising token usage).
- [ ] Delete repeated instructions; prune the tool list to what the task needs.
- [ ] Replace `prompt_cache_retention` with `prompt_cache_options.ttl`; instrument `cached_tokens` / `cache_write_tokens`.
- [ ] Evaluate `reasoning.mode: "pro"` on representative hard tasks before turning it on.
- [ ] Benchmark programmatic tool calling only on bounded, multi-result workflows.
- [ ] Budget for larger image token counts if you send images.

### The `prompt` object is going away

The managed `prompt` resource (`prompt: { id, version, variables }`) is deprecated and the `v1/prompts` endpoint **shuts down November 30, 2026**. Move prompt content into application code: pass `input: [{ role, content }, ...]` plus `model`, build messages with a typed helper function whose arguments replace the old template variables, and version through git rather than the API. Pin to specific model snapshots and gate prompt changes behind your normal test/deploy process.

---

## Reasoning-model prompting rules (still apply)

- **Keep prompts simple and direct.** These models understand brief, clear instructions.
- **Do not add chain-of-thought scaffolding.** "Think step by step" and similar instructions do not help and add cost — reasoning happens internally.
- **Try zero-shot first.** Add few-shot examples only if needed, and make sure they align with the instructions rather than contradicting them.
- **State success criteria and constraints explicitly.** Be very specific about the end goal.
- **Use delimiters** (markdown or XML) to separate input sections.
- Reasoning models respond to **high-level, goal-oriented guidance**; non-reasoning GPT models want **precise instructions that spell out the logic and data** needed.

Most real workflows use both: a reasoning model to plan and decide, a cheaper model to execute.
