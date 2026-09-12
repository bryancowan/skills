---
name: prompt-creation
description: "Create, review, and refine prompts for LLMs and AI agents. Use
  this skill when the user wants to: write or improve a prompt or system prompt;
  write AI instructions for tools like Lovable, ElevenLabs, Figma, Midjourney,
  or Veo; build a multi-agent pipeline or agentic workflow; fix a prompt
  producing bad results (hallucinating, off-topic, too generic, wrong format);
  write image generation, text-to-speech, video, or coding agent prompts; adapt
  prompts when switching models (e.g., GPT to Claude); or describe any task they
  want an LLM to do and need help with the instructions. Covers all output types
  and all major models. Also trigger when the user doesn't say 'prompt' but is
  clearly asking how to instruct an AI — use this skill liberally."
metadata:
  copilot-enabled-agents: opencode,claude,codex
---

# Prompt Creation & Refinement

This skill helps create effective prompts for any LLM task — from simple one-shot instructions to complex multi-agent workflows. It applies prompt engineering best practices, adapts to specific models and output types, and guides users through iterative improvement.

## Hard rules — never violate

These rules apply across every mode. Violating any of them produces worse output than no prompt at all.

- **Never add Chain-of-Thought to reasoning-native models.** Claude 5 / 5.1 (adaptive thinking), GPT-6 Astra, GPT-5.x with reasoning on, Gemini 3.x, GLM-5.3, Qwen3 thinking mode, Gemma 4 thinking, and the o-series all reason internally. "Think step by step" wastes tokens and degrades output. State the goal and desired format, nothing more. Full matrix in `references/techniques.md`. **Raise the effort parameter instead of prompting around shallow reasoning** — every vendor says this. Two models can't even be put in a non-thinking state: GPT-6 Astra (no `none` level) and GLM-5.3 (thinking mandatory).
- **Never embed fabrication-prone techniques in a single prompt.** Mixture of Experts, Tree of Thought, Graph of Thought, Universal Self-Consistency, and deep prompt chaining all require multi-pass orchestration or external infrastructure. When forced into a single forward pass, the model role-plays the structure and fabricates the content. Use these only when the user has real orchestration (e.g., agent SDK, LangChain, multi-call pipeline).
- **Delete instructions that current models made obsolete — but check whose model you're targeting.** These findings are vendor-specific and do not transfer:
  - **Claude 5.x**: drop "double-check your answer", forced progress summaries, "CRITICAL: you MUST use this tool", tool-call examples, and prescriptive style rules — they cause over-verification and tool overtriggering. Replace rules with judgment framings the model can generalize. Anthropic cut >80% of Claude Code's system prompt with no eval loss. Prefill, `temperature`/`top_p`/`top_k`, and thinking `budget_tokens` additionally return **400 errors**.
  - **GPT-6 Astra / GPT-5.6**: delete *redundancy*, not specificity — lean prompts are the measured win. OpenAI still prescribes **concrete examples of how to invoke commands** for coding, so don't strip tool-call examples here.
  - **GLM-5.3**: keep the structure. Z.ai's documented prompt shapes *enumerate deliverables* and bake in a verification step; stripping them works against the vendor's own guidance.
  - **Don't confuse two different things called "verification".** Telling Claude to *re-check its own reasoning* is redundant (it self-verifies). Telling any model to *run the build and report results* is a deliverable, not scaffolding — keep it everywhere.

  Full context: `references/context-engineering.md`; per-model delete list in `context/models/anthropic-claude/claude-5-family-guide.md`.
