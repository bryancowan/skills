#!/usr/bin/env python3
"""
parse_srt.py — SRT transcript parser for podcast-to-markdown workflow.

Usage:
    python parse_srt.py <file.srt> [--gap 1500]
    python parse_srt.py <file.srt> --proper-nouns [--min-count 1]
    python parse_srt.py <file.srt> --diarized                       # inspect speaker labels
    python parse_srt.py <file.srt> --diarized --map 1=Andrew --map 2=Bill [--review]

Default mode prints numbered, cleaned paragraphs to stdout separated by blank
lines. The --gap flag controls the silence threshold in milliseconds for
paragraph breaks.

--proper-nouns mode instead prints capitalized tokens and multi-word capitalized
runs with their frequency counts. Use it to spot proper nouns (people, places,
brands) that the speech-to-text engine may have mangled the same way repeatedly
across the episode.

--diarized mode is for SRTs whose cues already carry speaker labels
("Speaker 1: ...", ">> JOHN: ...", "JOHN: ..."). Without --map it prints a speaker
table (cue range per label), warns when label sets change partway through (chunk-
local labels: "Speaker 1/2" in the first half, "Speaker 3/4" in the second) and
lists anchor cues (intros, sign-offs) to map labels to names. With --map it
reassembles interleaved fragments, applies light cleanup and prints the labeled
transcript body as markdown. See SKILL.md Step 1D.

Importable functions:
    parse_srt(filepath)               → list of (index, start_ms, end_ms, text)
    group_paragraphs(entries, gap_ms) → list of merged paragraph strings
    clean_text(text)                  → filler-stripped, deduped paragraph
    process_srt(filepath, gap_ms)     → full pipeline → list of clean paragraphs
    proper_noun_counts(paragraphs)    → Counter of candidate proper nouns
"""

import re
import sys
import argparse
from collections import Counter, namedtuple


def _ts_to_ms(ts: str) -> int:
    """Convert SRT timestamp (HH:MM:SS,mmm) to milliseconds."""
    h, m, rest = ts.split(":")
    s, ms = rest.split(",")
    return int(h) * 3_600_000 + int(m) * 60_000 + int(s) * 1_000 + int(ms)


def _read_normalized(filepath: str) -> str:
    """
    Read a file and normalize line endings + strip a leading BOM.

    SRTs are frequently exported with Windows CRLF line endings. Without this
    normalization, block splitting on "\\n\\n" fails on "\\r\\n\\r\\n" separators
    and the entire file collapses into a single block.
    """
    with open(filepath, encoding="utf-8-sig") as f:  # utf-8-sig drops a BOM
        content = f.read()
    return content.replace("\r\n", "\n").replace("\r", "\n")


def parse_srt(filepath: str) -> list[tuple[int, int, int, str]]:
    """
    Parse an SRT file into a list of (index, start_ms, end_ms, text) tuples.
    Multi-line subtitle text is joined with a space.
    """
    content = _read_normalized(filepath)

    entries = []
    for block in content.strip().split("\n\n"):
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        ts_line = lines[1].strip()
        if "-->" not in ts_line:
            continue
        start_str, end_str = [x.strip() for x in ts_line.split("-->")]
        # Timestamps may carry trailing positioning info (e.g. "X1:0 ...").
        start_str = start_str.split()[0]
        end_str = end_str.split()[0]
        text = " ".join(lines[2:]).strip()
        if not text:
            continue
        entries.append((idx, _ts_to_ms(start_str), _ts_to_ms(end_str), text))

    return entries


def group_paragraphs(entries: list[tuple[int, int, int, str]], gap_ms: int = 1500) -> list[str]:
    """
    Merge consecutive SRT entries into paragraphs.
    A new paragraph starts whenever the gap between the end of one entry
    and the start of the next exceeds gap_ms milliseconds.
    """
    paragraphs = []
    current: list[str] = []

    for i, (_, _start, end, text) in enumerate(entries):
        current.append(text)
        if i + 1 < len(entries):
            next_start = entries[i + 1][1]
            if next_start - end > gap_ms:
                paragraphs.append(" ".join(current))
                current = []
        else:
            paragraphs.append(" ".join(current))

    return paragraphs


_FILLERS = ("um", "uh", "ah")       # legacy plain-paragraph cleanup
_HESITATIONS = ("um", "uh")          # diarized build: "ah"/"hmm" are reactions, never stripped
# Function words that STT repeats with a comma: "and, and", "it's, it's".
_STUTTER_FUNC = r"(?:I|it|it's|a|an|the|and|that|they|we|he|like|so|but|this|there|is)"
_W = r"[\w']+"


def _strip_fillers(text: str, fillers: tuple = _FILLERS) -> str:
    """
    Remove standalone fillers, including a trailing comma, period or cut-off dash.
    Leaves "Uh-huh", "uh-oh", and URL/path pieces ("example.com/uh/page") alone.
    """
    for filler in fillers:
        # The filler plus trailing comma / cut-off dash. A final period is NOT swallowed, so
        # "I said uh. Then left." keeps its sentence break ("I said. Then left.").
        text = re.sub(rf"(?<![\w/.:@-]){filler}\b(?!-\w)[-–—,]*\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\(\s*\)\s*", "", text)           # "(uh)" → "" not "()"
    text = re.sub(r"^\s*[.,]\s*", "", text)           # "Um. So…" → "So…"
    return text


