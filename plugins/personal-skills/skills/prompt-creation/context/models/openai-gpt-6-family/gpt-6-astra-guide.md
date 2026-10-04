# GPT-6 Astra Prompting Guide

## Overview

`gpt-6-astra` is OpenAI's current flagship and the capability ceiling of the GPT-6 family. The cost tiers beneath it are now **`gpt-6.1-sol`** ($2 / $10) and **`gpt-6-luna`** ($0.10 / $0.50); selection, effort, API constraints, and OpenAI's GPT-6 prompt snippets are in `gpt-6-family-guide.md`. Read that file first. This one covers what is specific to Astra. GPT-5.6 is previous generation (`context/models/openai-gpt-5-family/gpt-5-6-guide.md`).

The four capabilities that are genuinely new — and that change how you architect around the model rather than just how you word the prompt — are **async tool calling**, **mid-turn steering**, **dynamic reasoning configuration**, and **misalignment monitoring**.

Sourced: 2026-10-03 (lineup, pricing, and effort re-verified; the architecture sections were last checked 2026-09-12)

Sources:
- https://developers.openai.com/api/docs/models/gpt-6-astra
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/guides/model-selection
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/guides/prompt-engineering

---

## Spec

| Property | Value |
|---|---|
| Model ID | `gpt-6-astra` |
| Context window | 1,050,000 tokens (max input 922,000) |
| Max output | 128,000 tokens |
| Knowledge cutoff | 2026-04-30 |
| Modalities | text + image in, text out |
| Price per 1M | $10 input / $1 cached input / $12.50 cache write / $50 output |
| Endpoints | **Responses** (`v1/responses`), Chat Completions, Batch. Not supported: Realtime, Live, Assistants, fine-tuning, embeddings, image generation, audio. |
| Reasoning effort | `low`, `medium`, `high`, `xhigh`, `max` — **no `none`** |

**Long-context cost cliff:** requests above **272K input tokens** are billed at **2× input and cache rates, 1.5× output rates**, for the full request. The same rule applies to 6.1 Sol, Sol, and Luna. This is a hard step, not a gradient. If you are anywhere near that boundary, measure your actual input size — trimming a prompt from 280K to 270K halves its input cost. (Claude bills its 1M window at flat rates; Gemini 2.5 Pro has a similar step at 200K. See `references/model-selection.md`.)

Supported features: streaming, structured outputs, function calling, file search, image input, web search, prompt caching.
Supported hosted tools: web search, file search, image generation, code interpreter, hosted shell, apply patch, skills, computer use, MCP, tool search — reached **through the Responses API**.

> **Use the Responses API for reasoning and tool workflows.** Chat Completions never carries reasoning items across turns, which degrades multi-function-call performance and raises token usage. The `instructions` parameter and `previous_response_id` discussed below are Responses-only. Astra can generate images via the hosted tool but is not itself an image-generation endpoint.

---

## What's actually new

### Async tool calling
Tools can run in parallel **while the model continues reasoning**, rather than blocking the turn until results return. This is an architecture change, not a prompt change: your tool layer has to be able to return later. The prompting consequence is that "call these tools, then wait" framing is now leaving latency on the table — describe what the model needs, not the order in which to block.

### Mid-turn steering
A correction or changed requirement can be sent over WebSocket **during** a turn without discarding the work already done. Design your product around this instead of around cancel-and-restart: the user's "actually, make it Postgres not MySQL" no longer costs the whole turn.

### Dynamic reasoning configuration
Reasoning effort can be adjusted **mid-conversation while preserving the cache**, by adding a `configuration_update` input item; the new level applies until the next override. This is a real break from prior OpenAI models, where changing effort invalidated the prompt cache and the standing advice was "pick a level and hold it." On Astra you can run a conversation at `low` and step up to `high` for the two turns that need it. Update any prompt or harness note that still says effort changes are cache-destroying — that rule is now Astra-specific in the other direction.

### Misalignment monitoring
A safeguard layer that detects model misalignment. Budget for the same class of false positives you'd handle on any classifier-fronted model: if benign requests get blocked, rephrase away from the pattern rather than arguing with it in the prompt.

