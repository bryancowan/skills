# Cline Prompting Guide

## Overview
Cline (formerly Claude Dev) is an agentic VS Code extension that autonomously edits files, runs terminal commands, and uses browser tools. It can be powered by Claude, GPT, or other LLMs — prompting style should match the underlying model.

## Key principles
- Always specify the underlying model — prompt style differs (Claude: explicit + XML; GPT: compact + structured).
- Always specify which files to edit and which to leave untouched.
- Add explicit approval gates: "Ask before running terminal commands" or "Ask before installing dependencies".
- Cline shows a task list before executing — review and adjust scope before approving.
- For multi-step tasks, break into sequential prompts with checkpoints.

## Template

```
Underlying model: [Claude 4.x / GPT-5 / etc.]

Starting State:
[current file structure, open files, repo state]

Target State:
[what should exist when Cline is done]

File Scope:
Allowed: [paths/globs]
Forbidden: [paths/globs — config, lockfiles, .env, infrastructure]

Allowed Actions:
- Edit files within scope
- Use browser/search tools for reference docs
[etc.]

Forbidden Actions:
- Do NOT run terminal commands without asking
- Do NOT install dependencies without asking
- Do NOT push to git
- Do NOT modify files outside scope

Stop Conditions:
Pause and ask before:
- Deleting any file
- Adding any dependency
- Modifying schema, migrations, or CI config
- Two valid implementation paths exist

Checkpoints:
After each major step output: ✅ [what was completed]
```

## Anti-patterns
- No file scope → Cline edits anywhere it thinks helps
- No approval gates → unwanted dependencies installed silently
- No stop conditions → runaway loops on errors
- Task list approved without review → scope creep
