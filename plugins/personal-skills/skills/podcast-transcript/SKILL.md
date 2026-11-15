---
name: podcast-transcript
description: Convert a podcast SRT transcript (plain or already speaker-diarized) into clean, speaker-labeled markdown — either appended to an existing note or written as a standalone file with metadata. Use when given a .srt file path, or when asked to "add transcript", "process the SRT", or "convert podcast transcript".
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
- **Diarized** SRTs (cues already prefixed `Speaker 1:` / `NAME:`) are far better
  starting points but are **not ground truth either**: labels can be chunk-local
  (the same person is `Speaker 1` in the first half, `Speaker 4` in the second) and
  overlapped speech is chopped into alternating fragments. Step 1D handles both.
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
| `GAP_MS` | Silence gap threshold for paragraph breaks (default: **1500ms**; plain SRTs only) |
| `SPEAKER_MAP` | Diarized SRTs only: label → name, e.g. `1=Andrew 2=Bill 3=Bill 4=Andrew` (derived in Step 1D, not asked for) |

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
  Step 7 then pushes it to TypeWhisper so the next Parakeet pass starts closer to
  correct.

---

## Workflow

### Step 1 — Parse the SRT

**First, find out whether the SRT is already diarized** (cues start with
`Speaker 1:`, `>> NAME:`, etc.):

```bash
python3 -I scripts/parse_srt.py "$SRT_FILE" --diarized
```

- It prints a speaker table, or says *"does not look diarized"* (exit 2).
- **Diarized → follow Step 1D** (then continue at Step 2). Do **not** use the plain
  paragraph mode below: it runs the labels together.
- **Not diarized → follow Step 1P** (the original flow), then Steps 2–4.

#### Step 1P — Plain (unlabeled) SRT

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

#### Step 1D — Diarized SRT

Learned the hard way on a real two-host episode: the new diarizers get the *speaker
turns* mostly right, but the labels and the cue order need repair before you can
trust them.

**1. Inspect.** `--diarized` with no `--map` prints, per label, its cue count and
first/last cue, then **anchor cues** (intros, sign-offs, direct address).

```bash
python3 -I scripts/parse_srt.py "$SRT_FILE" --diarized
```

**2. Map every label to a name — per label group.** If the report says
`WARNING: N disjoint label groups — labels are CHUNK-LOCAL`, the diarizer ran in
chunks and *re-labeled the people in each one* (e.g. `1`=Andrew/`2`=Bill for cues
1–342 but `3`=Bill/`4`=Andrew from cue 343). A naive "1→host, 2→guest" mapping
silently swaps the speakers for the second half. For **each** group, find an anchor
that pins both names:

- an intro ("I'm Andrew Sharp… on the other line, Bill Bishop"),
- a sign-off exchange ("…great to see you, Bill" → reply "Thanks, Andrew"),
- direct address ("Bill, what do you think?" → the *other* label is speaking),
- the profile's role signals (host asks / introduces, analyst gives long answers).

Every label-looking prefix is kept as a label — a rare one is **never** silently
merged into the previous speaker. The inspect report lists rare labels separately
("RARE LABELS"), and an unmapped one is a hard error with the fix in the message:
a real speaker who just talks little (`--map bob=Bob`), or stray text that merely
looks like a label, e.g. a cue starting `NOTE:` (`--not-label note`). If one label is
reused for different people inside a single group, limit it with a
cue range: `--map 1=Andrew@1-300 --map 1=Bill@301-`. If entries overlap, the **last**
one wins (a broad default followed by a narrower override). Unmapped labels are a hard
error, never a guess. Some diarizers label only the first cue of each turn: unlabeled
cues then inherit the previous cue's speaker, and the run prints a `NOTE:` saying how
many did.

**3. Build.** Put the Step 2 artifact fixes in a `--fixes-file` (`old => new`, one per
line; applied to the raw text *before* cleanup so they can match across cue
boundaries). On a first pass start with an empty file (`touch fixes.txt`), read the
draft to find artifacts, then fill it in and re-run. The command is copy-pasteable as
written:

