# Antigravity Prompting Guide

## Overview
Antigravity is Google's agent-first IDE, powered by Gemini 3 Pro. It is task-based — describe outcomes, not steps — and supports Artifact-first workflows where the agent produces a task list or implementation plan you review before execution. Browser automation is built in for verification.

## Key principles
- Task-based prompting: describe the outcome, not the steps.
- Prompt for an Artifact (task list, plan, design doc) before execution. Review it, then approve.
- Use the built-in browser agent for verification: "After building, verify the UI at 375px and 1440px."
- Specify autonomy level explicitly: "Ask before running destructive terminal commands."
- Scope to one deliverable per session — do not mix unrelated tasks.

## Template

```
Outcome:
[the deliverable, in one sentence]

Artifact First:
Before executing, produce a [task list / implementation plan / architecture sketch] for review.
Wait for approval before making any code changes.

Constraints:
- Stack: [language, framework, versions]
- Scope: [paths/files/components]
- Do not touch: [list]

Verification:
After building, use the browser agent to verify:
- [URL or local path]
- [viewports: 375px, 768px, 1440px]
- [specific behaviors to confirm]

Autonomy:
- Ask before: running destructive commands, installing dependencies, modifying schema/CI
- Auto-approved: editing files within scope, running tests, reading docs

Done When:
[binary condition]
```

## Anti-patterns
- Step-by-step instructions → Antigravity is designed for outcomes; over-specifying steps reduces quality
- Skipping the Artifact review → loses the main safety lever
- No viewport list for UI work → agent verifies one viewport and misses regressions
- Mixing two unrelated tasks in one session → context bleed, worse output on both
