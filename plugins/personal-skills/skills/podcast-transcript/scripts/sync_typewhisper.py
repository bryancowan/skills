#!/usr/bin/env python3
"""
sync_typewhisper.py — push podcast-profile STT fixes into the TypeWhisper dictionary.

Usage:
    python sync_typewhisper.py              # dry-run: show what would change
    python sync_typewhisper.py --apply      # write to TypeWhisper
    python sync_typewhisper.py --budget 200 # override the 256-term Parakeet cap

Reads the "Known STT artifacts" tables in references/podcasts/*.md and syncs them
through TypeWhisper's local HTTP API (Settings > Advanced > API Server):

- Terms: the *correct* spellings (proper nouns). Parakeet's vocabulary boosting
  uses these during transcription, so they improve the SRT itself. Parakeet
  boosts at most 256 terms; extras are silently dropped by the app, so this
  script fills only the free slots, highest-recurrence terms first.
- Corrections: heard-as -> correct pairs applied after transcription. Corrections
  are GLOBAL (they run on all dictation), so only distinctive garbles are sent;
  ambiguous ones ("she" -> "Xi") are filtered out. Watch-folder SRTs do not get
  corrections; they help dictation and file transcription.

The script only adds. It never deletes, never replaces the dictionary, and never
overwrites an existing correction that has a different replacement. It is
idempotent, and exits 0 when the API server is off so it cannot fail a run.

Importable functions:
    parse_profiles(directory)          → list of ProfileRow
    term_candidates(rows)              → dict of term → recurrence score
    safe_corrections(rows, words, deny)→ (accepted, skipped)
    plan_terms(cands, existing, budget)→ (to_add, present, overflow)
    plan_corrections(accepted, existing) → (to_add, present, conflicts)
"""

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

PARAKEET_TERM_CAP = 256
DEFAULT_PORT = 8978
DISCOVERY_FILE = Path.home() / "Library/Application Support/TypeWhisper/api-discovery.json"
PROFILES_DIR = Path(__file__).resolve().parent.parent / "references" / "podcasts"
DENYLIST_FILE = Path(__file__).resolve().parent.parent / "references" / "typewhisper-denylist.txt"
SYSTEM_WORDS = Path("/usr/share/dict/words")
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


def plan_terms(
    candidates: dict[str, int], existing: list[str], budget: int = PARAKEET_TERM_CAP
) -> tuple[list[str], list[str], list[str]]:
    """Fill free Parakeet slots by recurrence score, then longer (more specific) terms.
    Returns (to_add, present, overflow)."""
    have = {t.lower() for t in existing}
    present = sorted(t for t in candidates if t.lower() in have)
    fresh = sorted((t for t in candidates if t.lower() not in have), key=lambda t: (-candidates[t], -len(t), t))
    free = max(0, budget - len(existing))
    return fresh[:free], present, fresh[free:]


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
    def __init__(self, port: int, token: str | None):
        self.base = f"http://127.0.0.1:{port}"
        self.token = token

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

    def terms(self) -> list[str]:
        return self._request("GET", "/v1/dictionary/terms")["terms"]

    def corrections(self) -> dict[str, str]:
        items = self._request("GET", "/v1/dictionary/corrections")["corrections"]
        return {c["original"]: c["replacement"] for c in items}

    def add_terms(self, terms: list[str]) -> None:
        self._request("PUT", "/v1/dictionary/terms", {"terms": terms, "replace": False})

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
    args = parser.parse_args()

    rows = parse_profiles(args.profiles)
    words = load_system_words()
    candidates = term_candidates(rows, words)
    accepted, skipped = safe_corrections(rows, words, load_denylist())

    client = TypeWhisperClient.discover()
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

    terms_to_add, terms_present, terms_overflow = plan_terms(candidates, existing_terms, args.budget)
    corr_to_add, corr_present, corr_conflicts = plan_corrections(accepted, existing_corrections)

    mode = "APPLY" if args.apply else "DRY-RUN"
    print(f"[{mode}] {len(rows)} profile rows, {len(existing_terms)}/{args.budget} term slots used")
    _show("Terms to add", terms_to_add, limit=len(terms_to_add))
    _show("Terms deferred (no free Parakeet slot)", terms_overflow)
    _show("Corrections to add", corr_to_add)
    _show("Corrections conflicting with an existing entry (left alone)", corr_conflicts)
    if not args.apply:
        _show("Corrections skipped as unsafe", skipped, limit=15)

    if args.apply:
        if terms_to_add:
            client.add_terms(terms_to_add)
        for original, replacement in corr_to_add:
            client.put_correction(original, replacement)
        have_terms = {t.lower() for t in client.terms()}
        have_corr = {k.lower() for k in client.corrections()}
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
