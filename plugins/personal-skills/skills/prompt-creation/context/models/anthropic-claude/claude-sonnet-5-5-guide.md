# Claude Sonnet 5.5 Prompting Guide

## Overview

Claude Sonnet 5.5 (`claude-sonnet-5-5`, $2 / $10 per MTok) is the current Sonnet. **Existing Sonnet 5 prompts should perform well without changes**, so this guide is a list of deltas: find the symptom you observe and apply that section only. For the hardest long-horizon work, Anthropic says an Opus model is the better choice.

Read `claude-5-family-guide.md` first for what applies across the family. Every snippet below is Anthropic's wording, measured on Sonnet 5.5. Re-check against your own evals before applying one to another model.

Sourced: 2026-10-03

Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices

| Symptom | Section |
|---|---|
| Unsure which effort level; turns run longer or shorter than on Sonnet 5 | Calibrate effort |
| Stops to check in before a coding task is done, or does more than asked | Steer initiative and scope |
| The integration runs with thinking off today | Running without up-front thinking |
| JSON answers to multi-step tasks are wrong or don't parse | Reasoning tasks with JSON output |
| Long agentic turns look silent | User-facing progress updates |
| Answers from training knowledge when a search would catch changes | Tool use in chat and knowledge work |
| Mid-task user messages are ignored or treated as injected text | Mid-turn user messages |
| Code changes reported done without a test or build run | Verification on coding tasks |
| Tool called with wrong letter case or a slightly different parameter name | Tolerant tool-call handling |
| Answers about dense charts or technical drawings miss detail | Tools for complex visual inputs |
| Requests return `stop_reason: "refusal"` | Safeguard refusals |

---

## Calibrate effort

Levels are **recalibrated from Sonnet 5**: the same name doesn't buy the same thinking. Run a fresh sweep.

| Workload | Start at |
|---|---|
| General (the Claude API default) | `high` |
| Agentic coding and multistep tool use, well-specified | `medium`, moving to `high` for harder or longer tasks |
| Chat and other latency-sensitive work | `medium` or `low` |

Effort changes how the model finishes agentic work, not only how much it thinks:

- At `low`, it keeps thinking short and **can skip verifying a change** (see Verification on coding tasks).
- At `low` and `medium`, on long agentic tasks, it's **more likely to stop and check in** (see Steer initiative and scope).
- From `medium` up, it thinks briefly before almost every reply, even a greeting. **Asking it in the system prompt to think less doesn't reliably work.** Lower the effort level. At `low` it skips thinking on most simple requests.
- Set `max_tokens` with room for thinking plus the reply. For agentic coding, set 128,000 and stream.
- Reserve `xhigh` and `max` for measured gains; thinking and replies get much longer, and `between_tools` isn't accepted there.
- Changing top-level `effort` between requests invalidates the cache; a per-message effort change (beta) keeps it, and needs adaptive thinking. Example: run an interactive session at `low` and raise to `high` when the user submits a hard problem.

## Steer initiative and scope

**Carrying work through.** At `low` and `medium` the model sometimes pauses to confirm a plan, asks a question it could answer itself, or stops after one part of a multipart task. Try a higher effort first. To keep it working without changing effort:

```text
Keep working until everything the user asked for is done, and only stop to ask when you can't go on without the user or before a risky step.

When the work the user asked for is done and checked, stop and report. Don't add features, tests, files, docs or refactors that weren't asked for. If you think one would help, mention it at the end instead of doing it.
```

Sessions at those levels then run longer and cost more. This doesn't replace your own rules about risky or irreversible actions.

**Unrequested additions when coding.** The model tends to add tests, documentation, and small supporting files that fit the repo's conventions, at every effort level and more at higher effort. The requested change itself stays close to what was asked, and most teams welcome this. To limit changes to what was requested, add **only the second paragraph** above (starting "When the work the user asked for is done").

**Thoroughness at `xhigh` and `max`.** After finishing, the model can start its own rounds of review and verification, sometimes with subagents, and make related fixes. Run routine work at `high` or below, where this is rare. To keep the thoroughness but direct it at the task:

