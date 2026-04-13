# Bryan's Vault Layout

## Paths

| Item | Path |
|------|------|
| Vault root | `/Users/bryan/Obsidian/vault` |
| Master Index | `/Users/bryan/Obsidian/vault/00-09 System Management/00 System-management category/00.00 Master Index.md` |
| Attachments | `/Users/bryan/Obsidian/vault/00-09 System Management/00.05 Attachments` |
| Templates | `/Users/bryan/Obsidian/vault/00-09 System Management/00.03 Templates` |

## Change Log

Both `obsidian-jd-organizer` and `obsidian-wiki-compiler` write to a shared change log:

**Path:** `00-09 System Management/00.02 Task & Project Management (system-wide)/Vault Change Log.md`

Append an entry after every vault modification. Format: `YYYY-MM-DD — Short description`. Reverse chronological order.

## JD Areas (active)

| Area | Title | Status |
|------|-------|--------|
| 00-09 | System Management | Built |
| 10-19 | Personal Life Administration | Partially built (some categories planned) |
| 20-29 | Work & Professional Projects | Built |
| 30-39 | Knowledge Management & Reading | Built |
| 40-49 | Financial & Legal | Reserved (folder exists, no categories) |
| 50-59 | Health & Wellness | Reserved (folder exists, no categories) |
| 60-99 | Reserved for future expansion | Not created |

## Special Folders (outside JD structure)

These folders exist in the vault root but are not part of the JD hierarchy. They serve specific Obsidian plugin functions:

| Folder | Purpose |
|--------|---------|
| `Copilot` | Files for the Copilot plugin |
| `Daily Note` | Daily notes for task tracking and quick notes |
| `Reading List` | Web articles clipped via Obsidian Web Clipper |
| `Watch List` | YouTube content clipped via Obsidian Web Clipper |

These are common sources of "loose files" that should be triaged into JD locations.

## Special Files (vault root)

| File | Purpose |
|------|---------|
| `Task Week.md` | Kanban-style weekly task planner |
| `Quick Note.md` | Temp file for copy-pasting between apps |

## Master Index Format

The Master Index uses YAML frontmatter followed by a plain-text indented tree:

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
      00.04 Links for the system
```

**Indentation**: Areas = 0 spaces, Categories = 3 spaces, IDs = 6 spaces.

**Unbuilt categories** use: `      [Planned - not yet built]` (6-space indent).

## Metadata Conventions

Notes use this frontmatter template:

```yaml
---
tags:
  - camelCaseTag
created: yyyy-mm-dd
location: obsidian
keywords: comma, separated, keywords
related:
  - "[[jd.id Title]]"
---
```

- Tags: `#camelCase` format
- Dates: `yyyy-mm-dd`
- Related notes: wikilink format `[[AC.ID Title]]`
- Attachments: all saved to the central `00.05 Attachments` folder
