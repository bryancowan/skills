# Claude 5 Family Prompting Guide

## Overview

The current Claude lineup is **Claude Fable 5**, **Claude Opus 5**, **Claude Sonnet 5**, and **Claude Haiku 4.5**. Claude Mythos 5 shares Fable 5's specs and pricing but is invitation-only (Project Glasswing). Everything from Opus 4.8 and earlier is legacy.

The single biggest prompting shift in this generation: **`effort` replaced thinking budgets, sampling parameters were removed, and prefill is gone.** Prompts written for Claude 4.x mostly still work, but several instructions that *helped* older models now actively hurt — see "Instructions to delete" below.

Sourced: 2026-07-26

Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5
- https://platform.claude.com/docs/en/about-claude/models/overview
- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/about-claude/models/migration-guide

---

## Model selection

| Model | API ID | Price (in / out per MTok) | Context / Max output | Pick it for |
|---|---|---|---|---|
| Claude Fable 5 | `claude-fable-5` | $10 / $50 | 1M / 128k | Highest available capability: multiday autonomous runs, hardest unsolved problems, parallel subagent fleets |
| Claude Opus 5 | `claude-opus-5` | $5 / $25 | 1M / 128k | Complex agentic coding, enterprise knowledge work, code review, vision-heavy workflows |
| Claude Sonnet 5 | `claude-sonnet-5` | $2 / $10 through 2026-08-31, then $3 / $15 | 1M / 128k | Best speed-to-intelligence ratio: production coding, agentic tool use, data analysis |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1 / $5 | 200k / 64k | Real-time and high-volume work, subagent tasks, cost-sensitive deployments |

Model IDs from the 4.6 generation onward are dateless but still **pinned snapshots**, not evergreen pointers.

Two viable starting strategies: start efficiency-first with Haiku 4.5 and upgrade only on a measured capability gap, or start capability-first with Opus 5, tune the prompt, then optimize downward via `effort` before switching models. **Tuning effort is usually a better lever than switching models.**

---

## Effort: the primary cost/intelligence control

`effort` lives in `output_config` and takes `low`, `medium`, `high`, `xhigh`, `max`. It defaults to `high` on Opus 5 and Sonnet 5 (Claude API and Claude Code).

| Level | Use for |
|---|---|
| `max` | Absolute maximum capability, no token constraints. Can overthink. |
| `xhigh` | The hardest coding and agentic work. Step up here from the default. |
| `high` | Default. Balances tokens and intelligence for most work. |
| `medium` | Cost-sensitive workloads that trade some intelligence. |
| `low` | Short scoped tasks and latency-sensitive work that isn't intelligence-sensitive. |

Behavior notes that change how you prompt:

- **Effort is respected strictly at the low end.** At `low` and `medium` the model scopes work to exactly what was asked. Good for cost, but risks under-thinking on moderately complex tasks.
- **On Opus 5, `low` and `medium` produce strong quality at a fraction of the tokens.** Use them liberally as the primary cost/latency control wherever quality holds.
- **On Fable 5, lower effort settings often exceed `xhigh` on prior models.**
- Rough Sonnet mapping when migrating: Sonnet 5 at `medium` ≈ Sonnet 4.6 at `high`; Sonnet 5 at `high` ≈ Sonnet 4.6 at `max`.
- If you see shallow reasoning, **raise effort rather than prompting around it.** If you must stay at `low`:
  ```text
  This task involves multistep reasoning. Think carefully through the problem before responding.
  ```
- At `high`/`xhigh`/`max`, leave `max_tokens` headroom — thinking counts against it. Start at 64k. A tight budget produces an answer that is almost all thinking followed by a truncation with `stop_reason: "max_tokens"`.

### Thinking

Adaptive thinking is **on by default** on Opus 5 and Sonnet 5, and **always on** (not disableable) on Fable 5.

- Manual extended thinking (`thinking: {type: "enabled", budget_tokens: N}`) returns a 400 error. Use `effort` instead.
- On Opus 5, `thinking: {type: "disabled"}` works only at `effort: "high"` or below.
- On Fable 5, raw thinking is never returned; opt into summaries with `thinking: {display: "summarized"}` (default is omitted).
- If the model thinks more often than you want (common with large system prompts):
  ```text
  Thinking adds latency and should only be used when it will meaningfully improve answer quality, typically for problems that require multistep reasoning. When in doubt, respond directly.
  ```

**Running Opus 5 with thinking disabled has two artifacts:** tool calls occasionally written as visible text instead of a `tool_use` block, and internal XML tags leaking into output. Prefer thinking-on at low effort over thinking-off. If you must disable it, do **not** add a rule telling the model not to think (that increases tag leakage) — use:
```text
When you use a tool, you may say a brief sentence first. If no tool can express what the user asked for, say so instead of guessing. Do not include internal or system XML tags in your response.
```

