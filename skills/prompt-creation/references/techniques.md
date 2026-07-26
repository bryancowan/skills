# Prompt Engineering Techniques Reference

Quick-lookup guide for selecting the right prompting technique based on task type and complexity. Read the full comprehensive guide at `context/Comprehensive Guide to Prompt Engineering Techniques  Claude - 2026-03-28T181003-0500.md` for detailed explanations and examples.

---

## ⚠️ Single-prompt vs. multi-pass techniques

Some techniques in this reference require **multiple model calls or external orchestration** to actually work. Embedding them in a single prompt makes the model role-play the structure and fabricate the content — output looks sophisticated but is unreliable.

**Multi-pass only — do NOT embed in a single prompt:**

| Technique | Why it fails in a single prompt |
|---|---|
| **Self-Consistency** | Requires N independent samples followed by aggregation. In one pass, later "samples" contaminate earlier ones — they are not independent. |
| **Tree-of-Thoughts (ToT)** | The model generates linear text and *describes* branching, but no real parallel evaluation happens. Output simulates the structure without the substance. |
| **Graph-of-Thoughts (GoT)** | Requires an external graph engine to track nodes and edges across calls. Single-prompt = pure fabrication. |
| **Mixture of Experts (MoE) prompting** | Asks the model to role-play multiple experts in one forward pass. No real routing — the model produces consensus-flavored text from a single distribution. |
| **Universal Self-Consistency** | Requires independent sampling + post-hoc agreement scoring. Single-pass collapses both. |
| **Deep prompt chaining as a single technique** | Long chains compound hallucination per step. If the user has no real orchestration (agent SDK, LangChain, manual chaining), do not pretend to chain inside one prompt — split into Prompt 1, Prompt 2, etc. and have the user run them sequentially. |

**Use these only when the user has real orchestration** (multiple API calls, agent framework, scripted pipeline). If they just want a single prompt to paste somewhere, pick a single-pass alternative: Few-Shot, Skeleton-of-Thought, RCI within one response, or Decomposed Prompting delivered as labeled sub-prompts.

---

## ⚠️ Reasoning-native models: never add Chain-of-Thought

Most current frontier models reason internally. Adding "think step by step" or any reasoning scaffolding wastes tokens and degrades output. State the goal, the constraints, and the desired format — nothing more.

**Reasoning is internal — do NOT add CoT:**

| Family | How reasoning is controlled |
|---|---|
| Claude Fable 5 / Opus 5 / Sonnet 5 | Adaptive thinking, on by default (always on for Fable 5). `effort`: `low`…`max`. Manual `budget_tokens` returns a 400 error. |
| Claude Opus 4.8 / 4.7 | Adaptive thinking, **off** unless `thinking: {type: "adaptive"}`. Same `effort` scale. |
| GPT-5.6 / 5.5 / 5.4 | `reasoning.effort`: `none`, `low`, `medium`, `high`, `xhigh`, `max`. Plus `reasoning.mode: "pro"` on 5.6. |
| Gemini 3.x | Thinking built in; Gemini 3.1 Flash Image exposes `minimal` / `high` thinking levels |
| GLM-5.2 | `thinking: {type: "enabled"}` (default) + `reasoning_effort`: `high` / `max`. The model decides *whether* to think. |
| Qwen3 (3.6+) | `thinking: true`; `/think` and `/no_think` in chat UIs |
| Gemma 4 | `enable_thinking=True` via `apply_chat_template()`. On Cerebras, `reasoning_effort` defaults to `none` — and `low`/`medium`/`high` are **currently equivalent**. |
| Kimi K2.5 / K2.6 / K2-Thinking | Thinking enabled; `tool_choice` restricted to `auto`/`none` while thinking |
| o3 / o4-mini / DeepSeek-R1 | Legacy reasoning models; same rule |

**When CoT still helps:** non-thinking models, and thinking-capable models running with thinking *disabled* (`reasoning.effort: "none"`, `thinking: {type: "disabled"}`, `/no_think`). There it remains a real 10–30% accuracy lever on reasoning tasks.

**Raise effort instead of prompting around shallow reasoning.** Every vendor says this. Adding "think harder" to a `low`-effort request is worse than setting the parameter.

**Corollaries for current models:**
- Don't instruct a model to reproduce or explain its internal reasoning as response text — on Claude Fable 5 this can trigger a `reasoning_extraction` refusal. Read the structured `thinking` blocks instead.
- Don't add "double-check your answer" or "include a verification step" to Claude Opus 5 — it self-verifies, and these instructions cause over-verification at real token cost.
- Changing the reasoning-effort parameter invalidates prompt caches on OpenAI. Pick a level and hold it.

See `model-selection.md` for what else changes when switching families.

---

## Technique Selection Matrix

| Task Type | Simple | Moderate | Complex |
|---|---|---|---|
| **Factual Q&A** | Zero-Shot | Few-Shot + Clear Instructions | Few-Shot + Step-Back |
| **Reasoning / Analysis** | Chain-of-Thought | Self-Consistency + CoT | Tree-of-Thoughts |
| **Creative Writing** | Role + Style Prompting | Emotional Prompting + Examples | Perspective-Taking + RCI |
| **Code Generation** | Zero-Shot + Clear Instructions | Few-Shot + Decomposed | Least-to-Most + Self-Ask |
| **Data Extraction** | Clear Instructions + Format | Few-Shot + Tabular CoT | Decomposed + Self-Consistency |
| **Summarization** | Zero-Shot + Constraints | Skeleton-of-Thought | Recursive Criticism + Improvement |
| **Classification** | Zero-Shot | Few-Shot (3-5 examples) | Self-Consistency (multiple passes) |
| **Multi-step Workflows** | Chain-of-Thought | Least-to-Most | Prompt Chaining + Sub-agents |
| **Image Generation** | Clear descriptive language | Role + Scene composition | Iterative refinement + style refs |
| **Agent Instructions** | System prompt + tools | Context engineering + memory | Multi-agent + compaction |

