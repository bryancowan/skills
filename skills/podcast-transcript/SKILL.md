---
name: podcast-transcript
description: Convert a podcast SRT transcript into clean, speaker-labeled markdown — either appended to an existing note or written as a standalone file with metadata. Use when given a .srt file path, or when asked to "add transcript", "process the SRT", or "convert podcast transcript".
---

# Podcast Transcript → Markdown

Convert a speech-to-text SRT transcript into a clean, speaker-labeled
`## Transcript`. Two output modes:

- **append** — add the transcript to an existing markdown / Obsidian note.
- **new-file** — write a standalone markdown file with YAML frontmatter (title,
  podcast, speakers, source, topics) plus a short summary, then the transcript.

## Scope / limitations

- **SRT input only.** `.vtt` / WebVTT is out of scope.
- Speaker attribution on **unlabeled** audio is inference, not ground truth —
  best-effort, verify the result (Step 6).
- Rolling / overlapping captions (e.g. YouTube auto-captions) can repeat whole
  phrases; the light cleanup dedupes consecutive *words*, not repeated phrases.

## Inputs

Collect these before starting.

| Input | Description |
|-------|-------------|
| `SRT_FILE` | Absolute path to the `.srt` transcript file (required) |
| `OUTPUT_MODE` | `append` or `new-file` (see resolution below) |
| `NOTE_FILE` | append mode: absolute path to the target `.md` note |
| `OUTPUT_FILE` | new-file mode: absolute path to write the new `.md` |
| `PROFILE` | Optional podcast profile slug (see Podcast profiles) |
| `GAP_MS` | Silence gap threshold for paragraph breaks (default: **1500ms**) |

**Resolving `OUTPUT_MODE`:** if the user gave an existing note to add to → `append`.
If they gave only an SRT (no target note) → `new-file`. If ambiguous, ask.

## Podcast profiles

A profile (`references/podcasts/<slug>.md`) pre-fills **speakers** and **known STT
artifacts** for a recurring podcast. `references/podcasts/sharp-china.md` is the
worked example.

- **Known podcast?** Read its profile before Step 2 and use its speakers + artifact
  list.
- **New podcast?** Proceed without a profile (Steps 2–3 derive speakers and
  artifacts from the transcript). If this podcast will recur, offer to save a new
  profile by copying the sharp-china format.
- **Compounding:** when you confirm a new recurring artifact for a known podcast,
  append it to that profile's artifact table so future runs catch it automatically.

---

## Workflow

### Step 1 — Parse the SRT

Run `parse_srt.py` from this skill's directory to produce numbered, cleaned
paragraphs:

```bash
python scripts/parse_srt.py "$SRT_FILE" --gap $GAP_MS
```

The parser handles Windows (CRLF) and BOM-prefixed files, splits paragraphs on
silence gaps, strips fillers (`um`/`uh`/`ah`), and collapses stutters. Note the
**total paragraph count** (stderr). Typical podcast: 20–80 paragraphs per hour.

> **Paragraphs are reading chunks, not speaker turns.** In fast conversation the
> silence between cues rarely lines up with who's talking, so a single paragraph
> often contains many back-and-forth turns (expect occasional 1000+ word blobs).
> Lowering `--gap` does **not** reliably recover turns — segment by *content* in
> Steps 3–4 instead. For very long transcripts, work through the paragraphs in
> sections rather than one pass, so you don't lump a whole blob under one speaker.

If the script is unavailable, the logic is ~40 lines: parse each SRT block into
`(index, start_ms, end_ms, text)`, start a new paragraph whenever the gap to the
next entry exceeds `GAP_MS`, then apply light cleanup. Reimplement rather than
maintaining a second copy here.

---

### Step 2 — Scan for STT artifacts

Goal: a single **fix list** of mis-transcribed terms, applied consistently in
Step 4. STT reliably mangles proper nouns (people, places, brands) and
industry-specific or foreign terms.

1. **Surface candidates across the whole episode** (not just the ends):

   ```bash
   python scripts/parse_srt.py "$SRT_FILE" --proper-nouns --min-count 2
   ```

   This lists capitalized terms with counts. A name that recurs in a suspicious
   spelling is a strong artifact signal.

2. **Read the full output** (or at least skim every paragraph) and flag garbled
   phrases, sentence fragments from crosstalk, and phonetically-mangled names.

3. **Apply the profile's known artifacts** if a profile was loaded.

4. **Verify uncertain terms.** For proper nouns / specialized terms you're not
   sure how to spell, verify the correct form — use WebSearch when available
   (recommended). If offline, use best judgment and flag low-confidence fixes.

5. Record confirmed recurring fixes back into the podcast profile (see above).

---

### Step 3 — Speaker attribution

SRT from STT usually has **no** speaker labels, so attribution is inference. Work
top-to-bottom; most turns flow naturally once the first few are anchored.

**First, check for existing labels.** Some diarized SRTs already contain inline
speaker tags (`Speaker 1:`, `>> NAME:`, `JOHN:`). If present, use them as ground
truth — map each tag to a real name and skip inference.

