# Claude 5 Family Prompting Guide

## Overview

The current Claude lineup is **Claude Fable 5.1**, **Claude Mythos 5.1**, **Claude Fable 5**, **Claude Mythos 5**, **Claude Opus 5**, **Claude Sonnet 5**, and **Claude Haiku 4.5**. Claude Opus 4.8 / 4.7 / 4.6 and Sonnet 4.6 are still documented and supported but are prior-generation.

Two prompting shifts define this generation:

1. **`effort` replaced thinking budgets, sampling parameters were removed, and prefill is gone.** Several instructions that *helped* Claude 4.x now actively hurt — see "Instructions to delete" below.
2. **Conversation history is now append-only.** On Fable 5.1, editing earlier turns between requests is an error, not just a cache miss. See "Append-only history" below. This is the single most common way an existing harness breaks on 5.1.

Prompts written for Fable 5 generally run well on Fable 5.1 without changes. The behavioral deltas that matter are in "Fable 5.1 behavioral deltas".

Sourced: 2026-09-12

Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5-1
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-fable-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5
- https://platform.claude.com/docs/en/about-claude/models/overview
- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/about-claude/models/migration-guide
- https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/

Companion: `references/context-engineering.md` covers the system-prompt-shrinking guidance that accompanies this generation.

---

## Model selection

| Model | API ID | Price (in / out per MTok) | Context / Max output | Pick it for |
|---|---|---|---|---|
| **Claude Fable 5.1** | `claude-fable-5-1` | $10 / $50 | 1M / 128k | Current top of range: multiday autonomous runs, hardest unsolved problems, parallel subagent fleets, dense-image vision work |
| Claude Mythos 5.1 | (invitation-only) | $10 / $50 | 1M / 128k | Shares Fable 5.1's specs, pricing, and prompting guidance; Project Glasswing access only |
| Claude Fable 5 | `claude-fable-5` | $10 / $50 | 1M / 128k | Superseded by 5.1; existing deployments run fine |
| Claude Opus 5 | `claude-opus-5` | $5 / $25 | 1M / 128k | Complex agentic coding, enterprise knowledge work, code review, vision-heavy workflows |
| Claude Sonnet 5 | `claude-sonnet-5` | $2 / $10 | 1M / 128k | Best speed-to-intelligence ratio: production coding, agentic tool use, data analysis |
| Claude Haiku 4.5 | `claude-haiku-4-5` | $1 / $5 | 200k / 64k | Real-time and high-volume work, subagent tasks, cost-sensitive deployments |

Model IDs from the 4.6 generation onward are dateless but still **pinned snapshots**, not evergreen pointers.

> **Sonnet 5 stayed at $2/$10.** The increase to $3/$15 that was scheduled for 2026-09-01 was cancelled; $2/$10 is now the standard price. If you are working from a guide or a budget written before September 2026, check this one.

Two viable starting strategies: start efficiency-first with Haiku 4.5 and upgrade only on a measured capability gap, or start capability-first with Opus 5, tune the prompt, then optimize downward via `effort` before switching models. **Tuning effort is usually a better lever than switching models.**

Anthropic maintains a separate prompting page per model (Fable 5.1, Fable 5, Sonnet 5, Opus 5, Opus 4.8). If the user names a specific model, read that page's deltas rather than assuming the family defaults apply.

---

## Effort: the primary cost/intelligence control

`effort` lives in `output_config` and takes `low`, `medium`, `high`, `xhigh`, `max`. It defaults to `high` on Fable 5.1, Opus 5, and Sonnet 5 (Claude API and Claude Code).

> **Effort level names are not comparable across models.** The same label buys a different amount of thinking on each model. Re-run your effort sweep against your own evals every time you change model — including on a point upgrade like Fable 5 → Fable 5.1.

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
- **On Fable 5.1, capability gains over Fable 5 show up at every level and are largest at the high end.** At `medium`, 5.1 roughly matches Fable 5 at lower cost — step down where your evals show quality holds. At `low`, 5.1 is often competitive with Opus and Sonnet models on cost per task while scoring higher, so include it in the comparison anywhere you'd otherwise reach for a smaller model at higher effort.
- Rough Sonnet mapping when migrating: Sonnet 5 at `medium` ≈ Sonnet 4.6 at `high`; Sonnet 5 at `high` ≈ Sonnet 4.6 at `max`.
- If you see shallow reasoning, **raise effort rather than prompting around it.** If you must stay at `low`:
  ```text
  This task involves multistep reasoning. Think carefully through the problem before responding.
  ```
