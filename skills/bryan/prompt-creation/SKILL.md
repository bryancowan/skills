---
name: prompt-creation
description: "Create, review, and refine prompts for LLMs and AI agents. Use this skill when the user wants to: write or improve a prompt or system prompt; write AI instructions for tools like Lovable, ElevenLabs, Figma, Midjourney, or Veo; build a multi-agent pipeline or agentic workflow; fix a prompt producing bad results (hallucinating, off-topic, too generic, wrong format); write image generation, text-to-speech, video, or coding agent prompts; adapt prompts when switching models (e.g., GPT to Claude); or describe any task they want an LLM to do and need help with the instructions. Covers all output types and all major models. Also trigger when the user doesn't say 'prompt' but is clearly asking how to instruct an AI — use this skill liberally."
---

# Prompt Creation & Refinement

This skill helps create effective prompts for any LLM task — from simple one-shot instructions to complex multi-agent workflows. It applies prompt engineering best practices, adapts to specific models and output types, and guides users through iterative improvement.

## Hard rules — never violate

These rules apply across every mode. Violating any of them produces worse output than no prompt at all.

- **Never add Chain-of-Thought to reasoning-native models.** o3, o4-mini, DeepSeek-R1, and Qwen3 in thinking mode reason internally across thousands of tokens. Adding "think step by step" or any reasoning scaffolding actively degrades their output. For these models, give short clean instructions stating only the goal and desired output format.
- **Never embed fabrication-prone techniques in a single prompt.** Mixture of Experts, Tree of Thought, Graph of Thought, Universal Self-Consistency, and deep prompt chaining all require multi-pass orchestration or external infrastructure. When forced into a single forward pass, the model role-plays the structure and fabricates the content. Use these only when the user has real orchestration (e.g., agent SDK, LangChain, multi-call pipeline).
- **Add an over-engineering guard to any Claude Opus 4.x prompt.** Opus 4.x adds features, refactors, and abstractions that were not requested. Always include: "Only make changes directly requested. Do not add features, refactor, or introduce abstractions beyond what was asked."
- **Cap clarifying questions at 3.** Lead with the 1–2 most important based on context; fold the rest in later. Endless clarification frustrates users and pushes the prompt off-topic.
- **Never output a prompt without confirming the target tool/model when ambiguous.** Different tools and models need different syntax — guessing produces a worse first-shot result than asking.

## Detect what the user needs

Before writing anything, figure out which mode applies:

| Mode | Signal |
|---|---|
| **Create new prompt** | User describes a task they want an LLM to do |
| **Create agent series** | User needs multiple coordinated prompts for a workflow |
| **Review & improve** | User shares an existing prompt and wants it better |
| **Iterate from results** | User has a prompt that's producing unsatisfactory outputs |
| **Quick paste** | User wants a single ready-to-paste prompt with no commentary |

Signals for **Quick paste mode**: "just give me the prompt", "no explanation", "ready to paste", "just the prompt", "don't explain", or the user is clearly mid-flow and needs output, not lessons. When in doubt and the request is concrete (clear tool, clear task), default to Quick paste; switch to Mode 1 only if pedagogy is requested.

Then gather the key details. Ask targeted follow-up questions for anything missing — don't guess at critical parameters.

### What to ask about

- **Task**: What should the LLM accomplish? What does a good output look like?
- **Target model**: Which model will run this? (Claude, GPT-5, Gemini, Codex, GLM, etc.) Different models respond differently to the same prompt.
- **Output type**: Text, code, image generation prompt, text-to-speech script, video prompt, structured data, or something else?
- **Tool or service**: Will this run in a specific tool? (Lovable, Figma, ElevenLabs, OpenClaw, Claude Code, ChatGPT, etc.)
- **Audience & tone**: Who sees the output? What personality should the LLM adopt?
- **Constraints**: Length limits, format requirements, compliance needs, token budgets?

Don't ask all of these at once. Lead with the 1-2 most important questions based on context, and fold the rest in naturally.

---

## Mode 1: Create a new prompt

Build the prompt using this structure. Not every prompt needs every element — use judgment about what the task requires.

### Prompt anatomy

1. **Role / Persona** — Who the LLM should be. A clear role provides implicit context about expertise, tone, and perspective. ("You are a senior data analyst who specializes in financial reporting.")

