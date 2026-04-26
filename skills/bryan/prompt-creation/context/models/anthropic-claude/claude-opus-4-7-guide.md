# Claude Opus 4.7 Prompting Guide

## Overview

Claude Opus 4.7 is Anthropic's most capable generally available model, with particular strengths in long-horizon agentic work, knowledge work, vision, and memory tasks. It performs well out of the box on existing Claude Opus 4.6 prompts. The patterns below cover the behaviors that most often require tuning when upgrading.

Source: [Anthropic Prompting Best Practices](https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices)

---

## Response Length and Verbosity

Opus 4.7 calibrates response length to task complexity rather than defaulting to a fixed verbosity — shorter on simple lookups, much longer on open-ended analysis.

If your product needs a consistent style, tune explicitly:

```text
Provide concise, focused responses. Skip non-essential context, and keep examples minimal.
```

Positive examples showing appropriate concision are more effective than negative instructions or telling the model what not to do.

---

## Effort Levels

The `effort` parameter (via `output_config`) controls intelligence vs. token spend. Opus 4.7 respects effort levels strictly — especially at the low end, where it scopes its work to what was asked rather than going above and beyond.

| Level | Best for |
|---|---|
| `max` | Intelligence-demanding tasks; may show diminishing returns or overthinking |
| `xhigh` *(new in 4.7)* | Coding and agentic use cases — best default for these |
| `high` | Most intelligence-sensitive use cases — recommended minimum |
| `medium` | Cost-sensitive workloads trading off some intelligence |
| `low` | Short, scoped tasks; latency-sensitive; not intelligence-sensitive |

**At `max` or `xhigh`:** Set a large `max_tokens` budget (start at 64k) so the model has room to think and act across subagents and tool calls.

**If under-thinking at `low`:** Raise effort first. If you must stay at `low`, add targeted guidance:

```text
This task involves multi-step reasoning. Think carefully through the problem before responding.
```

**If over-thinking (adaptive thinking triggering too often):** Add guidance to constrain it:

```text
Thinking adds latency and should only be used when it will meaningfully improve answer quality — typically for problems that require multi-step reasoning. When in doubt, respond directly.
```

---

## Tool Use Triggering

Opus 4.7 uses tools less often than Opus 4.6, relying more on internal reasoning. This produces better results in most cases, but if your use case needs more tool usage:

- Raise effort to `high` or `xhigh` — this substantially increases tool usage in agentic search and coding.
- Explicitly instruct the model when and how to use specific tools: if a web search tool is being skipped, describe why and how it should be used.

---

## User-Facing Progress Updates

Opus 4.7 provides more regular, higher-quality progress updates during long agentic traces by default.

- **Remove** any scaffolding you added to force interim status messages (e.g., "After every 3 tool calls, summarize progress") — it's no longer needed and may interfere.
- If the length or content of updates isn't right for your use case, describe explicitly what they should look like and provide examples.

---

## More Literal Instruction Following

Opus 4.7 interprets prompts more literally than Opus 4.6, particularly at lower effort levels:

- It will not silently generalize an instruction from one item to another.
- It will not infer requests you didn't make.

**Upside:** Less thrash, better for structured pipelines and careful API use cases.

**Adjustment:** State scope explicitly. Instead of letting Claude infer, write: "Apply this formatting to every section, not just the first one."

---

## Tone and Writing Style

Opus 4.7 is more direct and opinionated than Opus 4.6:

- Less validation-forward phrasing
- Fewer emoji
- More fact-based, less warm

If your product relies on a warmer voice:

```text
Use a warm, collaborative tone. Acknowledge the user's framing before answering.
```

Re-evaluate existing style prompts against the new baseline — what worked for 4.6 may need adjustment.

---

## Subagent Spawning

Opus 4.7 spawns fewer subagents by default than Opus 4.6. This is steerable:

```text
Do not spawn a subagent for work you can complete directly in a single response
(e.g. refactoring a function you can already see).

Spawn multiple subagents in the same turn when fanning out across items
or reading multiple files in parallel.
```

---

## Design and Frontend Defaults

Opus 4.7 has a strong, persistent default house style:

- **Background:** warm cream/off-white (~`#F4F1EA`)
- **Type:** serif display (Georgia, Fraunces, Playfair), italic word-accents
- **Accent:** terracotta/amber

This appears in web UIs and slide decks. Generic overrides ("don't use cream," "make it clean and minimal") tend to shift to a different fixed palette rather than producing variety.

**Two reliable approaches:**

**1. Specify a concrete direction explicitly.** The model follows precise specs:

```text
Visual direction: cold monochrome atmosphere, pale silver-gray tones deepening into blue-gray and near-black.
Color palette: #E9ECEC, #C9D2D4, #8C9A9E, #44545B, #11171B.
Typography: square, angular sans-serif, wider letter spacing, uppercase headlines.
4px corner radius on all cards, buttons, inputs, and media frames.
```

**2. Have the model propose options before building.** Breaks the default and produces meaningfully different directions:

```text
Before building, propose 4 distinct visual directions tailored to this brief
(each as: bg hex / accent hex / typeface — one-line rationale).
Ask the user to pick one, then implement only that direction.
```

This replaces temperature-based variety from older workflows.

**Anti-slop snippet** (still effective with minimal prompting on 4.7):

```text
<frontend_aesthetics>
NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial,
system fonts), cliched color schemes (particularly purple gradients on white or dark backgrounds),
predictable layouts and component patterns, and cookie-cutter design that lacks context-specific
character. Use unique fonts, cohesive colors and themes, and animations for effects and micro-interactions.
</frontend_aesthetics>
```

Note: Opus 4.7 requires less frontend design prompting than prior models to avoid generic patterns.

---

## Interactive Coding Products

Opus 4.7 uses more tokens in interactive (multi-turn) coding sessions than in autonomous single-turn sessions, primarily because it reasons more after each user turn. This improves long-horizon coherence and instruction following, but increases cost.

To maximize both performance and token efficiency:

- Use `xhigh` or `high` effort.
- Reduce the number of human interactions required — add autonomous features (auto-mode).
- Specify task, intent, and relevant constraints upfront in the first human turn.

Ambiguous prompts spread across multiple turns reduce token efficiency and sometimes performance. Opus 4.7's autonomy makes well-specified first turns especially valuable.

---

## Code Review Harnesses

Opus 4.7 is meaningfully better at finding bugs (11pp better recall in one hard internal eval), but follows filtering instructions more literally than prior models.

**The risk:** If your prompt says "only report high-severity issues," Opus 4.7 may investigate thoroughly, find bugs, and then filter them out before reporting — because it's faithfully following your bar. Precision rises, but measured recall can fall even though underlying capability improved.

**Fix:** Tell the model its job at the finding stage is coverage, not filtering:

```text
Report every issue you find, including ones you are uncertain about or consider low-severity.
Do not filter for importance or confidence at this stage — a separate verification step will do that.
Your goal here is coverage: it is better to surface a finding that later gets filtered out
than to silently drop a real bug. For each finding, include your confidence level and an estimated
severity so a downstream filter can rank them.
```

If your harness has a separate verification or ranking stage, make that explicit. If you want single-pass self-filtering, be concrete about the bar: "report any bugs that could cause incorrect behavior, a test failure, or a misleading result; only omit nits like pure style or naming preferences."

---

## Computer Use

- Supports resolutions up to 2576px / 3.75MP.
- **1080p** recommended for balance of performance and cost.
- **720p or 1366×768** for cost-sensitive workloads.
- Experiment with effort settings to tune behavior for your specific use case.
