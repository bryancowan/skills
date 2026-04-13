---
name: obsidian-jd-organizer
description: Use this skill for any Obsidian vault file organization task. This includes: moving or filing notes into folders, triaging items out of inboxes or reading/watch lists, figuring out where a note belongs, assigning the next ID number in a numbered category, creating or expanding folder structures, cleaning up a messy vault, or auditing what's out of place. Especially relevant when the user's vault follows Johnny Decimal (JD) conventions with numbered areas, categories, and AC.ID patterns — but trigger for any "organize my vault" or "sort these notes" or "where should this file go" request. Do NOT use for: summarizing content, building wikis, creating templates, plugin development, dataview queries, or vault backups.
---

# Obsidian JD Organizer

Maintain a Johnny Decimal organizational system within an Obsidian vault. This skill handles auditing structure, filing items, reorganizing folders, updating indexes, and expanding the system.

Before doing any vault operations, invoke the **obsidian-cli** skill for reading/creating/searching notes and the **obsidian-markdown** skill for proper Obsidian formatting (frontmatter, wikilinks, callouts).

## Decision Framework

These principles guide every organizational decision:

- **Clarity over completeness.** Five well-chosen areas beat nine mediocre ones.
- **Broad over granular.** Fewer, broader categories reduce decision fatigue. `Money` beats `Investments`, `Savings`, and `Budget` as separate categories.
- **The JDex is the source of truth** — not the filesystem. The Master Index IS the system.
- **Friction at the category level is a feature.** Creating a new category should require thought; creating a new ID should be effortless.

## Vault Configuration

Read `references/vault-layout.md` for the vault path, special folders, and Master Index location. Read `references/jd-rules.md` for the complete JD structural rules including the standard zeros pattern and AC.ID notation.

## Workflows

### 1. Audit

Compare the vault filesystem against the Master Index to find drift.

**Steps:**

1. Read the Master Index at `00-09 System Management/00 System-management category/00.00 Master Index.md`
2. List the vault's actual folder/file structure using `ls` or `find`
3. Compare and report:

| Check | What to look for |
|-------|-----------------|
| Missing folders | IDs in Master Index but no corresponding folder on disk |
| Orphaned folders | Folders on disk not listed in Master Index |
| Loose files | Files sitting outside JD structure (in vault root, Reading List, Watch List, Daily Note) that should be filed |
| ID collisions | Same AC.ID number used for different items |
| Category creep | Any area exceeding 10 categories |
| Overlapping categories | Categories with similar purposes that could merge |
| Empty standard zeros | Categories missing their standard zero IDs (.00-.04, .09) |

4. Output a markdown table with columns: `Issue`, `Location`, `Recommended Action`
5. Ask the user which actions to take before making changes

### 2. File Items

Move loose files from inbox areas, Reading List, Watch List, or Daily Note into proper JD locations.

**Steps:**

1. Read the file to understand its content and topic
2. Read the Master Index to find candidate JD locations
3. Suggest the best AC.ID placement with reasoning — prefer the most specific existing category
4. If no suitable ID exists, propose creating one (with the next available number in the right category)
5. On user approval:
   - Move the file to the target JD folder
   - Search for backlinks using `obsidian search` to find notes that reference this file
   - Update any wikilinks in other notes that pointed to the old location
   - Update the relevant JDex note (category-level `.00` file)
   - Update the Master Index if a new ID was created

### 3. Reorganize

Analyze a given directory and restructure it according to JD conventions.

**Steps:**

1. List all files in the target directory
2. Read the Master Index to understand the current JD structure
3. For each file, determine the best JD category and ID
4. Present a reorganization plan as a table: `File`, `Current Location`, `Proposed Location`, `Reason`
5. On user approval, execute moves one at a time:
   - Move the file
   - Update backlinks (search with obsidian-cli first)
   - Update the category JDex
   - Update the Master Index

### 4. Update Indexes

Regenerate the Master Index and per-category JDex notes to reflect the current filesystem state.