def _collapse_cutoffs(text: str) -> str:
    """
    Collapse STT false starts that were cut off with a hyphen:
    "it- it is" → "it is", "I- I- I think" → "I think", "it is- it is" → "it is",
    plus comma stutters of function words: "and, and" → "and".
    """
    def keep_second(m):
        keep = m.group(2)   # follow the CASE of what the speaker started with
        return keep[0].upper() + keep[1:] if m.group(1)[0].isupper() else keep[0].lower() + keep[1:]

    for _ in range(4):  # repeat so "I- I- I" collapses fully
        text = re.sub(rf"\b({_W}(?: {_W}){{0,2}})- (\1)\b", keep_second, text, flags=re.IGNORECASE)
        text = re.sub(rf"\b({_STUTTER_FUNC}), (\1)\b", keep_second, text, flags=re.IGNORECASE)
    # A word cut off mid-way and then said in full: "show- shown" → "shown".
    text = re.sub(r"\b(\w+)- (\1\w+)\b", keep_second, text, flags=re.IGNORECASE)
    return text


_REPEAT_FUNC = r"(?:and|the|a|I|it|it's|we|you|to|of|but|they|there)"   # not "so so": real emphasis


def _collapse_function_repeats(text: str) -> str:
    """"and and the" → "and the". Function words only, so "had had" / "that that" survive."""
    return re.sub(rf"\b({_REPEAT_FUNC}) (\1)\b", r"\1", text, flags=re.IGNORECASE)


def _tidy(text: str) -> str:
    """Normalize cut-off dashes to em dashes, fix spacing, capitalize sentence starts."""
    startcap = text[:1].isupper()
    text = re.sub(r"([A-Za-z])- ", r"\1— ", text)   # "the- uh" leftovers → "the— " ("2- 3" untouched)
    text = re.sub(r"([A-Za-z])-$", r"\1—", text)
    text = re.sub(r"\s+([,.?!])", r"\1", text)
    text = re.sub(r"\s{2,}", " ", text).strip()
    text = re.sub(r"(?<![.])([.?!][\"”]?) ([a-z])", lambda m: m.group(1) + " " + m.group(2).upper(), text)
    if startcap and text[:1].islower():
        text = text[0].upper() + text[1:]
    return re.sub(r"^[-—,\s]+$", "", text)


def clean_text(text: str) -> str:
    """
    Intentionally light, lossy cleanup of a paragraph string:
    - Remove standalone filler words: um, uh, ah (with optional trailing comma)
    - Collapse hyphen cut-off stutters ("it- it is" → "it is") and comma stutters
      of function words ("and, and" → "and")
    - Collapse repeated consecutive words: "the the" → "the", "I I I" → "I"
    - Fix double spaces and spaces before punctuation
    - Strip whitespace and capitalize the first character

    NOTE: this is deliberately conservative but not perfect — the repeated-word
    collapse can flatten intentional emphasis ("very very") and filler removal
    runs before speaker attribution. It trades a little fidelity for readability;
    real STT artifacts (mangled proper nouns) are handled by the model in the
    skill workflow, not here.
    """
    text = _strip_fillers(text)
    text = _collapse_cutoffs(text)

    # Repeated consecutive words (handles 2–4 repetitions)
    text = re.sub(r"\b(\w+)( \1){1,3}\b", r"\1", text, flags=re.IGNORECASE)

    text = _tidy(text)
    if text:
        text = text[0].upper() + text[1:]
    return text


def process_srt(filepath: str, gap_ms: int = 1500) -> list[str]:
    """Full pipeline: parse → group → clean → return list of paragraph strings."""
    entries = parse_srt(filepath)
    raw_paragraphs = group_paragraphs(entries, gap_ms=gap_ms)
    return [clean_text(p) for p in raw_paragraphs]


# Words that are capitalized only because they start a sentence — ignore them as
# proper-noun candidates to cut noise.
_COMMON_SENTENCE_STARTERS = {
    "The", "A", "An", "And", "But", "So", "Or", "Yet", "If", "When", "While",
    "I", "We", "You", "They", "He", "She", "It", "This", "That", "These",
    "Those", "There", "Here", "Then", "Now", "Well", "Yeah", "Yes", "No",
    "Okay", "Right", "What", "Why", "How", "Who", "Where", "Which", "Because",
    "As", "At", "In", "On", "Of", "To", "For", "With", "Is", "Was", "Are",
    "Do", "Does", "Did", "Have", "Has", "Had", "Let", "Let's", "Also", "Just",
    "My", "Your", "Our", "Their", "His", "Her", "Its",
}

