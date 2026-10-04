# GPT-6 Family Prompting Guide

## Overview

OpenAI's current general-purpose lineup is three models: **`gpt-6-astra`**, **`gpt-6.1-sol`**, and **`gpt-6-luna`**. `gpt-6-sol` is still served and priced, but its model page points to GPT-6.1 Sol as the newer version. The GPT-5.6 general-purpose variants (`sol` / `terra` / `luna`) no longer appear on the models overview; they remain on the pricing page, so treat them as previous generation (`context/models/openai-gpt-5-family/gpt-5-6-guide.md`). `gpt-5.6-cyber` is still listed as the cybersecurity specialist.

This file covers what the whole family shares: selection, effort, API constraints, and OpenAI's prompt snippets. Astra-only detail (async tool calling, mid-turn steering, misalignment monitoring) is in `gpt-6-astra-guide.md`.

Sourced: 2026-10-03

Sources:
- https://developers.openai.com/api/docs/guides/latest-model
- https://developers.openai.com/api/docs/models (and the `gpt-6.1-sol`, `gpt-6-luna`, `gpt-6-sol` model pages)
- https://developers.openai.com/api/docs/pricing
- https://developers.openai.com/api/docs/guides/model-selection
- https://developers.openai.com/api/docs/guides/prompt-engineering
- https://developers.openai.com/api/docs/guides/reasoning-best-practices (**stale upstream**: still names o3 / o4-mini / GPT-4.1. Used here only for its durable claims.)

---

## Models

