#!/usr/bin/env python3
"""
verify_transcript.py — automated Step 6 checks for a finished '## Transcript'.

Usage:
    python verify_transcript.py NOTE.md --srt SRT_FILE [--speakers Andrew Bill]
                                [--forbid TERM ...] [--forbid-file FILE]

Checks (FAIL = exit 1, WARN = look at it, PASS = fine):
  * exactly one '## Transcript' heading, with a single blank line before it
  * every turn is '**Name:** text'; names match --speakers when given
  * no leftover raw diarizer labels ('Speaker 3:')
  * no forbidden terms (known STT artifacts, e.g. --forbid "Namibia" "Alice Wang")
  * the transcript really ends where the SRT ends (not truncated) and starts where it starts
  * word count is plausible against the SRT (light cleanup removes a few percent)
  * adjacent same-speaker turns (should be merged) and wildly unbalanced speakers
  * YAML frontmatter, if present, still closes

Only the standard library is used; run with `python3 -I`.
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import parse_srt as P  # noqa: E402

TURN_RE = re.compile(r"^\*\*([^*]+?):\*\* ?(.*)$")


def _norm_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", text.lower().replace("’", "'"))


def split_transcript(note_text: str) -> tuple[str, int]:
    """Return (text after the first '## Transcript' heading, count of such headings)."""
    headings = list(re.finditer(r"(?m)^## Transcript[ \t]*$", note_text))
    if not headings:
        return "", 0
    return note_text[headings[0].end():], len(headings)


def parse_turns(body: str) -> list[tuple[str, str, int]]:
    """[(speaker, text, line_no_in_body)] — continuation lines are joined to their turn."""
    turns: list[list] = []
    for n, line in enumerate(body.splitlines(), 1):
        m = TURN_RE.match(line)
        if m:
            turns.append([m.group(1).strip(), m.group(2).strip(), n])
        elif line.strip() and turns:
            turns[-1][1] += " " + line.strip()
    return [(s, t, n) for s, t, n in turns]


def srt_plain_text(srt_path: str) -> tuple[list[str], list[str]]:
    """(first/last cue words, all words) of the SRT with speaker labels stripped."""
    cues = P.strip_speaker_labels(P.parse_labeled_cues(P.parse_srt(srt_path)))
    # The transcript has hesitations (um/uh) removed, so compare against the SRT the same way.
    words_of = lambda t: [w for w in _norm_words(t) if w not in ("um", "uh")]  # noqa: E731
    texts = [c.text for c in cues if words_of(c.text)]
    allw = [w for t in texts for w in words_of(t)]
    return texts, allw


def ngram_coverage(srt_words: list[str], transcript_words: list[str], samples: int = 60, n: int = 5):
    """Sample evenly spaced n-grams from the SRT; count how many occur in the transcript."""
    if len(srt_words) < n + 1:
        return 0, 0
    have = {tuple(transcript_words[i:i + n]) for i in range(len(transcript_words) - n + 1)}
    step = max(1, (len(srt_words) - n) // samples)
    picks = [tuple(srt_words[i:i + n]) for i in range(0, len(srt_words) - n + 1, step)]
    return sum(1 for g in picks if g in have), len(picks)


def verify(note_path: str, srt_path: str | None, speakers: list[str] | None,
           forbid: list[str]) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    add = lambda level, msg: results.append((level, msg))  # noqa: E731

    with open(note_path, encoding="utf-8") as f:
        note = f.read()

    # frontmatter: the closing '---' must come before the transcript (a '---' after it doesn't count)
    if note.startswith("---\n"):
        first_heading = re.search(r"(?m)^## Transcript[ \t]*$", note)
        head_region = note[4:first_heading.start()] if first_heading else note[4:]
        add("PASS" if re.search(r"(?m)^---\s*$", head_region) else "FAIL", "YAML frontmatter closes before the transcript")

    body, n_headings = split_transcript(note)
    if n_headings != 1:
        add("FAIL", f"expected exactly one '## Transcript' heading, found {n_headings}")
        if n_headings == 0:
            return results
    else:
        add("PASS", "one '## Transcript' heading")
        idx = note.index("## Transcript")
        add("WARN" if note[max(0, idx - 3):idx] == "\n\n\n" else "PASS",
            "single blank line before '## Transcript'")

    turns = parse_turns(body)
    if not turns:
        add("FAIL", "no '**Name:** text' turns found after the heading")
        return results
    names = sorted({s for s, _, _ in turns})
    add("PASS", f"{len(turns)} turns, speakers: {', '.join(names)}")

    body_lines = body.splitlines()
    turn_line_nos = [n for n, ln in enumerate(body_lines, 1) if TURN_RE.match(ln)]
    last_turn = turn_line_nos[-1] if turn_line_nos else 0
    stray = [(n, ln) for n, ln in enumerate(body_lines, 1) if ln.strip() and not TURN_RE.match(ln)]
    inside = [(n, ln) for n, ln in stray if n < last_turn]
    after = [(n, ln) for n, ln in stray if n > last_turn]
    if inside:
        add("FAIL", f"{len(inside)} line(s) inside the transcript are not '**Name:** text' turns "
                    f"(first at body line {inside[0][0]}: {inside[0][1][:60]!r})")
    else:
        add("PASS", "every line inside the transcript is a '**Name:** text' turn")
    if after:
        add("WARN", f"{len(after)} non-turn line(s) after the last turn (first: {after[0][1][:60]!r})")

    if speakers:
        extra = [n for n in names if n not in speakers]
        add("FAIL" if extra else "PASS", f"speaker names match {speakers}" if not extra
            else f"unexpected speaker names: {extra}")

    raw = [ (s, n) for s, t, n in turns if re.fullmatch(r"(?i)speaker\s*\d+", s)] + \
          [("text", n) for s, t, n in turns if re.search(r"(?i)\bspeaker \d+:", t)]
    add("FAIL" if raw else "PASS", "no raw 'Speaker N' labels left" if not raw
        else f"raw diarizer labels left (body line {raw[0][1]})")

    for term in forbid:
        hits = [n for _, t, n in turns if term.lower() in t.lower()]
        add("FAIL" if hits else "PASS", f"forbidden term {term!r} (case-insensitive): " +
            (f"{len(hits)} turn(s), first at body line {hits[0]}" if hits else "absent"))

    adj = sum(1 for a, b in zip(turns, turns[1:]) if a[0] == b[0])
    add("WARN" if adj else "PASS", f"{adj} adjacent same-speaker turns" if adj else "no adjacent same-speaker turns")

    counts = {n: sum(1 for s, _, _ in turns if s == n) for n in names}
    if len(counts) >= 2:
        lo, hi = min(counts.values()), max(counts.values())
        add("WARN" if hi and lo / hi < 0.25 else "PASS", f"turns per speaker: {counts}")

    words = [w for _, t, _ in turns for w in _norm_words(t)]
    if srt_path:
        texts, srt_words = srt_plain_text(srt_path)
        if srt_words:
            ratio = len(words) / len(srt_words)
            add("PASS" if 0.75 <= ratio <= 1.03 else "WARN",
                f"word count {len(words)} vs SRT {len(srt_words)} (ratio {ratio:.2f}; cleanup normally keeps ~0.85-0.99)")
            hit, n = ngram_coverage(srt_words, words)
            frac = hit / n if n else 1.0
            add("PASS" if frac >= 0.85 else ("WARN" if frac >= 0.6 else "FAIL"),
                f"{hit}/{n} evenly spaced 5-word samples from the SRT appear in the transcript "
                f"({frac:.0%}; below ~85% suggests missing passages — artifact fixes explain a few)")
            tail = [w for w in _norm_words(texts[-1]) if w not in ("um", "uh")][-4:]
            head = [w for w in _norm_words(texts[0]) if w not in ("um", "uh")][:4]
            # Anchored: the transcript's own last/first words must match the SRT's. A match that
            # only appears somewhere nearby (e.g. an echoed phrase) does not count.
            if words[-len(tail):] == tail:
                add("PASS", f"transcript ends with the SRT's last words ({' '.join(tail)!r})")
            elif " ".join(tail) in " ".join(words[-40:]):
                add("WARN", f"SRT's last words {' '.join(tail)!r} appear near the end, but the transcript "
                            f"actually ends {' '.join(words[-4:])!r} (extra text after the real ending?)")
            else:
                add("FAIL", f"transcript does not end with the SRT's last words ({' '.join(tail)!r}); "
                            f"it ends {' '.join(words[-4:])!r} — truncated?")
            if words[:len(head)] == head:
                add("PASS", f"transcript starts with the SRT's first words ({' '.join(head)!r})")
            else:
                add("WARN", f"transcript starts {' '.join(words[:4])!r}, SRT starts {' '.join(head)!r} "
                            "(artifact fixes can explain this; otherwise the opening is missing or reordered)")
    return results


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify a finished '## Transcript' section.")
    ap.add_argument("note", help="the .md file containing '## Transcript'")
    ap.add_argument("--srt", help="source SRT (enables truncation / word-count checks)")
    ap.add_argument("--speakers", nargs="+", help="allowed speaker names")
    ap.add_argument("--forbid", nargs="+", default=[], help="terms that must not appear (STT artifacts)")
    ap.add_argument("--forbid-file", help="file with one forbidden term per line")
    args = ap.parse_args()

    forbid = list(args.forbid)
    if args.forbid_file:
        with open(args.forbid_file, encoding="utf-8") as f:
            forbid += [ln.rstrip("\n") for ln in f if ln.strip() and not ln.startswith("#")]

    results = verify(args.note, args.srt, args.speakers, forbid)
    for level, msg in results:
        print(f"{level:<4}  {msg}")
    fails = sum(1 for lv, _ in results if lv == "FAIL")
    warns = sum(1 for lv, _ in results if lv == "WARN")
    print(f"\n{fails} FAIL, {warns} WARN, {len(results) - fails - warns} PASS")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
