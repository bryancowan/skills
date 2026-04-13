# Johnny Decimal Rules Reference

## Structure (AC.ID)

Every item has a unique ID in the format `AC.ID`:

| Element | Format | Example | Limits |
|---------|--------|---------|--------|
| Area | `X0-X9` | `10-19` | Up to 10 per system |
| Category | `XY` | `15` | Up to 10 per area (x1-x9) |
| ID | `XY.ZZ` | `15.23` | Up to 99 per category (.00-.99) |

## Core Rules

1. **Up to 10 areas** (00-09 through 90-99). Leave room for growth — start sparse.
2. **Up to 10 categories per area** (x1 through x9). Categories begin at `x1`, not `x0`. The `x0` slot is the area management category.
3. **IDs are the deepest level.** No nested folders except date-stamped subfolders within an ID (e.g., `2024-08-08 NYC trip/`).
4. **JDex is primary.** Create the JDex entry before creating a folder or note. The index prevents duplicate IDs across storage locations.

## Standard Zeros

Reserved IDs for system management at every level:

### Per-Category (most specific — prefer these)

```
.00 JDex for category XX
.01 Inbox for category XX
.02 Task & project management for category XX
.03 Templates for category XX
.04 Links for category XX
.05-.07 Reserved
.08 Someday for category XX
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

## Audit Checklist

1. **Category creep**: Any area exceeding 10 categories → merge or archive
2. **Overlapping purposes**: Categories that could serve the same function → name the overlap, propose merge
3. **ID duplication**: Same number used twice → JDex workflow was skipped
4. **Orphaned files**: Items on disk not in JDex → add or archive
5. **Missing folders**: Items in JDex but not on disk → create or remove from index

## Design Principles

- **Functional groupings** over topic groupings. "What work happens here?" beats "What is this about?"
- The test for a good category: "When I sit down to do this type of work, I come here."
- When uncertain whether two categories should be separate, merge them.
- Prefer extending an existing system over creating a new one.
