---
name: obsidian-reading-list-enrichment
description: Use when working with Obsidian Reading List notes clipped from the web that need description, note summary, tags, or a better headline filename. Triggers when user mentions Obsidian notes, clipped articles, web clippings, or wants to enrich, update, or rename reading list items.
---

# Obsidian Reading List Enrichment

## Overview

Enrich Obsidian web-clipping notes by generating description, note summary, tags, and a descriptive headline filename using the prompts below.

## Strict Scope

**Frontmatter:** modify only `description`, `note`, `tags`, `status`. Any other field — `title`, `source`, `author`, `published`, `created`, `related` — must not be changed, even if empty or null.

**Filename:** rename the file with a rewritten headline. The `title` field in frontmatter is never changed.

| Field | Action |
|-------|--------|
| `description` | Generate if null, empty, or value exactly matches `title` |
| `note` | Generate if null or empty |
| `tags` | Generate if list has **4 or fewer tags** |
| `status` | **Always change to `Read`** — this is not conditional |
| `title` | **Never modify.** Original headline stays in frontmatter. |
| filename | Rename file with rewritten headline, preserving timestamp suffix |

## Red Flags — Stop and Reconsider

| Thought | What to do instead |
|---------|--------------------|
| "author is empty, I'll fill it in from the article" | Leave it empty. author is out of scope. |
| "published is empty, I found the date in the body" | Leave it empty. published is out of scope. |
| "status is already set to Unread, I'll leave it" | Change it to Read. status always changes. |
| "description looks okay to me" | Check: does it exactly equal the title? If yes, regenerate it. |
| "there are already some tags, I'll skip tag generation" | Count them. 4 or fewer = generate more. Existing tags are kept; only append new ones. |
| "I'll update the title field to the rewritten headline" | Never. `title` stays as-is. Only the **filename** changes. |
| "the headline is fine, I'll skip the rename" | Still apply the prompt. Only skip rename if the prompt returns the exact same text. |

## Workflow

1. Read the note file
2. Parse the YAML frontmatter (between `---` delimiters)
3. For each field that needs generation, apply the prompt below using the full article body as input
4. For `note`: treat text wrapped in `==double equals==` as highlighted passages — weight them heavily as the reader's key takeaways
5. Write all generated content back to the frontmatter (see **Output Formatting** below)
6. Write `status: Read`
7. Generate a rewritten headline using the **Headline Rewrite Prompt** below
8. If the rewritten headline differs from the original `title`, **rename the file** (see **Filename** under Output Formatting)

## Prompts

### Description Prompt

> Summarize the piece in a single declarative sentence, written in first person as the author stating your central claim. Be specific to this piece—not a generic description of its topic. Output the sentence only, under 30 words.

### Note/Summary Prompt

> ## Role
> You are a reading assistant. Your job is to extract and express the core ideas from an article, saving the reader time while preserving accuracy.
>
> ## Context
> Highlighted text is marked with double equals signs: ==like this==. The user highlighted these passages to signal what they consider most important. Treat highlighted passages — and the one or two sentences immediately surrounding each one — as your primary evidence for the article's thesis and key supporting points.
>
> Include content from outside highlighted sections only when it is essential for the summary to be accurate. If no highlights are present, treat the full article as your source.
>
> ## Instructions
> 1. Read the entire article before drawing any conclusions.
> 2. Identify the central argument or thesis and the key supporting points, using highlights as your primary guide.
> 3. Write a summary of 1–2 paragraphs that:
>    - Stands on its own without requiring the original article
>    - Maintains a neutral, factual tone throughout
>    - Flows as plain prose — no bullets, headers, or Markdown formatting
>    - Reads as if written directly from the article, with no mention of highlights or your process
>
> ## Output
> Plain prose. 1–2 paragraphs. Nothing else.

### Tags Prompt

> ## Role
> You are a tagging assistant for an Obsidian personal knowledge base. Your job is to generate concise, reusable tags that capture what an article is *actually about*—not just its surface topic. Look for the story behind the story: incentives, platform dynamics, power structures, and long-term economic or social stakes.
>
> ## Tag Categories
> Generate between 5 and 8 tags per note. Every note must have exactly one Primary Topic tag and one Content Type tag. Source and Perspective tags are optional and conditional.
>
> ### 1. Primary Topic Tags
> The core domain(s) of the content. Be specific enough to be meaningful, general enough to recur.
> Examples: `#elections`, `#supremeCourt`, `#climate`, `#ai`, `#platforms`, `#privacy`, `#copyrightLaw`, `#misinformation`, `#antitrust`, `#generativeAi`
>
> Prefer specific over generic: use `#copyrightLaw` not `#law`, use `#generativeAi` not `#tech`.
>
> ### 2. Content Type Tags
> The format of the writing. Pick exactly one.
> Options: `#news`, `#opinion`, `#analysis`, `#investigation`, `#longform`, `#howTo`, `#reference`, `#tutorial`, `#recipe`, `#travelNote`
>
> ### 3. Source Tags (conditional)
> Use only for major, recognizable publications with a distinct editorial identity.
> Examples: `#nyt`, `#wapo`, `#atlantic`, `#economist`, `#propublica`, `#theVerge`, `#wsj`, `#techdirt`
>
> Omit entirely for personal blogs, local outlets, or any source that is not clearly a major publication.
>
> ### 4. Perspective Tags (conditional)
> Use only if an ideological or analytical lens is explicit and central—not merely implied.
> Examples: `#progressive`, `#conservative`, `#libertarian`, `#techOptimist`, `#techSkeptic`
>
> Omit entirely for neutral, reported, or ambiguous pieces.
>
> ## Formatting Rules
> - Prefix every tag with `#`
> - Use lowerCamelCase exclusively: `#supremeCourt`, not `#SupremeCourt` or `#supreme_court`
> - Flat hierarchy only — no nested tags, no `/`
> - No spaces, punctuation, or emojis within a tag
>
> ## Output
> Tags on a single line, space-separated. No explanation, no preamble.

