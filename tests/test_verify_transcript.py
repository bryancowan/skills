#!/usr/bin/env python3
"""Tests for skills/podcast-transcript/scripts/verify_transcript.py.

Run from the repo root:  python3 -m unittest tests/test_verify_transcript.py
"""
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the bundled skill dir
ROOT = Path(__file__).resolve().parent.parent
HERE = str(ROOT / "skills" / "podcast-transcript" / "scripts")
sys.path.insert(0, HERE)
import verify_transcript as V  # noqa: E402

SRT = (
    "1\n00:00:01,000 --> 00:00:02,000\nSpeaker 1: Hello and welcome back to the show today.\n\n"
    "2\n00:00:03,000 --> 00:00:04,000\nSpeaker 2: Thanks for having me on again.\n\n"
    "3\n00:00:05,000 --> 00:00:06,000\nSpeaker 1: We will talk about chips and tariffs.\n\n"
    "4\n00:00:07,000 --> 00:00:08,000\nSpeaker 2: Sounds good, thanks everybody, see you next week.\n"
)
GOOD_BODY = (
    "**Andrew:** Hello and welcome back to the show today.\n\n"
    "**Bill:** Thanks for having me on again.\n\n"
    "**Andrew:** We will talk about chips and tariffs.\n\n"
    "**Bill:** Sounds good, thanks everybody, see you next week.\n"
)
FRONT = "---\ntitle: Test\n---\nSome intro.\n\n"


