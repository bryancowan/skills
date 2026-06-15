#!/usr/bin/env python3
"""
parse_srt.py — SRT transcript parser for podcast-to-markdown workflow.

Usage:
    python parse_srt.py <file.srt> [--gap 1500]
    python parse_srt.py <file.srt> --proper-nouns [--min-count 1]

Default mode prints numbered, cleaned paragraphs to stdout separated by blank
lines. The --gap flag controls the silence threshold in milliseconds for
paragraph breaks.

--proper-nouns mode instead prints capitalized tokens and multi-word capitalized
runs with their frequency counts. Use it to spot proper nouns (people, places,
brands) that the speech-to-text engine may have mangled the same way repeatedly
across the episode.

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
from collections import Counter


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


def clean_text(text: str) -> str:
    """
    Intentionally light, lossy cleanup of a paragraph string:
    - Remove standalone filler words: um, uh, ah (with optional trailing comma)
    - Collapse repeated consecutive words: "the the" → "the", "I I I" → "I"
    - Fix double spaces and spaces before punctuation
    - Strip whitespace and capitalize the first character

    NOTE: this is deliberately conservative but not perfect — the repeated-word
    collapse can flatten intentional emphasis ("very very") and filler removal
    runs before speaker attribution. It trades a little fidelity for readability;
    real STT artifacts (mangled proper nouns) are handled by the model in the
    skill workflow, not here.
    """
    # Standalone fillers (word boundary, optional trailing comma+space)
    for filler in ("um", "uh", "ah"):
        text = re.sub(rf"\b{filler}\b,?\s*", "", text, flags=re.IGNORECASE)

    # Repeated consecutive words (handles 2–4 repetitions)
    text = re.sub(r"\b(\w+)( \1){1,3}\b", r"\1", text, flags=re.IGNORECASE)

    # Collapse multiple spaces
    text = re.sub(r"  +", " ", text)

    # Fix space before punctuation
    text = re.sub(r" ([,\.!\?])", r"\1", text)

    text = text.strip()
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
    args = parser.parse_args()

    paragraphs = process_srt(args.srt_file, gap_ms=args.gap)

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
