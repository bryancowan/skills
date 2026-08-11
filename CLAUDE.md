# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A personal collection of Claude Code skills. Skills live in `skills/`. The `spec/` directory contains `agent-skills-spec.md`, which redirects to the Agent Skills specification at <https://agentskills.io/specification>.

## Skill Structure

Every skill is a folder containing a `SKILL.md` with YAML frontmatter and markdown instructions:

```text
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

- Skills go in `skills/<skill-name>/SKILL.md`. Current skills:
  - `description-and-tags/` — skill name `obsidian-reading-list-enrichment`; enriches Obsidian web-clipping notes with description, note summary, and tags in YAML frontmatter
  - `construction-near-me/` — researches new buildings and businesses proposed, permitted, under construction, or recently opened near a location; discovers each jurisdiction's permit/GIS/agenda sources and caches them as per-jurisdiction profiles in `references/jurisdictions/`
  - `good-documentation/` — writing and reviewing documentation
  - `obsidian-jd-organizer/` — maintains Johnny Decimal vault structure; audits, files notes, updates indexes, expands categories
  - `obsidian-wiki-compiler/` — compiles raw sources into interconnected Obsidian wikis with diagrams and visualizations
  - `podcast-transcript/` — converts a podcast SRT into speaker-labeled markdown (append to a note or standalone file); profile-driven speakers + STT-artifact correction
  - `prompt-creation/` — creating and refining prompts for LLMs and AI agents
  - `ship-and-watch/` — commits, pushes, opens a PR, then polls CI every 5 minutes, auto-fixing failures until green
  - `ship-and-watch-tick/` — one iteration of the ship-and-watch polling loop; invoked automatically by `ship-and-watch`, not called directly
- Use `template/SKILL.md` as a starting point
- If the SKILL.md body approaches 500 lines, split content into `references/` files and add clear pointers from SKILL.md
- For multi-domain skills, organize reference files by variant (e.g., `references/aws.md`, `references/gcp.md`) so only the relevant file is loaded

## `.claude-plugin/marketplace.json`

Defines the plugin bundles exposed by `/plugin marketplace add bryancowan/skills`. Note this file still lists plugins/skills (e.g. `document-skills`, `skill-creator`, `frontend-design`, `claude-api`) that are **not** present in this repo's `skills/` directory — they were part of the original Anthropic example-skills fork and were removed from `skills/` when this repo was promoted to personal use, but the marketplace entries were not cleaned up. Don't assume a skill referenced there actually exists locally; check `skills/` first.

## Installing Skills in Claude Code

```bash
/plugin marketplace add bryancowan/skills
```