- **Effort level names are not comparable across models.** `high` buys a different amount of thinking on every model — including between point releases of the same family. Never port a prompt at "the same effort level" and call it a comparison; re-sweep against real evals. Defaults also run in different directions: Claude and OpenAI default mid-range and you step up, **GLM-5.3 defaults to `max`** and you step down.
- **Agent conversation history must be append-only.** On Claude Fable 5.1, editing earlier turns between requests returns a 400 — not just a cache miss. Injecting/removing per-turn reminders, summarizing in place, and rebuilding `system` or `tools` mid-session are all now correctness bugs. If you are writing an agent-loop prompt, read the append-only section of the Claude 5 guide before anything else.
- **Scope guards are still needed, but the wording changed.** Claude Opus 5, Fable 5, and Fable 5.1 expand scope and over-tidy at high effort; use the current snippets in the Claude 5 guide rather than the old Opus 4.x boilerplate.
- **Check the vendor docs before quoting a model name, price, or parameter.** This skill's guides carry a `Sourced:` date; model generations have turned over in under two months. If the user is choosing a model or budgeting, verify rather than reciting.
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

Signals for **Quick paste mode**: "just give me the prompt", "no explanation", "ready to paste", "just the prompt", "don't explain", or the user is clearly mid-flow and needs output, not lessons.

**Tiebreakers** (these modes overlap constantly — resolve them this way):

- **Mode 1 vs. Mode 5.** Concreteness alone doesn't decide it. Go to Quick paste when the user's message is *short and transactional*. Go to Mode 1 when they supplied background, constraints, or an example product/input — that effort signals they want the reasoning too.
- **Mode 3 vs. Mode 4.** If they pasted a prompt, start in Mode 3. But **always check the Mode 4 symptom table too** — the diagnosis for "goes off on tangents", "too verbose", or "ignores instructions" lives there, and Mode 3's checklist alone will miss it.
- **Mode 2** wins over all of them whenever the answer is more than one prompt.

Then gather the key details. Ask targeted follow-up questions for anything missing — don't guess at critical parameters.

### What to ask about

- **Task**: What should the LLM accomplish? What does a good output look like?
- **Target model**: Which model will run this? (Claude Fable 5.1 / Opus 5 / Sonnet 5, GPT-6 Astra, GPT-5.6, Gemini 3.x, Codex, GLM-5.3, etc.) Different models respond differently to the same prompt. **Family-level ("Claude", "GPT") is usually not specific enough** — effort defaults, verbosity, and cost differ sharply within a family. Ask for the tier when it would change the prompt.
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
- **Reasoning-heavy tasks** → On reasoning-native models, **raise effort** — do not add chain-of-thought. Step-back prompting is still fine. CoT only helps on non-thinking models.
- **Complex multi-part tasks** → Decompose into sub-prompts or use least-to-most.
- **Quality-critical outputs** → Recursive criticism & improvement *within one response*. **Self-consistency needs N real samples plus aggregation** — only recommend it when the user has actual orchestration, never as a line inside a single prompt.

Start with the simplest approach that could work. Add complexity only when simpler methods fall short.

### Adapt to the target model

If the user specifies a model (or you can infer one), load the relevant model-specific guide from `context/models/` to apply model-specific optimizations:

