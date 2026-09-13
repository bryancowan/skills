# ChatGPT Prompting Guide (end user / Enterprise)

## Overview

This is prompting guidance for people using **ChatGPT the product**, not the API. It matters because the audience is different: someone summarizing a contract or drafting a stakeholder email, who does not want to hear about `reasoning.effort` or token budgets.

When a user asks for help prompting ChatGPT itself — as opposed to building on the API — write for this register. Skip parameters, skip system-prompt architecture, and give them something they can type into the box.

Sourced: 2026-09-12

Sources:
- https://developers.openai.com/cookbook/examples/chatgpt/chatgpt_prompt_guide/chatgpt_prompt_guide

---

## Mindset

**Treat the prompt like a handoff to a new intern.** Capable, fast, and entirely without context on your situation. Give them the background, the task, and what "done well" looks like.

**Optimize for clarity, not cleverness.** There is no magic phrasing. A plainly written request with the right context beats a clever one without it.

---

## Structure

| Part | Contents |
|---|---|
| **Context** | Background, relevant documents, who you are / what persona the model should take |
| **Instructions** | The specific actions to perform |
| **Constraints** | Tone, format, audience, length, acceptance criteria |

Two tactics that do most of the work:

- **Scope tightly: one prompt, one deliverable.** Asking for a summary *and* an email *and* a risk list in one turn gets three shallow outputs. Split them and each gets depth.
- **Use markdown headers** to separate the parts. It costs nothing and measurably helps the model find the instruction.

---

## Improving accuracy

- Ask for **sources** alongside claims.
- Tell it to **mark what it's uncertain about** rather than smoothing over it.
- Include a **checklist** the output must satisfy, so there's something to check against.
- **Iterate on the failure, not the whole prompt.** When output is wrong, identify what specifically went wrong and change that.

---

## Meta-prompting: use ChatGPT to write the prompt

A documented, recommended workflow: describe the task and ask ChatGPT to draft the prompt, then critique and refine it. Useful to suggest when a user is stuck on phrasing — it is faster than teaching prompt structure in the abstract.

---

## Product features that change the prompt

- **Skills** — reusable add-ons. If the user has one for the task, the prompt should invoke it rather than restate its contents.
- **Apps / connectors** (e.g. SharePoint search) — when a connector can reach the source material, reference it instead of pasting documents in.
- **Speech input** — spoken prompts run longer and less structured. Worth suggesting the user dictate the context and then tidy the instruction.

---

## Where this differs from API prompting

| | ChatGPT | API |
|---|---|---|
| Audience | Non-technical, task-focused | Developer |
| Levers | Wording, structure, attached files, Skills, connectors | Model choice, effort, verbosity, tools, caching, system vs developer roles |
| Iteration | Conversational — follow up in the same thread | Versioned in code |
| Output | One good answer now | A prompt that works across many inputs |

Don't hand an API-shaped system prompt to someone who asked how to get a better answer out of ChatGPT. The mode signals are usually clear: mentions of "the app", "the box", screenshots of the UI, or a one-off task rather than a repeated pipeline.
