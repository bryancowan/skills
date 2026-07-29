# Moonshot Kimi Prompting Guide

## Overview

Prompting and benchmarking guidance for Moonshot AI's Kimi models.

> **Version note (verified 2026-07-26):** Moonshot's platform documentation covers **K2.6** (newest), **K2.5**, and the **K2-Thinking** series. Neither the prompting nor the benchmarking guide mentions a **K3** model. If you are targeting K3, check `platform.kimi.ai` for a newer page before relying on the version-specific numbers below — the general prompting principles carry over, the parameter tables may not.

Sourced: 2026-07-26

Sources:
- https://platform.kimi.ai/docs/guide/prompt-best-practice
- https://platform.kimi.ai/docs/guide/benchmark-best-practice

---

## Prompting principles

Moonshot's guidance is close to classic OpenAI-style prompting — notably *not* the lean-prompt direction GPT-5.6 has moved in. Kimi rewards explicit structure.

1. **Be explicit — "the model can't read your mind."** Define desired length, format, complexity level, and output style.
2. **Assign a role** in the system message.
3. **Use delimiters** — XML tags, triple quotes, or section headings — to separate content that needs different handling.
4. **Number the steps** for sequential tasks in the system prompt.
5. **Give few-shot examples** when the desired style is hard to describe.
6. **Supply reference material** and instruct the model to answer from the provided sources only.
7. **Specify length in paragraphs or bullet points, not word counts** — Moonshot explicitly recommends this as more precise.
8. **Break complex multi-scenario tasks into categorized instructions.**
9. **Manage context** in long dialogues by summarizing or filtering earlier turns.

### Complex task patterns

- **Query categorization** — classify the incoming request first, then route to a scenario-specific subset of instructions. This keeps any single prompt short while covering many cases.
- **Conversation summarization** — trigger a summary at a fixed turn or token threshold rather than letting history grow to the context limit.
- **Recursive summarization** — for long documents, summarize sections progressively and aggregate the partial summaries.

---

## Evaluation and benchmarking settings

Moonshot treats benchmarking as an engineering problem: "Benchmarking is an engineering task that needs stability and reproducibility." Their documented defaults are useful whenever you're running a prompt at scale, not just for benchmarks.

**Universal defaults for unlisted or proprietary benchmarks:** `temperature = 1.0`, `top_p = 0.95`, `stream = true`.

| Model | Settings |
|---|---|
| K2.6 | Max tokens 96k–256k depending on task category; thinking enabled across all benchmarks; 1–32 runs by complexity |
| K2.5 | Similar token allocations; thinking enabled; 1–32 runs; needs explicit context management on agentic search |
| K2-Thinking | Temperature 0.7 acceptable for code/SWE, 1.0 for reasoning; max 256k tokens; 1–32 runs |

### Hard API requirements

- **Use the official API.** Third-party endpoints show "noticeable accuracy drift."
- **`stream = true` is mandatory** for connection stability on long generations.
- Include retry logic for transient failures.
- Keep concurrency low to avoid HTTP 429.

### Tool-use constraints when thinking is enabled

- `tool_choice` is restricted to `"auto"` or `"none"`.
- Reasoning content **must persist across multi-step calls** — don't strip it between tool calls.
- `$web_search` is **incompatible** with K2.5/K2.6 thinking mode. Use your own search tool instead.

### Agentic task budgets

- Multi-hop search: 256k max tokens plus explicit context management.
- Other agentic tasks: 16k–64k tokens, max steps 100–300.

---

## Practical notes

- **Run any prompt multiple times before judging it.** With `temperature = 1.0` as the documented default, single-sample evaluation is noise.
- The mandatory streaming requirement means your harness needs to handle partial output — build that in before you scale up, not after your first timeout.
- Because reasoning content must persist across tool calls, any context-trimming logic you write needs an exception for reasoning blocks inside an active turn.