| Model Family | Reference Path |
|---|---|
| **Anthropic Claude 5.x** (Fable 5.1 / Mythos 5.1 / Fable 5 / Opus 5 / Sonnet 5 / Haiku 4.5) | `context/models/anthropic-claude/claude-5-family-guide.md` — model selection, `effort`, adaptive thinking, **append-only history**, the Fable 5.1 behavioral deltas, verbosity, scope control, agentic patterns, and the delete list |
| Anthropic Claude Opus 4.8 (prior gen) | `context/models/anthropic-claude/claude-opus-4-8-guide.md` |
| **OpenAI GPT-6 Astra** (`gpt-6-astra`) | `context/models/openai-gpt-6-family/gpt-6-astra-guide.md` — spec, effort (no `none`), the 272K pricing cliff, async tool calling, mid-turn steering, dynamic reasoning config, `instructions` vs roles, `prompt` object retirement |
| **OpenAI GPT-5.6** (`sol` / `terra` / `luna` / `cyber`) — cost tier below Astra | `context/models/openai-gpt-5-family/gpt-5-6-guide.md` — lean prompts, autonomy boundaries, programmatic tool calling, persisted reasoning, explicit caching |
| OpenAI GPT-5.5 | `context/models/openai-gpt-5-family/gpt-5-5-guide.md` |
| OpenAI frontend/UI generation | `context/models/openai-gpt-5-family/gpt-5_frontend` |
| OpenAI — prompt isn't working and you don't know why | `context/models/openai-gpt-5-family/gpt-5-toubleshooting-guide` (filename typo is in the repo, not here) |
| OpenAI vision / document input | `context/vision-and-documents/document-understanding-tips.md` (settings-first decision guide), `context/models/openai-gpt-5-family/openai-vision-guide.md` |
| **Google Gemini 3.x** (flagship `gemini-3.8-flash`) | `context/models/google-gemini/gemini-3-family-guide.md` (models + pricing + behavior), `gemini-prompting-strategies.md` (technique), `gemini-file-prompting.md` (files as input) |
| Google Gemma 4 | `context/models/google-gemma/gemma-4-guide.md` — chat template control tokens, thinking, Cerebras `reasoning_effort` and image inputs |
| Google Nano Banana | `context/image-generation/google-image-models-guide.md`; source clipping in `context/models/google-nano-banana/` |
| **Z.ai GLM-5.3 / GLM-5.3-Flash (VLM)** | `context/models/zai-glm/glm-5-3-guide.md`; agentic coding harnesses: `context/coding/zai-coding-agents.md` — mandatory thinking, `reasoning_effort` defaulting to `max`, deliverable-enumerating prompt style, and the VLM render→inspect→refine loop |
| OpenAI Codex (`gpt-5.3-codex`) | `context/models/openai-codex/codex-prompting-guide` — starter prompt, AGENTS.md, compaction, tools, preambles, phase parameter, metaprompting. **Goals (`/goal`): `context/coding/codex-goals.md`.** Full source: `context/coding/codex-full-guide.md` |
| Mistral | `context/models/mistral/mistral-guide.md` — model selection, prompting, sampling (incl. cheap `N > 1`) |
| Alibaba Qwen3 (text) | `context/models/alibaba-qwen/qwen3-prompt-guide.md` |
| Alibaba **Wan** (image + video generation — a different family from Qwen) | `context/models/alibaba-wen/text-to-image-guide.md`, `context/models/alibaba-wen/Text-to-video-image-to-video prompt guide` |
| Moonshot Kimi | `context/models/moonshot-kimi/kimi-guide.md` |

Superseded guides live in `archive/` subfolders under each model directory — load them only when the user is explicitly targeting a legacy model.

