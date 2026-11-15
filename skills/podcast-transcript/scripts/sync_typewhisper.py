#!/usr/bin/env python3
"""
sync_typewhisper.py — push podcast-profile STT fixes into the TypeWhisper dictionary.

Usage:
    python sync_typewhisper.py              # dry-run: show what would change
    python sync_typewhisper.py --apply      # write to TypeWhisper
    python sync_typewhisper.py --budget 200 # override the 256-term Parakeet cap
    python sync_typewhisper.py --corpus ~/vault  # rank by use in finished transcripts
    python sync_typewhisper.py --corpus ~/vault --prune          # dry-run: which weak terms to swap out
    python sync_typewhisper.py --corpus ~/vault --prune --apply  # swap them (with a full backup)

Reads the "Known STT artifacts" tables in references/podcasts/*.md and syncs them
through TypeWhisper's local HTTP API (Settings > Advanced > API Server):

- Terms: the *correct* spellings (proper nouns). Parakeet's vocabulary boosting
  uses these during transcription, so they improve the SRT itself. Parakeet
  boosts at most 256 terms; extras are silently dropped by the app, so this
  script fills only the free slots, best-ranked terms first (see ranking below).
- Corrections: heard-as -> correct pairs applied after transcription. Corrections
  are GLOBAL (they run on all dictation), so only distinctive garbles are sent;
  ambiguous ones ("she" -> "Xi") are filtered out. Watch-folder SRTs do not get
  corrections; they help dictation and file transcription.

By default the script only adds: it never deletes, never replaces the dictionary, and
never overwrites an existing correction that has a different replacement. It is
idempotent, and exits 0 when the API server is off so it cannot fail a run.

--prune opts in to swapping, because the 256-term cap fills up and a new, valuable term
(e.g. a name in this week's news) otherwise waits forever. When there is no free slot it
removes the weakest *profile-derived* terms and adds stronger deferred ones. Removal has
guard rails, because the API's only write path is "replace the whole list":
  - needs --corpus with at least MIN_CORPUS_EPISODES finished transcripts: episode counts
    are what justify removing a term, so it never prunes on mis-hearing counts alone;
  - a deferred term must score at least SWAP_RATIO x the term it replaces and beat it by
    SWAP_MIN_GAIN (no churn over 3 vs 2), and at most --max-prune terms go per run;
  - terms with no profile evidence (your own words, other dictation) are NEVER removed,
    and neither is anything in references/typewhisper-keep.txt;
  - it re-reads the dictionary right before writing and refuses if it changed, saves the
    full previous list to a backup file, verifies the result, and rolls back on mismatch.
Without --apply the --prune run is a read-only report.

Importable functions:
    parse_profiles(directory)          → list of ProfileRow
    term_candidates(rows)              → dict of term → recurrence score
    safe_corrections(rows, words, deny)→ (accepted, skipped)
    profile_prose(directory)           → profile text before the artifact tables
    corpus_usage(terms, corpus_dir)    → dict of term → (mentions, episodes)
    rank_scores(cands, prose, usage)   → dict of term → ranking score
    plan_terms(cands, existing, budget)→ (to_add, present, overflow)
    plan_prune(cands, existing, ...)   → PrunePlan (removals, additions, left_alone, ...)
    plan_corrections(accepted, existing) → (to_add, present, conflicts)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

PARAKEET_TERM_CAP = 256
DEFAULT_PORT = 8978
DISCOVERY_FILE = Path.home() / "Library/Application Support/TypeWhisper/api-discovery.json"
PROFILES_DIR = Path(__file__).resolve().parent.parent / "references" / "podcasts"
DENYLIST_FILE = Path(__file__).resolve().parent.parent / "references" / "typewhisper-denylist.txt"
SYSTEM_WORDS = Path("/usr/share/dict/words")
PROSE_BONUS = 2  # a term named in a profile's title or Speakers section counts as this many extra mis-hearings
_NON_CORPUS_DIRS = {".git", ".obsidian", ".trash"}
MIN_CORPUS_EPISODES = 10  # pruning is justified by episode counts, so require a real corpus
SWAP_RATIO = 2  # a deferred term must score at least this many times the term it replaces...
SWAP_MIN_GAIN = 2  # ...and beat it by at least this many points (no churn over 3 vs 2)
DEFAULT_MAX_PRUNE = 25  # terms removed per run: limits the blast radius of a bad corpus
KEEP_FILE = Path(__file__).resolve().parent.parent / "references" / "typewhisper-keep.txt"
BACKUP_DIR = Path(os.environ.get("PODCAST_TRANSCRIPT_BACKUP_DIR") or Path.home() / ".podcast-transcript" / "backups")
WEAK_EVIDENCE_MAX = 2  # generic single words need more than this many logged mis-hearings
MAX_CORRECTION_TOKENS = 3  # longer garbles are one-off sentence fragments, not reusable fixes
_LOWERCASE_CONNECTORS = {"of", "the", "and", "von", "van", "der", "de", "la", "el", "al", "bin"}

_QUOTED = re.compile(r'"([^"]+)"')
_PAREN = re.compile(r"\([^)]*\)")


@dataclass
class ProfileRow:
    profile: str
    heard: list[str]  # quoted heard-as variants (parentheticals removed)
    correct: list[str]  # quoted correct values (parentheticals removed)
    has_context: bool  # heard-as cell carries a "(context)" qualifier
    ambiguous: bool  # cell is not a plain heard -> correct pair


def parse_profiles(directory: Path) -> list[ProfileRow]:
    """Parse every `| "heard" / "heard2" | "Correct" (note) |` table row."""
    rows: list[ProfileRow] = []
    for path in sorted(Path(directory).glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.startswith("|") or line.startswith("|--") or "Heard as" in line:
                continue
            cells = [c.strip() for c in line.strip().strip("|").split(" | ")]
            if len(cells) < 2:
                continue
            heard_cell, correct_cell = cells[0], cells[1]
            heard = _QUOTED.findall(_PAREN.sub("", heard_cell))
            correct = _QUOTED.findall(_PAREN.sub("", correct_cell))
            if not heard or not correct:
                continue
            rows.append(
                ProfileRow(
                    profile=path.stem,
                    heard=heard,
                    correct=correct,
                    has_context=bool(_PAREN.search(heard_cell)),
                    ambiguous=" heard as " in heard_cell,
                )
            )
    return rows


def _normalize_term(value: str) -> str:
    value = value.strip()
    return value[:-2] if value.endswith("'s") else value


def _looks_like_proper_noun(term: str) -> bool:
    words = term.split()
    if not 1 <= len(words) <= 4 or len(term) < 3:
        return False
    if words[0].lower() == "the":
        return False
    if not any(c.isupper() or c.isdigit() for c in term):
        return False
    # Names, not phrases: every word is capitalised, digit-led, mixed-case or a connector.
    return all(
        w[0].isupper() or w[0].isdigit() or any(c.isupper() for c in w) or w.lower() in _LOWERCASE_CONNECTORS
        for w in words
    )


def term_candidates(rows: list[ProfileRow], words: set[str] | None = None) -> dict[str, int]:
    """Correct spellings that look like proper nouns, scored by how many distinct
    mis-hearings were logged for them (a proxy for how often STT gets them wrong).

    Skips comma-joined lists. When `words` is given, also skips a single ordinary
    English word ("Duo", "Sol", "Paramount") unless it has at least
    WEAK_EVIDENCE_MAX + 1 logged mis-hearings: boosting a common word on thin
    evidence only adds false positives."""
    scores: dict[str, int] = {}
    canonical: dict[str, str] = {}
    for row in rows:
        for raw in row.correct:
            term = _normalize_term(raw)
            if not _looks_like_proper_noun(term) or "," in term:
                continue
            key = term.lower()
            canonical.setdefault(key, term)
            scores[key] = scores.get(key, 0) + len(row.heard)
    result = {}
    for key, score in scores.items():
        term = canonical[key]
        generic = words and " " not in term and term[1:].islower() and _is_english(term, words)
        if generic and score <= WEAK_EVIDENCE_MAX:
            continue
        result[term] = score
    return result


def load_system_words(path: Path = SYSTEM_WORDS) -> set[str]:
    if not path.exists():
        return set()
    return {w.strip().lower() for w in path.read_text(encoding="utf-8", errors="ignore").splitlines()}


def load_denylist(path: Path = DENYLIST_FILE) -> set[str]:
    """Heard-as forms that are real names or words, one per line (# comments allowed)."""
    if not path.exists():
        return set()
    lines = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return {line.lower() for line in lines if line}


def _is_english(token: str, words: set[str]) -> bool:
    """Dictionary lookup that also catches common inflections (the system list has few plurals)."""
    t = token.lower().strip(".,'\u2019-")
    stems = {t, t.removesuffix("s"), t.removesuffix("es"), t.removesuffix("ed"), t.removesuffix("d"),
             t.removesuffix("ing"), t.removesuffix("ing") + "e", t.removesuffix("ies") + "y"}
    return any(stem in words for stem in stems if stem)


def _unsafe_reason(
    variant: str, replacement: str, row: ProfileRow, words: set[str], denylist: set[str]
) -> str | None:
    tokens = variant.split()
    if variant.lower() in denylist:
        return "on the denylist (real name or word)"
    if len(tokens) > MAX_CORRECTION_TOKENS:
        return "long one-off phrase"
    if row.ambiguous:
        return "row is not a plain heard-as pair"
    if row.has_context:
        return "needs context to disambiguate"
    if variant.lower() == replacement.lower():
        return "same as replacement"
    if len(tokens) == 1 and len(variant) < 6:
        return "short single word"
    if all(_is_english(t, words) for t in tokens):
        return "ordinary English words (would corrupt dictation)"
    return None


def safe_corrections(
    rows: list[ProfileRow], words: set[str], denylist: set[str] | None = None
) -> tuple[dict[str, tuple[str, str]], list[tuple[str, str, str]]]:
    """Return ({original_lower: (original, replacement)}, [(original, replacement, reason)])."""
    denylist = denylist or set()
    accepted: dict[str, tuple[str, str]] = {}
    skipped: list[tuple[str, str, str]] = []
    conflicted: set[str] = set()
    for row in rows:
        if len(row.correct) != 1:
            row_reason = (
                "needs context to disambiguate"
                if row.has_context
                else "row is not a plain heard-as pair"
                if row.ambiguous
                else "multiple correct values"
            )
            for variant in row.heard:
                skipped.append((variant, " / ".join(row.correct), row_reason))
            continue
        replacement = row.correct[0]
        for variant in row.heard:
            reason = _unsafe_reason(variant, replacement, row, words, denylist)
            if reason:
                skipped.append((variant, replacement, reason))
                continue
            key = variant.lower()
            if key in accepted and accepted[key][1] != replacement:
                conflicted.add(key)
            accepted.setdefault(key, (variant, replacement))
    for key in conflicted:
        original, replacement = accepted.pop(key)
        skipped.append((original, replacement, "conflicting replacements across profiles"))
    return accepted, skipped


def _count_mentions(term: str, text: str) -> int:
    return len(re.findall(r"(?<!\w)" + re.escape(term) + r"(?!\w)", text, flags=re.IGNORECASE))


def profile_prose(directory: Path) -> str:
    """Text of each profile before its "Known STT artifacts" section: the title,
    intro and Speakers section. A term named there is central to the show."""
    chunks: list[str] = []
    for path in sorted(Path(directory).glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("## Known STT artifacts"):
                break
            chunks.append(line)
    return "\n".join(chunks)


def corpus_bodies(corpus: Path) -> list[str]:
    """The text after "## Transcript" of every finished transcript under `corpus`."""
    bodies: list[str] = []
    root = Path(corpus).resolve()
    for path in Path(corpus).rglob("*.md"):
        if _NON_CORPUS_DIRS & set(path.parts):
            continue
        # A symlink could point outside the folder, or ten links at one file would fake ten episodes
        # and slip past the --prune corpus-size guard.
        if path.is_symlink() or not path.resolve().is_relative_to(root):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "\n## Transcript" in text:
            bodies.append(text.split("\n## Transcript", 1)[1])
    return bodies


def corpus_usage(terms: list[str], corpus: Path) -> dict[str, tuple[int, int]]:
    """Count each term across finished transcripts: markdown files under `corpus`
    that contain a "## Transcript" section (what this skill writes). Only the text
    after that heading counts. Returns {term: (mentions, episodes_containing_it)}."""
    bodies = corpus_bodies(corpus)
    usage: dict[str, tuple[int, int]] = {}
    for term in terms:
        counts = [_count_mentions(term, body) for body in bodies]
        usage[term] = (sum(counts), sum(1 for n in counts if n))
    return usage


def rank_scores(
    candidates: dict[str, int],
    prose: str = "",
    usage: dict[str, tuple[int, int]] | None = None,
) -> dict[str, int]:
    """Final ranking score: (mis-hearings + prose bonus) x (1 + episodes using the term).

    Mis-hearings say how often STT gets a term wrong; episodes say how often it comes
    up at all, so boosting it pays off. Without a corpus every term has one factor of
    1 and the ranking falls back to mis-hearings plus the prose bonus."""
    scores: dict[str, int] = {}
    for term, base in candidates.items():
        bonus = PROSE_BONUS if prose and _count_mentions(term, prose) else 0
        episodes = usage[term][1] if usage and term in usage else 0
        scores[term] = (base + bonus) * (1 + episodes)
    return scores


def plan_terms(
    candidates: dict[str, int], existing: list[str], budget: int = PARAKEET_TERM_CAP
) -> tuple[list[str], list[str], list[str]]:
    """Fill free Parakeet slots by ranking score, then longer (more specific) terms.
    Returns (to_add, present, overflow)."""
    have = {t.lower() for t in existing}
    present = sorted(t for t in candidates if t.lower() in have)
    fresh = sorted((t for t in candidates if t.lower() not in have), key=lambda t: (-candidates[t], -len(t), t))
    free = max(0, budget - len(existing))
    return fresh[:free], present, fresh[free:]


def _key(term: str) -> str:
    """Canonical form for matching terms: case, Unicode composition ("é" vs "e" + accent) and runs of
    whitespace must not let a term slip past the keep list. Deliberately NOT compatibility folding
    (NFKC) or casefold: "Ⅳ" and "IV", or "ß" and "ss", are different terms and must never be conflated,
    because a conflated match would remove more than the plan names."""
    return " ".join(unicodedata.normalize("NFC", term).split()).lower()


def load_keeplist(path: Path = KEEP_FILE) -> set[str]:
    """Terms --prune must never remove, one per line (# comments allowed), as canonical keys."""
    if not path.exists():
        return set()
    lines = (line.split("#", 1)[0].strip() for line in path.read_text(encoding="utf-8").splitlines())
    return {_key(line) for line in lines if line}


@dataclass
class PrunePlan:
    removals: list[tuple[str, int]] = field(default_factory=list)  # existing profile terms to drop (weakest first)
    additions: list[tuple[str, int]] = field(default_factory=list)  # new terms: free slots first, then swap-ins
    left_alone: list[str] = field(default_factory=list)  # existing terms with no profile evidence: never removed
    protected: list[str] = field(default_factory=list)  # existing profile terms on the keep list
    deferred: list[tuple[str, int]] = field(default_factory=list)  # still waiting after the plan


def plan_prune(
    candidates: dict[str, int],
    existing: list[str],
    budget: int = PARAKEET_TERM_CAP,
    keep: set[str] | None = None,
    max_removals: int = DEFAULT_MAX_PRUNE,
    mentions: dict[str, int] | None = None,
) -> PrunePlan:
    """Fill free slots first, then swap the weakest removable existing terms for the strongest
    deferred ones. Only terms the profiles know about (a score in `candidates`) can be removed:
    a term with no profile evidence is somebody's own word and is left alone. A swap needs the new
    term to score >= SWAP_RATIO x the old one and beat it by >= SWAP_MIN_GAIN; because both lists
    are sorted, the first pair that fails ends the search. Scores tie a lot (every one-episode,
    one-variant term scores 2); `mentions` (raw corpus mention counts) then decides: the term said
    least often goes first, and the one said most often is added first, so ties are not settled by
    the alphabet."""
    keep = {_key(k) for k in (keep or set())}
    said = {_key(t): n for t, n in (mentions or {}).items()}
    score_of = {_key(t): s for t, s in candidates.items()}
    have = {_key(t) for t in existing}
    removable: list[tuple[str, int]] = []
    plan = PrunePlan()
    for term in existing:
        score = score_of.get(_key(term))
        if score is None:
            plan.left_alone.append(term)
        elif _key(term) in keep:
            plan.protected.append(term)
        else:
            removable.append((term, score))
    removable.sort(key=lambda ts: (ts[1], said.get(_key(ts[0]), 0), _key(ts[0])))
    fresh = sorted(
        ((t, s) for t, s in candidates.items() if _key(t) not in have),
        key=lambda ts: (-ts[1], -said.get(_key(ts[0]), 0), -len(ts[0]), ts[0]),
    )
    free = max(0, budget - len(existing))
    plan.additions, queue = fresh[:free], fresh[free:]
    while queue and removable and len(plan.removals) < max_removals:
        (new_term, new_score), (old_term, old_score) = queue[0], removable[0]
        if new_score >= SWAP_RATIO * old_score and new_score - old_score >= SWAP_MIN_GAIN:
            plan.removals.append(removable.pop(0))
            plan.additions.append(queue.pop(0))
        else:
            break
    plan.left_alone.sort(key=str.lower)
    plan.protected.sort(key=str.lower)
    plan.deferred = queue
    return plan


class PruneError(Exception):
    """A prune could not be written safely; the message says what state the dictionary is in."""


def _sig(entry: dict) -> str:
    """Order-independent identity of a whole entry: the term AND its settings."""
    return json.dumps(entry, sort_keys=True, ensure_ascii=False)


def _restore(client, before: list[dict], backup: Path) -> str:
    """Put the previous entries (settings included) back and confirm it. Any failure leaves the state
    unknown, so say so."""
    try:
        client.replace_terms(before)
        now = client.term_entries()
    except Exception:  # noqa: BLE001 - mid-recovery, ANY failure means we cannot vouch for the state
        now = None
    if now is not None and {_sig(e) for e in now} == {_sig(e) for e in before}:
        return "the previous dictionary was restored"
    if now is not None and {_key(e["term"]) for e in now} == {_key(e["term"]) for e in before}:
        return (f"the previous terms were restored, but TypeWhisper stored some with different spelling or "
                f"per-term settings than the originals (exact copy at {backup})")
    return f"RESTORE FAILED OR COULD NOT BE CONFIRMED: the dictionary state is unknown; full backup at {backup}"


def apply_prune(
    client, plan: PrunePlan, expected: list[str], budget: int = PARAKEET_TERM_CAP, backup_dir: Path | None = None
) -> tuple[Path, list[str]]:
    """Write a prune plan. The API's only removal path is replacing the whole term list, so every
    step is defensive. Terms travel as the API's own `term_entries` objects, verbatim, so per-term
    settings (e.g. ctc_min_similarity) of the terms that stay are preserved, and verification checks
    the settings, not just the names. The backup of the planning snapshot is written FIRST so that no
    filesystem work sits between the final read and the write; that read must still match the snapshot
    exactly, the plan must remove exactly the terms it names (look-alike or duplicate entries abort it),
    the cap is enforced, and after the single write the result is verified. If the write, the verifying
    read or the verification itself fails, the previous entries are restored (the write may or may not
    have landed). Returns (backup path, notes).

    Residual risk, because the API has no conditional write: a term added in the TypeWhisper app in the
    instant between the final read and the write is overwritten and cannot be detected. Don't edit the
    dictionary while a sync runs."""
    snapshot = client.term_entries()
    if {_key(e["term"]) for e in snapshot} != {_key(t) for t in expected}:
        raise PruneError("the TypeWhisper dictionary changed while this plan was being made; nothing was "
                         "written. Re-run to plan against the current dictionary.")
    try:
        backup = _write_backup(backup_dir or BACKUP_DIR, snapshot, [t for t, _ in plan.removals],
                               [t for t, _ in plan.additions])
    except OSError as exc:
        raise PruneError(f"could not write the backup ({exc}); nothing was written.") from exc

    before = client.term_entries()  # the final read: nothing slow happens between here and the write
    if {_sig(e) for e in before} != {_sig(e) for e in snapshot}:
        raise PruneError("the TypeWhisper dictionary (or a term's settings) changed just before the write; "
                         "nothing was written. Re-run.")
    removed = {_key(t) for t, _ in plan.removals}
    dropped = [e["term"] for e in before if _key(e["term"]) in removed]
    if len(dropped) != len(plan.removals):
        raise PruneError(f"the plan names {len(plan.removals)} terms to remove but {len(dropped)} dictionary "
                         f"entries match them ({dropped[:5]}): duplicates or look-alike spellings. "
                         "Nothing was written.")
    kept = [e for e in before if _key(e["term"]) not in removed]
    kept_keys = {_key(e["term"]) for e in kept}
    added = [{"term": t} for t, _ in plan.additions if _key(t) not in kept_keys]
    new_entries = kept + added
    if len(new_entries) > budget:
        raise PruneError(f"refusing to write {len(new_entries)} terms (cap {budget}); nothing was written.")
    if len({_key(e["term"]) for e in new_entries}) != len(new_entries):
        raise PruneError("the new term list has duplicates; nothing was written.")

    try:
        client.replace_terms(new_entries)
        after = client.term_entries()
    except Exception as exc:  # noqa: BLE001 - once the write has started, any failure leaves the state uncertain
        raise PruneError(f"the write could not be confirmed ({type(exc).__name__}: {exc}); "
                         f"{_restore(client, before, backup)}.") from exc
    after_by_key = {_key(e["term"]): e for e in after}
    gone = [e["term"] for e in kept if _key(e["term"]) not in after_by_key]
    stuck = [t for t, _ in plan.removals if _key(t) in after_by_key]
    missing = [e["term"] for e in added if _key(e["term"]) not in after_by_key]
    changed = [e["term"] for e in kept
               if _key(e["term"]) in after_by_key and
               {k: v for k, v in after_by_key[_key(e["term"])].items() if k != "term"} != {k: v for k, v in e.items() if k != "term"}]
    if gone or stuck or missing or changed:
        raise PruneError(f"verification failed (kept terms missing: {gone[:5]}; removed terms still present: "
                         f"{stuck[:5]}; additions missing: {missing[:5]}; per-term settings changed: {changed[:5]}); "
                         f"{_restore(client, before, backup)}.")
    notes = []
    if {e["term"] for e in after} != {e["term"] for e in new_entries}:
        notes.append("TypeWhisper stored some terms with different capitalization or spacing than were sent.")
    new_keys = {_key(e["term"]) for e in new_entries}
    extra = [e["term"] for e in after if _key(e["term"]) not in new_keys]
    if extra:
        notes.append(f"{len(extra)} term(s) are in the dictionary that this sync did not write "
                     f"(added in the app during the sync?): {extra[:5]}")
    return backup, notes


def _write_backup(directory: Path, entries: list[dict], removed: list[str], added: list[str]) -> Path:
    """Save the full previous term list with its per-term settings. It is the user's personal
    vocabulary, so the directory is created 0700 and the file 0600 (the process umask can only
    tighten that); O_EXCL means two runs in the same second can never overwrite each other's backup."""
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    payload = json.dumps({"written": stamp, "terms": [e["term"] for e in entries], "term_entries": entries,
                          "removed": removed, "added": added}, indent=2, ensure_ascii=False)
    n = 1
    while True:
        path = directory / (f"terms-before-prune-{stamp}.json" if n == 1 else f"terms-before-prune-{stamp}-{n}.json")
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            n += 1
            continue
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        return path


def plan_corrections(
    accepted: dict[str, tuple[str, str]], existing: dict[str, str]
) -> tuple[list[tuple[str, str]], list[str], list[tuple[str, str, str]]]:
    """Split into (to_add, already_present, conflicts with a user's own correction)."""
    have = {k.lower(): v for k, v in existing.items()}
    to_add: list[tuple[str, str]] = []
    present: list[str] = []
    conflicts: list[tuple[str, str, str]] = []
    for key, (original, replacement) in sorted(accepted.items()):
        if key not in have:
            to_add.append((original, replacement))
        elif have[key] == replacement:
            present.append(original)
        else:
            conflicts.append((original, replacement, have[key]))
    return to_add, present, conflicts


class ApiUnavailable(Exception):
    pass


class TypeWhisperClient:
    def __init__(self, port: int, token: str | None, require_count: bool = False):
        self.base = f"http://127.0.0.1:{port}"
        self.token = token
        self.require_count = require_count  # pruning needs the API's total count to prove a list is complete

    @classmethod
    def discover(cls, discovery_file: Path = DISCOVERY_FILE) -> "TypeWhisperClient":
        port, token = DEFAULT_PORT, os.environ.get("TYPEWHISPER_API_TOKEN")
        if os.environ.get("TYPEWHISPER_PORT"):
            port = int(os.environ["TYPEWHISPER_PORT"])
        if discovery_file.exists():
            try:
                data = json.loads(discovery_file.read_text(encoding="utf-8"))
                token = token or data.get("token")
                port = int(data.get("port", port)) if not os.environ.get("TYPEWHISPER_PORT") else port
            except (OSError, ValueError):
                pass
        return cls(port, token)

    def _request(self, method: str, path: str, body: dict | None = None) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"{method} {path} failed: HTTP {exc.code} {exc.read().decode('utf-8', 'ignore')}")
        except (urllib.error.URLError, ConnectionError, TimeoutError) as exc:
            raise ApiUnavailable(str(exc))

    def _checked(self) -> dict:
        """GET the term list and refuse an incomplete or malformed response. Pruning writes back whatever
        it reads, so a partial list would silently delete the terms it left out."""
        data = self._request("GET", "/v1/dictionary/terms")
        terms = data.get("terms")
        if not isinstance(terms, list) or not all(isinstance(t, str) and t.strip() for t in terms):
            raise RuntimeError("GET /v1/dictionary/terms returned a malformed term list")
        if "count" not in data:
            if self.require_count:
                raise RuntimeError("GET /v1/dictionary/terms did not report a total count, so a truncated list "
                                   "cannot be told from a complete one; refusing to prune on it")
        elif data["count"] != len(terms):
            raise RuntimeError(f"GET /v1/dictionary/terms is incomplete: count={data['count']} "
                               f"but {len(terms)} terms were returned")
        return data

    def terms(self) -> list[str]:
        return self._checked()["terms"]

    def term_entries(self) -> list[dict]:
        """The terms WITH their per-term settings (e.g. {"term": "Accessibility", "ctc_min_similarity": 0.8}).
        Replacing the list with bare strings would reset those settings, so pruning carries these
        objects through verbatim."""
        data = self._checked()
        entries = data.get("term_entries")
        if entries is None:  # an API version without per-term settings
            return [{"term": t} for t in data["terms"]]
        if not isinstance(entries, list) or not all(isinstance(e, dict) and isinstance(e.get("term"), str) for e in entries):
            raise RuntimeError("GET /v1/dictionary/terms returned malformed term_entries")
        if [e["term"] for e in entries] != data["terms"]:
            raise RuntimeError("GET /v1/dictionary/terms: term_entries do not match terms; refusing to prune on it")
        return entries

    def corrections(self) -> dict[str, str]:
        items = self._request("GET", "/v1/dictionary/corrections")["corrections"]
        return {c["original"]: c["replacement"] for c in items}

    def add_terms(self, terms: list[str]) -> None:
        self._request("PUT", "/v1/dictionary/terms", {"terms": terms, "replace": False})

    def replace_terms(self, items: list) -> None:
        """Replace the ENTIRE term list (the only removal path the API has). Use apply_prune().
        Items that are dicts go in `term_entries` (settings preserved); strings go in `terms`. The API
        accepts one or the other, never both."""
        key = "term_entries" if any(isinstance(i, dict) for i in items) else "terms"
        self._request("PUT", "/v1/dictionary/terms", {key: items, "replace": True})

    def put_correction(self, original: str, replacement: str) -> None:
        self._request(
            "PUT",
            "/v1/dictionary/corrections",
            {"original": original, "replacement": replacement, "caseSensitive": False},
        )


def _show(title: str, items: list, limit: int = 40) -> None:
    print(f"\n{title} ({len(items)})")
    for item in items[:limit]:
        print("  " + (item if isinstance(item, str) else " -> ".join(str(x) for x in item)))
    if len(items) > limit:
        print(f"  ... and {len(items) - limit} more")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync podcast profile fixes into the TypeWhisper dictionary.")
    parser.add_argument("--apply", action="store_true", help="Write changes (default is a dry-run)")
    parser.add_argument("--budget", type=int, default=PARAKEET_TERM_CAP, help="Total term cap (default: 256)")
    parser.add_argument("--profiles", type=Path, default=PROFILES_DIR, help="Directory of podcast profiles")
    parser.add_argument(
        "--corpus",
        type=Path,
        default=os.environ.get("PODCAST_TRANSCRIPT_CORPUS"),
        help="Folder of finished transcripts (e.g. an Obsidian vault); ranks terms by how many "
        "episodes use them. Also read from $PODCAST_TRANSCRIPT_CORPUS",
    )
    parser.add_argument(
        "--prune",
        action="store_true",
        help="When no slot is free, swap the weakest profile-derived terms for stronger deferred ones. "
        "Needs --corpus. Read-only unless combined with --apply",
    )
    parser.add_argument("--max-prune", type=int, default=DEFAULT_MAX_PRUNE, help="Most terms --prune removes per run")
    parser.add_argument("--keep-file", type=Path, default=KEEP_FILE, help="Terms --prune must never remove")
    args = parser.parse_args()
    if args.corpus and not Path(args.corpus).is_dir():
        print(f"--corpus is not a folder: {args.corpus}", file=sys.stderr)
        return 2
    if args.max_prune < 0 or args.budget < 1:
        print("--max-prune must be >= 0 and --budget >= 1", file=sys.stderr)
        return 2
    if args.prune:
        if not args.corpus:
            print("--prune needs --corpus (or $PODCAST_TRANSCRIPT_CORPUS): episode counts are what justify "
                  "removing a term, and without them the scores cannot tell a recurring name from a one-off.",
                  file=sys.stderr)
            return 2
        episodes = len(corpus_bodies(Path(args.corpus)))
        if episodes < MIN_CORPUS_EPISODES:
            print(f"--prune needs at least {MIN_CORPUS_EPISODES} finished transcripts in the corpus; "
                  f"found {episodes} under {args.corpus}.", file=sys.stderr)
            return 2

    rows = parse_profiles(args.profiles)
    words = load_system_words()
    base_scores = term_candidates(rows, words)
    usage = corpus_usage(list(base_scores), Path(args.corpus)) if args.corpus else None
    candidates = rank_scores(base_scores, profile_prose(args.profiles), usage)
    if words:
        accepted, skipped = safe_corrections(rows, words, load_denylist())
    else:
        # Without a word list the "no ordinary English words" filter silently does nothing and
        # ~100 ordinary phrases ("dumb and", "easy pass") would become GLOBAL dictation fixes.
        accepted, skipped = {}, []
        print(f"WARNING: no system word list at {SYSTEM_WORDS}, so the ordinary-English-word filter "
              "cannot run; skipping ALL corrections (they apply to all dictation). Terms still sync. "
              "Install a word list (e.g. `apt install wamerican`) to enable corrections.", file=sys.stderr)

    client = TypeWhisperClient.discover()
    if args.prune and hasattr(client, "require_count"):
        client.require_count = True
    try:
        existing_terms = client.terms()
        existing_corrections = client.corrections()
    except ApiUnavailable:
        print(
            "TypeWhisper API server is off: enable Settings > Advanced > API Server. "
            "Nothing was synced; the next run will catch up."
        )
        return 0
    except RuntimeError as exc:
        print(f"TypeWhisper API error: {exc}", file=sys.stderr)
        return 1

    plan = None
    if args.prune:
        mentions = {t: m for t, (m, _) in usage.items()} if usage else None
        # A term the user tuned (e.g. ctc_min_similarity) is a deliberate choice, like a term they added themselves:
        # never remove it, whatever its corpus score. (Pruning an untuned term loses nothing the backup can't restore;
        # pruning a tuned one destroys the tuning.)
        tuned = {_key(e["term"]) for e in client.term_entries() if set(e) - {"term"}}
        plan = plan_prune(candidates, existing_terms, args.budget, load_keeplist(args.keep_file) | tuned,
                          args.max_prune, mentions)
        have_lower = {t.lower() for t in existing_terms}
        terms_to_add = [t for t, _ in plan.additions]
        terms_present = [t for t in candidates if t.lower() in have_lower]
        terms_overflow = [t for t, _ in plan.deferred]
    else:
        terms_to_add, terms_present, terms_overflow = plan_terms(candidates, existing_terms, args.budget)
    corr_to_add, corr_present, corr_conflicts = plan_corrections(accepted, existing_corrections)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {len(rows)} profile rows, {len(existing_terms)}/{args.budget} term slots used")
    ranked = lambda terms: [f"{t}  [score {candidates[t]}]" for t in terms]  # noqa: E731
    if plan is not None:
        _show("Terms to REMOVE (weakest first; each is replaced by a stronger deferred term)",
              [f"{t}  [score {sc}]" for t, sc in plan.removals], limit=len(plan.removals))
    _show("Terms to add", ranked(terms_to_add), limit=len(terms_to_add))
    _show("Terms deferred (no free Parakeet slot)", ranked(terms_overflow))
    if plan is not None:
        used = corpus_usage(plan.left_alone, Path(args.corpus)) if plan.left_alone else {}
        _show("Left alone: existing terms with no profile evidence (never removed)",
              [f"{t}  [{used.get(t, (0, 0))[1]} episodes]" for t in plan.left_alone], limit=12)
        _show("Protected (keep list, or the term has custom per-term settings)", plan.protected)
    _show("Corrections to add", corr_to_add)
    _show("Corrections conflicting with an existing entry (left alone)", corr_conflicts)
    if not args.apply:
        _show("Corrections skipped as unsafe", skipped, limit=15)
        if not args.prune and terms_overflow:
            print(f"\n{len(terms_overflow)} terms are deferred. Add --prune (with --corpus) to see which "
                  "weak terms could be swapped out for them.")

    if args.apply:
        try:
            if plan is not None and plan.removals:
                backup, notes = apply_prune(client, plan, existing_terms, args.budget)
                print(f"\nPruned {len(plan.removals)} terms and added {len(terms_to_add)}; the previous dictionary "
                      f"is saved at {backup}")
                for note in notes:
                    print(f"NOTE: {note}")
            elif terms_to_add:
                client.add_terms(terms_to_add)
            for original, replacement in corr_to_add:
                client.put_correction(original, replacement)
            have_terms = {t.lower() for t in client.terms()}
            have_corr = {k.lower() for k in client.corrections()}
        except ApiUnavailable:
            # Writes are add-only and idempotent, so the next run fills any gap.
            print("TypeWhisper API server went away mid-sync; the next run will catch up.")
            return 0
        except PruneError as exc:
            print(f"PRUNE FAILED: {exc}", file=sys.stderr)
            return 1
        except RuntimeError as exc:
            print(f"TypeWhisper API error: {exc}", file=sys.stderr)
            return 1
        missing = [t for t in terms_to_add if t.lower() not in have_terms]
        missing += [o for o, _ in corr_to_add if o.lower() not in have_corr]
        if missing:
            print(f"\nVerification failed; not found after write: {missing}", file=sys.stderr)
            return 1

    print(
        f"\nSummary: terms +{len(terms_to_add)} (already present {len(terms_present)}, "
        f"deferred {len(terms_overflow)}); corrections +{len(corr_to_add)} "
        f"(already present {len(corr_present)}, conflicts {len(corr_conflicts)}, skipped {len(skipped)})"
    )
    if not args.apply:
        print("Re-run with --apply to write these changes.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