- At `high`/`xhigh`/`max`, leave `max_tokens` headroom — thinking counts against it. Start at 64k. A tight budget produces an answer that is almost all thinking followed by a truncation with `stop_reason: "max_tokens"`.
- Effort can be **changed mid-conversation**. When only some turns need depth — e.g. a retrieval-heavy turn that needs to actually search — raise it for those turns rather than for the whole session.

### Thinking

Adaptive thinking is **on by default** on Opus 5 and Sonnet 5, and **always on** (not disableable) on Fable 5 and Fable 5.1.

- Manual extended thinking (`thinking: {type: "enabled", budget_tokens: N}`) returns a 400 error. Use `effort` instead.
- On Opus 5, `thinking: {type: "disabled"}` works only at `effort: "high"` or below.
- On Fable 5 and 5.1, raw thinking is never returned. Opt into `thinking: {display: "summarized"}` for summaries, or `display: "updates"` for progress updates (see below). The default is `"omitted"`.
- If the model thinks more often than you want (common with large system prompts):
  ```text
  Thinking adds latency and should only be used when it will meaningfully improve answer quality, typically for problems that require multistep reasoning. When in doubt, respond directly.
  ```

**Running Opus 5 with thinking disabled has two artifacts:** tool calls occasionally written as visible text instead of a `tool_use` block, and internal XML tags leaking into output. Prefer thinking-on at low effort over thinking-off. If you must disable it, do **not** add a rule telling the model not to think (that increases tag leakage) — use:
```text
When you use a tool, you may say a brief sentence first. If no tool can express what the user asked for, say so instead of guessing. Do not include internal or system XML tags in your response.
```

---

## Append-only history (Fable 5.1) — read this before building an agent loop

Append each assistant turn to the history **exactly as the API returned it**, thinking blocks included, and never edit earlier turns between requests.

For accounts created on or after **2026-08-31**, a Fable 5.1 thinking block is valid only in the exact conversation that produced it. A request that replays a thinking block after its prefix changed — the system prompt, the tool list, or any earlier message — returns a **400**, or silently drops the affected blocks if you set `thinking.block_binding.prefix_mismatch_behavior: "drop_block"` (beta header `thinking-binding-controls-2026-08-01`). Anthropic expects to enforce this for all accounts on future models, so adopt the pattern now.

The edits that trip this check are exactly the ones that restart the prompt cache:

