# Claude Opus 4.8 Prompting Guide

## Overview

Claude Opus 4.8 (`claude-opus-4-8`, $5/$25 per MTok, 1M context, 128k max output) is now a **legacy** model — Claude Opus 5 supersedes it — but it remains widely deployed and is the designated fallback target for Fable 5 refusals. Its strengths are long-horizon agentic work, knowledge work, vision, and memory tasks. It runs existing Opus 4.7 prompts well.

Use this guide when a prompt is explicitly targeting Opus 4.8. For anything new, use `claude-5-family-guide.md`.

Sourced: 2026-07-26

Sources:
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-4-8
- https://platform.claude.com/docs/en/about-claude/models/migration-guide

---

## Where Opus 4.8 differs from Opus 5

| Behavior | Opus 4.8 | Opus 5 |
|---|---|---|
| Thinking default | **Off** unless you set `thinking: {type: "adaptive"}` | On by default |
| Effort default | `high` on all surfaces | `high` on API and Claude Code |
| Recommended coding effort | `xhigh` — start here | Start at `high`, step to `xhigh` |
| Subagents | Spawns **fewer** by default; prompt to encourage | Spawns readily; prompt to cap |
| Tool use | Favors reasoning over tool calls | More balanced |
| Verbosity | Calibrates to task complexity | Runs long by default |
| Self-verification | Prompt for it | Built in — remove verification instructions |
| Frontend default style | Persistent cream/serif/terracotta house style | Different default; same mitigation |

---

## Effort and thinking

| Level | Guidance |
|---|---|
| `max` | Gains on some tasks but diminishing returns and occasional overthinking. |
| `xhigh` | **Best setting for most coding and agentic use cases.** |
| `high` | Minimum for most intelligence-sensitive use cases. |
| `medium` | Cost-sensitive work, trading some intelligence. |
| `low` | Short scoped tasks, latency-sensitive, not intelligence-sensitive. |

Effort matters more on this model than on any prior Opus — experiment actively on upgrade. Effort is respected strictly at the low end: at `low`/`medium` the model scopes to exactly what was asked, with some under-thinking risk on moderately complex tasks. Raise effort before prompting around shallow reasoning. If you must hold at `low`:

```text
This task involves multistep reasoning. Think carefully through the problem before responding.
```

At `max` or `xhigh`, set a large output budget — start at 64k tokens — so the model has room to think and act across subagents and tool calls.

Thinking is off unless explicitly enabled with `thinking: {type: "adaptive"}`. If adaptive thinking triggers more than you want (common with large system prompts):

```text
Thinking adds latency and should only be used when it will meaningfully improve answer quality — typically for problems that require multistep reasoning. When in doubt, respond directly.
```

---

## Verbosity and tone

Opus 4.8 calibrates response length to perceived task complexity: short on lookups, much longer on open-ended analysis. To tighten:

```text
Provide concise, focused responses. Skip non-essential context, and keep examples minimal.
```

Positive examples of appropriately concise communication work better than negative instructions.

Its default prose is direct and opinionated, with minimal validation-forward phrasing and sparing emoji. For a warmer product voice:

```text
Use a warm, collaborative tone. Acknowledge the user's framing before answering.
```

---

## Tool use and subagents

Opus 4.8 favors reasoning over tool calls. This is usually better output, but when you need more tool usage, raising effort to `high`/`xhigh` substantially increases it — especially in agentic search and knowledge work. Alternatively, describe explicitly why and how a specific tool should be used.

Because it under-spawns subagents by default, encourage rather than cap:

```text
Do not spawn a subagent for work you can complete directly in a single response (e.g. refactoring a function you can already see).

Spawn multiple subagents in the same turn when fanning out across items or reading multiple files.
```

---

## Progress updates and literalism

Opus 4.8 already gives regular, high-quality interim updates. **Remove scaffolding like "After every 3 tool calls, summarize progress."** If the updates aren't calibrated to your product, describe what they should look like and give examples.

It interprets prompts literally and does not silently generalize an instruction from one item to another. State scope explicitly: "Apply this formatting to every section, not just the first one." This literalism is why carefully tuned API prompts, structured extraction, and predictable pipelines perform well on it.

---

## Code review harnesses

Opus 4.8 has higher bug-finding recall and precision than prior models, but a harness tuned for an older model can show *lower* measured recall — it follows "only report high-severity issues" / "be conservative" / "don't nitpick" faithfully and drops findings below your stated bar. Ask for coverage and filter separately:

```text
Report every issue you find, including ones you are uncertain about or consider low-severity. Do not filter for importance or confidence at this stage - a separate verification step will do that. Your goal here is coverage: it is better to surface a finding that later gets filtered out than to silently drop a real bug. For each finding, include your confidence level and an estimated severity so a downstream filter can rank them.
```

If you do want single-pass self-filtering, be concrete about the bar rather than saying "important": e.g. "report any bugs that could cause incorrect behavior, a test failure, or a misleading result; only omit nits like pure style or naming preferences."

---

## Design and frontend defaults

Opus 4.8 has a strong, persistent default house style: warm cream/off-white backgrounds (~`#F4F1EA`), serif display type (Georgia, Fraunces, Playfair), italic word-accents, terracotta/amber accent. Great for editorial, hospitality, and portfolio work; wrong for dashboards, dev tools, fintech, healthcare, enterprise. It shows up in slide decks as well as web UIs.

Generic negatives ("don't use cream", "make it clean and minimal") just move it to a different fixed palette. Two things work:

1. **Specify a concrete alternative** — exact palette hexes, typeface character, corner radius, section-by-section structure, transition timings. It follows explicit specs precisely.
2. **Have it propose 4 distinct visual directions first** (bg hex / accent hex / typeface + one-line rationale), then implement only the chosen one. This is the replacement for using `temperature` for design variety.

Opus 4.8 needs less anti-slop prompting than earlier models. This snippet suffices alongside the above:

```text
<frontend_aesthetics>
NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white or dark backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character. Use unique fonts, cohesive colors and themes, and animations for effects and micro-interactions.
</frontend_aesthetics>
```

---

## Interactive coding products

Opus 4.8 uses more tokens in interactive, multi-turn coding sessions than in single-turn autonomous ones, because it reasons more after each user turn. That improves long-horizon coherence but costs tokens. To get both performance and efficiency: use `xhigh` or `high` effort, add autonomous features like an auto mode, and reduce required user interactions — while specifying task, intent, and constraints fully in the first turn. Ambiguous prompts spread across many turns reduce both token efficiency and, sometimes, performance.

---

## Computer use

Works across resolutions up to 2576px / 3.75MP. **1080p is the best performance/cost balance** in Anthropic's internal testing; 720p or 1366×768 are lower-cost options that still perform strongly. Effort settings are an additional tuning lever.

---

## Migrating off Opus 4.8

Moving to Opus 5 means: thinking on by default (revisit `max_tokens`), `thinking: {type: "disabled"}` allowed only at `effort: high` or below, `temperature`/`top_p`/`top_k` now 400 errors, prefill now a 400 error, minimum cacheable prompt down to 512 tokens, and removal of verification/self-check instructions. Full detail in `claude-5-family-guide.md`.
