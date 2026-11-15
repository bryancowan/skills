# Syncing profile fixes to TypeWhisper (`scripts/sync_typewhisper.py`)

Reference for SKILL.md Step 7. The script reads the "Known STT artifacts" tables in
`references/podcasts/*.md` and pushes them into TypeWhisper's dictionary through its local
HTTP API (Settings > Advanced > API Server).

```bash
python scripts/sync_typewhisper.py                                    # dry-run
python scripts/sync_typewhisper.py --apply                            # add terms + corrections
python scripts/sync_typewhisper.py --corpus ~/vault --prune           # dry-run: weak terms to swap out
python scripts/sync_typewhisper.py --corpus ~/vault --prune --apply   # swap them
```

- **Terms** (correct spellings) are what actually improve the Parakeet pass:
  vocabulary boosting uses them during transcription. Parakeet boosts at most
  256 terms and silently drops the rest, so the script fills only the free slots,
  best-ranked first, and lists what it deferred with each term's score. Never
  push past the cap to "make room": free a slot with `--prune` instead.
- **Pruning** (`--prune`, the user has approved automating it): when the slots are full,
  swap the weakest *profile-derived* terms for stronger deferred ones. It needs
  `--corpus` with at least 10 finished transcripts, because episode counts are what
  justify removing a term. A deferred term must score at least 2× the term it
  replaces and beat it by 2, at most 25 terms go per run (`--max-prune`), and ties
  go to whichever term is said less often in the corpus. **Never removed:** terms with
  no profile evidence (the user's own words and other dictation: they show up under
  "Left alone") and anything in `references/typewhisper-keep.txt`; add a term there if
  it matters more than its transcript counts suggest. TypeWhisper's API has no
  delete, only "replace the whole list", so the script re-reads the dictionary right
  before writing and refuses if it changed, saves the full previous list to
  `~/.podcast-transcript/backups/`, verifies the result and restores it on any
  mismatch. **The first `--prune --apply` on a machine:** show the user the dry-run
  plan and get a go-ahead (it is the first write through that path); after that, run it
  automatically after the normal sync. Without `--apply` it is a read-only report.
- **Ranking:** score = (logged mis-hearings + a small bonus if the profile's title
  or Speakers section names the term) × (1 + number of finished episodes that use
  it). The episode factor needs `--corpus <folder>`: a folder of finished
  transcripts (markdown files with a `## Transcript` section, such as the Obsidian
  vault this skill writes into). Pass it when the user keeps one; set
  `PODCAST_TRANSCRIPT_CORPUS` to make it the default. Without it, ranking falls
  back to mis-hearings plus the profile bonus.
- **Corrections** (heard-as → correct) are a filtered bonus. They are global to
  all dictation and the watch folder never applies them, so only distinctive
  garbles are sent: no context-dependent rows ("she" → "Xi"), no ordinary English
  words, no long one-off phrases, and nothing in
  `references/typewhisper-denylist.txt`. Add to that file any heard-as form that
  turns out to be a real name or word.
- Without `--prune` it only adds: it never deletes, replaces the dictionary, or
  overwrites a correction the user already has. With no system word list it skips
  corrections entirely (the English-word filter can't run) and says so.
- It needs TypeWhisper's API server (Settings > Advanced > API Server). If the
  server is off the script says so and exits 0; skip the step and mention it in
  one line. The next run catches up, because the profiles are the source of truth.