Key model differences to keep in mind:
- **Claude 5.x**: XML tags for structure; explanations of *why* a rule exists generalize well; `effort` is the main cost/quality dial; **no sampling parameters, no prefill**; **history must be append-only on Fable 5.1**. Opus 5 runs verbose and needs an explicit brevity instruction. **Fable 5.1 inverts two old habits**: it *under*-formats in chat and *under*-narrates during tool calls, so anti-bullet and "save it for the summary" rules ported from older prompts make things worse.
- **GPT-6 Astra / GPT-5.6**: Lean prompts measurably outperform padded ones; state each instruction once; put tool guidance in tool descriptions. On Astra, match register to effort — precise logic and data at `low`/`medium`, goal-and-constraints at `high`+.
- **Gemini 3.x**: Defaults to *concise* output — ask for detail; Google now **strongly** recommends leaving sampling params at default despite accepting them; Google recommends few-shot examples in nearly every prompt (the opposite of OpenAI's lean-prompt guidance). Don't port either belief blindly.
- **Open-weight models** (Gemma, Qwen, GLM, Kimi): benefit from more explicit structure and few-shot examples than the frontier hosted models; Gemma 4 needs literal chat-template control tokens. GLM rewards **enumerating the deliverables** you want back.

If no model is specified and it matters for the prompt, ask.

### Adapt to the output type

Different output modalities need different prompting strategies. Load the relevant guide when applicable:

| Output Type | Reference Path | Key Principle |
|---|---|---|
| **Image generation (OpenAI)** | `context/image-generation/gpt-image-prompting-guide.md` — **gpt-image-2.5 (`flare` / `sunburst`)** default, plus gpt-image-2 and the 1.x family: model selection, quality levels through `max`, sizing to 3840px, transparency, Images API vs. the Responses `image_generation` tool. Deep source with worked examples: `gpt-image-models-full-guide.md` | Define the result, then use labeled sections: scene → subject → details → constraints. Format (prose, JSON-ish, tags) is your choice — optimize for maintainability. Separate what changes from what must be preserved. |
| **Image generation (Google)** | `context/image-generation/google-image-models-guide.md` — Nano Banana 2 / 2 Lite / Pro and Imagen 4 | Nano Banana wants descriptive prose and reference images (up to 14); Imagen wants subject + context + style with photography modifiers and a 480-token ceiling. |
| **Vision / document input** | `context/vision-and-documents/document-understanding-tips.md`; `context/models/openai-gpt-5-family/openai-vision-guide.md`; Gemini: `context/models/google-gemini/gemini-file-prompting.md` | **Check the settings before rewriting the prompt** — `detail`, verbosity, and reasoning effort dominate wording here. Name the operation, not the object. Extract before interpreting. Tell the model to write "unreadable" rather than guess. State the bounding-box coordinate contract explicitly. |
| **Speech-to-speech (Realtime)** | `context/speech-to-speech/gpt-realtime-prompting-guide` — `gpt-realtime-2.1` / `1.5` | Voice agents need different prompting than text. Use the 8-section structure (Role, Personality, Context, Pronunciations, Tools, Rules, Conversation Flow, Safety). Prefer bullets, pin language, add Variety rule, define explicit conversation states with exit criteria. Preambles: one short sentence. |
| **Live voice with backend delegation** | `context/speech-to-speech/gpt-live-prompting-guide.md` — `gpt-live-1` | Different model *and* different prompt shape: the prompt is mostly a **delegation policy**. Personality + backchannel policy + interruption policy + delegation policy. "Delegate before answering; don't guess while waiting." Not interchangeable with gpt-realtime prompts. |
| **Text-to-speech** | `context/text-to-speech/` | Normalize text (expand numbers, abbreviations). Use SSML break tags for pauses. Control pacing through narrative styling. |
| **Video generation** | `context/video-generation/` — OpenAI Sora: `openai-video-generation-guide.md`; Google Veo: `google-veo-prompt-guide.md` | Name shot type, subject, action, setting, and lighting. One action beat per generation; chain beats with the extend endpoint. Describe the camera, not just the scene. |
| **Code** | `context/coding/` — includes `codex-goals.md` (persistent `/goal` objectives) and `codex-full-guide.md` (full OpenAI Codex agentic-coding source) | Specify language, framework, patterns. Include example signatures. Define error handling expectations. For long-running work with an unknown path, reach for a Codex Goal instead of a prompt. |
| **Structured data** | (no special file) | Provide exact schema. Use few-shot examples of valid output. Specify edge case handling. |

### Adapt to tools and services

If the prompt will run in a specific tool, load the relevant guide:

| Tool / Service | Reference Path |
|---|---|
| ChatGPT (the product, not the API) | `context/tools-and-services/chatgpt/chatgpt-prompt-guide.md` — write for a non-technical user: no parameters, no system-prompt architecture |
| Lovable | `context/tools-and-services/lovable/` |
| ElevenLabs | `context/tools-and-services/eleven-labs/` |
| Figma | `context/tools-and-services/figma/` — **plugin-API reference only (`defineProperties`), not prompting guidance.** For Figma Make, use the Bolt / v0 / Stitch row below. |
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

## Cross-cutting concerns

These apply in every mode. Load the reference file when the concern is live; don't inline the content.

### Choose the model, not just the prompt

`references/model-selection.md` — cross-vendor pricing, task-shape recommendations, and **what breaks when you switch families** (sampling params, prefill, few-shot philosophy, effort semantics, verbosity defaults, tokenizer changes).

Two rules worth applying by default: optimize for accuracy against a real eval set before optimizing for cost, and **tune the effort parameter before switching models** — on Claude 5 and GPT-5.6 the effort range is wider than the gap between adjacent models. If the user is choosing a model or complaining about cost, read this file.

### Context engineering — read this when reviewing any long prompt

`references/context-engineering.md` — the habits that helped 2024–2025 models now hurt. Prescriptive rules → judgment framings; tool-call examples → expressive parameters; front-loading → progressive disclosure; prose specs → test suites and reference code. Anthropic removed **>80% of Claude Code's system prompt** with no eval loss.

**Default hypothesis when a user brings a long system prompt for review: it's too long, not missing a rule.** Work the five-step reduction pass in that file before adding anything.

### Guardrails

`references/guardrails.md` — hallucination reduction, output consistency, jailbreak and prompt-injection defense, and prompt-leak mitigation, with copyable snippets.

Reach for it whenever the prompt will (a) make factual claims from supplied documents, (b) run in production against untrusted users, or (c) process third-party content — web pages, emails, tool results, OCR. **Any agent that reads content it didn't author needs the indirect-injection section**, and that need is easy to miss.

### Cost and caching

`references/caching-and-cost.md` — caching is a prompt-*structure* decision. Static content first, volatile content last; never reorder tool definitions; never inject a timestamp near the top.

Apply the ordering rule to every long system prompt you write, whether or not the user mentioned cost. Read the file when the user is running at volume, complaining about spend, or building a multi-turn agent.

### Research, search, and citations

`references/research-and-search.md` — deep research models, the web search tool, and citation formatting. Includes the clarify → rewrite → research pipeline that ChatGPT's Deep Research runs and the API does not.

Use it for any prompt that gathers information and has to show sources. A domain allowlist enforces source quality; "use reputable sources" only wishes for it.

---

## Mode 2: Create an agent prompt series

When the user needs multiple coordinated prompts for a workflow (e.g., a research pipeline, content creation flow, or data processing chain), apply context engineering principles.

Read `references/context-engineering.md` first — it carries the current generation's rules. `context/Effective context engineering for AI agents - 2026-03-28T130401-0500.md` is the older deep source; its altitude and just-in-time material still holds, its scaffolding assumptions don't. Key principles:

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
- **Right altitude**: Specific enough to guide behavior, flexible enough to handle edge cases. Brittle if-else logic and vague hand-waving fail in opposite directions.
- **Judgment over rules**: Give each agent the goal and the reasoning behind a constraint, not a list of prohibitions. Rules fire in the cases you didn't anticipate; judgment framings generalize.
- **Just-in-time context**: Don't front-load. Let agents retrieve what they need when they need it.
- **Minimal context**: Each agent receives only what its task needs. Pass a summary, not the full history.
- **Progressive disclosure**: Let agents discover context through exploration rather than preloading everything.
- **State each instruction once.** If it's in the tool description, it doesn't belong in the system prompt too.
- **Don't give tool-call examples.** They constrain the agent to the demonstrated exploration space. Make the tool's parameters and types expressive instead.
- **Prefer rich references to prose specs.** A failing test is an unambiguous specification; a paragraph describing the test is not.
- **Keep history append-only** in any Claude-backed loop — see the hard rules.

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
- **Bloat**: Is it longer than it needs to be? Repeated instructions, anti-laziness scaffolding ("be thorough", "double-check"), tool-call examples, and prescriptive style rules are all net-negative on current models. Run the reduction pass in `references/context-engineering.md` — on a long prompt this is usually the highest-impact edit available.
- **Technique usage**: Is it using appropriate techniques for the task complexity? (See `references/techniques.md`)
- **Examples**: Does it include examples where they'd help? Are the examples diverse and representative?
- **Negative framing**: Are there "don't do X" instructions? Reframe them positively where the positive form is at least as clear — models generally follow positive instructions more reliably. "Don't use jargon" becomes "Use plain language accessible to a general audience."
  **Two exceptions — do not convert these.** (a) Vendor-published snippets measured in the vendor's own testing: the scope-control and unrequested-changes blocks in the Claude 5 guide are deliberately negative and outperform paraphrases. Paste them as written. (b) Cases where the negative names a specific behavior and the positive only gestures at it — "don't add error handling for scenarios that cannot happen" has no crisp positive equivalent.
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
| Output too short / shallow | Insufficient context; no instruction to elaborate; effort set too low | **Raise effort first** — that is the intended lever on every current model. Then add "Provide detailed analysis with reasoning". Add Chain-of-Thought only on non-thinking models. |
| Wrong format | No format specification or examples | Add explicit format template; add 2-3 few-shot examples |
| Hallucinating facts | No grounding instruction; no source material | Add "Only use information from the provided context"; add Fact-Based personality |
| Ignoring instructions | Instructions buried in long prompt; contradictory rules | Restructure with headers; move critical instructions to the top; resolve contradictions; **cut length** — dilution is as common a cause as burial |
| Over-verifying, over-tidying, expanding scope | Anti-laziness scaffolding written for older models | Delete "double-check"/"be thorough"/"CRITICAL: you MUST"; add the current scope-control snippet from the Claude 5 guide |
| Agent goes silent during long tool runs (Claude) | Fable 5.1 narrates less; client may not be requesting updates at all | Set `thinking.display: "updates"`; delete "hold findings for the final response" lines |
| Agent request fails with a 400 mid-conversation (Claude) | History was edited between requests | Make history append-only; move reminders to turn-scoped system messages |
| Inconsistent outputs | No examples; ambiguous instructions | Add few-shot examples; tighten constraints. Self-Consistency is an option **only if they can make multiple runs and aggregate** — it is not a prompt instruction. |
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

**Reasoning:** logic task with no step-by-step (on standard models) → add CoT; CoT on reasoning-native model → REMOVE IT; shallow reasoning → raise effort, don't prompt around it; new prompt contradicts prior session decisions → flag and resolve.

**Bloat:** same instruction stated twice → keep one; anti-laziness scaffolding → delete; tool-call examples → move guidance into the tool description.

**Agentic:** no starting state → add current state; no target state → add deliverable; silent agent → add "After each step output: ✅ [what was completed]"; unrestricted filesystem → add scope lock; no human-review trigger → add stop conditions for destructive actions.

### Quick-paste verification

Before delivering, confirm:
1. Target tool/model correctly identified, syntax matches.
2. Critical constraints in the first 30% of the prompt.
3. Emphasis used sparingly and only where it's load-bearing. Do **not** reflexively upgrade to MUST/NEVER/CRITICAL — on current models that causes tool overtriggering and over-compliance. Give the reason behind the rule instead; it generalizes further than the shouting does.
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

## Output format (Modes 1–4)

**Mode 5 overrides this entirely** — Quick paste delivers the prompt plus two lines and nothing else. The rest of this section does not apply there.

When delivering a prompt to the user in Modes 1–4:

1. **The prompt itself** in a fenced code block (easy to copy)
2. **Key design choices** — 3-5 bullets explaining the most important decisions and why (so the user learns, not just receives)
3. **Suggested first test** — a specific input to try with the prompt to verify it works
4. **Iteration hooks** — what to watch for in the output that might signal a need for refinement

Keep explanations concise. The prompt is the deliverable — the commentary supports it, not the other way around.
