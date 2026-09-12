# Context Engineering for Current-Generation Models

## Why this file exists

The prompt-engineering habits that produced good results on 2024–2025 models now measurably *hurt* on current frontier models. This is the single most common defect in prompts users bring for review: they are too long, too prescriptive, and too front-loaded — written for a model that needed the scaffolding.

The benchmark number worth quoting to users: **Anthropic removed over 80% of Claude Code's system prompt** for Claude Opus 5 and Claude Fable 5, **with no measurable loss on their coding evaluations.**

So when reviewing a long system prompt, the default hypothesis is *this is too long*, not *this is missing a rule*.

Sourced: 2026-09-12

Sources:
- https://claude.com/blog/the-new-rules-of-context-engineering-for-claude-5-generation-models/
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/claude-prompting-best-practices
- `context/Effective context engineering for AI agents - 2026-03-28T130401-0500.md` (earlier framework; altitude and just-in-time context still hold)

Applies to: Claude 5 family, GPT-6 Astra / GPT-5.6, Gemini 3.x, GLM-5.3 — the shift is generational, not vendor-specific. It is best documented by Anthropic.

---

## Then / now

| Was | Now | Why |
|---|---|---|
| Prescriptive guardrails — *"Never write multi-paragraph docstrings"* | **Judgment framings** — *"Write code that reads like the surrounding code: match its comment density, naming, and idiom"* | The model makes this call better from context than from a rule. A rule fires in the cases you didn't anticipate. |
| Examples of how to call each tool | **Expressive tool parameters and data structures** | Examples constrain the model to the demonstrated exploration space. Good parameter names and types hint at correct use without fencing it in. |
| Front-load everything the model might need | **Progressive disclosure** — load on demand | Front-loading buys attention dilution and token cost against information that usually goes unused. |
| The same instruction in the system prompt *and* the tool description | **State it once**, in the tool description | Repetition reads as emphasis, and emphasis on the wrong thing distorts behavior. |
| Manual memory — make the user save to `CLAUDE.md` | **Auto-memory** | The model handles relevant work context itself now. |
| Markdown specs describing what to build | **Rich references** — test suites, reference code, HTML artifacts, rubrics | A failing test is an unambiguous spec. Prose about the test is not. |

The through-line: **give the model something to reason from, not a rule to comply with.**

---

## The layering model

Where a given piece of context belongs:

| Layer | Holds | Keep it |
|---|---|---|
| **System prompt** | Product context and core behavior | Rarely modified by users; short |
| **`CLAUDE.md` / `AGENTS.md`** | Repository-specific gotchas | **Minimal.** Not the obvious stuff — things a competent newcomer would get wrong. |
| **Skills** | Team- and product-specific opinions and best practices | Lightweight; loaded when relevant |
| **References** | Specs, mockups, codebases, test suites | @mentioned / loaded on demand |

The most common mistake is putting layer-3 and layer-4 content into layer 1. If a rule only applies to one kind of task, it belongs in a skill, not the system prompt.

Anthropic ships `claude doctor` to help rightsize skills and `CLAUDE.md` files for current models.

---

## Applying this when reviewing a prompt

Work through in this order — the first three usually account for most of the length:

1. **Find the repeated instructions.** Same rule in the system prompt and a tool description, or restated three ways for emphasis. Keep one instance, in the most specific location.
2. **Find the anti-laziness scaffolding.** "Be thorough", "double-check", "use tools aggressively", "CRITICAL: you MUST". Current models are already proactive; this causes over-verification and tool overtriggering. Delete it. (Full delete list: `context/models/anthropic-claude/claude-5-family-guide.md`.)
3. **Find the prescriptive rules and ask what they're protecting against.** Replace each with a framing that states the goal and lets the model judge. If you can't articulate the goal, the rule was probably cargo-culted.
4. **Find the front-loaded context.** Anything the model needs only sometimes should be retrievable, not resident.
5. **Find the prose that should be an artifact.** "The function should handle empty input, nulls, and unicode" is three sentences the model has to interpret. Three test cases are not.

**Then re-measure.** The blog's claim is specifically that removal was validated against evals — not that shorter is self-evidently better. If a user is deleting 80% of a working production prompt, tell them to keep the eval set, not just the diff.

---

## What has *not* changed

Don't over-rotate. These still hold:

- **Be explicit about the task, the output format, and the success criteria.** Removing scaffolding is not the same as removing specificity. Vague prompts still produce vague output.
- **Give the reason behind a rule.** "Never use ellipses" is weaker than "your response will be read aloud by a TTS engine, which can't pronounce them." Reasons generalize; bare rules don't.
- **Examples remain the strongest lever for output format** — that is distinct from tool-call examples, which now constrain more than they help.
- **Long context: documents first, query last.**
- **Right altitude.** Specific enough to guide, flexible enough to handle the cases you didn't list. Brittle if-else logic and vague hand-waving fail in opposite directions.

---

## Multi-agent implications

- **Minimal context per agent.** Pass a summary, not the full conversation history.
- **Just-in-time retrieval over preloading.** Let each agent fetch what it needs.
- **Compaction between stages**, preserving decisions, constraints, and unresolved issues — not a prose recap. See the compaction summarization instruction in the Claude 5 family guide.
- **Separate instruction memory from learning memory.** Rules and constraints are not the same artifact as accumulated experience.
- **Keep conversation history append-only.** On Claude Fable 5.1 this is now a correctness requirement, not just a caching optimization — editing earlier turns invalidates thinking blocks and errors. See `caching-and-cost.md`.