class Verify(unittest.TestCase):
    def run_verify(self, note, srt=SRT, speakers=("Andrew", "Bill"), forbid=()):
        with tempfile.TemporaryDirectory() as d:
            n = os.path.join(d, "note.md")
            s = os.path.join(d, "ep.srt")
            with open(n, "w", encoding="utf-8") as f:
                f.write(note)
            with open(s, "w", encoding="utf-8") as f:
                f.write(srt)
            return V.verify(n, s, list(speakers), list(forbid))

    def levels(self, results):
        return {msg: lv for lv, msg in results}

    def fails(self, results):
        return [m for lv, m in results if lv == "FAIL"]

    def test_good_note_has_no_failures(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY)
        self.assertEqual(self.fails(r), [])

    def test_missing_heading_fails(self):
        self.assertTrue(self.fails(self.run_verify(FRONT + GOOD_BODY)))

    def test_duplicate_heading_fails(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY + "\n## Transcript\n\n" + GOOD_BODY)
        self.assertTrue(any("exactly one" in m for m in self.fails(r)))

    def test_truncated_transcript_fails(self):
        truncated = GOOD_BODY.rsplit("\n\n", 1)[0] + "\n"
        r = self.run_verify(FRONT + "## Transcript\n\n" + truncated)
        self.assertTrue(any("does not end with the SRT's last words" in m for m in self.fails(r)))

    def test_raw_diarizer_label_fails(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY.replace("**Bill:**", "**Speaker 2:**", 1))
        self.assertTrue(any("raw" in m.lower() or "unexpected speaker" in m for m in self.fails(r)))

    def test_unexpected_speaker_name_fails(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY.replace("**Bill:**", "**Bob:**"))
        self.assertTrue(any("unexpected speaker" in m for m in self.fails(r)))

    def test_forbidden_artifact_fails(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY.replace("chips", "Namibia chips"), forbid=["Namibia"])
        self.assertTrue(any("forbidden term 'Namibia'" in m for m in self.fails(r)))

    def test_missing_middle_passage_is_caught(self):
        words = [f"word{i}" for i in range(400)]
        srt = "1\n00:00:01,000 --> 00:00:02,000\nSpeaker 1: " + " ".join(words) + " thanks everybody.\n"
        holed = " ".join(words[:120] + words[260:]) + " thanks everybody."
        r = self.run_verify(FRONT + "## Transcript\n\n**Andrew:** " + holed + "\n", srt=srt)
        self.assertTrue([m for lv, m in r if lv in ("WARN", "FAIL") and "5-word samples" in m],
                        "a deleted 140-word chunk in the middle should not pass silently")

    # ---- regressions from the independent review ----
    def srt_of(self, text):
        return "1\n00:00:01,000 --> 00:00:02,000\nSpeaker 1: " + text + "\n"

    def msgs(self, results, level):
        return [m for lv, m in results if lv == level]

    def test_frontmatter_terminator_after_transcript_does_not_count(self):
        note = "---\ntitle: X\n## Transcript\n\n**Andrew:** Hello world yes indeed.\n---\n"
        r = self.run_verify(note, srt=self.srt_of("Hello world yes indeed."))
        self.assertTrue(any("frontmatter" in m for m in self.msgs(r, "FAIL")))

    def test_malformed_line_inside_transcript_fails(self):
        note = FRONT + "## Transcript\n\nraw text inserted before any turn\n**Andrew:** Hello world yes indeed.\n"
        r = self.run_verify(note, srt=self.srt_of("Hello world yes indeed."))
        self.assertTrue(any("not '**Name:** text'" in m for m in self.msgs(r, "FAIL")))

    def test_trailing_non_turn_line_only_warns(self):
        note = FRONT + "## Transcript\n\n**Andrew:** Hello world yes indeed.\n\n---\n"
        r = self.run_verify(note, srt=self.srt_of("Hello world yes indeed."))
        self.assertEqual(self.msgs(r, "FAIL"), [])
        self.assertTrue(any("after the last turn" in m for m in self.msgs(r, "WARN")))

    def test_tail_must_be_the_actual_end_not_just_nearby(self):
        # transcript echoes the SRT's closing phrase but then keeps going
        srt = self.srt_of("alpha beta gamma delta epsilon zeta eta theta final words are heard now")
        note = FRONT + "## Transcript\n\n**Andrew:** alpha beta gamma delta epsilon zeta eta theta final words are heard now and then some extra trailing text here\n"
        r = self.run_verify(note, srt=srt)
        self.assertEqual(self.msgs(r, "FAIL"), [])
        self.assertTrue(any("appear near the end" in m for m in self.msgs(r, "WARN")))

    def test_shifted_opening_warns(self):
        words = [f"w{i}" for i in range(100)]
        moved = words[4:10] + words[:4] + words[10:]
        r = self.run_verify(FRONT + "## Transcript\n\n**Andrew:** " + " ".join(moved) + "\n", srt=self.srt_of(" ".join(words)))
        self.assertTrue(any("transcript starts" in m for m in self.msgs(r, "WARN")))

    def test_forbidden_terms_match_case_insensitively(self):
        r = self.run_verify(FRONT + "## Transcript\n\n" + GOOD_BODY.replace("chips", "namibia chips"), forbid=["Namibia"])
        self.assertTrue(any("forbidden term 'Namibia'" in m for m in self.msgs(r, "FAIL")))

    def test_srt_ending_in_a_hesitation_cue_does_not_fail_a_clean_transcript(self):
        srt = ("1\n00:00:01,000 --> 00:00:02,000\nSpeaker 1: Hello world everyone today.\n\n"
               "2\n00:00:03,000 --> 00:00:04,000\nSpeaker 2: Um.\n")
        r = self.run_verify(FRONT + "## Transcript\n\n**Andrew:** Hello world everyone today.\n", srt=srt)
        self.assertEqual(self.msgs(r, "FAIL"), [])

    def test_adjacent_same_speaker_warns(self):
        body = GOOD_BODY.replace("**Bill:** Thanks", "**Andrew:** Thanks")
        r = self.run_verify(FRONT + "## Transcript\n\n" + body)
        self.assertEqual(self.levels(r).get("2 adjacent same-speaker turns"), "WARN")

    def test_double_blank_line_before_heading_warns(self):
        r = self.run_verify("---\ntitle: T\n---\nIntro.\n\n\n## Transcript\n\n" + GOOD_BODY)
        self.assertEqual(self.levels(r).get("single blank line before '## Transcript'"), "WARN")

    def test_unclosed_frontmatter_fails(self):
        r = self.run_verify("---\ntitle: Test\nIntro.\n\n## Transcript\n\n" + GOOD_BODY)
        self.assertTrue(any("frontmatter" in m for m in self.fails(r)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