2. **Context** — Background information the LLM needs to do the job well. Include what's relevant, omit what isn't. Place long reference documents above the instructions, not after.

3. **Task** — What specifically to do. Use imperative mood. Be direct and unambiguous. ("Analyze the attached CSV and identify the top 3 revenue trends" not "Could you maybe look at this data?")

4. **Constraints** — Boundaries on the output. What to include, what to avoid, length limits, format requirements, style guidelines. Frame all constraints positively: instead of "don't use technical jargon," write "use plain language accessible to a general audience." Models follow positive instructions ("do X") more reliably than negative ones ("don't do Y").

5. **Output format** — How the result should be structured. Specify explicitly. Use examples of the desired format when possible.

6. **Examples** — 2-5 diverse, representative input/output pairs that demonstrate expected behavior. Wrap in delimiters (`<example>` tags, markdown code blocks, or clear separators). Quality and diversity of examples matters more than quantity.

### Apply the right techniques

Read `references/techniques.md` for a complete technique selection matrix. The key decision:

- **Simple, well-defined tasks** → Zero-shot with clear instructions is often enough. Start here.
- **Tasks needing consistent format** → Few-shot examples are the most reliable lever.
- **Reasoning-heavy tasks** → Chain-of-thought or step-back prompting.
- **Complex multi-part tasks** → Decompose into sub-prompts or use least-to-most.
- **Quality-critical outputs** → Recursive criticism & improvement, or self-consistency.

Start with the simplest approach that could work. Add complexity only when simpler methods fall short.

### Adapt to the target model

If the user specifies a model (or you can infer one), load the relevant model-specific guide from `context/models/` to apply model-specific optimizations:

| Model Family | Reference Path |
|---|---|
| Anthropic Claude | `context/models/anthropic-claude/` |
| OpenAI GPT-5 / GPT-5.4 | `context/models/openai-gpt-5-family/` — vision/document tasks: see `gpt-5-4_vision_document_guide` in that directory |
| Google Gemini | `context/models/google-gemini/` |
| Google Nano Banana | `context/models/google-nano-banana/` |
| Z.ai GLM | `context/models/zai-glm/` |
| OpenAI Codex | `context/models/openai-codex/` |
| Mistral | `context/models/mistral/` |
| Alibaba Qwen | `context/models/alibaba-qwen/` |
| MiniMax M2 | `context/models/minimax-m2/` |
| Moonshot Kimi | `context/models/moonshot-kimi/` |

Key model differences to keep in mind:
- **Claude**: Excels with XML tags for structure, explicit instructions, extended thinking for complex reasoning. Responds well to explanations of *why* behavior matters.
- **GPT models**: Work well with markdown formatting, system/user message separation, strong function calling support.
- **Gemini**: Handles very large contexts (up to 2M tokens), strong at factual tasks and visual reasoning.

If no model is specified and it matters for the prompt, ask.

### Adapt to the output type

Different output modalities need different prompting strategies. Load the relevant guide when applicable:

| Output Type | Reference Path | Key Principle |
|---|---|---|
| **Image generation** | `context/image-generation/` — for gpt-image-2 specifically, read `gpt-image-2-prompting-guide` | Use natural language descriptions, not tag soup. Structure as background → subject → details → constraints. Be specific about materials, medium, and composition. |
| **Speech-to-speech (Realtime)** | `context/speech-to-speech/gpt-realtime-prompting-guide` | Voice agents need different prompting than text. Use the 8-section structure (Role, Personality, Context, Pronunciations, Tools, Rules, Conversation Flow, Safety). Prefer bullets, pin language, add Variety rule, define explicit conversation states with exit criteria. |
| **Text-to-speech** | `context/text-to-speech/` | Normalize text (expand numbers, abbreviations). Use SSML break tags for pauses. Control pacing through narrative styling. |
| **Video generation** | `context/video-generation/` | Load `context/video-generation/google-veo-prompt-guide.md` for Veo-specific guidance. |
| **Code** | `context/coding/` | Specify language, framework, patterns. Include example signatures. Define error handling expectations. |
| **Structured data** | (no special file) | Provide exact schema. Use few-shot examples of valid output. Specify edge case handling. |

### Adapt to tools and services

If the prompt will run in a specific tool, load the relevant guide:

