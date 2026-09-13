# Devin / SWE-agent Prompting Guide

## Overview
Devin and SWE-agent are fully autonomous coding agents. They browse the web, run terminal commands, write and test code, and make decisions across long sessions. Without explicit constraints, they make architectural decisions you did not intend. Forbidden-actions lists are critical, not optional.

## Key principles
- State starting state and target state both very explicitly. Ambiguity becomes scope creep.
- The forbidden-actions list is mandatory. Devin defaults to "do whatever it takes."
- Scope the filesystem to specific directories. Lock infrastructure, CI, config.
- Add human-review triggers for any action that is hard to reverse.
- Add ✅ checkpoints after each step so you can intercept early.

## Template

```
Objective:
[single unambiguous sentence]

Starting State:
[current repo state, branch, what already exists]

Target State:
[exact files/behavior that must exist when done]

Allowed Actions:
- Edit files in [scoped paths]
- Run [specific test command]
- Install only packages already listed in [package.json / requirements.txt]
- Use web search for documentation lookups

Forbidden Actions:
- Do NOT modify files outside [scope]
- Do NOT touch infrastructure, CI, config, .env, secrets
- Do NOT run the dev server or deploy
- Do NOT push to git or open PRs without approval
- Do NOT delete files without showing a diff first
- Do NOT add new dependencies
- Do NOT make architectural decisions without human approval

Stop Conditions (ask for human review):
- A file would be permanently deleted
- A new external service or API would be integrated
- Two valid implementation paths exist and the choice affects architecture
- An error cannot be resolved in 2 attempts
- The task requires changes outside the stated scope
- A test must be deleted or skipped to make the build pass

Checkpoints:
After each major step output: ✅ [what was completed]
At the end output a full summary of every file changed.
```

## Anti-patterns
- "Build the feature" → no target state, no scope, runaway agent
- No forbidden list → Devin installs packages, edits CI, decides architecture
- No stop conditions → 2-attempt loops become 20-attempt loops
- No checkpoints → silent agent until it claims success or fails entirely