**Master Index format** — preserve this exact structure (plain-text indented tree with YAML frontmatter):

```markdown
---
tags:
  - system
  - index
  - jdex
  - masterIndex
created: 2025-12-27
location: obsidian
keywords: index, master, system, jdex, johnny decimal, structure
related:
  - "[[00.00 Master Index]]"
---
00-09 System Management
   00 System Management Category
      00.00 Master Index
      00.03 Templates for the system
      ...

10-19 Personal Life & Administration
   10 Management of area 10-19
      10.00 JDex for area 10-19
      ...
   11 Personal Identity & Legal
      [Planned - not yet built]
```

**Rules for index updates:**
- Areas: `XX-X9 Title` (no indentation)
- Categories: `   XX Title` (3-space indent)
- IDs: `      XX.YY Title` (6-space indent)
- Unbuilt categories: `      [Planned - not yet built]` (6-space indent)
- Entries must appear in numerical order
- Never remove entries — mark unused ones for archival instead
- Preserve the existing YAML frontmatter exactly

**Per-category JDex notes** (e.g., `12.00 JDex for category 12`):
- List all IDs in that category
- Include a brief description of each ID's purpose
- Use wikilinks to link to each ID's note

### 5. Expand System

Build out categories marked `[Planned - not yet built]` in the Master Index.

**Steps:**

1. Read the Master Index to find planned categories
2. Ask the user which category to build (or build all if requested)
3. For each category, create:
   - The category folder: `XX Category Name/` inside the area folder
   - Standard zero notes with proper naming:
     - `XX.00 JDex for category XX.md`
     - `XX.01 Inbox for category XX.md`
     - `XX.02 Task & project management for category XX.md`
     - `XX.03 Templates for category XX.md`
     - `XX.04 Links for category XX.md`
     - `XX.09 Archive for category XX.md`
   - Each note gets Obsidian frontmatter (tags, created date, location, keywords, related)
4. Suggest starter IDs based on the category name and area context
5. Update the Master Index to replace `[Planned - not yet built]` with the new IDs

## JD Naming Conventions

| Level | Format | Example |
|-------|--------|---------|
| Area folder | `XX-X9 Title` | `10-19 Personal Life Administration` |
| Category folder | `XX Title` | `12 Home & Living Space` |
| ID note/folder | `XX.YY Title` | `12.11 Property & Lease Documents` |
| Standard zero | `XX.0N Description for category/area XX` | `12.00 JDex for category 12` |

- Category numbers start at `x1` (e.g., `11`, `12`), not `x0` — the `x0` slot is the area management category
- IDs start at `.11` for user content (`.00`-`.09` are standard zeros)
- Only exception to flat structure: date-stamped subfolders within an ID (e.g., `2024-08-08 claim docs/`)
- Tags use `#camelCase` format
- Dates use `yyyy-mm-dd` format

## Change Log

After every vault modification (file moves, index updates, category expansion, reorganization), append an entry to the change log at:

`00-09 System Management/00.02 Task & Project Management (system-wide)/Vault Change Log.md`

Create this file if it doesn't exist. Format:

```markdown
---
tags:
  - system
  - changeLog
created: 2026-04-12
location: obsidian
keywords: changelog, audit, vault changes
---
# Vault Change Log

2026-04-12 — Filed 3 Reading List items into 31.xx (Technology)
2026-04-12 — Expanded category 13 Health & Wellness with standard zeros
2026-04-11 — Audit: found 5 orphaned files, 2 missing index entries
```

Each entry: `YYYY-MM-DD — Short description of what changed`

Keep entries in reverse chronological order (newest first). This log is shared with the `obsidian-wiki-compiler` skill — both skills write to the same file.

## Safety

- Always show a plan and get user approval before moving files or modifying indexes
- Search for backlinks before any file move — broken wikilinks are the biggest risk
- Never delete files — move to the relevant `.09 Archive` instead
- Create the JDex entry before creating a folder (JDex is primary, filesystem is secondary)
- Always append to the change log after making vault modifications