| Tool / Service | Reference Path |
|---|---|
| Lovable | `context/tools-and-services/lovable/` |
| ElevenLabs | `context/tools-and-services/eleven-labs/` |
| Figma | `context/tools-and-services/figma/` |
| OpenClaw | `context/tools-and-services/openclaw/` |
| Cursor / Windsurf | `context/tools-and-services/cursor-windsurf/` |
| Cline | `context/tools-and-services/cline/` |
| GitHub Copilot | `context/tools-and-services/github-copilot/` |
| Devin / SWE-agent | `context/tools-and-services/devin/` |
| Antigravity | `context/tools-and-services/antigravity/` |
| Comet / Atlas (browser agents) | `context/tools-and-services/comet-atlas/` |
| Bolt / v0 / Figma Make / Stitch | `context/tools-and-services/bolt-v0/` |
| ComfyUI | `context/tools-and-services/comfyui/` |
| Meshy / Tripo / Rodin (3D) | `context/tools-and-services/meshy-tripo-rodin/` |

These guides contain tool-specific prompt patterns, constraints, and best practices that differ from general prompting. Each contains explicit anti-patterns (e.g., scope locks for IDE agents, stop conditions for autonomous agents) that prevent common first-shot failures.

### Set the personality

Help the user choose a personality when it would improve output consistency. The four proven archetypes (full templates in `context/prompt_personalities`):

- **Professional** — Formal, precise, business-appropriate. Best for enterprise, legal/finance, production support. Cordial but transactional.
- **Efficient** — Concise, direct, no extras. Best for code generation, developer tools, batch automation. No opinions, greetings, or emotional language.
- **Fact-Based** — Grounded, corrective, evidence-driven. Best for debugging, evals, risk analysis, coaching. States assumptions, never fabricates.
- **Exploratory** — Enthusiastic, clear explanations. Best for documentation, onboarding, training. Makes learning enjoyable with analogies and structured explanations.

Personality is an operational lever, not aesthetic polish. It shapes verbosity, structure, and decision-making style. Personality instructions should not override task-specific output formats — if the user asks for an email, the email's tone follows the task, not the personality.

### Memory Block — when prior session context matters

When the user references prior decisions, prior failures, or established stack/architecture choices ("continue where we left off", "you already know my project", "now add the other thing"), prepend a Memory Block to the generated prompt. Place it in the first 30% of the prompt so it survives attention decay in the target model.

```
## Context (carry forward)
- Stack and tool decisions: [list]
- Architecture choices locked: [list]
- Constraints from prior turns: [list]
- What was tried and failed: [list, with reason]
```

Always re-provide this block in every new session — LLMs have no inter-session memory. If the user does not supply prior decisions, ask once for the minimum needed (counts toward the 3-question cap).

---

## Mode 2: Create an agent prompt series

When the user needs multiple coordinated prompts for a workflow (e.g., a research pipeline, content creation flow, or data processing chain), apply context engineering principles.

Read `context/Effective context engineering for AI agents - 2026-03-28T130401-0500.md` for the full framework. Key principles:

### Clarify before writing
Before drafting the agent series, ask the user about operational details that affect prompt design:
- **What tools are available to each agent?** (web search, file system, APIs, databases, etc.) Agents that lack explicit tool instructions tend to under-utilize or misuse their capabilities.
- **What guardrails or limits should each agent have?** (max search results, time limits, output length caps, topic boundaries) Without limits, agents can spend unbounded effort on a single step.
- **How will the pipeline be orchestrated?** (Claude Code subagents, LangChain, manual chaining, etc.) This affects how state is passed between agents.

If the user doesn't know yet, suggest sensible defaults and note them in the prompts.

### Decompose the task
Break the overall goal into discrete agent steps. Each agent should have a clear, focused responsibility. Ask:
- What are the natural stages of this task?
- What does each stage need as input? What does it produce?
- Where are the handoff points between agents?

### Design each agent's prompt
For each agent in the series:
1. **Define its role and scope** — What this agent is responsible for, and explicitly what it is not.
2. **Specify inputs** — What context it receives from previous agents or the user.
3. **Specify outputs** — What it must produce for the next agent or as a final deliverable.
4. **Include state passing instructions** — How to format handoff data so downstream agents can parse it reliably.
5. **Specify tools and limits** — Which tools the agent should use, how many results to retrieve, and when to stop. Agents with explicit tool instructions and resource limits produce more focused, predictable results.