```text
When the work the user asked for is done and its checks pass, stop and report. Don't start extra rounds of review or hardening on your own, and don't launch reviewer sub-agents unless the user asked for a review. If you think a deeper review is worth doing, say so at the end.
```

At `max` effort on coding tasks, Anthropic measured this stopping reviewer subagents and cutting session cost by about a third with no quality change. It reduces self-started review rounds by the main agent but doesn't remove them.

**Open-ended requests.** "Show me what you can do with this" can lead to a built presentation when you wanted ideas:

```text
When the user asks for ideas, options or a plan, give them that and stop. Don't start building or changing anything until they say to go ahead.
```

## Running without up-front thinking

`thinking: {"type": "disabled"}` returns a 400. The lowest setting is `thinking: {"type": "between_tools"}`.

- Accepted at **`high` effort or below**. At `xhigh` or `max` it returns a 400.
- With `between_tools`, effort can't change mid-conversation: a per-message `output_config.effort` that differs from the level in effect returns a 400.
- It takes no other field: `display`, `budget_tokens`, or `block_binding` sent with it returns a 400.
- **Remove any instruction telling the model not to think.** Such lines make internal XML tags in visible output more likely.
- Read the response by block type. A response can begin with a `thinking` block.
- Pass `thinking` blocks back unchanged with the rest of the assistant turn.
- **In a request without tools, `between_tools` means the model answers without thinking first.** For tasks that need a few steps of working out, use adaptive thinking instead.

## Reasoning tasks with JSON output

Applies when you want JSON for a task that needs working out: totaling figures from a document, applying a rule, ranking items. On these the model often answers without thinking first, particularly at `low` and `medium`.

**With structured outputs (preferred).** The response text holds only the JSON, so the model can work the problem out only in its thinking. To keep accuracy up:

- Add this line at the end of the system prompt (adaptive thinking):
  ```text
  Think the problem through before you answer.
  ```
  At `high` it brings accuracy close to `xhigh` for a modest increase in output tokens. At `low` and `medium` it raises accuracy, though not to the `high` level, with a larger token increase.
- Or use `xhigh` with adaptive thinking, which gives the highest accuracy even without the line.
- Use adaptive thinking, not `between_tools`. Without tools, the line has no effect there.
- At `low` and `medium` the model occasionally keeps thinking until it hits `max_tokens`. **Treat any response whose `stop_reason` is `"max_tokens"` as failed, even if its text holds valid JSON, and retry.**
- Splitting into two requests (one for the answer, one for the JSON) gave high accuracy and compliance in testing, but at very high cost and latency.

**Without structured outputs.** The model often works the problem out in the response text and writes the JSON at the end, which breaks a parser that expects the whole response to be JSON.

- **Parse the last JSON value.** Read only the `text` blocks. Starting at each `{` or `[`, try to parse a value; when one parses, continue from its end; keep the last value found. Don't take everything from the first `{` to the last `}`, because the model occasionally writes a draft before its final JSON. Check the result has the fields you expect and retry once if not.
- Or use `xhigh` with adaptive thinking: the working moves into the thinking and the model nearly always returns the JSON alone, at about the same total output tokens as `high`.

> This is the one place Anthropic recommends a think-first line on a current model. It asks the model to think, not to **write out** its reasoning. Asking for visible reasoning invites a `reasoning_extraction` refusal.

## User-facing progress updates

Notes between tool calls that run longer than a sentence or two come back as progress-update `thinking` blocks; shorter remarks stay `text`. At the default `thinking.display` their text is empty.

- Set `display: "updates"` (beta header `thinking-display-updates-2026-08-18`). With `between_tools` the notes come back with summary text and no `display` field is needed.
- For exact text mid-turn (a code snippet, a question), give the model a send-message tool, tell it to use the tool only for that, and declare it in the first request.
- **Remove "hold all findings for the final response."** Then, if you want updates at predictable points, say so in the system prompt.
- If turns still go quiet, have the harness append a reminder after about five silent tool-calling steps, as a turn-scoped system message:
  ```text
  The user hasn't heard from you in a while — say in a few words what you're doing, then continue.
  ```
  Stop after the second or third. Leave each reminder in `messages`. Frequent harness text after tool results can make the model suspect a prompt injection (see Mid-turn user messages).

