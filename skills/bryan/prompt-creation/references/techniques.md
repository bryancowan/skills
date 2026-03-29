# Prompt Engineering Techniques Reference

Quick-lookup guide for selecting the right prompting technique based on task type and complexity. Read the full comprehensive guide at `context/Comprehensive Guide to Prompt Engineering Techniques  Claude - 2026-03-28T181003-0500.md` for detailed explanations and examples.

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