# A capitalized word, optionally possessive ('s) — Unicode-aware enough for
# common cases.
_CAP_WORD = r"[A-Z][a-zA-Z]+(?:'s)?"
_CAP_RUN = re.compile(rf"{_CAP_WORD}(?:\s+{_CAP_WORD})*")


def proper_noun_counts(paragraphs: list[str]) -> Counter:
    """
    Return a Counter of candidate proper nouns across all paragraphs.

    Counts both single capitalized words and multi-word capitalized runs
    (e.g. "Wang Huning"). Single words that are merely common sentence starters
    are dropped to reduce noise. Capitalization mid-sentence is the strongest
    signal, but we keep sentence-initial multi-word runs since those are usually
    real names.
    """
    counts: Counter = Counter()
    for para in paragraphs:
        for match in _CAP_RUN.finditer(para):
            phrase = match.group(0)
            words = phrase.split()
            if len(words) == 1:
                if phrase in _COMMON_SENTENCE_STARTERS:
                    continue
                counts[phrase] += 1
            else:
                counts[phrase] += 1
    return counts


# ---------------------------------------------------------------------------
# Diarized SRTs (cues that already carry speaker labels)
# ---------------------------------------------------------------------------
#
# Hard-won lessons from real diarized SRTs (see SKILL.md Step 1D):
#   * Labels can be CHUNK-LOCAL: "Speaker 1/2" in the first half and "Speaker 3/4"
#     in the second, with the people swapped. Map each label *range* to a name.
#   * Overlapped speech is chopped into alternating cues mid-sentence
#     ("I'll come back / I need / with some options"). The labels on those
#     fragments are almost always right; only the cue ORDER is wrong. Regrouping
#     each speaker's fragments fixes ~all of them. Genuinely mislabeled fragments
#     are rare and need a human — they are listed for review, never guessed.

Cue = namedtuple("Cue", "idx start end label text raw", defaults=(None,))
Frag = namedtuple("Frag", "idx speaker text")

# "Speaker 3:", ">> JOHN SMITH:", "HOST:" at the very start of a cue.
_LABEL_RE = re.compile(
    r"^(?:>>\s*)?(Speaker\s*\d+|[A-Z][A-Z0-9 .'\-]{0,24}?)\s*:\s*(.*)$", re.DOTALL
)
# Reactions that must never be read as the continuation of someone's sentence.
_BACKCHANNELS = {"yeah", "yes", "yep", "right", "sure", "okay", "ok", "mm", "mhm", "mm-hmm", "uh-huh",
                 "no", "indeed", "wow", "oh", "ah", "exactly", "interesting", "absolutely", "true",
                 "fair", "great", "good", "well", "alright", "totally", "correct"}
_BACKCHANNELS |= {"really", "seriously", "huh", "gosh", "whoa", "nope"}


def _is_fragment(text: str) -> bool:
    """An interjection fragment: one or two words, or a cue that stops mid-sentence."""
    return _word_count(text) <= 2 or _is_open(text) or bool(re.search(r"[-–—]$", text.strip()))


def _is_reaction_only(text: str) -> bool:
    """True for a cue made only of reaction words ("Yeah.", "No.", "Mm-hmm.")."""
    ws = re.findall(r"[\w'-]+", text.lower())
    return bool(ws) and all(w in _BACKCHANNELS for w in ws)


_TERMINAL_RE = re.compile(r"(?:[.?!…]+|[-–—]+)[\"')\]”’]*\s*$")


def _norm_label(label: str) -> str:
    """'Speaker 3' / 'speaker3' / '3' → '3'; other labels → lowercase."""
    label = label.strip().lstrip(">").strip()
    m = re.fullmatch(r"(?i)speaker\s*(\d+)", label)
    if m:
        return m.group(1)
    return label.lower()


def parse_labeled_cues(entries: list[tuple[int, int, int, str]], not_labels=()) -> list[Cue]:
    """
    Split a leading speaker label off every cue (label is '' when a cue has none).
    EVERY label-looking prefix is kept as a label — a rare one is never silently demoted
    to "unlabeled", because that would hand its text to the previous speaker. Labels in
    `not_labels` are the explicit escape hatch for stray text like "NOTE: read this":
    those cues keep their full text and no label. `Cue.raw` is the untouched cue text.
    """
    skip = {_norm_label(x) for x in not_labels}
    cues = []
    for idx, start, end, text in entries:
        m = _LABEL_RE.match(text)
        label = _norm_label(m.group(1)) if m else ""
        if m and label not in skip:
            cues.append(Cue(idx, start, end, label, m.group(2).strip(), text))
        else:
            cues.append(Cue(idx, start, end, "", text.strip(), text))
    return cues


def qualifying_labels(cues: list[Cue]) -> set[str]:
    """
    Labels that look like real speakers: "Speaker N" always; a name-style label (`A`,
    `JOHN`, `NOTE`) when it makes up at least 20% of the cues or appears 3+ times. Used
    to decide whether a file is diarized — NOT to drop labels (see parse_labeled_cues).
    """
    freq = Counter(c.label for c in cues if c.label)
    total = max(1, len(cues))
    return {lab for lab, n in freq.items() if lab.isdigit() or n >= 3 or n / total >= 0.2}