### Headline Rewrite Prompt

> You are an editorial headline rewriter. Your job is to rewrite article headlines so they are informative, specific, and scannable — modeled on the editorial standards of Techmeme's headline editors.
>
> Apply these five rewriting principles, in order of priority:
>
> 1. **Clickbait withholding** — If the headline deliberately omits key details to force a click, pack those details back in.
> 2. **Buried lede** — If the most newsworthy part of the story isn't in the headline, pull it forward. Read the full article to find the real news.
> 3. **Corporate euphemism** — If a company is obscuring bad news behind vague language, rewrite to be explicit about what happened.
> 4. **Too generic** — If the headline omits specifics about companies, people, technologies, or numbers, add those specifics.
> 5. **Fit for scanning** — The headline should function as an abstract. Favor active verbs, specific names, numbers, and concrete details.
>
> **When NOT to rewrite:** If the original headline is already specific, informative, and scannable, return it unchanged.
>
> **Constraints:**
> - Output ONLY the rewritten headline — no explanation, no commentary, no quotation marks around it.
> - Aim for under 120 characters when possible, but prioritize clarity over brevity.
> - Avoid these characters (they break filenames): `: / \ * ? " < > |`
> - Use a dash or comma instead of a colon. Use single quotes instead of double quotes if quoting is necessary.
> - Use sentence case, not title case.

## Output Formatting — CRITICAL

Incorrect formatting is the most common failure. Follow these rules exactly.

### Tags

The tags prompt outputs `#tag1 #tag2 #tag3` format. You MUST strip the `#` prefix before writing to YAML.

**Preserve existing tags.** When the note already has tags (e.g. `clippings`, `stratechery`), keep them all and append only the new ones. Do not remove or replace existing tags.

When passing the article to the tags prompt, note which tags already exist so the prompt avoids duplicating them. The goal is to reach 5–8 total tags.

**Keep `clippings` as the first tag**, then existing tags, then new generated tags.

**Correct:**
```yaml
tags:
  - clippings
  - analysis
  - ai
  - platforms
```

**Wrong — do NOT do this:**
```yaml
tags:
  - clippings
  - "#analysis"
  - "#ai"
```

### Note

The note MUST use `|-` block scalar syntax. Do NOT use a quoted string with `\n` escape sequences.

**Correct:**
```yaml
note: |-
  First paragraph of plain prose here.

  Second paragraph here.
```

**Wrong — do NOT do this:**
```yaml
note: "First paragraph.\n\nSecond paragraph."
```

### Description

Single unquoted string (or quoted if it contains special YAML characters):
```yaml
description: The central claim stated as a first-person declarative sentence.
```

### Status

Always set after enrichment:
```yaml
status: Read
```

### Filename

After frontmatter edits, rename the file with the rewritten headline.

**Filename format:** `{{title}} - {{timestamp}}.md`
- Timestamp pattern: ` - YYYY-MM-DDTHHMMSS-ZZZZ` (e.g. ` - 2026-04-08T213438-0500`)
- Some files have no timestamp — just `{{title}}.md`

**To rename:**
1. Extract the timestamp suffix by matching ` - \d{4}-\d{2}-\d{2}T\d{6}-\d{4}` at the end of the filename (before `.md`)
2. Replace the title portion with the rewritten headline
3. Construct: `{{rewritten_headline}} - {{timestamp}}.md` (or `{{rewritten_headline}}.md` if no timestamp)
4. Rename the file using `mv` (same directory)

**If the rewritten headline is identical to the original title, skip the rename.**

**Example:**
```
Before: "Can AI be a 'child of God' - 2026-04-08T213438-0500.md"
After:  "Sources - Anthropic met with Christian leaders in March to seek input on Claude's moral development - 2026-04-08T213438-0500.md"
```

## Complete Example

```yaml
title: "Some Article Title"
source: https://example.com/article
author: Jane Smith
published: 2026-01-15
created: 2026-04-05
description: I argue that slowing down deliberate practice produces better long-term results than optimizing for speed.
tags:
  - clippings
  - analysis
  - personalDevelopment
  - learningScience
  - opinion
status: Read
note: |-
  First paragraph summary in plain prose, drawing on the article's highlights and central argument.

  Second paragraph continuing the summary, covering key supporting points or implications.
related:
```
