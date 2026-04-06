# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A personal fork of [anthropics/skills](https://github.com/anthropics/skills). Upstream Anthropic skills live in `skills/` (most are Apache 2.0; docx/pdf/pptx/xlsx are source-available). Custom skills added in this fork live in `skills/bryan/`.

## Skill Structure

Every skill is a folder containing a `SKILL.md` with YAML frontmatter and markdown instructions:

```
my-skill/
├── SKILL.md           (required — frontmatter + instructions)
├── evals/evals.json   (test cases, optional)
├── scripts/           (reusable scripts bundled with the skill)
├── references/        (docs loaded into context on demand)
└── assets/            (templates, fonts, static files)
```

### SKILL.md frontmatter fields

- `name` — unique identifier (lowercase, hyphens)
- `description` — **primary triggering mechanism**: what the skill does AND when to use it; be specific and slightly "pushy" to avoid undertriggering
- `compatibility` — required tools/deps (rarely needed)

### Three-level loading system

1. **Metadata** (name + description) — always in context
2. **SKILL.md body** — loaded when skill triggers; keep under ~500 lines
3. **Bundled resources** — loaded on demand; scripts can execute without loading

## Adding or Editing Skills

- Custom skills go in `skills/bryan/<skill-name>/SKILL.md`
- Use `template/SKILL.md` as a starting point
- If the SKILL.md body approaches 500 lines, split content into `references/` files and add clear pointers from SKILL.md
- For multi-domain skills, organize reference files by variant (e.g., `references/aws.md`, `references/gcp.md`) so only the relevant file is loaded

## Skill Creator Eval Workflow

The `skills/skill-creator/` skill has an eval loop for testing and improving skills:

- Test cases stored in `evals/evals.json` within the skill directory
- Eval runs go into `<skill-name>-workspace/iteration-N/` as a sibling to the skill directory
- Aggregation script: `python -m scripts.aggregate_benchmark <workspace>/iteration-N --skill-name <name>` (run from `skills/skill-creator/`)
- Eval viewer: `python skills/skill-creator/eval-viewer/generate_review.py <workspace>/iteration-N --skill-name "name" --benchmark <workspace>/iteration-N/benchmark.json`
- Description optimizer: `python -m scripts.run_loop --eval-set <path> --skill-path <path> --model <model-id> --max-iterations 5` (run from `skills/skill-creator/`)
- Package a skill: `python -m scripts.package_skill <path/to/skill-folder>` (produces a `.skill` file)

## Installing Skills in Claude Code

```
/plugin marketplace add anthropics/skills
/plugin install document-skills@anthropic-agent-skills
/plugin install example-skills@anthropic-agent-skills
```