---

## Instructions to delete from older prompts

These helped Claude 4.x and now cause measurable harm:

| Delete | Why |
|---|---|
| "Include a final verification step" / "use a subagent to verify" | Opus 5 verifies its own work already; these cause over-verification and wasted tokens with no quality gain. |
| "Double-check your answer" / "re-verify before responding" | Same — compounds with built-in self-correction. |
| "After every 3 tool calls, summarize progress" | Opus 4.8+ and Sonnet 5 already give regular high-quality updates. |
| "CRITICAL: You MUST use this tool when…" | Causes overtriggering. Plain "Use this tool when…" is enough. |
| "If in doubt, use [tool]" / "Default to using [tool]" | Overtriggers. Use "Use [tool] when it would enhance your understanding of the problem." |
| Assistant-message prefill | Returns 400 on 4.6+ models. Use structured outputs, tool enums, or a direct system instruction instead. |
| `temperature` / `top_p` / `top_k` | Return 400 on Opus 5, Sonnet 5, Fable 5. Steer tone and variety through the prompt. |
| "Echo / transcribe / explain your internal reasoning as your response" | On Fable 5 this can trigger the `reasoning_extraction` refusal category and elevated fallbacks. Read the structured `thinking` blocks instead. |

Fable 5 in particular: **skills and prompts tuned for prior models are often too prescriptive and degrade its output.** Review and remove older scaffolding before assuming a regression.

---

## Verbosity, tone, and communication

Opus 5 is the exception to the family trend: its **default user-facing responses run longer** than prior models, and changing effort does not reliably change visible response length. Prompt for it explicitly.

```text
Keep responses focused, brief, and concise. Keep disclaimers and caveats short, and spend most of the response on the main answer. When asked to explain something, give a high-level summary unless an in-depth explanation is specifically requested.
```

In a long system prompt, repeat a short reminder near the end:
```text
<tone_preference>
Keep outputs reasonably concise.
</tone_preference>
```

Sonnet 5 and Opus 4.8 instead *calibrate* length to task complexity. To tighten:
```text
Provide concise, focused responses. Skip non-essential context, and keep examples minimal.
```

**Positive examples of the style you want beat negative instructions** about what not to do. This holds across the family.

Written deliverables (files on disk) are separately long on Opus 5:
```text
Match the length of written documents to what the task needs: cover the substance, but do not pad with filler sections, redundant summaries, or boilerplate.
```

Agentic narration on Opus 5 — describe cadence and shape rather than forbidding it:
```text
Before your first tool call, say in one sentence what you're about to do. While working, give a brief update only when you find something important or change direction. When you finish, lead with the outcome: your first sentence should answer "what happened" or "what did you find," with supporting detail after it for readers who want it.
```

Correction narration on Opus 5:
```text
Only correct an earlier statement when the error would change the user's code, conclusions, or decisions. State corrections plainly and briefly, then continue the task. For slips that change nothing for the user, make the fix and move on without noting it.
```

Fable 5's readability addendum for long asynchronous runs (its final message is often the user's first look at hours of work):
```text
Terse shorthand is fine between tool calls (that's you thinking out loud, and brevity there is good). Your final summary is different: it's for a reader who didn't see any of that. Write it as a re-grounding, not a continuation of your working thread: the outcome first, then the one or two things you need from them, each explained as if new. Drop the working shorthand, write complete sentences, spell out terms, and avoid arrow chains or labels you made up earlier. If you have to choose between short and clear, choose clear.
```

To suppress markdown/bullet overuse in long-form writing:
```text
<avoid_excessive_markdown_and_bullet_points>
When writing reports, documents, technical explanations, analyses, or any long-form content, write in clear, flowing prose using complete paragraphs and sentences. Reserve markdown primarily for `inline code`, code blocks, and simple headings (## and ###). Incorporate items naturally into sentences instead of listing them with bullets or numbers, unless the items are truly discrete or the user asked for a list.
</avoid_excessive_markdown_and_bullet_points>
```

Claude's latest models default to LaTeX for math. To disable, say so explicitly (no LaTeX/MathJax, use `/`, `*`, `^`).

---

## Scope control

Opus 5 expands task scope and applies its own judgment about what the task should be. For narrow tasks:
```text
Deliver what was asked, at the scope intended. Make routine judgment calls yourself, and check in only when different readings of the request would lead to materially different work. If the request seems mistaken or a better approach exists, say so in a sentence and continue with the task as asked rather than quietly narrowing, widening, or transforming it. Finish the whole task, and stop short of actions that are clearly beyond what was asked.
```

Fable 5 at higher effort can over-tidy code:
```text
Don't add features, refactor, or introduce abstractions beyond what the task requires. A bug fix doesn't need surrounding cleanup and a one-shot operation usually doesn't need a helper. Don't design for hypothetical future requirements: do the simplest thing that works well. Don't add error handling, fallbacks, or validation for scenarios that cannot happen. Trust internal code and framework guarantees. Only validate at system boundaries (user input, external APIs).
```

