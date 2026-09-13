# Johnny Decimal Rules Reference

Canonical source: <https://johnnydecimal.com/documentation/> (append `.md` to any URL for the LLM-readable version; `llms.txt` is the table of contents).

## Structure (AC.ID)

Every item has a unique ID in the format `AC.ID`:

| Element | Format | Example | Limits |
|---------|--------|---------|--------|
| Area | `X0-X9` | `10-19` | Up to 10 per system |
| Category | `XY` | `15` | Up to 10 per area (x1-x9) |
| ID | `XY.ZZ` | `15.23` | Up to 100 per category (.00-.99) |

## Core Rules

1. **Up to 10 areas** (00-09 through 90-99). Leave room for growth — start sparse.
2. **Up to 10 categories per area** (x1 through x9). Categories begin at `x1`, not `x0`. The `x0` slot is the area management category.
3. **IDs are the deepest level.** No nested folders except approved subfolder patterns within an ID (see below). Never store files in area or category folders — these are structural only.
4. **JDex is primary.** Create the JDex entry before creating a folder or note. The index prevents duplicate IDs across storage locations.
5. **Never re-use an ID.** Once assigned, an ID is permanent — even if the item is archived. The JDex is what prevents accidental re-use; search it before assigning a new number.

## AC.ID Variable Notation

JD docs use variable substitution to talk about IDs generically:

- `AC.ID` — any ID
- `1C.ID` — any ID in area 10-19
- `11.ID` — any ID in category 11
- `AC.11` — `.11` in any category
- `SYS.AC.ID` — fully-qualified ID across multiple systems (see Multiple Systems)

## Standard Zeros

Reserved IDs for system management at every level.

### Per-Category (most specific — prefer these)

```
.00 JDex for category XX
.01 Inbox for category XX
.02 Task & project management for category XX
.03 Templates for category XX
.04 Links for category XX
.05-.08 Reserved for future expansion (do not use)
.09 Archive for category XX
```

### Per-Area (area management category = x0)

```
X0 Management of area X0-X9
  X0.00 JDex for area X0-X9
  X0.01 Inbox for area X0-X9
  X0.02 Task & project management for area X0-X9
  X0.03 Templates for area X0-X9
  X0.04 Links for area X0-X9
  X0.09 Archive for area X0-X9
```

### System Level (area 00-09)

```
00-09 System Management
  00 System Management Category
    00.00 Master Index / JDex for the system
    00.01 Inbox for the system
    00.03 Templates for the system
    00.04 Links for the system
    00.09 Archive for the system
```

## Decision Chart for Filing

When filing an item, prefer the most specific zero:

1. Know exactly which ID it belongs to? → File it there.
2. Know the category but not the ID? → `XX.01 Inbox for category XX`
3. Know the area but not the category? → `X0.01 Inbox for area X0-X9`
4. No idea where it goes? → `00.01 Inbox for the system`

## Index File Format

Plain text, indented, in numerical order:

```text
10-19 Area Title
   11 Category Title
      11.01 First ID title
      11.02 Second ID title
   12 Another Category
20-29 Next Area
```

- Areas: no indentation
- Categories: 3-space indent
- IDs: 6-space indent
- Metadata on IDs: `- Key: value` on the line below
- Must be in numerical order
- Parents may be childless; orphans (category without area, ID without category) are not allowed

## Subfolder Patterns

A single level of subfolders inside an ID is allowed when it helps. Pick one approach per ID and stick to it. Never use ad-hoc, randomly-named, or un-numbered subfolders.

### 1. Date-based (preferred for time-stamped material)

| Granularity | Format | Example |
|-------------|--------|---------|
| Day | `yyyy-mm-dd` | `2026-08-08 claim docs` |
| Month | `yyyy-mm` | `2026-08 statements` |
| Quarter | `yyyy-qN` | `2026-q3 reports` (note calendar vs tax quarter) |
| Week | `yyyy-ww` | `2026-w32 timesheet` |

### 2. Alphabetical (for naturally-sorted material, e.g., suppliers, people)

- Consistent capitalization/spacing across all subfolders
- Optional `[NN]` suffix for creation-order tracking (does not affect alphabetical sort): `Acme [01]`, `Beta Corp [02]`

### 3. Numbered intervals (fallback template)

Subfolders numbered `10`, `20`, `30`, …, `90`. Up to nine slots; gaps allow inserts later (drop a `15` between `10` and `20`).

