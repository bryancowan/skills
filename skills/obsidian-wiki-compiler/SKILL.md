---
name: obsidian-wiki-compiler
description: Compile raw source documents into a structured markdown wiki with visualizations inside an Obsidian vault. Use when the user wants to build a knowledge base from raw files, create a wiki from articles/papers/notes, compile research into organized markdown, generate mermaid diagrams or charts from their notes, run Q&A over a wiki, enhance or lint an existing wiki, or organize raw data into a structured knowledge base. Also trigger when the user mentions "knowledge base", "compile wiki", "research synthesis", "raw files to wiki", "index my sources", or wants visualizations of their notes. If they say "summarize these articles" or "make sense of these files" — this skill applies.
---

# Obsidian Wiki Compiler

Transform raw source documents into a structured, interconnected markdown wiki with visualizations — all viewable natively in Obsidian. Inspired by Andrej Karpathy's LLM knowledge base workflow: raw data is collected, compiled by an LLM into `.md` wiki files, then operated on for Q&A and incremental enhancement.

The LLM writes and maintains the wiki. The user rarely edits it directly.

Before doing any vault operations, invoke the **obsidian-cli** skill for reading/creating/searching notes, the **obsidian-markdown** skill for proper Obsidian formatting, and the **obsidian-jd-organizer** skill when filing the wiki into JD locations.

## Workflows

### 1. Ingest

Index source documents into a date-stamped sources directory within a target location.

**Steps:**

1. Identify the target directory — either user-specified or determined via `obsidian-jd-organizer` for JD placement
2. Create a `YYYY-MM-DD sources/` subdirectory in the target location, using today's date (e.g., `2026-04-18 sources/`). This date-stamped format is the only subfolder form permitted by JD rules.
3. For each source file:
   - **Web URLs**: Use the `defuddle` skill to extract clean markdown, save as `.md` in the sources folder
   - **Local files** (PDFs, text, markdown, images): Copy to the sources folder
   - **Clipped articles** (from Reading List / Watch List): Move to the sources folder, preserving frontmatter
4. Create `YYYY-MM-DD sources/_manifest.md` listing all ingested sources with metadata:

```markdown
---
tags:
  - wiki
  - manifest
created: yyyy-mm-dd
---
# Source Manifest

| # | File | Type | Date Added | Summary |
|---|------|------|------------|---------|
| 1 | [[source-article.md]] | Article | 2026-04-12 | Brief description |
```

### 2. Compile Wiki

Analyze all raw sources and generate interconnected wiki articles.

**Pipeline:**

1. **Read all sources** in `context/` — extract full text content
2. **Extract concepts** — identify key entities, claims, themes, relationships, and data points across all sources
3. **Cluster by topic** — group related concepts into coherent article topics. Aim for 5-15 articles depending on source volume. Each article should cover a distinct concept, not just summarize one source.
4. **Generate wiki articles** — one `.md` file per topic, following the article template in `references/wiki-article-template.md`
5. **Generate `XX.YY Wiki Index.md`** — the master index for this wiki, using the JD ID of the target folder (e.g., `31.13 Wiki Index.md`). List all articles with one-line summaries and cross-references.

**Article structure** (each wiki article):

```markdown
---
tags:
  - wiki
  - topicTag
created: yyyy-mm-dd
location: obsidian
keywords: relevant, search, terms
related:
  - "[[other-article]]"
sources:
  - "[[YYYY-MM-DD sources/source-file.md]]"
---
# Article Title

## Summary

2-3 sentence overview of this concept. What is it, why does it matter.

## Details

The main content. Use subheadings as needed. Include:
- Key findings and claims (cite sources with wikilinks)
- Relationships to other concepts (cross-link with [[wikilinks]])
- Data points, statistics, or evidence

> [!info] Key Finding
> Use callouts for important discoveries or takeaways.

## Sources

- [[YYYY-MM-DD sources/source-1.md]] — what this source contributed
- [[YYYY-MM-DD sources/source-2.md]] — what this source contributed

## Related

- [[other-wiki-article]] — how it connects
```

**Index structure** (`XX.YY Wiki Index.md`, where XX.YY is the JD ID of the target folder):

```markdown
---
tags:
  - wiki
  - index
  - jdex
created: yyyy-mm-dd
location: obsidian
keywords: topic, wiki, index
related:
  - "[[XX.00 JDex for Category XX]]"
---
# Wiki: [Topic Name]

> Compiled from N sources on yyyy-mm-dd.

## Articles

| Article | Summary |
|---------|---------|
| [[article-name]] | One-line description |

## Concept Map

A mermaid diagram showing relationships between articles:

` ``mermaid
graph LR
  A[Article 1] --> B[Article 2]
  A --> C[Article 3]
  B --> C
` ``

## Sources

N source documents. See [[YYYY-MM-DD sources/_manifest]] for full list.

## Compilation Log

- yyyy-mm-dd: Initial compilation from N sources
- yyyy-mm-dd: Added N articles after Q&A session
```

### 3. Visualize

Generate visualizations that render natively in Obsidian.

**Mermaid diagrams** (inline in markdown, no plugin needed):

Use mermaid code blocks for:
- Concept maps showing relationships between wiki articles
- Flowcharts for processes described in the wiki
- Timeline diagrams for chronological data
- Mind maps for topic hierarchies

Read `references/visualization-formats.md` for mermaid syntax patterns.

```markdown
` ``mermaid
graph TD
  A[Main Concept] --> B[Sub-concept 1]
  A --> C[Sub-concept 2]
  B --> D[Detail]
