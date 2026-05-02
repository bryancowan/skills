# Skills

A personal collection of Claude Code skills. Skills are folders of instructions, scripts, and resources that Claude loads dynamically to improve performance on specialized tasks.

For background on the skills system, see:

- [What are skills?](https://support.claude.com/en/articles/12512176-what-are-skills)
- [Using skills in Claude](https://support.claude.com/en/articles/12512180-using-skills-in-claude)
- [How to create custom skills](https://support.claude.com/en/articles/12512198-creating-custom-skills)

---

## Skills in This Repo

- **[description-and-tags](./skills/description-and-tags)** — Enriches Obsidian web-clipping notes with description, summary, and tags for YAML frontmatter. Skill name: `obsidian-reading-list-enrichment`.
- **[good-documentation](./skills/good-documentation)** — Writing and reviewing documentation: user guides, READMEs, tutorials, onboarding materials.
- **[obsidian-jd-organizer](./skills/obsidian-jd-organizer)** — Maintains a Johnny Decimal organizational system in Obsidian: audits structure, files loose notes, updates indexes, expands categories.
- **[obsidian-wiki-compiler](./skills/obsidian-wiki-compiler)** — Transforms raw source documents into a structured, interconnected Obsidian wiki with concept maps and visualizations.
- **[prompt-creation](./skills/prompt-creation)** — Creating, reviewing, and refining prompts for LLMs and AI agents. Covers system prompts, multi-agent pipelines, image/video/audio prompts, and adapting across models.
- **[ship-and-watch](./skills/ship-and-watch)** — Commit, push, open a PR, then start a polling loop that checks CI every 5 minutes and auto-fixes failures until the PR is green.
- **[ship-and-watch-tick](./skills/ship-and-watch-tick)** — One iteration of the ship-and-watch loop: polls PR CI status, applies a minimal fix if any check is failing, and stops the loop when everything is green. Invoked automatically by ship-and-watch.

---

## Skill Structure

Every skill is a folder with a `SKILL.md` file:

```text
my-skill/
├── SKILL.md           (required — frontmatter + instructions)
├── evals/evals.json   (test cases, optional)
├── scripts/           (reusable scripts bundled with the skill)
├── references/        (docs loaded into context on demand)
└── assets/            (templates, fonts, static files)
```

### Three-level loading

1. **Metadata** (name + description) — always in context
2. **SKILL.md body** — loaded when skill triggers
3. **Bundled resources** — loaded on demand; scripts can execute without loading

---

## Creating a Skill

Use [template/SKILL.md](./template/SKILL.md) as a starting point:

```markdown
---
name: my-skill-name
description: A clear description of what this skill does and when to use it
---

# My Skill Name

[Instructions Claude will follow when this skill is active]

## Examples
- Example usage 1
- Example usage 2

## Guidelines
- Guideline 1
- Guideline 2
```

Required frontmatter:

- `name` — unique identifier (lowercase, hyphens)
- `description` — primary triggering mechanism; be specific about when to use it

---

## Installing in Claude Code

To install skills from this repo as a Claude Code plugin:

```bash
/plugin marketplace add bryancowan/skills
```
