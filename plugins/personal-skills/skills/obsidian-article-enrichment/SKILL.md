---
name: obsidian-article-enrichment
description: Enrich articles clipped into Bryan's Obsidian vault. Writes a summary into the `note` field, adds tags, replaces a missing or generic `description` with one in the author's voice, and decides from Bryan's past renames whether to retitle the file with a Techmeme-style headline. Use whenever the user asks to enrich, summarize, tag, describe, process, finish, or retitle a clipped article, web clipping, newsletter, or reading-list note in Obsidian, including "do the usual on this note", "run my prompts on this article", or "enrich everything in the inbox".
---

# Obsidian Article Enrichment

This skill runs four of Bryan's prompts on a clipped article and writes the results back into the note. It does only what the note needs: fields that are already good are left alone, and the file is renamed only when Bryan's history says he would rename it.

The scripts handle every deterministic part: deciding what needs work, writing YAML, renaming files. Your job is to write the text and make the judgment calls. Run the commands exactly as shown. `SKILL_DIR` means the folder that holds this file.

## Scope

| Field | Action |
|---|---|
| `note` | Write a summary if it is empty. Never overwrite an existing one. |
| `description` | Write one if the script flags it (empty, same as title, truncated publisher blurb, marketing voice, site boilerplate). Otherwise keep it. |
| `tags` | Add tags if the note has 4 or fewer. Keep every existing tag. |
| filename | Rename only per the rename rules below. The timestamp suffix stays. |
| everything else | Do not touch: `title`, `status`, `source`, `author`, `published`, `created`, `related`, and the body. |

## Workflow (one note at a time)

### 1. Find the note

- The user gave a path: use it.
- The user said "this note" or "the current note": run `obsidian file` and take the `path` line. The vault root comes from `obsidian vault info=path`.
- The user gave part of a title: run `obsidian search query="<words>" limit=5` and confirm with the user if more than one note matches.
- For a folder or batch ("everything in the inbox"), list the notes, then take them one at a time: finish steps 2–6 for a note before opening the next one. Don't read all the articles up front.

Work only on the note(s) the user named. Don't search the vault or open other notes for context; `analyze_note.py` already reads Bryan's history.

### 2. Analyze

```bash
python3 "SKILL_DIR/scripts/analyze_note.py" "<absolute path to note>"
```

If the note is outside the vault (a copy, a test file), add `--vault "<vault root>"` so the script can still read Bryan's history.

The script prints JSON. The parts you need:
- `fields.description.needs_work`, `fields.note.needs_work`, `fields.tags.needs_work`, each with a `reason`.
- `existing_tags` and `source_domain` (inputs for the tags prompt).
- `rename.lean` (`skip`, `keep`, `rename`, or `unclear`), plus `rename.history` and `rename.examples`.

If nothing needs work and `rename.lean` is `skip` or `keep`, report "already enriched" and move on.

### 3. Read the article

Read the note. The article is the body below the closing `---` of the frontmatter. Text wrapped in `==double equals==` is Bryan's highlighting.

### 4. Generate only what's flagged

Do each one as a separate step. For each, read the prompt file, then follow it with the article as input. Each prompt defines its own output format; produce exactly that, with no preamble.

| Field | Prompt file | Give the prompt |
|---|---|---|
| note | `SKILL_DIR/references/prompts/article-summarize.md` | the article body (highlights included) |
| description | `SKILL_DIR/references/prompts/description-as-author.md` | the title and the article body |
| tags | `SKILL_DIR/references/prompts/generate-tags.md` | the article body, the source URL, and `existing_tags` |

### 5. Write the frontmatter

Put the generated values in one JSON object. Include only the keys you generated:

```bash
python3 "SKILL_DIR/scripts/apply_frontmatter.py" "<note path>" --json '{"note": "Paragraph one.\n\nParagraph two.", "description": "One sentence.", "add_tags": ["analysis", "antitrust"]}'
```

- `add_tags` takes only the **new** tags. The script merges them with the existing ones, drops duplicates, keeps `clippings` first, and strips `#`.
- If the text contains single quotes that break shell quoting, write the JSON to a file in the temp folder (e.g. `/tmp/enrich.json`, never next to the note) and pass `--json-file <file>` instead. The script deletes that file after a successful write.
- The script prints a diff. If it prints `error:`, fix the input and run it again; don't edit the YAML by hand.

### 6. Decide on the rename

Use `rename.lean` from step 2:

| lean | action |
|---|---|
| `skip` | Already renamed. Stop here. |
| `keep` | Don't rename. |
| `rename` | Read `SKILL_DIR/references/prompts/rewrite-headline.md` and apply it to the title and article. If the headline comes back different, rename. If it comes back unchanged, keep. |
| `unclear` | Generate the headline as above, then apply the scan test in `SKILL_DIR/references/rename-judgment.md`: rename if the title clearly fails, keep if it clearly passes, otherwise **ask Bryan**. Show the old title, the new headline, and the history counts in one line. In batch runs, don't ask; list the proposal in the final report. |

To rename:

```bash
python3 "SKILL_DIR/scripts/rename_note.py" "<note path>" --headline "<new headline>"
```

The script cleans the headline for filenames (colon → ` -`, curly quotes → `'`, strips `?*<>|\/$`![]{}` and trailing periods), keeps the timestamp, and renames through the Obsidian CLI so links in other notes follow the rename. If Obsidian isn't running, it renames on disk and lists the notes that still link to the old name; pass that list on to Bryan. Add `--dry-run` to preview.

Bryan's headlines are usually 100–135 characters. A long one is fine now and then, but not every time. The script refuses headlines over 180 characters; when that happens, cut the least essential clause and run it again. Pass `--long-ok` only if every remaining detail is essential.

### 7. Report

For each note, give one short block: which fields were written, which were skipped and why, and the rename outcome (renamed to X / kept, with the history basis / proposed, waiting for Bryan).

## Common failures

| Mistake | Instead |
|---|---|
| Writing YAML by hand | Always use `apply_frontmatter.py`; it handles `|-` block scalars, quoting, and tag merging. Never write a note file directly. |
| Browsing other vault notes for tag ideas or history | Don't. The tags prompt and `analyze_note.py` cover it. |
| Tags with `#` or in `SnakeCase`/`kebab` | The prompt outputs `#lowerCamelCase`. Pass the tags as-is; the script strips `#`. |
| Changing `status` to Read | Leave `status` alone. Bryan sets it himself. |
| Editing `title` to match the new headline | `title` keeps the original headline. Only the filename changes. |
| Renaming a weekly roundup or an interview | Follow `rename.lean`. Those formats are always kept. |
| Rewriting a good author subhead | Only replace the description when `fields.description.needs_work` is true. |
| Starting the summary with "This article…" | The summary prompt forbids preambles. Start with the first fact. |
| Renaming with `mv` | Use `rename_note.py` so backlinks are updated. |

## Maintenance

The four prompts in `references/prompts/` are copies of Bryan's Obsidian Copilot prompts in `~/Obsidian/vault/copilot/copilot-custom-prompts/`. After he edits those, run:

```bash
python3 "SKILL_DIR/scripts/check_prompt_drift.py"           # show differences
python3 "SKILL_DIR/scripts/check_prompt_drift.py" --update  # copy the vault versions in
```
