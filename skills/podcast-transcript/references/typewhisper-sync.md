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
  it matters more than its transcript counts suggest. Matching ignores case, Unicode
  composition and extra spaces. Without `--apply` it is a read-only report.
- **Pruning safety rails.** TypeWhisper's API has no delete, only "replace the whole
  list", so a write is only as safe as the list it is built from:
  - A truncated or malformed term list is an error (the API reports a `count`; a
    mismatch aborts), because writing back a partial list would silently delete the
    terms it left out.
  - Before writing, the dictionary is re-read and the run aborts if it no longer matches
    the plan; the full previous list is saved to `~/.podcast-transcript/backups/` (an
    unwritable backup aborts before anything is written); a list over the cap or with
    duplicates is refused.
  - After the write the result is verified. If the write, the verifying read or the
    verification itself fails, the previous list is restored; if the restore cannot be
    confirmed the error says the state is unknown and names the backup file.
  - Notes are printed when the app stored terms with different capitalization, or when
    terms appear that the sync did not write.
  - **Residual risk:** the API has no conditional write, so a term added in the
    TypeWhisper app in the milliseconds between the final read and the write would be
    overwritten, undetectably. Ask the user not to edit the dictionary while a sync runs.
  - **The first `--prune --apply` on a machine:** show the user the dry-run plan and get
    a go-ahead (it is the first write through the replace-the-whole-list path); after
    that, run it automatically after the normal sync.
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