---

## Foundational Techniques

### Zero-Shot Prompting
Give the model a task with no examples. Works best for straightforward tasks where the model's training covers the domain well.

### Few-Shot Prompting (In-Context Learning)
Provide 3-5 diverse, representative examples before the task. Wrap examples in delimiters (e.g., `<example>` tags for Claude). Quality and diversity of examples matters more than quantity.

### Clear Instructions & Task Framing
Be explicit about what you want. Specify format, length, audience, and constraints. Use imperative mood ("Analyze..." not "Could you analyze...").

---

## Structured Frameworks

### CLEAR Framework
**C**ontext -> **L**imit -> **E**xample -> **A**ction -> **R**efine
Best for: Building prompts systematically from scratch.

### STAR Method
**S**ituation -> **T**ask -> **A**ction -> **R**esult
Best for: Prompts that need narrative structure or case-based reasoning.

### PREP Pattern
**P**oint -> **R**eason -> **E**xample -> **P**oint
Best for: Persuasive or analytical outputs.

### Trigger/Instruction Pairs
Separate trigger conditions from instructions using delimiters. Improves reliability in multi-step processes.
```
Trigger: User submits data
Instruction: Validate all required fields are present

Trigger: Validation passes
Instruction: Transform data into output format
```

---

## Reasoning Techniques

### Chain-of-Thought (CoT)
Ask the model to think step-by-step. Add "Let's think through this step by step" or structure explicit reasoning steps. Dramatically improves accuracy on math, logic, and multi-step problems.

### Tabular Chain-of-Thought (TCoT)
Structure reasoning in a table format. Each row is a reasoning step with columns for the step, reasoning, and intermediate result. Good for systematic comparisons and structured analysis.

### Skeleton-of-Thought (SoT)
Ask the model to first outline its answer structure, then fill in each section. Reduces rambling and produces more organized outputs. Two phases: skeleton generation, then parallel expansion.

### Step-Back Prompting
Before answering the specific question, ask the model to first consider a broader, more abstract version of the question. Helps avoid getting lost in details.

### Self-Consistency
Run the same prompt multiple times and aggregate results. Take the most common answer. Useful when you need high reliability on reasoning tasks.

### Tree-of-Thoughts (ToT)
Explore multiple reasoning paths simultaneously, evaluate each, and select the best. Resource-intensive but powerful for problems with multiple valid approaches.

### Self-Ask Prompting
The model generates and answers its own sub-questions before tackling the main question. Good for complex queries that benefit from decomposition.

---

## Iterative Improvement Techniques

### Rephrase & Respond
Ask the model to first rephrase the question in its own words, then answer the rephrased version. Reduces misinterpretation.

### Recursive Criticism & Improvement (RCI)
Generate an initial output, then ask the model to critique it and produce an improved version. Can be repeated multiple times. Effective for writing, code review, and quality improvement.

### Decomposed Prompting
Break complex tasks into discrete sub-tasks, each with its own optimized prompt. Chain the outputs together. More reliable than asking for everything at once.

### Least-to-Most Prompting
Start with the simplest sub-problem and progressively build to the full solution. Each step builds on previous answers. Good for problems that have natural difficulty gradients.

---

## Style & Persona Techniques

### Role Prompting
Assign the model a specific role or expertise. "You are a senior security engineer reviewing this code." Provides implicit context about tone, depth, and perspective.

### Emotional & Style Prompting
Specify emotional tone and writing style explicitly. Can reference known styles ("Write in the style of a New Yorker feature article") or define characteristics directly.

### Personality Archetypes
Four proven archetypes (see `context/prompt_personalities` for full templates):
- **Professional**: Formal, precise, business-appropriate. Best for enterprise, legal, finance.
- **Efficient**: Concise, direct, no extras. Best for code generation, developer tools, automation.
- **Fact-Based**: Grounded, corrective, evidence-driven. Best for debugging, evals, risk analysis.
- **Exploratory**: Enthusiastic, clear explanations. Best for documentation, onboarding, training.

---

## Advanced & Specialized Techniques

### Constitutional AI (CAI)
Define explicit principles the output must satisfy. The model self-evaluates against these principles and revises. Good for safety, compliance, and quality guardrails.

### Analogical Prompting
Ask the model to find and reason from analogies. "What situation is most similar to this, and what can we learn from it?"

### Perspective-Taking
Ask the model to consider the problem from multiple viewpoints. "How would a user, a developer, and a PM each see this issue?"

### Meta-Prompting
Use the model to generate or improve prompts. "Write a prompt that would produce [desired output]." Useful for prompt optimization.

### Prompt Chaining
Connect multiple prompts in sequence where the output of one becomes input to the next. Essential for agentic workflows and complex multi-step processes.

---

## Token Optimization

- Start simple. Add complexity only when simpler approaches fail.
- Few-shot examples are token-expensive. Use the minimum number that covers your edge cases.
- XML tags and markdown headers add minimal tokens but significantly improve output structure.
- For long documents, place them above the query (not after) and ask for relevant quotes before analysis.
- Role prompting is token-cheap and can replace paragraphs of behavioral instructions.
- Remove redundant instructions. If two instructions say the same thing differently, keep the clearer one.