Fable 5 can also take unrequested actions (drafting emails, creating backup branches):
```text
When the user is describing a problem, asking a question, or thinking out loud rather than requesting a change, the deliverable is your assessment. Report your findings and stop. Don't apply a fix until they ask for one. Before running a command that changes system state (restarts, deletes, config edits), check that the evidence actually supports that specific action.
```

For irreversible actions on any model in the family:
```text
Consider the reversibility and potential impact of your actions. Take local, reversible actions like editing files or running tests freely, but for actions that are hard to reverse, affect shared systems, or could be destructive, ask the user before proceeding. Examples that warrant confirmation: deleting files or branches, dropping tables, rm -rf, git push --force, git reset --hard, pushing code, commenting on PRs, sending messages. When encountering obstacles, do not use destructive actions as a shortcut.
```

---

## Agentic and long-horizon work

**Subagents.** Opus 5 and Fable 5 both delegate more readily than prior models; Opus 4.8 delegates *less*. Cap Opus 5:
```text
Delegate to a subagent only for large tasks that are genuinely independent and parallelizable, such as a wide multi-file investigation. Do not delegate work you can finish yourself in a handful of tool calls, and do not use subagents to verify or double-check your own work. If one subagent can complete the task, use one rather than several, and keep spawn counts low.
```
Encourage Fable 5 instead — it's dependable at sustaining parallel subagents, and long-lived subagents that keep context across subtasks save cost through cache reads:
```text
Delegate independent subtasks to subagents and keep working while they run. Intervene if a subagent goes off track or is missing relevant context.
```
Prefer asynchronous orchestrator↔subagent communication over blocking on each return. Fresh-context verifier subagents outperform self-critique.