def is_diarized(cues: list[Cue], threshold: float = 0.7, max_labels: int = 12) -> bool:
    """
    True when cues carry a small set of speaker labels. Either most cues are labeled,
    or — for diarizers that label only the first cue of each turn — the first cue is
    labeled, at least two distinct speakers appear and a fifth of the cues are labeled.
    A name-style label alone ("NOTE:" on every cue) isn't enough: it needs two of them.
    """
    if not cues:
        return False
    q = qualifying_labels(cues)
    if not q or len(q) > max_labels:
        return False
    if len(q) < 2 and not any(lab.isdigit() for lab in q):
        return False
    labeled = [c for c in cues if c.label in q]
    frac = len(labeled) / len(cues)
    return frac >= threshold or (cues[0].label in q and len(q) >= 2 and frac >= 0.2)


def strip_speaker_labels(cues: list[Cue]) -> list[Cue]:
    """Plain-mode view of a diarized file: drop real speaker labels, keep stray label-like text."""
    q = qualifying_labels(cues)
    return [c if c.label in q else c._replace(text=(c.raw or c.text).strip(), label="") for c in cues]


def _fmt_ms(ms: int) -> str:
    s = ms // 1000
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def label_groups(cues: list[Cue]) -> list[dict]:
    """
    Group labels whose active cue ranges overlap. Disjoint groups mean the labels
    are chunk-local (e.g. {1,2} for cues 1-342, {3,4} for 343-676) and each group
    must be mapped separately.
    """
    spans: dict[str, list[int]] = {}
    q = qualifying_labels(cues)
    for c in cues:
        if not c.label or c.label not in q:
            continue
        sp = spans.setdefault(c.label, [c.idx, c.idx])
        sp[1] = c.idx
    groups: list[dict] = []
    for label, (lo, hi) in sorted(spans.items(), key=lambda kv: kv[1][0]):
        if groups and lo <= groups[-1]["hi"]:
            groups[-1]["labels"].append(label)
            groups[-1]["hi"] = max(groups[-1]["hi"], hi)
        else:
            groups.append({"labels": [label], "lo": lo, "hi": hi})
    return groups


_ANCHOR_RES = [
    re.compile(r"\b(?:I'm|I am|my name is|this is)\s+[A-Z][a-z]+"),
    re.compile(r"\b(?:thanks|thank you),?\s+[A-Z][a-z]+", re.IGNORECASE),
    re.compile(r"\bwelcome (?:back )?to\b", re.IGNORECASE),
    # Direct address at the start of a cue: "Bill, how are you?" (not "Well, what…").
    re.compile(r"^(?!(?:And|But|So|Well|Yeah|Right|Okay|Now|Look|Then|Because|Congress|Obviously|Again|Indeed)\b)"
               r"[A-Z][a-z]+, (?:how|what|do|did|is|are|can)\b"),
    re.compile(r"\b(?:and|with) (?:on the other line|joining me),? [A-Z][a-z]+"),
]