### Apply context engineering principles
- **Right altitude**: Instructions should be specific enough to guide behavior, flexible enough to handle edge cases. Avoid brittle if-else logic and avoid vague hand-waving.
- **Just-in-time context**: Don't front-load all information. Let agents retrieve what they need when they need it.
- **Minimal context**: Each agent should receive only the context relevant to its task. Don't pass the full conversation history if a summary suffices.
- **Progressive disclosure**: Let agents discover context through exploration rather than preloading everything.

### For long-horizon workflows
Read `context/coding/agent-memory.md` for memory architecture patterns. Consider:
- **Compaction**: Summarize and compress context between steps, preserving key decisions and unresolved issues.
- **Structured note-taking**: Have agents write persistent notes that later agents can read.
- **Memory separation**: Keep instruction memory (rules, constraints) separate from learning memory (experience, preferences).

### Output the series
Present each agent's prompt separately, in execution order, with clear labels:
```
Agent 1: [Name / Role]
Purpose: [What this agent does]
Input: [What it receives]
Output: [What it produces]
---
[The actual prompt]
```

---

## Mode 3: Review and improve an existing prompt

When the user shares a prompt for improvement, analyze it systematically.

### Assessment checklist
Evaluate the prompt against these dimensions:

- **Clarity**: Are instructions unambiguous? Could they be misinterpreted?
- **Specificity**: Are expectations concrete? Or is the model left guessing about format, length, or approach?
- **Structure**: Is information organized logically? Are sections delineated? Or is it a wall of text?
- **Technique usage**: Is it using appropriate techniques for the task complexity? (See `references/techniques.md`)
- **Examples**: Does it include examples where they'd help? Are the examples diverse and representative?
- **Negative framing**: Are there "don't do X" instructions? Reframe them positively — models follow positive instructions more reliably. "Don't use jargon" becomes "Use plain language accessible to a general audience." "Don't add unrequested features" becomes "Implement exactly what was requested; if you notice improvement opportunities, mention them in a separate note." Always convert negatives during review.
- **Redundancy**: Are there repeated or contradictory instructions?
- **Model fit**: If a target model is known, does the prompt use that model's strengths?

### Deliver improvements

Present the improved prompt in a copyable code block, followed by "Revision Notes" — 3-5 bullets explaining the most impactful changes and why they matter. This teaches the user better prompting habits, not just gives them a better prompt.

**Example format:**
```
[Improved prompt here]
```

**Revision Notes:**
- Restructured instructions into clear sections with headers — helps the model parse the prompt and reduces missed instructions
- Added 3 few-shot examples covering the main edge cases — this is the single biggest lever for consistent output format
- Replaced "don't use jargon" with "use plain language accessible to a general audience" — positive framing is more reliably followed
- Added explicit output format specification with a template — removes guesswork about structure

---

## Mode 4: Iterate based on observed results

When the user's prompt is producing unsatisfactory outputs, diagnose the root cause before prescribing fixes.

### Common issues and targeted fixes

| Symptom | Likely Cause | Fix |
|---|---|---|
| Output too verbose | No length constraints; exploratory personality | Add explicit length limits; switch to Efficient personality; add "Be concise" |
| Output too short / shallow | Insufficient context; no instruction to elaborate | Add "Provide detailed analysis with reasoning"; use Chain-of-Thought |
| Wrong format | No format specification or examples | Add explicit format template; add 2-3 few-shot examples |
| Hallucinating facts | No grounding instruction; no source material | Add "Only use information from the provided context"; add Fact-Based personality |
| Ignoring instructions | Instructions buried in long prompt; contradictory rules | Restructure with headers; move critical instructions to the top; resolve contradictions |
| Inconsistent outputs | No examples; ambiguous instructions | Add few-shot examples; use Self-Consistency (multiple runs); tighten constraints |
| Off-topic tangents | Scope not defined; no guardrails | Add explicit scope ("Focus only on X"); add "If the question is outside [scope], say so" |
| Tone mismatch | No personality defined; wrong personality for task | Add or change personality archetype; provide tone examples |

### Iteration workflow