```bash
touch fixes.txt      # first pass: empty; add "old => new" lines after Step 2
python3 -I scripts/parse_srt.py "$SRT_FILE" --diarized \
  --map 1=Andrew --map 2=Bill --map 3=Bill --map 4=Andrew \
  --fixes-file fixes.txt --review > /tmp/transcript_body.md 2> /tmp/transcript_review.txt
```

Optional flags: `--not-label LABEL` (stray `NOTE:`-style text), `--first-speaker NAME`
(cues before the first label, for SRTs that label only some cues). Exit codes: `0` ok,
`2` bad input / unmapped label / not diarized, `3` coverage check failed.

stdout is the finished `**Name:** text` body (one turn per paragraph); stderr has the
coverage line, per-speaker turn counts, `REVIEW` flags and (with `--review`) every
regrouped cluster. Redirect stderr to a file for long episodes and read it. A
`REVIEW` flag means a turn *began mid-sentence* in the SRT — a continuation the
regrouping missed (on the reference episode: 1 flag in 676 cues, and it was real).

What the script does for you:

- **Regroups interleaved fragments.** Overlapped speech arrives as alternating cues
  mid-sentence (`"…and now"` / `"And that"` / `"here we are."`). It detects a
  *resumption* (a speaker's unfinished cue continued by a lowercase or one/two-word
  cue after a short interruption), regroups each speaker's fragments into whole
  sentences and orders them by where they finish. It never reorders one speaker's own
  words — only the interleaving between speakers changes (property-tested). Short reactions ("Yeah.") go after
  the sentence they interrupted. A cue that merely lacks final punctuation is **not**
  treated as interleaving.
- **Drops only hesitation cues** (`Um.`, `Uh,`) and never strips `ah`/`hmm` in the
  diarized build — those are reactions. `Uh-huh`, `uh-oh` and URL paths are left alone.
- **Cleans disfluencies**: `um/uh`, hyphen cut-offs (`it- it is` → `it is`,
  `show- shown` → `shown`), function-word repeats (`and and`), em-dash normalization.
- **Proves coverage after cleanup**: every cue ends up in exactly one final turn, the
  filler-only list, or the "emptied by cleanup" list (reported on stderr) — otherwise
  the run exits 3 instead of printing a transcript that silently lost text.

**4. Review — the part only you can do.** Fix every `REVIEW` flag, then skim the
`--review` clusters (BEFORE/AFTER) to confirm each regrouping reads right. The labels on interleaved fragments are almost always *correct* (in a
90-spot episode only 2 cues were truly mislabeled), but a genuinely mislabeled
fragment can't be detected mechanically — typically a one-person sentence split
across both labels, e.g. Bill quoting Lutnick: `Lutnick said, well, [A: I'll come back
to you] [B: I need] [A: with some options]`. Fix those by editing the body, using the
Step 3 signals. Read the first and last cue after each label-group boundary: that is
where a wrong map shows up.

Then continue at **Step 2** (artifact scan; `--proper-nouns` works on diarized files
and ignores the labels) and re-run the build with the finished `--fixes-file`.
Step 3 is already done; Step 4 reduces to resolving review flags and any
context-dependent fixes the literal list can't express (`she`→`Xi`).

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

**First, check for existing labels.** Some SRTs already contain inline speaker tags
(`Speaker 1:`, `>> NAME:`, `JOHN:`). If present, **use Step 1D** — treat the labels as
a strong prior, not ground truth: map each tag to a real name per label group using
anchors, watch for chunk-local label shifts, and review interleaved fragments. Fall
back to the inference signals below only where the labels are missing or look wrong.

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