**Two-person podcasts** (the common case) alternate. Attribution signals, priority
order:

1. **Direct address** — "Bill," at sentence start → the *other* person is
   speaking. Use profile names if available.
2. **Role signals** — long analytical passage with specific facts/citations or an
   "I mean / I think / You know" opener → analyst/guest. A question, topic intro,
   or read-aloud quote → host.
3. **Short affirmations** — a lone "Right." / "Yeah." mid-transcript usually
   belongs to whoever is *reacting* to the longer prior turn.
4. **Conversational rhythm** — if ambiguous, ask: does this continue the previous
   speaker's thought, or shift register?

**Three or more speakers:** read a ~500-word sample from the middle, identify each
distinct voice's patterns (vocabulary, role, who they address), note them, then
attribute conservatively. When genuinely unsure, prefer a generic label
(`Speaker 2`) over guessing a specific name.

**Unknown podcast (no profile):** before attributing, read a ~500-word sample,
identify each voice's characteristic patterns, and write them down to anchor the
pass.

---

### Step 4 — Write the labeled transcript

For each paragraph:

1. Prepend `**Name:**` based on Step 3.
2. Apply **light cleanup only** — no rephrasing, no added content:
   - Fix the STT artifacts from the Step 2 fix list (apply every fix everywhere).
   - Fix clear false starts: "It's co it's complicated" → "It's complicated".
   - Fix garbled fragments: "a l has influence" → "has influence".
3. Preserve the speaker's actual words and register otherwise.

**Paragraph splitting (expect to do this a lot):** a parser paragraph is a
reading chunk, not a turn — long ones routinely contain many turns. Split each
paragraph into separate labeled turns wherever the speaker changes, using the
Step 3 signals (direct address, role/register shift, question→answer, short
affirmations). Don't assume one paragraph equals one speaker.

**Short turns:** keep short turns (single sentence, affirmation) as their own
labeled paragraph — don't merge into an adjacent turn.

**`[inaudible]` / `[crosstalk]`:** if the STT produced these, leave them — they're
honest markers. Don't silently delete them.

---

### Step 5 — Output

Build the labeled paragraphs as `(speaker, text)` pairs, then write per mode.

**append mode** — guard against duplicates, then append:

```python
NOTE_FILE = "/path/to/note.md"
with open(NOTE_FILE, encoding="utf-8") as f:
    existing = f.read()
if "## Transcript" in existing:
    raise SystemExit("Note already has a ## Transcript section — aborting to avoid a duplicate.")

body = "\n\n".join(f"**{spk}:** {txt}" for spk, txt in labeled_paragraphs)
sep = "" if existing.endswith("\n\n") else ("\n" if existing.endswith("\n") else "\n\n")
with open(NOTE_FILE, "a", encoding="utf-8") as f:
    f.write(sep + "## Transcript\n\n" + body + "\n")
```

**new-file mode** — write frontmatter + summary + transcript. Refuse to clobber:

```python
import os, datetime
OUTPUT_FILE = "/path/to/new-note.md"
if os.path.exists(OUTPUT_FILE):
    raise SystemExit(f"{OUTPUT_FILE} already exists — choose a different path or confirm overwrite.")

speakers = sorted({spk for spk, _ in labeled_paragraphs})
fm = [
    "---",
    f"title: {title}",                       # episode title or a derived headline
    f"podcast: {podcast}",                    # from profile if known; else omit
    "speakers: [" + ", ".join(speakers) + "]",
    f"source: {SRT_FILE}",
    f"date: {datetime.date.today().isoformat()}",
    "topics: [" + ", ".join(topics) + "]",   # 2–5 topics you extract from the transcript
    "---",
]
body = "\n\n".join(f"**{spk}:** {txt}" for spk, txt in labeled_paragraphs)
doc = "\n".join(fm) + f"\n\n# {title}\n\n> Summary: {summary}\n\n## Transcript\n\n" + body + "\n"
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(doc)
```

Derive `title`, `topics`, and `summary` from the full transcript content. **Skip
any frontmatter field you can't determine — don't invent values.**

---

### Step 6 — Verify

1. Read the **tail of the output** (append: end of `NOTE_FILE`; new-file:
   `OUTPUT_FILE`) and confirm `## Transcript` appears cleanly after the existing
   content / frontmatter.
2. Spot-check 2–3 speaker labels from the middle against the raw Step 1 paragraphs.
3. Confirm the transcript ends with the last speaker's sign-off (not truncated).
4. new-file mode: confirm the YAML frontmatter parses (no stray colons/brackets)
   and only contains fields you could actually determine.

---

## Tips

- **`.md` vs SRT:** if both exist, use the SRT — its timestamps drive paragraph
  grouping. A flat `.md` export has no structure.
- **Gap tuning:** paragraphs too long/fragmented? Try `--gap 2000` (fewer breaks)
  or `--gap 800` (more breaks).
- **Crosstalk:** when people talk over each other the STT output is a garbled mix.
  Apply a light cleanup rather than reconstructing what was said.