**Grounding progress claims** (Fable 5; near-eliminated fabricated status reports in Anthropic's testing):
```text
Before reporting progress, audit each claim against a tool result from this session. Only report work you can point to evidence for; if something is not yet verified, say so explicitly. Report outcomes faithfully: if tests fail, say so with the output; if a step was skipped, say that; when something is done and verified, state it plainly without hedging.
```

**Checkpointing.** Rather than enumerating every case:
```text
Pause for the user only when the work genuinely requires them: a destructive or irreversible action, a real scope change, or input that only they can provide. If you hit one of these, ask and end the turn, rather than ending on a promise.
```

**Autonomous pipelines** (Fable 5 can end a turn on a statement of intent deep into a long session):
```text
You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task, so asking "Want me to…?" will block the work. For reversible actions that follow from the original request, proceed without asking. Before ending your turn, check your last paragraph. If it is a plan, an analysis, a question, a list of next steps, or a promise about work you have not done, do that work now with tool calls. End your turn only when the task is complete or you are blocked on input only the user can provide.
```

**Context budget.** Fable 5 occasionally suggests a new session when the harness shows a token countdown. Avoid surfacing counts; if you must:
```text
You have ample context remaining. Do not stop, summarize, or suggest a new session on account of context limits. Continue the work.
```
For harnesses with compaction or file-based memory:
```text
Your context window will be automatically compacted as it approaches its limit, allowing you to continue working indefinitely from where you left off. Do not stop tasks early due to token budget concerns. As you approach your token budget limit, save your current progress and state to memory before the context window refreshes.
```

**Multi-window workflows:** use a different prompt for the first context window (set up tests and scripts), have the model keep structured state (`tests.json`) plus freeform progress notes, use git as the state log, and prefer starting a fresh window over compaction — these models discover state from the filesystem well. Be prescriptive on restart: "Call pwd", "Review progress.txt, tests.json, and the git logs."

**Memory** (Fable 5 performs particularly well with a notes file):
```text
Store one lesson per file with a one-line summary at the top. Record corrections and confirmed approaches alike, including why they mattered. Don't save what the repo or chat history already records; update an existing note rather than creating a duplicate; delete notes that turn out to be wrong.
```

**send_to_user tool.** For long asynchronous agents, define a client-side tool whose input you render verbatim (tool inputs are never summarized), so the agent can surface deliverables mid-run without ending its turn. Defining it is not enough — pair it with elicitation language, and don't route narration through it.

**Parallel tool calls** — the family runs independent calls in parallel; this snippet pushes success toward 100%:
```text
<use_parallel_tool_calls>
If you intend to call multiple tools and there are no dependencies between the tool calls, make all of the independent calls in parallel. However, if some tool calls depend on previous calls to inform dependent values, call them sequentially. Never use placeholders or guess missing parameters in tool calls.
</use_parallel_tool_calls>
```

---

## Task-shaped patterns

**Code review harnesses.** Both Opus 5 and Sonnet 5 follow "only report high-severity issues" or "be conservative" *literally*, which reads as a recall regression when it's a harness effect. Ask for coverage and filter downstream:
```text
Report every issue you find, including ones you are uncertain about or consider low-severity. Do not filter for importance or confidence at this stage — a separate verification step will do that. For each finding, include your confidence level and an estimated severity so a downstream filter can rank them.
```

**Anti-hallucination in agentic coding:**
```text
<investigate_before_answering>
Never speculate about code you have not opened. If the user references a specific file, you MUST read the file before answering. Never make any claims about code before investigating unless you are certain of the correct answer.
</investigate_before_answering>
```

**Generalizing solutions instead of passing tests:**
```text
Write a high-quality, general-purpose solution using the standard tools available. Implement a solution that works correctly for all valid inputs, not just the test cases. Do not hard-code values or create solutions that only work for specific test inputs. If the task is unreasonable or infeasible, or if any of the tests are incorrect, inform me rather than working around them.
```

**Action vs. suggestion.** These models are literal: "Can you suggest some changes" gets suggestions. Say "Change this function to improve its performance." To set a default:
```text
<default_to_action>
By default, implement changes rather than only suggesting them. If the user's intent is unclear, infer the most useful likely action and proceed, using tools to discover missing details instead of guessing.
</default_to_action>
```
Invert it with a `<do_not_act_before_instructions>` block when you want research-then-recommend behavior.

**Literal instruction following.** Sonnet 5 and Opus 4.8 do not silently generalize an instruction from one item to another. State scope explicitly: "Apply this formatting to every section, not just the first one."

**Frontend design.** Sonnet 5 settles into a default house style on open-ended briefs; generic negatives just move it to a different fixed palette. Two things work: specify a concrete alternative (palette hexes, typeface character, radius, section structure), or have the model propose 4 distinct directions and let the user pick — this is the recommended substitute for the removed `temperature` knob. Plus:
```text
<frontend_aesthetics>
NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white or dark backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character. Use unique fonts, cohesive colors and themes, and animations for effects and micro-interactions.
</frontend_aesthetics>
```

**Interactive coding products.** Use `xhigh` or `high` effort, add an auto mode, and minimize required user turns. Well-specified first turns maximize autonomy and token efficiency; underspecified prompts dribbled across turns cost more and sometimes perform worse.

**Give the reason, not only the request** (Fable 5 connects task to context better when it knows intent):
```text
I'm working on [the larger task] for [who it's for]. They need [what the output enables]. With that in mind: [request].
```

**Start Fable 5 at the top of your difficulty range.** Testing it only on simple workloads undersells its range.

---

## Structure fundamentals (all current models)

- **Be explicit.** Treat Claude as a brilliant new employee with no context on your norms. Golden rule: if a colleague with minimal context would be confused by your prompt, so will Claude.
- **Give the reason for a rule.** "Never use ellipses" is weaker than "Your response will be read aloud by a text-to-speech engine, so never use ellipses since it will not know how to pronounce them." Claude generalizes from the explanation.
- **Examples are the strongest formatting lever.** 3–5, relevant, diverse, wrapped in `<example>` tags inside `<examples>`.
- **XML tags** for mixed content: `<instructions>`, `<context>`, `<input>`. Nest where there's hierarchy.
- **A one-sentence role** in the system prompt measurably focuses behavior.
- **Long context (20k+ tokens): put the documents at the top, the query at the end.** Queries at the end improved response quality by up to 30% in Anthropic's testing on complex multi-document inputs. Wrap each doc in `<document index="n">` with `<source>` and `<document_content>`, and ask Claude to pull relevant quotes into `<quotes>` tags before answering.
- **Tell Claude what to do, not what to avoid.** "Do not use markdown" → "Write in smoothly flowing prose paragraphs."
- **Match prompt style to desired output style** — markdown in the prompt begets markdown in the response.

---

## Cost levers

- Prompt caching: 5-minute writes cost 1.25× base input, 1-hour writes 2×, cache hits 0.1×. Breaks even after one read (5m) or two reads (1h). Minimum cacheable prompt on Opus 5 dropped to **512 tokens** (from 1,024).
- Batch API: 50% off input and output. Stacks with caching. Not available with fast mode.
- Fast mode (research preview, Opus 5 / Opus 4.8): up to 2.5× output speed at $10/$50 per MTok.
- `inference_geo: "us"` applies a 1.1× multiplier on every token category.
- The 1M context window is billed at standard rates — a 900k request costs the same per token as a 9k one.
- **Re-baseline your token counts.** Claude 4.7 and later use a tokenizer that produces ~30% more tokens for the same text. `max_tokens` values tuned on 4.6 may now truncate.

See `references/caching-and-cost.md` and `references/model-selection.md` for the cross-vendor picture.