*(Diarized SRTs: Step 1D already produced the body. Here you only resolve the
`REVIEW` flags, repair genuinely mislabeled fragments, and apply fixes the literal
`--fixes-file` can't express. The rest of this step is for plain SRTs.)*

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

**Diarized SRTs:** the body from Step 1D (`/tmp/transcript_body.md`) is already the
finished markdown — pass it straight to the append command below. The Python snippets
(fallback append, new-file) need `labeled_paragraphs`; build it from that file:

```python
import re
with open("/tmp/transcript_body.md", encoding="utf-8") as f:
    labeled_paragraphs = re.findall(r"^\*\*(.+?):\*\* (.*)$", f.read(), re.M)
```

**append mode** — guard against duplicates, then append. In an Obsidian vault, prefer
the `obsidian` CLI (the vault's `CLAUDE.md` asks for it; needs Obsidian open):

```bash
NOTEP="Reading List/My Note.md"          # path from the vault root
NOTE_ABS="/abs/vault/$NOTEP"
cp "$NOTE_ABS" /tmp/note_before_transcript.md        # for the byte-identical-prefix check below
rg -q "^## Transcript" "$NOTE_ABS"; check=$?     # 0 = found, 1 = not found, 2 = error (missing/unreadable)
if [ "$check" -eq 0 ]; then
  echo "ABORT: note already has a ## Transcript — not appending"
elif [ "$check" -eq 1 ]; then
  obsidian append path="$NOTEP" content="$(printf '## Transcript\n\n'; cat /tmp/transcript_body.md)" silent
else
  echo "ABORT: could not read $NOTE_ABS (rg exit $check) — not appending"
fi
```

- **Start the content at `## Transcript`, with no leading newline.** The CLI inserts
  its own newline when appending; a leading `\n` produced two blank lines before the
  heading (fixed by hand last time; `verify_transcript.py` now warns about it).
- ~80 KB passed fine through `content="$(cat …)"`. If the shell rejects the argument
  size, use the Python fallback below.
- Afterwards confirm the original text is a byte-identical prefix of the new file:
  `head -c "$(wc -c < /tmp/note_before_transcript.md)" "$NOTE_ABS" | cmp - /tmp/note_before_transcript.md`.

**append mode, fallback** (no Obsidian / CLI failed):

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
import datetime
import json
import os

OUTPUT_FILE = "/path/to/new-note.md"
if os.path.exists(OUTPUT_FILE):
    raise SystemExit(f"{OUTPUT_FILE} already exists — choose a different path or confirm overwrite.")

speakers = sorted({spk for spk, _ in labeled_paragraphs})
metadata = {
    "title": title,                           # episode title or a derived headline
    "podcast": podcast,                       # from profile if known; else None
    "speakers": speakers,
    "source": SRT_FILE,
    "date": datetime.date.today().isoformat(),
    "topics": topics,                         # 2–5 topics extracted from the transcript
}
fm = ["---"]
fm.extend(
    f"{key}: {json.dumps(value, ensure_ascii=False)}"
    for key, value in metadata.items()
    if value is not None
)
fm.append("---")
body = "\n\n".join(f"**{spk}:** {txt}" for spk, txt in labeled_paragraphs)
doc = "\n".join(fm) + f"\n\n# {title}\n\n> Summary: {summary}\n\n## Transcript\n\n" + body + "\n"
with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    f.write(doc)
```

JSON strings and arrays are valid YAML, so this standard-library encoding keeps
colons, hashes, commas, quotes, Unicode, and path punctuation literal. Never
interpolate unquoted metadata values into the frontmatter.

Derive `title`, `topics`, and `summary` from the full transcript content. **Skip
any frontmatter field you can't determine — don't invent values.**

---

### Step 6 — Verify

**Run the automated checks first** on the file you wrote to:

```bash
if [ "$OUTPUT_MODE" = "new-file" ]; then TARGET_MD="$OUTPUT_FILE"; else TARGET_MD="$NOTE_FILE"; fi
python3 -I scripts/verify_transcript.py "$TARGET_MD" --srt "$SRT_FILE" \
  --speakers Andrew Bill --forbid "Namibia" "Alice Wang"   # heard-as forms you fixed
```

It FAILs on a missing/duplicate `## Transcript`, raw `Speaker N` labels, unexpected
speaker names, forbidden artifact strings, a transcript that doesn't end where the SRT
ends (truncation — anchored: the transcript's *own* last words must match the SRT's,
a nearby echo only warns), a line inside the transcript that isn't `**Name:** text`,
frontmatter that doesn't close *before* the transcript, forbidden terms (matched
case-insensitively), and when well under ~60% of evenly spaced
5-word samples from the SRT appear in the transcript (a deleted passage in the
middle); it WARNs on 60–85% sample coverage, adjacent same-speaker turns, lopsided
speakers, an implausible word count vs the SRT, and a double blank line before the
heading. (It ignores `um`/`uh` and hesitation-only cues on the SRT side, since the
transcript has them removed.) Fix every FAIL; look at every WARN. Then the manual
checks:

1. Read the **tail of the output** (append: end of `NOTE_FILE`; new-file:
   `OUTPUT_FILE`) and confirm `## Transcript` appears cleanly after the existing
   content / frontmatter.
2. Spot-check 2–3 speaker labels from the middle against the raw Step 1 paragraphs.
   For diarized SRTs, spot-check **at each label-group boundary** (the cues either side
   of the shift) against the SRT — a wrong map shows up there first.
3. Confirm the transcript ends with the last speaker's sign-off (not truncated).
4. new-file mode: confirm the YAML frontmatter parses (no stray colons/brackets)
   and only contains fields you could actually determine.

---

### Step 7 — Sync fixes to TypeWhisper (optional)

**Only if the SRT came from TypeWhisper's watch folder with Parakeet** — a diarized
SRT from another model/tool doesn't benefit; skip this step (still update the profile
in Step 2, which is the source of truth) — push the profile fixes back into its
dictionary so the next episode starts cleaner:

```bash
python scripts/sync_typewhisper.py           # dry-run: shows what would change
python scripts/sync_typewhisper.py --apply   # write it
```

Run the dry-run first the first time and show the user the output. After that,
run `--apply` once at the end of any run that added rows to a profile.

If the dry-run lists **deferred terms** (all 256 Parakeet slots are used) and a corpus
is available (`--corpus <folder of finished transcripts>` or
`$PODCAST_TRANSCRIPT_CORPUS`), follow it with `--prune`: it swaps the weakest
*profile-derived* terms for stronger deferred ones, never touches the user's own words
or terms they gave custom per-term settings, and backs up, verifies and (on any doubt)
restores every write; it can't make the
write atomic, so don't edit the TypeWhisper dictionary while it runs. The user has
approved automating this. **The first `--prune --apply` on a machine needs their
go-ahead after you show the dry-run plan, and should be a one-term canary
(`--max-prune 1`)** that they check in TypeWhisper: it is the first write through the
replace-the-whole-list path and its effect on per-term settings has not been seen on a
live app. After that run it automatically. Never push past the cap to "make room" any other way.

Read `references/typewhisper-sync.md` before running `--prune` or explaining a score:
it covers the ranking formula, exactly what pruning removes and never removes, the safety
rails, how corrections are filtered, and the keep list (`references/typewhisper-keep.txt`).

---

## Tips

- **`.md` vs SRT:** if both exist, use the SRT — its timestamps drive paragraph
  grouping. A flat `.md` export has no structure.
- **Gap tuning:** paragraphs too long/fragmented? Try `--gap 2000` (fewer breaks)
  or `--gap 800` (more breaks).
- **Crosstalk:** when people talk over each other the STT output is a garbled mix.
  Apply a light cleanup rather than reconstructing what was said.
- **Genuinely ambiguous overlap:** when two people talk over each other the true word
  order is unknowable; the regrouping picks a defensible reading, it can't prove one.
  Don't spend time perfecting those few spots.
- **Tests** (in the skills repo, stdlib only): `python3 -m unittest tests/test_parse_srt.py
  tests/test_verify_transcript.py`. Run them after touching the scripts.