## Headers

Headers break a category into labelled sections so the eye can jump to the right cluster of IDs at a glance. Use when IDs in a category naturally clump.

- **Format**: an ID ending in `0` (e.g., `12.30`), prefixed with `■` then an emoji, then the section title. Example: `12.30 ■ 🏠 Housing`
- **Containers only.** Never store files or notes against a header.
- **When to add**: during a category audit, if a cluster of 4+ IDs share an obvious theme, propose a header above them.
- **Filesystem caveat**: if the `■` or emoji breaks on a filesystem, drop them and keep the `.X0` numbering.

## Extend-the-End (`+`)

Used when one ID needs repeated variations (three chickens, multiple instances of the same event) and a full category split would be overkill.

- **Format**: `AC.ID+ unique title`. Example: `11.63+ Belinda`, `11.63+ Greta`, `11.63+ Mabel`.
- Each `+` entry gets its own JDex line.
- Works with multi-system notation: `SYS.AC.ID+`.
- **Incompatible** with expand-an-area (an expanded area no longer uses standard `AC.ID`).
- **Smell test**: if you reach for `+` often within one category, the category is probably mis-scoped — consider a redesign or area expansion.

## Expand-an-Area

When a domain genuinely needs more than 3 levels or more than 100 IDs per category, expand the area into a custom structure rather than forcing creep.

- The expanded area abandons the standard `AC.ID` shape and can grow arbitrarily.
- Custom IDs are allowed (or no IDs at all if the hierarchy is self-describing).
- JDex still applies — items in expanded areas can still receive JD-style IDs for cross-referencing.
- Cannot combine with extend-the-end.

**Skill behaviour**: when an audit finds a category over capacity (>100 IDs, repeated `+` usage, or 3+ levels of needed nesting), suggest expanding the area as an alternative to letting the category sprawl.

## Multiple Systems (`SYS.AC.ID`)

For users running more than one JD system (home, work, business), each system gets a 3-character prefix matching `[A-Z][0-9][0-9]`.

- **Format**: `SYS.AC.ID`. Example: `H01.11.11` and `W01.11.11` for the same `11.11` in home vs work systems.
- Combined JDex entries must use the full `SYS.AC.ID` to avoid ambiguity.
- Prefer filling an existing system before creating another. JD's guidance: "Avoid creating multiple systems where possible."
- **Skill behaviour**: detect `SYS.` prefixes in imported notes and preserve them; never strip silently.

## File Naming

Choose a convention and apply it ruthlessly across the vault.

- **Dates**: ISO 8601 only — `yyyy-mm-dd`. Shorten to `yyyy-mm` or `yyyy` if the day isn't meaningful.
- **Versions**: pick one placement and stick to it — `v1 Name.doc` (prefix) or `Name v1.doc` (suffix). Don't mix.
- **Separators / casing / spacing**: be uniform. Inconsistency breaks sorting and looks sloppy.
- **Optional AC.ID in filename**: include when the file leaves the vault (email attachments, files that show up in "recently opened" lists). Example: `12.11 lease 2026-08-08.pdf`.
- **Renaming a category is free.** The number is the identifier; titles are descriptions. Rename titles freely when meaning shifts.

## Audit Checklist

1. **Category creep**: any area > 10 categories → merge or archive
2. **Overlapping purposes**: categories that could serve the same function → name the overlap, propose merge
3. **ID duplication**: same number used twice → JDex workflow was skipped
4. **Orphaned files**: items on disk not in JDex → add or archive
5. **Missing folders**: items in JDex but not on disk → create or remove from index
6. **Non-standard subfolders**: subfolders inside an ID that don't follow date / alphabetical / numbered-interval patterns
7. **Headers missing `■` / emoji**: `.X0` IDs that look like headers but lack the prefix (or vice versa)
8. **Category over capacity**: > 100 IDs, frequent `+` use, or growing nested needs → propose expand-an-area
9. **Unrecognised `SYS.` prefix**: imported items carrying multi-system notation that the vault hasn't accounted for

## Design Principles

- **Functional groupings** over topic groupings. "What work happens here?" beats "What is this about?"
- The test for a good category: "When I sit down to do this type of work, I come here."
- When uncertain whether two categories should be separate, merge them.
- Prefer extending an existing system over creating a new one.
- **Renaming is free; renumbering is not.** Numbers are identity; titles are labels.