1. **Ask to see** the current prompt and a sample of the problematic output
2. **Diagnose** the root cause using the table above
3. **Make targeted changes** — fix the specific issue, don't rewrite the whole prompt
4. **Explain the change** so the user understands what went wrong and why the fix works
5. **Suggest a test** — propose a specific input to try with the revised prompt to verify the fix

If multiple issues exist, fix the most impactful one first and iterate. Avoid changing too many things at once — it makes it hard to know what worked.

### When to suggest A/B testing

If the user is optimizing a prompt for production use (high volume, consistent quality matters), suggest:
- Run the same inputs through both versions
- Compare outputs on the specific dimension that matters (accuracy, tone, format, etc.)
- Test on edge cases, not just typical inputs

---

## Mode 5: Quick paste — single ready-to-paste prompt, no commentary

Use this mode when the user wants a single copyable prompt and nothing else. Trigger phrases: "just give me the prompt", "no explanation", "ready to paste", "just the prompt", "don't explain". Also default here when the request is concrete (clear tool + clear task) and the user is clearly mid-flow.

### Process

1. Silently extract the 9 dimensions: task, target tool, output format, constraints, input, context, audience, success criteria, examples needed.
2. If a critical dimension is missing, ask up to 3 questions. If still ambiguous on the target tool, ask one more.
3. Apply all hard rules. Apply tool-specific routing if applicable.
4. Run the diagnostic checklist (see below) silently — fix issues without explaining unless a fix changes user intent.
5. Output exactly:

```
[the prompt — single fenced block, ready to paste]
```

🎯 Target: [tool/model name]  
💡 [one sentence — what was optimized and why]

If setup steps are needed before pasting (e.g., "attach reference image first", "set temperature to 0.1"), add a 1–2 line note below. Otherwise omit.

### Diagnostic checklist (silent fix)

Scan the user's request for these failure patterns. Fix without commentary unless the fix changes intent.

**Task:** vague verb → precise operation; two tasks in one prompt → split into Prompt 1/2; no success criteria → derive binary pass/fail; emotional description → extract specific fault.

**Context:** assumes prior knowledge → add Memory Block; invites hallucination → add grounding constraint ("State only what you can verify. If uncertain, say so.").

**Format:** no output format → derive from task type; implicit length → add word/sentence count; vague aesthetic ("professional") → translate to measurable specs.

**Scope:** no file/function boundaries for IDE AI → add scope lock; no stop conditions for agents → add checkpoint and human-review triggers.

**Reasoning:** logic task with no step-by-step (on standard models) → add CoT; CoT on reasoning-native model → REMOVE IT; new prompt contradicts prior session decisions → flag and resolve.

**Agentic:** no starting state → add current state; no target state → add deliverable; silent agent → add "After each step output: ✅ [what was completed]"; unrestricted filesystem → add scope lock; no human-review trigger → add stop conditions for destructive actions.

### Quick-paste verification

Before delivering, confirm:
1. Target tool/model correctly identified, syntax matches.
2. Critical constraints in the first 30% of the prompt.
3. Strongest signal words used (MUST over should, NEVER over avoid).
4. No fabrication-prone single-prompt techniques embedded.
5. No CoT instructions on reasoning-native models.
6. Every sentence load-bearing — no padding.

Success metric: user pastes, it works first try.

---

## Accepting new best practices

When the user provides new model-specific, tool-specific, or output-type guidance, save it to the appropriate location:

- **New model**: Create a directory under `context/models/[model-name]/` and save the guide there
- **New tool/service**: Create a directory under `context/tools-and-services/[tool-name]/` and save the guide there
- **New output type**: Create a file or directory under `context/` with a descriptive name
- **Updated guidance**: Update the existing file in place

Format for new reference files:
```markdown
# [Model/Tool/Output Type] Prompting Guide

## Overview
Brief description of what this is and when these practices apply.

## Key Principles
The most important things to know.

## Specific Techniques
Detailed guidance organized by use case.

## Examples
Before/after examples showing the techniques in action.
```

---

## Output format

When delivering a prompt to the user:

1. **The prompt itself** in a fenced code block (easy to copy)
2. **Key design choices** — 3-5 bullets explaining the most important decisions and why (so the user learns, not just receives)
3. **Suggested first test** — a specific input to try with the prompt to verify it works
4. **Iteration hooks** — what to watch for in the output that might signal a need for refinement

Keep explanations concise. The prompt is the deliverable — the commentary supports it, not the other way around.