## Tool use in chat and knowledge work

Sonnet 5.5 sometimes answers from training knowledge when a search would catch details that have changed, such as what is allowed, required, or charged.

First **remove language that discourages tool use**: "only use tools when strictly necessary", "minimize tool calls". Then, if the product has a search tool:

```text
Use the search tool to check specifics that may have changed since your training, such as what is allowed, required or charged, even when you feel confident. For researched work such as a report or a comparison, gather current sources rather than writing from your training knowledge.
```

## Mid-turn user messages

Sonnet 5.5 is trained to resist indirect prompt injection, and sometimes treats a genuine user message as one. It happens when text arrives right after tool results: a user message delivered as a system message after a tool result or inside a `tool_result` block, a token countdown after every tool result, or per-step harness instructions.

- **Never put user text inside a `tool_result` block.** The model misreads that placement most often.
- Deliver mid-turn user input **as a user turn**: a text block in the user message that carries the `tool_result` blocks, after the last `tool_result`.
- Keep harness notices in a separate mid-conversation system message **after** the user's words. Never put a notice and the user's words in the same block.
- In interactive sessions where users can type mid-turn, **don't add your own token or budget countdown** after tool results. Task budgets (beta) add a similar countdown but haven't been seen to cause this.
- If a reminder of your own triggers the reaction, send it less often.

## Verification on coding tasks

Sonnet 5.5 generally checks its work before reporting a change done. At `low` effort it sometimes doesn't, for example skipping the tests because dependencies aren't installed. If transcripts show changes reported complete with no test or build output:

```text
When you change code that can be run, built, or type-checked, run a real check that exercises the change before reporting it done: the project's tests, type-checker, or build, or the changed command itself. A syntax-only check, or a check command that failed to start, does not count; if all that is missing is the project's declared dependencies, install them with its own package manager and lockfile (e.g. npm install, pip install -r requirements.txt), never via sudo or the system package manager, unless told not to. Only if no real check can run here, say which one you did not run and why instead of reporting the change as done.
```

At `low` effort it makes skipped or superficial checks rare, with no measurable change in task quality and only slightly higher cost.

> This is a run-the-build **deliverable**, not "double-check your answer" scaffolding. It belongs in a Sonnet 5.5 coding prompt at `low` effort; the Opus 5 advice to delete verification instructions does not transfer here.

## Tolerant tool-call handling

Sonnet 5.5 occasionally calls a declared tool with different letter case (`bash` for `Bash`) or passes a known parameter under a slightly different name. In the harness, either accept the call when the match is unambiguous, or return a `tool_result` with `is_error: true` stating the exact expected name; the model usually corrects itself next turn. Don't treat it as fatal.

## Tools for complex visual inputs

Give the model a way to crop, zoom, or run code on dense charts and technical drawings.

- Charts: tools help at every effort level, and **help more than raising effort**. With tools at `high`, the model read charts more accurately than without tools at `max`, at a fraction of the cost.
- Technical drawings: tools help only from `high` up, most at `xhigh` and `max`.

Working tool definition: `platform.claude.com/cookbook/multimodal-crop-tool`.

## Safeguard refusals

A decline is a normal response with `stop_reason: "refusal"`; `stop_details.category` names it:

| Category | Meaning | Server-side fallback (beta) retries on Sonnet 5? |
|---|---|---|
| `cyber` | Could enable cyber harm (malware, exploit development). Finding vulnerabilities in source code is allowed. | Yes |
| `frontier_llm` | Could assist development of competing AI models | Yes |
| `bio` | Could enable biological harm. Everyday health and educational questions unaffected. | No |
| `reasoning_extraction` | Asks the model to reproduce internal reasoning in the response text | No |
| `general_harms` | Another usage-policy area. Benign work can also trigger it. | No |

If prompts ask the model to include its reasoning in the response, remove those instructions. Read reasoning from summarized thinking blocks (`display: "summarized"`). A short explanation of the answer or a summary of actions taken is still fine to ask for.