| Model | Positioning (OpenAI's words) | Input / cached / output per 1M | Effort levels | Knowledge cutoff |
|---|---|---|---|---|
| `gpt-6-astra` | "Our most capable model for the most demanding work." | $10 / $1 / $50 | `low`–`max`, **no `none`** | 2026-04-30 |
| `gpt-6.1-sol` | "Near-Astra performance for complex work at a lower cost." | $2 / $0.10 / $10 | `low`–`max`, **no `none`** | 2026-04-30 |
| `gpt-6-luna` | "Our most efficient model for focused, high-volume tasks." | $0.10 / $0.01 / $0.50 | `none`, `low`–`max` | 2026-05-18 |
| `gpt-6-sol` | Complex coding and agentic workflows; "a newer version, GPT-6.1 Sol, is available" | $2 / $0.20 / $10 | `none`, `low`–`max` | 2026-04-20 |

All four: 1,050,000-token context (922,000 max input), 128,000 max output, text and image in, text out. Endpoints: Responses, Chat Completions, Batch. Cache writes bill at 1.25× input.

**The 272K cliff applies to every model in the family**, not only Astra: prompts with more than 272K input tokens are priced at 2× input and cache rates and 1.5× output **for the full request**. Batch is roughly 50% off. Regional and FedRAMP processing carries a 10% uplift.

Two details worth pointing out to a user choosing between the Sols: `gpt-6.1-sol` has the same input and output price as `gpt-6-sol` but **half the cached-input rate** ($0.10 vs $0.20), and it drops the `none` effort level. A workload that depended on `none` can't move to 6.1 Sol without changing how it runs.

### Choosing

OpenAI's guidance: experiment with different models and reasoning settings on the same inputs, and "keep the lightest setting that meets your quality bar."

| Situation | Start with |
|---|---|
| Hardest reasoning, long-horizon agentic work, the quality ceiling | `gpt-6-astra` |
| Complex projects where cost matters (OpenAI's examples: a board presentation from financial results, a website from a product brief) | `gpt-6.1-sol`, compared against Astra on the same task |
| Focused, high-volume work: classification, extraction, routing | `gpt-6-luna` |
| Needs `reasoning.effort: "none"` | `gpt-6-luna` or `gpt-6-sol` |
| Tool calling over Chat Completions | `gpt-6-luna` or `gpt-6-sol` at `none` only. Otherwise move to Responses. |
| Agentic coding in a Codex harness | `context/models/openai-codex/codex-prompting-guide` |

---

## Reasoning effort

`reasoning.effort` (Responses) or `reasoning_effort` (Chat Completions): `low`, `medium` (default), `high`, `xhigh`, `max`.

- **`none`** exists only on GPT-6 Sol and GPT-6 Luna. On Astra and 6.1 Sol, use `low`.
- **`minimal`:** OpenAI states that 6.1 Sol supports neither `none` nor `minimal`, and its migration note for the family is "If your existing request uses `minimal`, start with `low` and compare results on representative tasks."
- When migrating, OpenAI says to preserve your current effective reasoning effort where supported, then tune. Level names still don't transfer between models, so re-sweep against evals.
- **Change effort mid-conversation with a `configuration_update` input item.** It adjusts reasoning effort without rewriting the prompt prefix, so the cache survives, and the new level applies until the next override. Run a conversation at `low` and step up for the turns that need it.

## API constraints that change what you can recommend

| Constraint | Detail |
|---|---|
| Tool calling | **Astra and 6.1 Sol require the Responses API for tool calling.** Chat Completions works for them without tools. On GPT-6 Sol and Luna, Chat Completions function calling works only with `reasoning_effort: "none"`; use Responses for reasoning with tools. |
| Sampling parameters | When reasoning is anything other than `none`, `temperature`, `top_p`, and `top_logprobs` are unsupported. On Chat Completions also remove `logprobs`; on Responses remove `message.output_text.logprobs` from `include`. |
| Cache TTL | Replace `prompt_cache_retention` with `prompt_cache_options.ttl` set to `"30m"` when migrating from GPT-5.5 or earlier. |
| Reading output | Don't assume text is at `output[0].content[0].text`; the `output` array can hold tool calls and reasoning items. Use the SDK's `output_text`. |
| Reasoning items | Chat Completions never carries reasoning items across turns, which degrades multi-call performance and raises reasoning token use. Use Responses with `previous_response_id` or pass reasoning items back. |
| Data residency | Fast mode is not available with EU data residency for GPT-6 Astra, GPT-6 Sol, or GPT-6 Luna. Ultrafast mode supports US data residency and global processing only. |
| Prompt objects | `v1/prompts` shuts down 2026-11-30. Keep prompt builders in code near the feature, with typed arguments and tests. |
| Snapshots | Pin production to a specific snapshot and re-run evals when you change it. |

---

## Prompt structure

- **Roles.** `developer` messages carry the application's rules and outrank `user` messages. OpenAI's analogy: developer messages are the function definition, user messages are the arguments. The `instructions` parameter sets high-level behavior for the current response only (see the Astra guide for the `previous_response_id` trap).
- **Order of a developer message:** Identity → Instructions → Examples → Context. Put content you reuse across requests at the beginning of the prompt, and among the first parameters in the request body, so it caches.
- **Markdown plus XML.** Markdown headers and lists for sections and hierarchy; XML tags to delimit supplied content and examples.
- **Few-shot.** A handful of input/output pairs showing a diverse range of inputs. Try zero-shot first, then add examples if needed.
- **No chain-of-thought.** OpenAI: prompting a reasoning model to "think step by step" or "explain your reasoning" is unnecessary. Keep prompts simple and direct, state the end goal specifically, and spell out any constraints.
- **Precision by register.** OpenAI's prompt-engineering page says GPT models want "precise instructions that explicitly provide the logic and data required," while reasoning models do better with high-level guidance, "like a senior co-worker." Every GPT-6 model reasons unless set to `none`. Resolve it by effort: explicit logic and data at `none`/`low`/`medium`, goal and constraints at `high` and above.

## OpenAI's prompt snippets for GPT-6

These come from the "Using GPT-6" page and are reproduced in full. Use one when the matching behavior is the problem; don't add all of them by default. Note the first group pushes hard toward acting without asking ("You don't need user permission for reversible tasks…", "Do not introduce unsolicited warnings…"). Pair it with the approval-boundary block, or your own confirmation rule, in any product that writes to external systems.

**Initiative and follow-through** — the model stops short, offers instead of acting, or asks before doing authorized work:
```text
You should infer the user's intent and task scope from the instructions and prior conversation context. Your job is to bias towards action and carry the user's intended task to completion.

When the user expresses intent to perform new work or fix an existing issue, persist until the user's intended goal is complete. Progress autonomously towards the user's goal (e.g. creating isolated worktrees / checkouts if needed, resolving merge conflicts, read-only actions, creating draft PRs etc.) unless they are clearly destructive or irreversible.
```
```text
When the user's prompt indicates a request for action, such as "can you...", "I want to...", "help me..." and similar expressions, treat these as instructions to do the work and take action. Do not stop at acknowledging capability (e.g. "Yes…"), proposing a plan, or offering to continue. Do not settle for a partial or "helpful enough" solution that does not fully satisfy the user's task to save time, effort or tokens. If a task requires sustained work, complete all the necessary work until the intended outcome is fulfilled.
```
```text
Before asking the user clarifying questions, you should complete the work that is already authorized from context and necessary to make the proposed action concrete and reviewable. The user should be approving a concrete, reviewable result. For example, before deploying a change, writing to an external application, merging a PR or publishing a site, do all the required work first so that user approval is the final step. You don't need user permission for reversible tasks, read-only actions, reviews or fixes, or anything for which authorization is provided earlier in the session or strongly implied from the task instruction.

Do not introduce unsolicited warnings, disclaimers, approval flows, or safety/compliance checklists due to hypothetical risk.
```

**Instruction following** — a skill overrides what the user asked for:
```text
The user's instructions take precedence over guidelines provided in a skill. If explicit user instructions conflict with a skill's instructions, prioritize the user's instructions.
```
```text
If a skill causes you to ask for permission or confirmation, pause, leave requested work unfinished, or diverge from the user's intent, name and link to the exact SKILL.md file you read, quote the relevant instruction, and briefly explain how it applies. Distinguish explicit skill requirements from your interpretation of guidelines.
```

**Personality and writing style** — output is over-formatted, jargon-heavy, or full of stock phrasing:
```text
Default to using clear, concise paragraphs, each developing one main idea. Use lists only when the information is genuinely parallel, sequential, or easier to compare, and avoid nested lists unless the hierarchy cannot be expressed clearly in prose. Use plain, simple language: familiar words, concrete examples, and precise verbs. Prefer active voice and direct statements.

Make sure to state the main point clearly and early, then develop it with the explanation and detail the reader needs. Let each sentence build on what came before. Develop the points that matter and provide enough support to be useful.
```
```text
Use plain language over jargon, and reference technical details only to the degree that it helps illustrate an idea or your work to the user. Communicate complex concepts in a clear and cohesive manner, and calibrate your writing to the level of background knowledge assumed from the user's prompt and context.
```
```text
Avoid using slop words or phrases like "Bottom Line:" in conclusions, "delve," "foster," "leverage," "it's worth noting," "importantly," "Question? Answer." or "This isn't about X. It's about Y.", "genuinely" or hyphenated compound descriptions and adjectives. Do not use concluding summary statements such as "In short:..", "The simplest mental model is:...".

State the intended action directly. Avoid adding what you won't do, what will remain unchanged, or how you'll separate or categorize results. Do not use contrastive framing such as "X, not Y" that introduces an unprompted alternative that the user didn't ask about. Avoid invented compound labels like "exact-head checks" and "editorial-row layouts", vague qualifiers, and canned transitions; use plain verbs and prepositions to state the actual relationship directly.
```

**Subagent delegation** — multi-agent work runs serially, or inter-agent messages are unreadable:
```text
If at any point you can parallelize work by delegating tasks to another agent (no matter if you are the root or subagent), you should do so using collaboration tools if it could save time or improve quality.
```
```text
Messages that you send to other agents and your final answer may be read by a human, so ensure they are legible. Always put proper spaces between words and/or numbers.
```

**Testing and verification** — it writes tests nobody needs, or keeps re-testing:
```text
Do not write tests for reversible, low-impact changes that mirror the implementation. If you do choose to verify your work with tests, make sure that the tests are meaningful and necessary to verify implementation.

Run tests appropriate to the change and complete required checks. Once those pass, broaden or repeat testing only when new changes, failures, or unresolved concerns justify it; otherwise, continue toward completing the task.
```

**Autonomy and approval boundaries** — a compact alternative when you want the boundary stated by request type:
```text
For requests to answer, explain, review, diagnose, or plan, inspect the relevant materials and report the result. Do not implement changes unless the request also asks for them.

For requests to change, build, or fix, make the requested in-scope local changes and run relevant non-destructive validation without asking first.

Require confirmation for external writes, destructive actions, purchases, or a material expansion of scope.
```

**What a short answer must include**, and **tone**:
```text
Lead with the conclusion. Include the evidence needed to support it, any material caveat, and the next action. Omit secondary detail and repetition.

Keep all required facts, decisions, caveats, and next steps. Trim introductions, repetition, generic reassurance, and optional background first.
```
```text
State the answer directly. If the user reports a problem, acknowledge the specific issue before giving the next step. Use reassurance only when it is relevant. Omit generic praise and unnecessary sign-offs.
```

**Routing work to Programmatic Tool Calling** — a template; fill the brackets:
```text
<tool_orchestration>
Use Programmatic Tool Calling for [bounded stage] using only [eligible tools]. Run independent calls concurrently when safe. Use only documented tool input and output fields.

Process and reduce the intermediate results, then emit exactly [output schema], including the evidence needed for the final answer.

Stop when [condition] is met. Retry transient failures at most [R] times. Do not repeat completed calls or perform side-effecting actions. If a required result is still missing, return a clear structured failure.

Use direct tool calls for [semantic judgment, approval, or final validation].
</tool_orchestration>
```

### Agentic and coding prompts

From the prompt-engineering page, written for `gpt-6-astra`:

- Agentic tasks: plan thoroughly, give a short preamble before notable tool calls, and track work with a TODO tool. "Keep going until the user's query is completely resolved."
- Coding: define the agent's role, **include concrete examples of how to invoke commands**, require testing with unit tests or commands, and set Markdown standards (file paths, functions, and classes in backticks). This is the opposite of Anthropic's advice to delete tool-call examples, so don't port that deletion here.
- Front-end: Tailwind CSS, shadcn/ui, or Radix Themes; Lucide, Material Symbols, or Heroicons; Motion for animation. For work in an existing codebase, supply principles, UI/UX rules, structure, components, and page templates.

### Lean prompts

OpenAI's lean-prompt finding (eval scores up roughly 10–15%, tokens down 41–66%) was measured on GPT-5.6 and has not been restated for GPT-6. The "Using GPT-6" page does ask for less by default: concise paragraphs, fewer tests, no slop phrasing. Stating each instruction once remains the safe edit; verify the size of the gain on your own evals.

---

## Migrating a prompt from GPT-5.x

1. Move tool-calling workloads to Responses if the target is Astra or 6.1 Sol.
2. Replace `none` (on Astra and 6.1 Sol) and `minimal` with `low`, then compare on representative tasks.
3. Remove `temperature`, `top_p`, and logprobs parameters unless running at `none`.
4. Swap `prompt_cache_retention` for `prompt_cache_options.ttl`.
5. Re-run the effort sweep and your evals. Then trim the prompt.

OpenAI ships a Codex skill for the mechanical parts: `$openai-docs migrate this project to the GPT-6 model family`.

## Cross-references

- Astra-only features: `gpt-6-astra-guide.md`
- Previous generation: `context/models/openai-gpt-5-family/gpt-5-6-guide.md`
- Cross-vendor pricing and switching costs: `references/model-selection.md`
- Caching detail: `references/caching-and-cost.md`