| Don't | Do instead |
|---|---|
| Inject and remove per-turn reminders | Send them as **turn-scoped system messages** (`role: "system"` in `messages` with `clear_at: "next_user_message"`, beta header `mid-conversation-system-clear-at-2026-08-21`). Append a fresh copy each turn and leave earlier copies byte-for-byte in place — once cleared they cost no input tokens. |
| Summarize older turns in place | Use server-side [compaction](https://platform.claude.com/docs/en/build-with-claude/compaction) or context editing. |
| Rebuild `system` or `tools` mid-session | Use a mid-conversation system message. |

If you must compact client-side, the safe shape is to **replace the whole history with one summary message plus the new user turn** and replay nothing else — no thinking blocks carry over, so nothing can fail. Use the summarization instruction under "Compaction" below.

Cache reads are cheaper on Fable 5.1 than on Fable 5, so **compacting early to save money may no longer be the right trade** — test later compaction points.

To find edits your harness already makes: run a session with `prefix_mismatch_behavior: "drop_block"` and log `input_transformations`, or capture the raw requests over a few turns and confirm consecutive requests are byte-identical up to the appended turns.

---

## Fable 5.1 behavioral deltas

Each of these is a *change from Fable 5*. Start with the one matching the symptom you actually observe — don't apply all of them preemptively.

### Little or no text between tool calls

5.1 narrates less during long tool-calling turns, more so at high effort and in long chains. Users see minutes of silence, or a final message covering only the last step.

**First, check your client is even receiving updates.** The model's between-tool-call notes come back as progress-update `thinking` blocks, which are empty under the default `thinking.display: "omitted"`. Set `display: "updates"` (beta `thinking-display-updates-2026-08-18`) and render each non-empty `thinking` block as a status line.

**Second, delete prompt lines that suppress narration.** Older models were over-eager to narrate, so many prompts carry lines like "hold all findings for the final response." Remove those before adding anything.

Only then, if you want more:
```text
Before you start, say in a line what you're about to do; brief updates while you work help the user follow along. Close with a short recap that stands on its own — what you found, what you did, and what's next — so a reader who only sees the last message has the full picture.
```

If your UI collapses or hides tool output, say so in a turn-scoped system message — otherwise the model runs commands to "show" the user output they never see:
```text
Only you see that command's output — the user's terminal shows at most a few lines of it. If the user needs to read any of it, put it in your reply.
```

### One tool call per turn in agent loops

5.1 parallelizes correctly when a request *names* several things to fetch. It may serialize in coding and computer-use loops where the next independent calls are only *implied* by the task. Quality is unaffected; you pay in turns, round trips, and wall-clock time.

Append this after the tool results each turn, as a turn-scoped system message (or a text block after the `tool_result` blocks if you're not on the beta):
```text
First privately list what you need next; then request every item that doesn't depend on another's result in this one response.
```

### Prose runs long and dense

5.1 writes better than earlier models overall — fewer stock phrases, less unexplained jargon — but its sentences run longer with fewer paragraph breaks. Defining the anti-pattern works better than asking for brevity. Put it in a user message (preferred) or the system prompt:
```text
Mannered prose substitutes metaphor and flourish for direct statement. Instead of "a parameter worth varying," the mannered writer produces "a dial worth turning." Instead of "this point still matters," they write "this point earns its keep." The phrases exist to display the writer, not to convey the idea, and readers can tell. That is why mannered prose irritates: it makes the reader work harder so the writer can perform. It is also imprecise. Metaphors drag in connotations the writer did not choose and cannot control. The fix is to say what you mean. When a literal phrase is available, use it.
```
The short version often works too: `Please remove all mannered prose.`

### Chat replies carry less structure than the content needs

This reverses the old problem. Earlier models overused bullets and bold, so many prompts carry anti-formatting rules. 5.1 under-formats: less bold, less likely to reach for headers, lists, or quotation marks. **Delete your anti-formatting language** and replace it with a conditional rule:
```text
Use lists and bullet points when asked to, or when the content is multifaceted enough that they help with clarity. If the person explicitly requests minimal formatting, always format your responses without bullet points, headers, lists, or bold emphasis, as requested. In conversational, personal, or emotional exchanges, keep to plain prose.
```

### Summaries reproduce source wording without marking it as a quotation

When summarizing retrieved documents, 5.1 is more likely than Fable 5 to lift passages unmarked. The fix is **one complete worked example** in the system prompt — the user's request, a correct response, and a rationale explaining *why* it's correct. Sketch:

```text
<example>
<user>look up how the Riverton Ledger and the Coast Dispatch each covered the Harbor Bridge closure and compare their reporting</user>
[web_search: Riverton Ledger Harbor Bridge closure]
[web_search: Coast Dispatch Harbor Bridge closure]
<response>
Both outlets agree on the basics: the bridge closed on March 3 after inspectors found cracked welds, and the state expects repairs to take about eight months. Where they differ is emphasis. The Ledger treats it as a local-economy story. The Dispatch frames it as a funding failure; its editorial calls the closure "entirely foreseeable." Read together, the Ledger explains who is affected now and the Dispatch explains how it came to this — neither account alone gives the whole picture.
</response>
<rationale>CORRECT: The response is organized around where the two outlets agree and differ, not as a walk through either article. Each outlet's reporting is conveyed in one or two sentences of the assistant's own indirect speech. One short marked phrase from one source; every other claim is reworded. The response is still specific and complete.</rationale>
</example>
```
Replace the `[web_search: ...]` lines with your own tool's name so the model reads them as templated tool output rather than literal text to emit.

### Turn ends before the work is done

5.1 sometimes describes what it would do next ("Next, I'll…") or asks permission for a step the original request already covered ("Shall I apply this?"). Two system-prompt blocks together fix this. **Apply both**; if prompt length is tight, the first keeps most of the effect.

The opening sentence — telling the model the user isn't watching — carries much of the effect, so keep it as written. If your product needs specific confirmations, list them right after it. Note the trade-off: this block also makes the model less likely to ask about genuinely ambiguous requests.

```text
You are operating autonomously. The user is not watching in real time and cannot answer questions mid-task, so asking 'Want me to…?' or 'Shall I…?' will block the work. For reversible actions that follow from the original request, proceed without asking. Stop only for destructive actions or genuine scope changes the user must decide. Offering follow-ups after the task is done is fine; asking permission before doing the work is not.

Exception: when the user is describing a problem, asking a question, or thinking out loud rather than requesting a change, the deliverable is your assessment. Report your findings and stop. Don't apply a fix until they ask for one.

Before ending your turn, check your last paragraph. If it is a plan, an analysis, a question, a list of next steps, or a promise about work you have not done ('I'll…', 'let me know when…'), do that work now with tool calls. That includes retrying after errors and gathering missing information yourself. Do not stop because the context or session is long. End your turn only when the task is complete or you are blocked on input only the user can provide.

Before running a command that changes system state (such as restarts, deletes, or config edits), check that the evidence actually supports that specific action. A signal that pattern-matches to a known failure may have a different cause.
```

The second defines the request as the scope of the deliverable:
```text
The user's request — or the plan they approved — sets the scope, and the scope is the deliverable: don't quietly narrow, widen, or swap it. Read ambiguity the way a careful colleague would: make routine judgment calls yourself, and check in only when different readings would lead to materially different work. If you see a real problem with the task as specified, say so in a sentence or two and keep building under stated assumptions; if the user hears the concern and reaffirms, that is their decision, so deliver the full request.

If a question comes up partway, first do everything that doesn't depend on the answer; then state the assumption you made, or — when going ahead on a wrong guess would be unsafe or would make the work useless — put the question at the end of a turn that also delivers that progress. If one part turns out to be blocked, complete every other part in full and say exactly what you left out and why — the whole task is the deliverable, and scaling it down is the user's call, not yours. A step you have decided on is something to run, not to announce: describing the next step and ending the turn leaves it undone until the user replies.

Keep changes to what the request needs. Something else you notice worth doing — cleanup or documentation the task didn't call for, a change to a file the task didn't require — is a suggestion to make at the end, not a change to make; actions clearly beyond what the ask implies, and risky or destructive ones, still need the user's go-ahead.
```

### Compaction summaries drop constraints or exact details

Server-side compaction already handles this. For client-side compaction, use this summarization instruction verbatim — the six numbered items and the asymmetric weighting of user vs. assistant voice are both load-bearing:
```text
Summarize the transcript inside <summary></summary> tags. Include relevant information in the summary such that this conversation will be continued by a new context window without needing to redo work or be reprovided with relevant constraints or context. Be sure to preserve: (1) any difficulties or problems that came up, and how they were handled or resolved; (2) any possibilities, options, or approaches that were raised, tried, or set aside, and why; (3) anything that was asked for, decided, agreed, ruled out, or established as a preference, constraint, or boundary — stated exactly; (4) exactly where things stand now — what has been covered, settled, or completed so far; (5) anything still open, unresolved, promised, or expected to happen next; (6) specific details that would be hard to reconstruct — names, numbers, dates, exact wording, links or references — kept exactly. Be complete on these even at the cost of length; keep everything else concise. Weight the two voices differently: keep what the user said, asked for, shared, or established carefully and close to their own words; your own explanations and reasoning can be condensed much further, to what they concluded or produced — as long as nothing in the six items above is dropped.
```

### Unrequested fixes, or more test files than the task warranted

Anthropic measured this instruction dropping unrequested additions and committed test code substantially, with no measurable change in task success:
```text
If, while working or testing, you find a pre-existing bug, a performance concern, or behavior the task doesn't mention, don't fix, optimize or extend it in this change unless the requested behavior cannot work without it; report it as a follow-up in your summary. Where the task is ambiguous, implement the reading its wording and the surrounding code most directly support, state that assumption in your summary, and don't build for the other readings as well. Verify your work however you like; scratch scripts and quick checks need not be kept. Commit tests only where the task asks for them or this repository already keeps tests for this kind of change, sized like the neighboring test files — roughly one focused test per stated behavior — and don't turn scratch checks into additional permanent test files. This is about extras only: implement every behavior the task asks for, completely.
```

### Answers from memory instead of searching, at `low` effort

At `low`, 5.1 calls search and retrieval tools less often than Fable 5 did. Often the cleanest fix is to **raise effort for the affected turns** rather than the whole conversation. Otherwise:
```text
When a query centers on a name you do not confidently recognize, or recognize from a fast-moving area like AI models and developer tools where the landscape shifts within months, the name itself is the thing to verify: search before answering, and include the name as the user wrote it in at least one query alongside any reformulations. This holds even when you have some background on it — partial background is exactly what makes an out-of-date answer sound authoritative, so familiarity is not a reason to skip the search.
```

### Benign coding requests return `stop_reason: "refusal"`

5.1's safety classifiers produce fewer false positives than Fable 5's did at launch, and finding vulnerabilities in source code is permitted. Three situations still raise the odds:

- **Compile-check phrasing.** Ask "Are there any bugs in this program?" instead of "Does this program compile without errors?"
- **Lesser-known languages.** Give the model context about the language — ideally access to its documentation.
- **Base64 in tool output.** Tools that return base64-encoded data into context can trigger false positives. Strip it.

### Whole files rewritten for small changes

5.1 is likelier than Fable 5 to rewrite an entire text file rather than edit it. The result is usually the same file at higher output-token cost and latency. Append to the system prompt or first user message:
```text
The number of tokens used to edit files is best minimized, all else being equal. Therefore, when it will not affect the end result, try to surgically edit a file rather than rewrite the entire thing.
```

### Long deliverables at `xhigh`/`max` run long or hit `max_tokens`

At `xhigh` and especially `max`, 5.1 can draft most of a long deliverable inside its thinking and then write it out again as the reply — double the tokens, double the wait. The simplest fix is to **run long-deliverable requests at `high`** and only move up where you've measured a gain. If you do run them high:

- Set `max_tokens` to cover thinking *and* reply, not just the expected reply length.
- Append this to the user message, substituting the real `max_tokens` value:
```text
Everything produced in one reply, including any reasoning or drafting done before the reply, counts toward a single limit of about [max_tokens] tokens. If that limit is reached before the reply is finished, the person receives a cut-off response and has to start over. Composing an entire output or deliverable in full as reasoning and then again as a reply would double the length of the turn without improving the result, so don't do that.

Instead, when the person has asked for a long or effort-intensive deliverable such as a multi-section document, a large table or dataset, or a complete code file, spend extra effort on understanding the request, checking the inputs the answer depends on, settling the structure and other difficult decisions, and otherwise using the reasoning space to reason and the output space to write an output. Usually it is not needed to draft an output multiple times.
```

### Lead agent idles while subagents run

Don't force the lead to block on each subagent. On coding tasks, letting it continue lowers average time to completion at similar quality, tokens, and cost. Three requirements:

- The tool that starts a subagent **returns immediately**.
- Each subagent's result comes back to the lead in a later `user` message.
- The lead gets a **separate tool** it can call when it actually wants to wait.

The model still often chooses to wait; the savings come from the runs where it doesn't.

### Vision answers miss detail on dense charts

5.1's vision is better out of the box, and it does its best work on dense visual input when it can iteratively analyze, crop, and verify. Best setup: run it as an agent with a container holding the raw images and PIL/OpenCV preinstalled. If that's too much overhead, **an image-cropping tool alone delivers most of the uplift** — a tool that returns a chosen region cropped and enlarged lets the model scale test-time compute with image tokens. Anthropic publishes a working definition at `platform.claude.com/cookbook/multimodal-crop-tool`.

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
| "Hold all findings for the final response" | Written for models that over-narrated. Fable 5.1 under-narrates; this makes the silence worse. |
| Anti-formatting rules ("no bullets", "no bold", "no headers") | Same inversion. Fable 5.1 under-formats. Replace with a conditional rule (see the formatting delta above). |
| Prescriptive style guardrails ("Never write multi-paragraph docstrings") | Replace with judgment framings the model can generalize: "Write code that reads like the surrounding code: match its comment density, naming, and idiom." |
| Examples of how to call a tool | They constrain the model to the demonstrated exploration space. Put the guidance in the tool *description* and make the parameters expressive instead. |
| The same instruction repeated in the system prompt and a tool description | State it once, in the tool description. |

Fable 5 and 5.1 in particular: **skills and prompts tuned for prior models are often too prescriptive and degrade output.** Review and remove older scaffolding before assuming a regression. Anthropic removed over 80% of Claude Code's system prompt for Opus 5 and Fable 5 with no measurable loss on their coding evals — see `references/context-engineering.md`.

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
- **Cache reads are 4× cheaper on Fable 5.1 and Mythos 5.1**: hits bill at **0.025× base input ($0.25/MTok)** rather than the 0.1× every other Claude model uses. Writes are unchanged (1.25× for 5m, 2× for 1h), so the break-even moves in favor of caching aggressively and **compacting later** — an early-compaction threshold tuned on Fable 5 is probably now costing you money.
- Batch API on Fable 5.1: $5 / $25 per MTok.
- Batch API: 50% off input and output. Stacks with caching. Not available with fast mode.
- Fast mode (research preview, Opus 5 / Opus 4.8): up to 2.5× output speed at $10/$50 per MTok.
- `inference_geo: "us"` applies a 1.1× multiplier on every token category.
- The 1M context window is billed at standard rates — a 900k request costs the same per token as a 9k one.
- **Re-baseline your token counts.** Claude 4.7 and later use a tokenizer that produces ~30% more tokens for the same text. `max_tokens` values tuned on 4.6 may now truncate.

See `references/caching-and-cost.md` and `references/model-selection.md` for the cross-vendor picture.