---

## Prompting guidance

OpenAI's own prompt-engineering guide is thinner on Astra than the GPT-5.6 material was on 5.6 — and it's worth being precise about the gap rather than inventing detail.

**What OpenAI documents for Astra specifically:**

- "GPT models like gpt-6-astra benefit from **precise instructions that explicitly provide the logic and data required** to complete the task in the prompt."
- For coding: define the agent's role, enforce structured tool use **with concrete examples of how to invoke commands**, require thorough testing for correctness, and set Markdown standards for output.
- For agentic tasks: plan thoroughly and decompose into sub-tasks.
- For front-end: Tailwind CSS, shadcn/ui, and Radix Themes are the recommended libraries; Astra generates front-end apps from a single prompt without examples.

**A tension worth flagging to users.** OpenAI's page files Astra under "GPT models" — the category it says wants *precise* instructions — while reserving "high-level guidance only" for "reasoning models" (a section that still names o3/o4-mini). But Astra has no `reasoning.effort: "none"`; it always reasons. Don't resolve this by guessing. Resolve it by effort level:

- At `low`/`medium`, write it like a GPT model: explicit logic, explicit data, concrete tool-call examples.
- At `high`/`xhigh`/`max`, write it like a reasoning model: state the goal, the constraints, and the success criteria, and let it plan. Over-specifying the method here wastes the capability you're paying for.

Either way, **never add chain-of-thought scaffolding.** "Think step by step" on a model that always reasons internally is pure token cost. Raise effort instead.

### Lean prompts
The lean-prompt finding (eval scores up ~10–15%, tokens down 41–66%, cost down 33–67%) was measured on GPT-5.6; OpenAI has not retracted it or restated it for GPT-6. State each instruction once. Deleting redundancy remains the safest edit when migrating an older prompt.

### Message roles and `instructions`
Authority runs `instructions` → `developer` → `user` → `assistant`.

- `instructions` carries high-level behavior: tone, goals, examples of correct responses.
- `developer` messages are application-developer instructions and take priority over `user`.
- **`instructions` applies only to the current response.** It does **not** carry across turns linked with `previous_response_id`. If behavior must persist for a whole conversation, put it in a `developer` message or re-send it each turn — this is a common and silent source of "the model forgot its instructions on turn 3."

---

## Deprecation: the `prompt` object

OpenAI's reusable **prompt objects are being retired**: de-emphasized from **2026-06-03**, shutdown **2026-11-30**. Version prompts in your own code instead.

If you are reading an older guide (including this skill's GPT-5.6 file before its 2026-09 revision) that recommends migrating *to* the `prompt` object, that advice is now backwards. Migrate off it.

---

## Choosing between Astra and the rest of the family

OpenAI's current method: experiment with different models and reasoning settings on the same inputs and keep the lightest setting that meets your quality bar. `gpt-6.1-sol` is the documented model to compare Astra against "for complex projects where cost matters."

Astra carries 5× the per-token price of 6.1 Sol. Whether it costs more per completed task depends on token use and retries on your workload — measure cost per completed task, not cost per token.

| Situation | Pick |
|---|---|
| Hardest reasoning, long-horizon agentic runs, unsolved problems | `gpt-6-astra` |
| Complex work where cost matters | `gpt-6.1-sol`, compared against Astra on the same task |
| High volume, well-specified, latency-sensitive | `gpt-6-luna` |
| Agentic coding in a Codex harness | `gpt-5.3-codex` — see `context/models/openai-codex/codex-prompting-guide` |
| Needs `reasoning.effort: "none"` | Not Astra or 6.1 Sol. Use `gpt-6-luna` or `gpt-6-sol`. |

---

## Cross-references

- Family-wide selection, effort, API constraints, snippets: `gpt-6-family-guide.md`
- Previous generation: `context/models/openai-gpt-5-family/gpt-5-6-guide.md`
- Codex agentic coding + Goals: `context/models/openai-codex/codex-prompting-guide`, `context/coding/codex-goals.md`
- Document and image input: `context/vision-and-documents/document-understanding-tips.md`
- Cross-vendor pricing and switching costs: `references/model-selection.md`
