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
  "Left alone"), any term with custom per-term settings (see below), and anything in
  `references/typewhisper-keep.txt`; add a term there if it matters more than its
  transcript counts suggest. Matching ignores case, Unicode composition and extra
  spaces. Without `--apply` it is a read-only report.
- **Per-term settings.** The API returns each term as an object (`term_entries`), and some
  carry settings: on the author's dictionary 53 of 256 terms have
  `ctc_min_similarity: 0.8`. A whole-list replace with bare strings would reset all of
  them, so `--prune` always sends the entry objects, verbatim, for every term that stays
  (the endpoint accepts `terms` *or* `term_entries`, never both). A response without
  usable `term_entries` is an error: entries are never invented from bare names.
  Verification compares the settings, not just the names (JSON `1` and `true` differ,
  `1` and `1.0` don't, null counts as absent, and fields the server adds itself are
  ignored), and the backup stores the full entries. If the restore brings the names back
  without the settings, it tries once to re-apply them with a non-replace upsert. A term
  the user tuned is a deliberate choice, so it is **never pruned** (like their own
  words), and that is re-checked against the final read at write time, so a term tuned
  mid-run is not removed.
- **Pruning safety rails.** TypeWhisper's API has no delete, only "replace the whole
  list", so a write is only as safe as the list it is built from:
  - The term list must be provably complete: when pruning, the API's `count` is
    required and must match the list (a truncated list would otherwise be written back
    and silently delete whatever it left out). A malformed list is an error too.
  - Terms match on case, Unicode composition and extra spaces, never on compatibility
    folding: `Ⅳ` and `IV`, `ß` and `ss` are different terms. The plan must remove
    exactly the terms it names; if duplicate or look-alike entries would make it remove
    more, it aborts.
  - The full previous list is saved first, to `~/.podcast-transcript/backups/` (private:
    directory 0700, file 0600, never overwritten; an unwritable backup aborts before
    anything is written). Then the dictionary is re-read immediately before the write and
    the run aborts if it no longer matches the plan; a list over the cap or with
    duplicates is refused.
  - After the write the result is verified. If the write, the verifying read or the
    verification itself fails, the previous list is restored; if the restore cannot be
    confirmed (or the app stored different capitalization) the message says so and names
    the backup file.
  - Notes are printed when the app stored terms with different capitalization, or when
    terms appear that the sync did not write.
  - The corpus never follows symlinks (they could fake extra episodes or read outside the
    folder).
  - A dictionary with duplicate terms (same term, different case or spacing) is
    refused, as is a plan that would remove more entries than it names.
  - **Verified on a live app (2026-11-15, one-term canary on a 256-term dictionary in which
    53 terms carry `ctc_min_similarity`):** a replace with `term_entries` preserved every
    kept term's entry field for field; the app accepts the entry objects and added no
    fields of its own; and it keeps the list alphabetically sorted itself, so list order
    is not ours to manage (an addition landed mid-list, not at the end).
  - **Unverified against the live app** (the rails above detect and undo these, but only
    a failing write would show how they behave): the rollback and the settings-repair
    upsert paths against the real app, and whether the add-only path leaves existing
    terms' settings alone (it only ever sends new, bare names).
  - **Residual risk:** the API has no conditional write, so a term added in the
    TypeWhisper app in the instant between the final read and the write would be
    overwritten, undetectably. Ask the user not to edit the dictionary while a sync runs.
  - **The first `--prune --apply` on a machine:** show the user the dry-run plan and get
    a go-ahead (it is the first write through the replace-the-whole-list path on that
    machine), then run it as a one-term canary, `--prune --apply --max-prune 1`, and
    diff the live dictionary against a snapshot taken just before (only the swapped terms
    should differ; every tuned term unchanged). The write rewrites the whole list either
    way, but a one-term change is easy to inspect. This has passed once on the author's
    machine (see above). Only then run the full prune; after that, run it automatically
    after the normal sync.
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