def anchor_cues(cues: list[Cue], limit: int = 14) -> list[Cue]:
    """Cues that usually name or address a speaker (intros, sign-offs, direct address)."""
    out = []
    for c in cues:
        if any(r.search(c.text) for r in _ANCHOR_RES):
            out.append(c)
    # Always include the first and last cue — intros and sign-offs live there.
    for edge in (cues[0], cues[-1]):
        if edge not in out:
            out.append(edge)
    out.sort(key=lambda c: c.idx)
    if len(out) > limit:  # keep head, tail and an even sample of the middle
        step = max(1, len(out) // limit)
        keep = {out[0].idx, out[-1].idx} | {o.idx for o in out[::step]}
        out = [o for o in out if o.idx in keep]
    return out


def speaker_report(cues: list[Cue]) -> str:
    """Human-readable speaker table, namespace warnings and anchor cues."""
    lines = ["LABEL   CUES  FIRST (cue @ time)     LAST (cue @ time)"]
    seen: dict[str, list[Cue]] = {}
    for c in cues:
        if c.label:
            seen.setdefault(c.label, []).append(c)
    for label, cs in sorted(seen.items(), key=lambda kv: kv[1][0].idx):
        lines.append(
            f"{label:<7} {len(cs):>4}  {cs[0].idx:>4} @ {_fmt_ms(cs[0].start)}        "
            f"{cs[-1].idx:>4} @ {_fmt_ms(cs[-1].start)}"
        )
    groups = label_groups(cues)
    rare = {lab: cs for lab, cs in seen.items() if lab not in qualifying_labels(cues)}
    if rare:
        lines.append("")
        lines.append("RARE LABELS (few cues — either real speakers or stray text such as a cue that starts 'NOTE:'):")
        for lab, cs in rare.items():
            lines.append(f"  {lab!r}: {len(cs)} cue(s), e.g. cue {cs[0].idx}: {cs[0].text[:60]!r}")
        lines.append("  Real speaker → give it a --map. Stray text → pass --not-label LABEL. "
                     "(Unmapped labels are an error, never silently merged into the previous speaker.)")
    lines.append("")
    if len(groups) > 1:
        lines.append(
            f"WARNING: {len(groups)} disjoint label groups — labels are CHUNK-LOCAL. "
            "The same person has a different label in each group; map each group "
            "separately (and check who is who in EACH group):"
        )
        for g in groups:
            lines.append(f"  cues {g['lo']}-{g['hi']}: labels {', '.join(g['labels'])}")
        lines.append("  e.g. --map 1=Andrew --map 2=Bill --map 3=Bill --map 4=Andrew")
    else:
        lines.append(f"One label group (cues {groups[0]['lo']}-{groups[0]['hi']}): "
                     f"labels {', '.join(groups[0]['labels'])}. If a label is reused for "
                     "different people, use --map LABEL=NAME@LO-HI.")
    lines.append("")
    lines.append("ANCHOR CUES (intros / sign-offs / direct address — use these to name each label):")
    for c in anchor_cues(cues):
        snippet = c.text if len(c.text) <= 110 else c.text[:107] + "..."
        lines.append(f"  cue {c.idx:>4} [{c.label or '-'}] {snippet}")
    return "\n".join(lines)


def parse_map_specs(specs: list[str]) -> list[tuple[str, str, int, int]]:
    """
    Parse --map values "LABEL=NAME" or "LABEL=NAME@LO-HI" (either bound may be
    empty: "@343-", "@-342") into (label, name, lo, hi) tuples.
    """
    out = []
    for spec in specs:
        m = re.fullmatch(r"\s*([^=@]+?)\s*=\s*([^@]+?)\s*(?:@\s*(\d*)\s*-\s*(\d*))?\s*", spec)
        if not m:
            raise ValueError(f"bad --map value {spec!r}; expected LABEL=NAME or LABEL=NAME@LO-HI")
        label, name, lo, hi = m.groups()
        out.append((_norm_label(label), name, int(lo) if lo else 0, int(hi) if hi else 10**9))
    return out


def apply_map(cues: list[Cue], maps: list[tuple[str, str, int, int]],
              inherit_unlabeled: bool = True) -> list[Frag]:
    """
    Name every cue's speaker. Unmapped labels are an error — never guessed.
    When --map entries overlap, the LAST one wins, so a broad default can be followed
    by a narrower override. Some diarizers label only the first cue of each turn; with
    inherit_unlabeled an unlabeled cue takes the previous cue's speaker (the first cue
    must be labeled). Use frag_notes(frags) afterwards to report how many were inherited.
    """
    frags, missing = [], {}
    prev_label = ""
    for c in cues:
        label = c.label or (prev_label if inherit_unlabeled else "")
        name = next((n for (l, n, lo, hi) in reversed(maps) if l == label and lo <= c.idx <= hi), None)
        if name is None:
            missing.setdefault(label or "(no label)", []).append(c.idx)
            continue
        if label:
            prev_label = label
        frags.append(Frag(c.idx, name, c.text))
    if missing:
        detail = "; ".join(f"{l!r}: cues {v[0]}-{v[-1]} ({len(v)})" for l, v in missing.items())
        raise ValueError(f"unmapped speaker labels → {detail}")
    return frags


def _is_open(text: str) -> bool:
    """True when a cue stops mid-sentence (no ./?/!/… and no cut-off dash)."""
    return not _TERMINAL_RE.search(text.strip())


def _word_count(text: str) -> int:
    return len(re.findall(r"[\w']+", text))


def _is_filler_only(text: str) -> bool:
    """A cue that is only a hesitation ("Um.", "Uh,", "-"). "Ah." / "Hmm." are reactions, kept."""
    letters = re.sub(r"[\W_]+", " ", text).strip().lower()
    return letters == "" or bool(re.fullmatch(r"(?:um+|uh+|er+)(?: (?:um+|uh+|er+))*", letters))


def _find_clusters(frags: list[Frag], max_dist: int = 4, max_between_words: int = 30) -> list[tuple[int, int]]:
    """
    Index ranges [lo, hi] of fragments that interleave.

    The reliable signature is a *resumption*: speaker X has a cue that stops
    mid-sentence, someone else says a short thing, then X continues with a cue that
    does not start with a capital letter, or is a one/two-word non-reaction cue
    ("...the famous" / "Steve" / "Jobs."). Everything from X's open cue to the resuming cue is one cluster.
    Two guards keep real turns apart: the interruption must be short
    (max_between_words) and recent (max_dist fragments). A cue that merely lacks
    final punctuation but is followed by a capitalized new sentence is a normal
    turn change, not interleaving.
    """
    spans: list[list[int]] = []
    pending: dict[str, int] = {}               # speaker → index of their latest open fragment
    for k, f in enumerate(frags):
        p = pending.get(f.speaker)
        words = re.findall(r"[\w'-]+", f.text.lower())
        lowercase_start = not f.text[:1].isupper()
        short_cap = 0 < len(words) <= 2 and words[0] not in _BACKCHANNELS
        if p is not None and p < k - 1 and k - p <= max_dist and (lowercase_start or short_cap):
            between = frags[p + 1:k]
            # A bare reaction ("No.") between a capitalized one-word cue and an unfinished one
            # means the speaker started a NEW utterance ("That's all" / "No." / "Go.").
            # Likewise a full sentence between ("What should we do next?") means a new utterance.
            new_utterance = not lowercase_start and any(
                _is_reaction_only(b.text) or not _is_fragment(b.text) for b in between)
            spoke_between = any(b.speaker == f.speaker for b in between)
            if not new_utterance and not spoke_between and \
                    sum(_word_count(b.text) for b in between) <= max_between_words:
                spans.append([p, k])
        if _is_open(f.text):
            pending[f.speaker] = k
        else:
            pending.pop(f.speaker, None)
    spans.sort()
    merged: list[list[int]] = []
    for lo, hi in spans:                        # union overlapping / touching spans
        if merged and lo <= merged[-1][1] + 1:
            merged[-1][1] = max(merged[-1][1], hi)
        else:
            merged.append([lo, hi])
    return [(lo, hi) for lo, hi in merged]


def _resolve_cluster(frags: list[Frag], lo: int, hi: int, short_words: int = 3) -> list[dict]:
    """
    Regroup one interleaved cluster into whole sentences per speaker and order the
    sentences by where each one finishes. A speaker's sentence that is still open
    at the end of the cluster goes last, so it joins that speaker's next cue.
    Very short interjections ("Yeah.") that land inside someone else's sentence are
    placed right after it. Returns [{"speaker","text","cues"}] in output order.
    """
    sents: list[dict] = []
    cur: dict[str, dict] = {}
    for k in range(lo, hi + 1):
        f = frags[k]
        s = cur.get(f.speaker)
        if s is None:
            s = cur[f.speaker] = {"speaker": f.speaker, "start": k, "end": k,
                                  "parts": [], "cues": [], "open": False}
        s["parts"].append(f.text)
        s["cues"].append(f.idx)
        s["end"] = k
        if not _is_open(f.text):
            sents.append(s)
            del cur[f.speaker]
    for s in cur.values():                       # still open when the cluster ends
        s["open"] = True
        sents.append(s)
    size = hi - lo + 1
    for s in sents:
        # Open sentences sort after every closed one; ties go to the later cue.
        s["pos"] = float(s["end"]) + ((size + s["end"] / 1000.0) if s["open"] else 0.0)
    for s in sents:                              # tuck short interjections after the sentence they interrupt
        if s["open"] or _word_count(" ".join(s["parts"])) > short_words:
            continue
        host = [t for t in sents if t["speaker"] != s["speaker"]
                and t["start"] < s["end"] and (t["open"] or t["end"] > s["end"])]
        if host:
            s["pos"] = min(t["pos"] for t in host) + 0.01
    # Invariant: regrouping may reorder sentences ACROSS speakers but must never reorder
    # one speaker's own sentences. `sents` holds each speaker's sentences in cue order,
    # so a running max per speaker keeps them monotonic.
    last_pos: dict[str, float] = {}
    for s in sents:
        s["pos"] = max(s["pos"], last_pos.get(s["speaker"], float("-inf")))
        last_pos[s["speaker"]] = s["pos"]
    sents.sort(key=lambda t: t["pos"])   # stable: ties keep closing (= cue) order
    return [{"speaker": t["speaker"], "text": " ".join(t["parts"]), "cues": t["cues"]} for t in sents]


def reassemble(frags: list[Frag]) -> tuple[list[dict], list[dict], list[int]]:
    """
    Fragments → turns. Returns (turns, clusters, dropped_cue_idxs).
      turns:    [{"speaker", "text", "cues"}], same-speaker neighbours merged
      clusters: [{"cues": [first_idx, last_idx], "before": [(idx, speaker, text)...],
                  "after": [(speaker, text)...]}] — every regrouped stretch, for review
      dropped:  cue indexes that were filler-only ("Um.") and removed
    """
    dropped = [f.idx for f in frags if _is_filler_only(f.text)]
    frags = [f for f in frags if not _is_filler_only(f.text)]
    starts = dict(_find_clusters(frags))

    pieces: list[dict] = []
    clusters: list[dict] = []
    k = 0
    while k < len(frags):
        if k in starts:
            hi = starts[k]
            sents = _resolve_cluster(frags, k, hi)
            clusters.append({
                "cues": [frags[k].idx, frags[hi].idx],
                "before": [(f.idx, f.speaker, f.text) for f in frags[k:hi + 1]],
                "after": [(s["speaker"], s["text"]) for s in sents],
            })
            pieces.extend(sents)
            k = hi + 1
        else:
            f = frags[k]
            pieces.append({"speaker": f.speaker, "text": f.text, "cues": [f.idx]})
            k += 1

    turns: list[dict] = []
    for p in pieces:
        if turns and turns[-1]["speaker"] == p["speaker"]:
            turns[-1]["text"] += " " + p["text"]
            turns[-1]["cues"] += p["cues"]
        else:
            turns.append({"speaker": p["speaker"], "text": p["text"], "cues": list(p["cues"])})
    return turns, clusters, dropped


def apply_fixes(text: str, fixes: list[tuple[str, str]]) -> str:
    """Literal old→new replacements (STT artifact fixes), applied in order."""
    for old, new in fixes:
        text = text.replace(old, new)
    return text


def parse_fix_specs(specs: list[str]) -> list[tuple[str, str]]:
    """Parse 'old => new' strings (from --fix or a --fixes-file line) into pairs."""
    out = []
    for spec in specs:
        if "=>" not in spec:
            raise ValueError(f"bad fix {spec!r}; expected 'old => new'")
        old, new = spec.split("=>", 1)
        if old.strip():
            out.append((old.strip(), new.strip()))
    return out


def build_labeled_turns(turns: list[dict], fixes: list[tuple[str, str]] | None = None,
                        emptied: list[int] | None = None) -> list[dict]:
    """
    Apply fixes (to the raw reassembled text, so they can match across cue
    boundaries), then disfluency cleanup. Turns that end up empty are dropped; their
    cue indexes are appended to `emptied` (when given) so callers can account for
    every cue. Same-speaker neighbours are re-merged.
    """
    out: list[dict] = []
    for t in turns:
        text = apply_fixes(t["text"], fixes or [])
        text = _tidy(_collapse_function_repeats(_collapse_cutoffs(_strip_fillers(text, _HESITATIONS))))
        if not text:
            if emptied is not None:
                emptied.extend(t["cues"])
            continue
        if out and out[-1]["speaker"] == t["speaker"]:
            out[-1]["text"] += " " + text          # keep the piece's own case when merging
            out[-1]["cues"] += t["cues"]
        else:
            out.append({"speaker": t["speaker"], "text": text[0].upper() + text[1:],
                        "cues": list(t["cues"]),
                        # began mid-sentence in the SRT: lowercase, or a digit right after an
                        # unfinished turn ("…they had" / "5 sources…"). A digit after a finished
                        # turn ("100%.") is a normal new turn.
                        "lower_start": t["text"][:1].islower() or (
                            t["text"][:1].isdigit() and bool(out) and _is_open(out[-1]["text"]))})
    return out


def review_flags(turns: list[dict]) -> list[str]:
    """
    Turns worth a human look: a turn whose raw SRT text began mid-sentence (lowercase
    or digit) is evidence of a continuation the regrouping did not catch — usually the
    tail of the previous turn, or a genuinely mislabeled fragment. (Turns that merely
    end without punctuation are normal interruptions and are NOT flagged.)
    """
    flags = []
    for i, t in enumerate(turns):
        if not t.get("lower_start"):
            continue
        prev = f" — previous turn [{turns[i - 1]['speaker']}] ends: …{turns[i - 1]['text'][-45:]!r}" if i else ""
        flags.append(f"cues {t['cues'][0]}-{t['cues'][-1]} [{t['speaker']}] begins mid-sentence: "
                     f"{t['text'][:55]!r}{prev}")
    return flags


def _run_diarized(args) -> int:
    entries = parse_srt(args.srt_file)
    cues = parse_labeled_cues(entries, args.not_label or ())
    if not is_diarized(cues):
        print("This SRT does not look diarized (most cues have no 'Speaker N:' / 'NAME:' prefix). "
              "Run without --diarized.", file=sys.stderr)
        return 2

    if not args.map:
        print(speaker_report(cues))
        return 0

    try:
        fixes = parse_fix_specs(args.fix or [])
        if args.fixes_file:
            with open(args.fixes_file, encoding="utf-8") as f:
                fixes += parse_fix_specs([ln for ln in f.read().splitlines()
                                          if ln.strip() and not ln.lstrip().startswith("#")])
        frags = apply_map(cues, parse_map_specs(args.map))
        inherited = sum(1 for c in cues if not c.label)
        if inherited:
            print(f"NOTE: {inherited} cue(s) had no speaker label and inherited the previous "
                  "cue's speaker (this SRT labels only some cues).", file=sys.stderr)
    except ValueError as e:
        hint = ("\n  Real speaker → add --map LABEL=NAME. Stray text that merely looks like a label "
                "(e.g. a cue starting 'NOTE:') → add --not-label LABEL.") if "unmapped" in str(e) else ""
        print(f"error: {e}{hint}", file=sys.stderr)
        return 2

    turns, clusters, dropped = reassemble(frags)
    emptied: list[int] = []
    final = build_labeled_turns(turns, fixes, emptied)

    # Coverage check, AFTER cleanup: every cue is in a final turn, was a filler-only cue,
    # or was emptied by cleanup — exactly once. (Not an assert: those vanish under -O.)
    used = [i for t in final for i in t["cues"]]
    expected = sorted(c.idx for c in cues)
    if sorted(used + dropped + emptied) != expected:
        lost = sorted(set(expected) - set(used) - set(dropped) - set(emptied))
        dupes = sorted({i for i in used if used.count(i) > 1})
        print(f"error: coverage check failed — lost cues {lost[:10]}, duplicated cues {dupes[:10]}",
              file=sys.stderr)
        return 3

    body = "\n\n".join(f"**{t['speaker']}:** {t['text']}" for t in final)
    print(body)
    if emptied:
        print(f"NOTE: cue(s) {emptied[:10]}{'…' if len(emptied) > 10 else ''} were empty after cleanup "
              "and dropped.", file=sys.stderr)

    words = sum(_word_count(t["text"]) for t in final)
    print(f"coverage OK: {len(expected)} cues -> {len(final)} turns, {words} words, "
          f"{len(dropped)} filler-only cues dropped, {len(clusters)} interleaved clusters regrouped",
          file=sys.stderr)
    by = {}
    for t in final:
        by[t["speaker"]] = by.get(t["speaker"], 0) + 1
    print("turns per speaker: " + ", ".join(f"{k}={v}" for k, v in by.items()), file=sys.stderr)

    flags = review_flags(final)
    if flags:
        print(f"\nREVIEW ({len(flags)} turns begin mid-sentence in the SRT — a missed continuation "
              "or a genuinely mislabeled fragment; only a human can tell):", file=sys.stderr)
        for fl in flags:
            print("  " + fl, file=sys.stderr)
    if args.review:
        print(f"\nREGROUPED CLUSTERS ({len(clusters)}) — confirm each reads right:", file=sys.stderr)
        for c in clusters:
            print(f"\n  cues {c['cues'][0]}-{c['cues'][1]}  BEFORE:", file=sys.stderr)
            for idx, spk, text in c["before"]:
                print(f"    {idx:>4} {spk[:1]}: {text[:100]}", file=sys.stderr)
            print("  AFTER:", file=sys.stderr)
            for spk, text in c["after"]:
                print(f"       {spk[:1]}: {text[:140]}", file=sys.stderr)
    return 0


def main():
    parser = argparse.ArgumentParser(description="Parse an SRT file into clean paragraphs.")
    parser.add_argument("srt_file", help="Path to the .srt transcript file")
    parser.add_argument(
        "--gap",
        type=int,
        default=1500,
        help="Silence gap in ms that triggers a paragraph break (default: 1500)",
    )
    parser.add_argument(
        "--proper-nouns",
        action="store_true",
        help="Instead of paragraphs, list candidate proper nouns with counts",
    )
    parser.add_argument(
        "--min-count",
        type=int,
        default=1,
        help="With --proper-nouns, only show terms appearing at least this often",
    )
    parser.add_argument(
        "--diarized",
        action="store_true",
        help="SRT cues already carry speaker labels. Alone: print the speaker table, "
             "label-namespace warnings and anchor cues. With --map: print the labeled transcript.",
    )
    parser.add_argument(
        "--map",
        action="append",
        metavar="LABEL=NAME[@LO-HI]",
        help="Name a speaker label (repeatable), e.g. --map 1=Andrew --map 2=Bill@1-342 "
             "--map 3=Bill --map 4=Andrew. @LO-HI limits the mapping to a cue range.",
    )
    parser.add_argument(
        "--not-label",
        action="append",
        metavar="LABEL",
        help="Treat cues starting 'LABEL:' as plain text, not a speaker (repeatable), "
             "e.g. --not-label note for a stray 'NOTE: …' cue",
    )
    parser.add_argument(
        "--fix",
        action="append",
        metavar="'old => new'",
        help="Literal STT-artifact fix (repeatable); applied to raw text before cleanup",
    )
    parser.add_argument(
        "--fixes-file",
        metavar="FILE",
        help="File with one 'old => new' per line ('#' comments allowed)",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="With --diarized --map: also print every regrouped cluster (before/after) to stderr",
    )
    args = parser.parse_args()

    if args.diarized:
        sys.exit(_run_diarized(args))

    entries = parse_srt(args.srt_file)
    if is_diarized(parse_labeled_cues(entries)):
        # Labels would run together inside paragraphs and pollute proper-noun counts.
        entries = [(c.idx, c.start, c.end, c.text) for c in strip_speaker_labels(parse_labeled_cues(entries))]
        print("NOTE: cues carry speaker labels, so they were stripped here. Use --diarized "
              "(SKILL.md Step 1D) to get a speaker-labeled transcript.", file=sys.stderr)
    paragraphs = [clean_text(p) for p in group_paragraphs(entries, gap_ms=args.gap)]

    if args.proper_nouns:
        counts = proper_noun_counts(paragraphs)
        rows = [(term, n) for term, n in counts.most_common() if n >= args.min_count]
        for term, n in rows:
            print(f"{n:>4}  {term}")
        print(f"\n{len(rows)} candidate proper nouns", file=sys.stderr)
        return

    for i, p in enumerate(paragraphs, 1):
        print(f"--- PARA {i} ---")
        print(p)
        print()

    print(f"Total paragraphs: {len(paragraphs)}", file=sys.stderr)


if __name__ == "__main__":
    main()
