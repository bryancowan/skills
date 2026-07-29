# Gemini Prompt Design Strategies

## Overview

Google's prompt design guidance for the Gemini API. Two things here differ from Anthropic and OpenAI guidance and are worth flagging when adapting a prompt across vendors:

1. **Google recommends few-shot examples in essentially every prompt** — "prompts without few-shot examples are likely to be less effective." OpenAI's current guidance for GPT-5.6 is the opposite (remove examples unless they encode a product requirement).
2. **Sampling parameters are still live.** `temperature`, `top_k`, `top_p` all work, where Claude 5 and GPT-5.6 have removed or de-emphasized them.

Sourced: 2026-07-26

Source: https://ai.google.dev/gemini-api/docs/prompting-strategies

---

## Input types

Frame the prompt as one of four shapes — being deliberate about which one you're using resolves most ambiguity:

| Type | Shape | Example |
|---|---|---|
| **Question** | Direct query expecting an answer | "What's a good name for a flower shop that specializes in selling bouquets of dried flowers? Create a list of 5 options with just the names." |
| **Task** | Instruction to perform an action | "Give me a simple list of just the things that I must bring on a camping trip. The list should have 5 items." |
| **Entity** | Classification or categorization | "Multiple choice problem: Which of the following options describes the book The Odyssey? Options: thriller, sci-fi, mythology, biography" |
| **Completion** | Partial prompt the model finishes | `Valid fields are cheeseburger, hamburger, fries, and drink. Order: Give me a cheeseburger and fries Output: { "cheeseburger": 1, "fries": 1 }` |

---

## Core tactics

**Constraints.** Bound length, format, and scope in the instruction itself: "Summarize this text in one sentence."

**Response format.** Name the structure — table, bulleted list, JSON, outline, prose. Supply a format example or a response prefix to lock it in.

**Few-shot examples.** 2–4 varied, specific examples. More than that risks overfitting; the model starts reproducing incidental patterns from your examples. Keep formatting identical across examples — same XML tags, same whitespace, same newlines. Inconsistent example formatting is a common silent failure.

**Add context rather than assuming knowledge.** Include the constraints, definitions, and reference material the task needs. Grounded pattern:

```text
Answer the question using the text below. Respond with only the text provided.
Question: What should I do to fix my disconnected wifi?
[reference text]
```

**Break down complex prompts.** Three decomposition moves: split instructions into separate prompts; chain prompts so each output feeds the next; aggregate parallel operations across different sections of data.

---

## Parameters

| Parameter | Guidance |
|---|---|
| `max_output_tokens` | ~4 characters per token; 100 tokens ≈ 60–80 words |
| `temperature` | Lower for deterministic/closed-ended work, higher for diverse or creative output. **Leave at default for Gemini 3.x.** |
| `top_k` | 1 = greedy decoding; higher values increase diversity |
| `top_p` | Cumulative-probability cutoff; default 0.95 |
| stop sequences | Character sequences that halt generation |

If a safety filter returns a fallback response, raising temperature sometimes produces a substantive answer instead.

---

## Iteration strategies

When a prompt isn't working, these three moves are more productive than adding more instructions:

1. **Rephrase** — different wording, same meaning.
2. **Switch the task** — reformulate as an analogous problem. A stubborn categorization task often works as a multiple-choice question.
3. **Reorder the content** — try examples → context → input versus input → context → examples. Order effects are real and cheap to test.

---

## Gemini 3 specifics

- **Direct language.** Drop persuasive or unnecessary phrasing; state the goal.
- **Consistent structure.** XML tags or Markdown headings — `<context>`, `<task>`, `<constraints>` — used the same way every time.
- **Define ambiguous parameters explicitly.**
- **Ask for verbosity if you want it.** Gemini 3 defaults to concise output.
- **Multimodal inputs are equal-class**; reference each explicitly.
- **Critical instructions go first** — role, behavioral constraints, format requirements at the top or in system instructions.
- **Long context: context first, question last**, bridged with "Based on the information above…".

### System instruction template

```text
<role>
You are Gemini 3, a specialized assistant for [Domain].
You are precise, analytical, and persistent.
</role>

<instructions>
1. **Plan**: Analyze the task and create step-by-step plan.
2. **Execute**: Carry out the plan.
3. **Validate**: Review output against user's task.
4. **Format**: Present final answer in requested structure.
</instructions>

<constraints>
- Verbosity: [Low/Medium/High]
- Tone: [Formal/Casual/Technical]
</constraints>

<output_format>
Structure your response:
1. **Executive Summary**
2. **Detailed Response**
</output_format>
```

### User prompt structure

```text
<context>
[Insert relevant documents/code/background]
</context>

<task>
[Insert specific request]
</task>

<final_instruction>
Remember to think step-by-step before answering.
</final_instruction>
```

### Gemini 3 Flash clauses

```text
Remember it is 2026 this year.
```
```text
Your knowledge cutoff date is January 2025.
```

---

## Tools and grounding

- **Google Search grounding** for current or obscure facts.
- **Code execution** for calculations and arithmetic — more reliable than asking the model to compute in-context.

## Agentic workflows

Steer these dimensions explicitly through system instructions:

- **Reasoning and strategy** — logical decomposition depth, problem diagnosis thoroughness, how exhaustive information gathering should be
- **Execution and reliability** — adaptability to new data, persistence and error recovery, risk assessment for read vs. write operations
- **Interaction and output** — ambiguity and permission handling, verbosity levels, precision requirements
