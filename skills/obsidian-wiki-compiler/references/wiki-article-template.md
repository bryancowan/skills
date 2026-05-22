# Wiki Article Template

Use this structure for every compiled wiki article.

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
  - "[[XX.09 Archive for category XX/YY <wiki> sources/YYYY-MM-DD sources/source-file.md]]"
---
# Article Title

## Summary

2-3 sentences. What is this concept? Why does it matter? This section should stand
alone — a reader should get the key takeaway without reading further.

## Details

The main content, organized by subheadings. Synthesize across sources rather than
summarizing each source separately.

### Subheading A

Content with citations: "According to [[XX.09 Archive for category XX/YY <wiki> sources/YYYY-MM-DD sources/source-1.md]], the approach involves..."

### Subheading B

Content with cross-references: "This relates to [[other-wiki-article]], which covers..."

> [!info] Key Finding
> Highlight the most important discovery or takeaway from this section.

> [!warning] Caveat
> Note any limitations, disagreements between sources, or areas of uncertainty.

## Sources

- [[XX.09 Archive for category XX/YY <wiki> sources/YYYY-MM-DD sources/source-1.md]] — Provided foundational data on X
- [[XX.09 Archive for category XX/YY <wiki> sources/YYYY-MM-DD sources/source-2.md]] — Offered alternative perspective on Y
- [[XX.09 Archive for category XX/YY <wiki> sources/YYYY-MM-DD sources/source-3.pdf]] — Quantitative data for charts

## Related

- [[related-article-1]] — Covers the prerequisite concept
- [[related-article-2]] — Explores a downstream application
```

## Naming Convention

- Filename: lowercase, hyphenated, descriptive
- Examples: `transformer-architecture.md`, `rag-vs-fine-tuning.md`, `training-data-quality.md`
- Avoid generic names like `overview.md` or `notes.md`
- The filename should be meaningful even without the parent folder context

## Frontmatter Rules

- `tags`: Always include `wiki` plus topic-relevant tags in `#camelCase`
- `created`: Date of article creation in `yyyy-mm-dd`
- `keywords`: Comma-separated search terms
- `related`: Wikilinks to other wiki articles (not raw sources)
- `sources`: Wikilinks to raw source files. Path: `XX.09 Archive for category XX/<YY> <wiki-short-name> sources/<sunday-date> sources/<file>` where `<YY>` is the wiki's two-digit ID suffix and `<sunday-date>` is the Sunday of the week the source was ingested

## Callout Usage

| Callout | Use for |
|---------|---------|
| `> [!info]` | Key facts, important findings |
| `> [!tip]` | Practical advice, actionable insights |
| `> [!warning]` | Limitations, caveats, contradictions |
| `> [!quote]` | Notable quotes from sources |
| `> [!example]` | Concrete examples or case studies |
| `> [!question]` | Open questions for future research |