` ``
```

**Matplotlib charts** (for data-heavy wikis):

When the wiki contains quantitative data (statistics, trends, comparisons), generate charts:

1. Run `scripts/generate_chart.py` with JSON data on stdin
2. The script outputs a PNG to the specified path (use the vault's attachments folder)
3. Embed in the wiki article: `![[chart-name.png]]`

```bash
echo '{"type": "bar", "title": "Comparison", "labels": ["A","B","C"], "values": [10,20,30]}' | python generate_chart.py --output "/path/to/attachments/chart-name.png"
```

### 4. Q&A Enhance

Research questions against the compiled wiki to deepen it over time.

**Manual mode** (default):

1. User asks a question about the wiki topic
2. Read `XX.YY Wiki Index.md` to understand scope and find relevant articles
3. Navigate to relevant articles for detail
4. Research the answer — actively use web search to find current, authoritative information. Searching for new sources is encouraged and makes the wiki stronger. Only fall back on existing wiki content or general knowledge when web search doesn't yield results.
5. Write the answer as either:
   - A new wiki article (if the answer covers a new concept) — update `_index.md`
   - An appendix to an existing article (if it extends a known concept)
6. Update cross-references and the concept map in `_index.md`
7. Update `_index.md` compilation log

**Source attribution on new content** — every new article or addition must clearly state where the information came from. Add a `> [!info] Source` callout at the top of each new article:

```markdown
> [!info] Source
> This article was researched via web search on yyyy-mm-dd, drawing from [source names/URLs].
```

Or if synthesized from existing wiki content:

```markdown
> [!info] Source
> Synthesized from existing wiki articles: [[article-1]], [[article-2]].
```

Or if from model knowledge:

```markdown
> [!info] Source
> Based on general domain knowledge. No specific sources consulted — consider verifying key claims.
```

This transparency helps the user understand the provenance and reliability of each piece of content.

**Loop mode** (autonomous enhancement):

When the user requests continuous enhancement (e.g., "keep improving this wiki"):

1. Read the full wiki via `XX.YY Wiki Index.md`
2. Identify gaps: concepts mentioned but not explained, claims without evidence, topics that could be explored deeper
3. Generate 3-5 suggested research questions
4. Present to user for approval
5. Research answers — use web search to find fresh, authoritative sources. File new sources into the existing date-stamped sources folder and update `_manifest.md`. If ingesting a new batch on a different date, create a new `YYYY-MM-DD sources/` folder for that batch.
6. Write answers as new articles or appendices, with source attribution callouts
7. Update the concept map and compilation log
8. Schedule next check using `/loop` — suggest questions again after a delay

The goal is that each Q&A session "adds up" — the wiki grows more comprehensive and interconnected over time.

### 5. Health Check

Lint the wiki for quality and consistency.

**Checks to run:**

| Check | What to look for |
|-------|-----------------|
| Broken wikilinks | Links to articles that don't exist |
| Missing backlinks | Articles referenced in `_index.md` but not linked from other articles |
| Stale summaries | `_index.md` summaries that don't match article content |
| Orphaned articles | Articles not listed in `_index.md` |
| Source coverage | Raw sources not cited by any article |
| Factual conflicts | Contradictory claims across articles |
| Empty sections | Articles with placeholder or stub sections |
| Missing visualizations | Topics with data but no charts/diagrams |

**Output:** A health report as a markdown table with `Issue`, `Location`, `Severity`, `Suggested Fix`.

After presenting the report, offer to auto-fix what's safe (broken links, missing index entries) and flag what needs human judgment (factual conflicts, reorganization).

## Wiki Organization within JD

When placing a wiki compilation in the vault's JD structure:

```
XX.YY Topic Name/
  YYYY-MM-DD sources/      # Original source files (date-stamped — required by JD)
    _manifest.md           # Source inventory
    source-1.md            # Raw sources
    source-2.pdf
  XX.YY Wiki Index.md      # Wiki master index with concept map
  concept-one.md           # Compiled wiki articles
  concept-two.md
```

**JD subfolder rules:** Only date-stamped subfolders are permitted within a JD ID folder. Always name the sources folder `YYYY-MM-DD sources/` using the ingest date. Never use generic names like `context/`, `sources/`, or `visualizations/` — these are JD violations.

Use the `obsidian-jd-organizer` skill to determine the correct AC.ID for placement.

For chart images, always save to the vault's central attachments folder (`00.05 Attachments`) and embed with `![[image.png]]`. Do not create a local `visualizations/` subfolder.

## Change Log

After every vault modification (wiki compilation, new articles, visualization generation, health check fixes), append an entry to the shared change log at:

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

2026-04-12 — Wiki compiled: LLM Knowledge Bases (27.14), 8 articles from 12 sources
2026-04-12 — Q&A: added 2 articles to LLM Knowledge Bases wiki
2026-04-11 — Health check: fixed 3 broken wikilinks in 31.12 wiki
```

Each entry: `YYYY-MM-DD — Short description of what changed`

Keep entries in reverse chronological order (newest first). This log is shared with the `obsidian-jd-organizer` skill — both skills write to the same file.

## Quality Standards

- Every wiki article must cite its sources via wikilinks to `context/` files
- Every article must cross-link to at least one related article
- The `_index.md` concept map must reflect actual cross-references
- Use Obsidian callouts (`> [!info]`, `> [!warning]`, `> [!tip]`) for key findings
- Frontmatter on every file: tags, created date, keywords, related notes
- Article filenames: lowercase, hyphenated, descriptive (e.g., `transformer-architecture.md`)
