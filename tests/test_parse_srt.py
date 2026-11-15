#!/usr/bin/env python3
"""
Tests for skills/podcast-transcript/scripts/parse_srt.py (diarized-SRT handling + cleanup).

Run from the repo root:  python3 -m unittest tests/test_parse_srt.py

Fixtures are synthetic but copy the failure patterns seen in a real diarized
episode: chunk-local labels, overlapped speech chopped into alternating cues, and
cues that merely lack final punctuation (which must NOT be treated as interleaving).
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the bundled skill dir
ROOT = Path(__file__).resolve().parent.parent
HERE = str(ROOT / "skills" / "podcast-transcript" / "scripts")
sys.path.insert(0, HERE)
import parse_srt as P  # noqa: E402


def make_srt(rows):
    """rows: [(label_text, text)] → SRT string with 1s cues."""
    blocks = []
    for i, (label, text) in enumerate(rows, 1):
        t0, t1 = i * 2, i * 2 + 1
        blocks.append(f"{i}\n00:00:{t0:02d},000 --> 00:00:{t1:02d},000\n{label}: {text}\n")
    return "\n".join(blocks)


def frags_from(rows):
    """rows: [(speaker_name, text)] → Frag list with idx 1..n."""
    return [P.Frag(i, spk, txt) for i, (spk, txt) in enumerate(rows, 1)]


def turns_of(rows):
    turns, clusters, dropped = P.reassemble(frags_from(rows))
    return [(t["speaker"], t["text"]) for t in turns], clusters, dropped


class LabelParsing(unittest.TestCase):
    def entries(self, rows):
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(make_srt(rows))
        self.addCleanup(os.unlink, f.name)
        return P.parse_srt(f.name)

    def test_speaker_labels_detected_and_normalized(self):
        cues = P.parse_labeled_cues(self.entries([("Speaker 1", "Hello there."), ("Speaker 2", "Hi.")]))
        self.assertEqual([c.label for c in cues], ["1", "2"])
        self.assertEqual(cues[0].text, "Hello there.")
        self.assertTrue(P.is_diarized(cues))

    def test_name_labels(self):
        rows = [(">> JOHN SMITH", "Hello."), ("MARY", "Hi."), (">> JOHN SMITH", "Well."),
                ("MARY", "Yes."), (">> JOHN SMITH", "Ok."), ("MARY", "Bye.")]
        cues = P.parse_labeled_cues(self.entries(rows))
        self.assertEqual([c.label for c in cues][:2], ["john smith", "mary"])

    def test_unlabeled_is_not_diarized(self):
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write("1\n00:00:01,000 --> 00:00:02,000\nJust some words.\n\n"
                    "2\n00:00:03,000 --> 00:00:04,000\nMore words here.\n")
        self.addCleanup(os.unlink, f.name)
        self.assertFalse(P.is_diarized(P.parse_labeled_cues(P.parse_srt(f.name))))

    def test_chunk_local_labels_make_disjoint_groups(self):
        rows = [("Speaker 1", "a."), ("Speaker 2", "b."), ("Speaker 1", "c."), ("Speaker 2", "d."),
                ("Speaker 3", "e."), ("Speaker 4", "f."), ("Speaker 3", "g.")]
        groups = P.label_groups(P.parse_labeled_cues(self.entries(rows)))
        self.assertEqual([g["labels"] for g in groups], [["1", "2"], ["3", "4"]])
        self.assertIn("CHUNK-LOCAL", P.speaker_report(P.parse_labeled_cues(self.entries(rows))))


class LabelRobustness(unittest.TestCase):
    """Regressions from the independent review."""
    def parse(self, texts):
        return P.parse_labeled_cues([(i, 0, 0, t) for i, t in enumerate(texts, 1)])

    def test_stray_label_like_cue_is_kept_as_a_label_but_does_not_qualify(self):
        # Never silently demote a rare label to "unlabeled": that hands its text to the PREVIOUS speaker.
        texts = [f"Speaker {1 + i % 2}: Line {i}." for i in range(20)]
        texts[7] = "NOTE: Read the next point."      # 1 stray cue in 20 (a real episode has hundreds)
        cues = self.parse(texts)
        self.assertEqual(cues[7].label, "note")
        self.assertNotIn("note", P.qualifying_labels(cues))
        with self.assertRaises(ValueError) as cm:
            P.apply_map(cues, P.parse_map_specs(["1=Andrew", "2=Bill"]))
        self.assertIn("'note'", str(cm.exception))

    def test_not_label_is_the_explicit_escape_hatch(self):
        entries = [(1, 0, 0, "Speaker 1: Hello."), (2, 0, 0, "NOTE: Read the next point."), (3, 0, 0, "Speaker 2: Hi.")]
        cues = P.parse_labeled_cues(entries, not_labels=["note"])
        self.assertEqual((cues[1].label, cues[1].text), ("", "NOTE: Read the next point."))

    def test_name_style_label_alone_does_not_make_a_file_diarized(self):
        self.assertFalse(P.is_diarized(self.parse(["NOTE: One.", "NOTE: Two.", "NOTE: Three."])))

    def test_short_real_diarized_file_is_detected(self):
        self.assertTrue(P.is_diarized(self.parse(["A: Yes.", "B: No.", "A: Maybe.", "B: Next."])))

    def test_single_letter_labels_work_when_repeated(self):
        cues = self.parse(["A: One.", "B: Two.", "A: Three.", "B: Four.", "A: Five.", "B: Six."])
        self.assertEqual([c.label for c in cues], ["a", "b", "a", "b", "a", "b"])

    def test_single_letter_stray_is_not_a_qualifying_label(self):
        texts = ["A: This is normal text."] + [f"Plain cue number {i}." for i in range(11)]
        self.assertEqual(P.qualifying_labels(self.parse(texts)), set())

    def test_turn_start_only_labeling_is_still_diarized(self):
        # Diarizers that label only the first cue of each turn fall below the 70% threshold.
        cues = self.parse(["Speaker 1: Hello.", "continues.", "Speaker 2: Hi."])
        self.assertTrue(P.is_diarized(cues))
        frags = P.apply_map(cues, P.parse_map_specs(["1=Andrew", "2=Bill"]))
        self.assertEqual([f.speaker for f in frags], ["Andrew", "Andrew", "Bill"])

    def test_single_speaker_low_label_rate_is_not_diarized(self):
        self.assertFalse(P.is_diarized(self.parse(["Speaker 1: Hi.", "more.", "more.", "more.", "more."])))


class PrReviewRegressions(unittest.TestCase):
    """Findings from the review of the PR itself."""
    def parse(self, texts):
        return P.parse_labeled_cues([(i, 0, 0, t) for i, t in enumerate(texts, 1)])

    def test_many_speaker_labels_are_not_capped(self):
        # a multi-chunk episode can legitimately have 13+ "Speaker N" labels (2 fresh ones per chunk)
        texts = [f"Speaker {n}: Line {n} a." for n in range(1, 14)] + [f"Speaker {n}: Line {n} b." for n in range(1, 14)]
        self.assertTrue(P.is_diarized(self.parse(texts)))

    def test_many_name_style_labels_are_still_not_diarized(self):
        names = [chr(65 + i) * 3 for i in range(13)]            # AAA, BBB, ... 13 distinct name labels
        texts = [f"{n}: line {i}." for _ in range(3) for i, n in enumerate(names)]
        self.assertFalse(P.is_diarized(self.parse(texts)))

    def test_accented_all_caps_name_labels_are_recognized(self):
        texts = ["ÉLODIE: Bonjour.", "JOSÉ: Hola.", "ÉLODIE: Encore.", "JOSÉ: Adiós."]
        cues = self.parse(texts)
        self.assertEqual([c.label for c in cues], ["élodie", "josé", "élodie", "josé"])
        self.assertTrue(P.is_diarized(cues))

    def test_ordinary_sentences_with_a_colon_are_not_labels(self):
        for text in ("Politico writes: unlike many peers, Nvidia lacks it.", "Here is the thing: it works.",
                     "Note: this is mixed case.", "Q&A: how it went."):
            self.assertEqual(self.parse([text])[0].label, "", text)

    def test_unlabeled_opening_cue_is_still_detected_and_needs_first_speaker(self):
        texts = ["intro words before any label", "Speaker 1: Hello.", "continues.", "Speaker 2: Hi.", "more.",
                 "Speaker 1: Sure."]
        cues = self.parse(texts)
        self.assertTrue(P.is_diarized(cues))
        maps = P.parse_map_specs(["1=Andrew", "2=Bill"])
        with self.assertRaises(ValueError) as cm:
            P.apply_map(cues, maps)
        self.assertIn("(no label)", str(cm.exception))
        frags = P.apply_map(cues, maps, first_speaker="Bill")
        self.assertEqual([f.speaker for f in frags], ["Bill", "Andrew", "Andrew", "Bill", "Bill", "Andrew"])

    def test_cli_first_speaker_flag_and_its_hint(self):
        rows = [("Speaker 1", "Hello."), ("Speaker 2", "Hi."), ("Speaker 1", "Sure."), ("Speaker 2", "Ok.")]
        srt = "\n".join(f"{i}\n00:00:{i*2:02d},000 --> 00:00:{i*2+1:02d},000\n{lab}: {txt}\n"
                        for i, (lab, txt) in enumerate(rows, 1))
        srt = "0\n00:00:00,000 --> 00:00:01,000\nWelcome everyone.\n\n" + srt
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(srt)
        self.addCleanup(os.unlink, f.name)
        base = [sys.executable, "-I", os.path.join(HERE, "parse_srt.py"), f.name, "--diarized",
                "--map", "1=Andrew", "--map", "2=Bill"]
        bad = subprocess.run(base, capture_output=True, text=True)
        self.assertEqual(bad.returncode, 2, bad.stdout)
        self.assertIn("--first-speaker", bad.stderr)
        good = subprocess.run(base + ["--first-speaker", "Bill"], capture_output=True, text=True)
        self.assertEqual(good.returncode, 0, good.stderr)
        self.assertIn("Welcome everyone.", good.stdout)


class Mapping(unittest.TestCase):
    def test_map_specs_with_ranges(self):
        self.assertEqual(P.parse_map_specs(["1=Andrew", "2=Bill@1-342", "3=Bill@343-"]),
                         [("1", "Andrew", 0, 10**9), ("2", "Bill", 1, 342), ("3", "Bill", 343, 10**9)])

    def test_bad_map_spec(self):
        with self.assertRaises(ValueError):
            P.parse_map_specs(["nonsense"])

    def test_same_label_reused_with_ranges(self):
        cues = [P.Cue(1, 0, 0, "1", "x."), P.Cue(5, 0, 0, "1", "y.")]
        frags = P.apply_map(cues, P.parse_map_specs(["1=Andrew@1-3", "1=Bill@4-"]))
        self.assertEqual([f.speaker for f in frags], ["Andrew", "Bill"])

    def test_unmapped_label_is_an_error_not_a_guess(self):
        with self.assertRaises(ValueError) as cm:
            P.apply_map([P.Cue(1, 0, 0, "1", "x."), P.Cue(2, 0, 0, "9", "y.")], P.parse_map_specs(["1=Andrew"]))
        self.assertIn("'9'", str(cm.exception))


class MappingRobustness(unittest.TestCase):
    def test_last_map_wins_on_overlap(self):
        cues = [P.Cue(1, 0, 0, "1", "x."), P.Cue(5, 0, 0, "1", "y.")]
        frags = P.apply_map(cues, P.parse_map_specs(["1=Andrew", "1=Bill@4-"]))
        self.assertEqual([f.speaker for f in frags], ["Andrew", "Bill"])

    def test_unlabeled_cue_inherits_previous_speaker(self):
        cues = [P.Cue(1, 0, 0, "1", "Hello there,"), P.Cue(2, 0, 0, "", "and welcome."), P.Cue(3, 0, 0, "2", "Hi.")]
        frags = P.apply_map(cues, P.parse_map_specs(["1=Andrew", "2=Bill"]))
        self.assertEqual([f.speaker for f in frags], ["Andrew", "Andrew", "Bill"])

    def test_first_cue_must_be_labeled(self):
        with self.assertRaises(ValueError):
            P.apply_map([P.Cue(1, 0, 0, "", "orphan.")], P.parse_map_specs(["1=Andrew"]))


class Reassembly(unittest.TestCase):
    def test_interrupted_sentence_is_regrouped(self):
        # "...and now [Bill: And that] here we are."  /  Bill's open sentence continues next cue
        rows = [("A", "Indeed, and then the journals on the board activity, and now"),
                ("B", "And that"),
                ("A", "here we are."),
                ("B", "Nvidia used corporate resources to cover it up, which is-")]
        turns, clusters, _ = turns_of(rows)
        self.assertEqual(turns, [("A", "Indeed, and then the journals on the board activity, and now here we are."),
                                 ("B", "And that Nvidia used corporate resources to cover it up, which is-")])
        self.assertEqual(len(clusters), 1)

    def test_missing_period_is_not_interleaving(self):
        # Cue 1 has no final punctuation but is a complete utterance; the reply is a new capitalized sentence.
        rows = [("B", "It's a cover-up, which is-"),
                ("A", "Oh, I didn't catch that detail in the Times"),
                ("B", "At the end of the article they said a bystander filmed them.")]
        turns, clusters, _ = turns_of(rows)
        self.assertEqual([t[0] for t in turns], ["B", "A", "B"])
        self.assertEqual(clusters, [])

    def test_names_split_across_speakers(self):
        rows = [("A", "He's skating to where the puck is going to be, to use the famous"),
                ("B", "Or-"),
                ("A", "Steve"),
                ("B", "or"),
                ("A", "Jobs."),
                ("B", "No, that was Wayne Gretzky.")]
        turns, _, _ = turns_of(rows)
        self.assertEqual(turns[0], ("A", "He's skating to where the puck is going to be, to use the famous Steve Jobs."))

    def test_backchannel_goes_after_the_sentence_it_interrupts(self):
        rows = [("B", "And we"), ("A", "Yeah."), ("B", "on our podcast, we said we hope he stays.")]
        turns, _, _ = turns_of(rows)
        self.assertEqual(turns, [("B", "And we on our podcast, we said we hope he stays."), ("A", "Yeah.")])

    def test_backchannel_not_treated_as_continuation(self):
        # "Yeah." after an open cue is a reaction, not the rest of A's sentence.
        rows = [("A", "I think the real issue is that the board"),
                ("B", "Right, and they know it."),
                ("A", "Yeah."),
                ("B", "So that's where we are.")]
        turns, clusters, _ = turns_of(rows)
        self.assertEqual(clusters, [])
        self.assertEqual([t[0] for t in turns], ["A", "B", "A", "B"])

    def test_long_reply_is_not_pulled_into_a_sentence(self):
        long_reply = " ".join(["word"] * 40) + "."
        rows = [("A", "We should talk about the"), ("B", long_reply), ("A", "legislation next.")]
        _, clusters, _ = turns_of(rows)
        self.assertEqual(clusters, [])

    def test_filler_only_cue_dropped_but_ah_kept(self):
        turns, _, dropped = turns_of([("A", "Hello."), ("B", "Um."), ("B", "Ah."), ("A", "Right.")])
        self.assertEqual(dropped, [2])
        self.assertIn(("B", "Ah."), turns)

    def test_every_cue_used_exactly_once(self):
        rows = [("A", "Indeed, and now"), ("B", "And that"), ("A", "here we are."), ("B", "Nvidia did it."),
                ("A", "Um."), ("A", "Okay.")]
        turns, _, dropped = P.reassemble(frags_from(rows))
        used = [i for t in turns for i in t["cues"]]
        self.assertEqual(sorted(used + dropped), list(range(1, len(rows) + 1)))
        self.assertEqual(len(used), len(set(used)))


class Invariants(unittest.TestCase):
    def test_fuzz_never_loses_cues_or_reorders_a_speakers_words(self):
        import random
        words = "the deal chip we they and but so Nvidia China Trump said that is not very okay right".split()
        ends = [".", "?", "!", "-", ",", "", "", ""]
        for seed in range(1500):
            rng = random.Random(seed)
            n, spk, frags = rng.randint(2, 40), rng.choice("AB"), []
            for i in range(1, n + 1):
                if rng.random() < 0.8:
                    spk = "B" if spk == "A" else "A"
                ws = [rng.choice(words) for _ in range(rng.choice([1, 1, 2, 3, 5, 9, 14]))]
                if rng.random() < 0.5:
                    ws[0] = ws[0].capitalize()
                frags.append(P.Frag(i, spk, " ".join(ws) + rng.choice(ends)))
            turns, _, dropped = P.reassemble(frags)
            used = [i for t in turns for i in t["cues"]]
            self.assertEqual(sorted(used + dropped), list(range(1, n + 1)), f"seed {seed}: cues lost/duplicated")
            for who in "AB":
                ids = [i for t in turns if t["speaker"] == who for i in t["cues"]]
                self.assertEqual(ids, sorted(ids), f"seed {seed}: speaker {who}'s own words were reordered")


class ReviewRegressions(unittest.TestCase):
    def build(self, text, fixes=None, emptied=None):
        out = P.build_labeled_turns([{"speaker": "A", "text": text, "cues": [1]}], fixes, emptied)
        return out[0]["text"] if out else ""

    def test_lone_ah_reaction_survives_cleanup(self):
        # High: "Ah." was kept by the filler-only check, then emptied by cleanup — silently lost.
        self.assertEqual(self.build("Ah."), "Ah.")
        self.assertEqual(self.build("I said ah! not now."), "I said ah! Not now.")

    def test_hesitation_only_turn_is_reported_not_lost(self):
        emptied = []
        self.assertEqual(self.build("Um, uh.", emptied=emptied), "")
        self.assertEqual(emptied, [1])

    def test_fillers_do_not_mangle_hyphenated_words_or_urls(self):
        self.assertEqual(self.build("Uh-huh, I agree."), "Uh-huh, I agree.")
        self.assertEqual(self.build("An uh-oh moment."), "An uh-oh moment.")
        self.assertEqual(self.build("See https://example.com/uh/page now."), "See https://example.com/uh/page now.")
        self.assertEqual(self.build("Uh- I think so."), "I think so.")

    def test_spaced_numeric_range_is_untouched(self):
        self.assertEqual(self.build("The cost is 2- 3 dollars."), "The cost is 2- 3 dollars.")

    def test_digit_start_flagged_only_after_an_unfinished_turn(self):
        def flag(prev_text):
            turns = P.build_labeled_turns([{"speaker": "B", "text": prev_text, "cues": [1]},
                                           {"speaker": "A", "text": "5 sources from the company.", "cues": [2]}])
            return turns[1]["lower_start"]
        self.assertTrue(flag("And they had"))          # continuation of an unfinished turn
        self.assertFalse(flag("That was the point."))  # normal new turn ("100%." style)

    def test_reaction_between_means_new_utterance_not_resumption(self):
        # Medium: "That's all" / "No." / "Go." must not become "That's all Go."
        for rows in ([("A", "That's all"), ("B", "No."), ("A", "Go.")],
                     [("A", "That's all"), ("B", "Really?"), ("A", "Go.")]):
            turns, clusters, _ = turns_of(rows)
            self.assertEqual(clusters, [], rows)
            self.assertEqual([t[0] for t in turns], ["A", "B", "A"], rows)

    def test_lowercase_reaction_is_not_a_continuation_either(self):
        # CodeRabbit: "yeah." must not become "I think the board yeah." with B moved first
        turns, clusters, _ = turns_of([("A", "I think the board"), ("B", "Right, and they know it."), ("A", "yeah.")])
        self.assertEqual(clusters, [])
        self.assertEqual([t[0] for t in turns], ["A", "B", "A"])

    def test_lowercase_resumption_still_regroups_across_a_reaction(self):
        turns, clusters, _ = turns_of([("A", "We should"), ("B", "No."), ("A", "go now.")])
        self.assertEqual(turns[0], ("A", "We should go now."))
        self.assertEqual(len(clusters), 1)

    def test_full_sentence_between_is_a_new_utterance_not_an_interruption(self):
        turns, clusters, _ = turns_of([("A", "I can handle that"), ("B", "What should we do next?"), ("A", "Go.")])
        self.assertEqual(clusters, [])
        self.assertEqual([t[0] for t in turns], ["A", "B", "A"])

    def test_fragment_interruption_still_regroups(self):
        turns, clusters, _ = turns_of([("A", "to use the famous"), ("B", "Or-"), ("A", "Steve"), ("B", "or"), ("A", "Jobs.")])
        self.assertEqual(turns[0], ("A", "to use the famous Steve Jobs."))

    def test_cleanup_does_not_eat_legitimate_speech(self):
        self.assertEqual(self.build("So so good."), "So so good.")
        self.assertEqual(self.build('I said "so so" on air.'), 'I said "so so" on air.')
        self.assertEqual(self.build("I said uh. Then left."), "I said. Then left.")
        self.assertEqual(self.build("It was (uh) unusual."), "It was unusual.")
        self.assertEqual(self.build("Uh— I think so."), "I think so.")
        self.assertEqual(self.build("Um. So we start."), "So we start.")

    def test_cli_keeps_ah_and_accounts_for_every_cue(self):
        r = CliRoundTrip.run_cli_static([("Speaker 1", "Hello."), ("Speaker 2", "Ah.")],
                                        "--diarized", "--map", "1=Andrew", "--map", "2=Bill")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Bill:** Ah.", r.stdout)


class Cleanup(unittest.TestCase):
    def build(self, text, fixes=None):
        out = P.build_labeled_turns([{"speaker": "A", "text": text, "cues": [1]}], fixes)
        return out[0]["text"] if out else ""

    def test_hyphen_cutoff_stutters(self):
        self.assertEqual(self.build("It- it is just a bombshell. I- I- I think so."),
                         "It is just a bombshell. I think so.")

    def test_stutter_keeps_the_speakers_case(self):
        self.assertEqual(self.build("And it- It- it is true."), "And it is true.")

    def test_partial_word_then_full_word(self):
        self.assertEqual(self.build("They have now show- shown weakness."), "They have now shown weakness.")

    def test_function_word_repeats_but_not_legit_doubles(self):
        self.assertEqual(self.build("And and the plan, they had had enough."), "And the plan, they had had enough.")

    def test_fillers_and_dash_normalization(self):
        self.assertEqual(self.build("Um, so, uh, the- the deal fell through-"), "So, the deal fell through—")

    def test_fixes_apply_before_cleanup_and_across_cues(self):
        self.assertEqual(self.build("protect Namibia's interests and Alice Wang", [("Namibia's", "Nvidia's"), ("Alice Wang", "Alice Huang")]),
                         "Protect Nvidia's interests and Alice Huang")

    def test_legacy_clean_text_still_works(self):
        self.assertEqual(P.clean_text("the the cat uh sat"), "The cat sat")
        self.assertEqual(P.clean_text("It- it is a deal."), "It is a deal.")


class ReviewFlags(unittest.TestCase):
    def flags(self, rows):
        turns, _, _ = P.reassemble(frags_from(rows))
        return P.review_flags(P.build_labeled_turns(turns))

    def test_plain_interruption_is_not_flagged(self):
        # first cue lacks a final period but the reply is a normal capitalized turn
        self.assertEqual(self.flags([("A", "Oh, I didn't catch that detail in the Times"),
                                     ("B", "At the end of the article they said so.")]), [])

    def test_turn_that_begins_mid_sentence_is_flagged(self):
        # a lowercase continuation far from its open cue is not regrouped, so it must be flagged
        rows = [("A", "We should really talk about the"),
                ("B", "Right, I agree with that point entirely and I would add much more to it than that."),
                ("A", "Yeah."),
                ("B", "So that is the plan."),
                ("A", "and then the legislation after that.")]
        flags = self.flags(rows)
        self.assertEqual(len(flags), 1)
        self.assertIn("begins mid-sentence", flags[0])


class CliRoundTrip(unittest.TestCase):
    @staticmethod
    def run_cli_static(rows, *args):
        with tempfile.NamedTemporaryFile("w", suffix=".srt", delete=False, encoding="utf-8") as f:
            f.write(make_srt(rows))
        try:
            return subprocess.run([sys.executable, "-I", os.path.join(HERE, "parse_srt.py"), f.name, *args],
                                  capture_output=True, text=True)
        finally:
            os.unlink(f.name)

    def run_cli(self, rows, *args):
        return self.run_cli_static(rows, *args)

    ROWS = [("Speaker 1", "Welcome to the show."), ("Speaker 2", "Thanks for having me."),
            ("Speaker 3", "Back again."), ("Speaker 4", "Good to see you.")]

    RARE = [("Speaker 1", f"Line {i}.") for i in range(1, 4)] + [("BOB", "No, I disagree.")] + \
           [("Speaker 1", f"More {i}.") for i in range(1, 4)]

    def test_rare_real_speaker_fails_loudly_not_silently_inherited(self):
        r = self.run_cli(self.RARE, "--diarized", "--map", "1=Alice")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("unmapped speaker labels", r.stderr)
        self.assertIn("--not-label", r.stderr)          # the hint tells you both ways out

    def test_rare_real_speaker_can_be_mapped(self):
        r = self.run_cli(self.RARE, "--diarized", "--map", "1=Alice", "--map", "bob=Bob")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Bob:** No, I disagree.", r.stdout)

    def test_stray_label_text_can_be_kept_with_not_label(self):
        rows = [("Speaker 1", "Hello."), ("Speaker 2", "Hi."), ("NOTE", "Read this."), ("Speaker 1", "Sure."),
                ("Speaker 2", "Ok."), ("Speaker 1", "Bye.")]
        r = self.run_cli(rows, "--diarized", "--map", "1=Andrew", "--map", "2=Bill", "--not-label", "note")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("NOTE: Read this.", r.stdout)

    def test_inspect_mode_warns_about_namespace_shift(self):
        r = self.run_cli(self.ROWS, "--diarized")
        self.assertEqual(r.returncode, 0)
        self.assertIn("CHUNK-LOCAL", r.stdout)

    def test_map_mode_outputs_labeled_markdown_and_coverage(self):
        r = self.run_cli(self.ROWS, "--diarized", "--map", "1=Andrew", "--map", "2=Bill",
                         "--map", "3=Bill", "--map", "4=Andrew")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("**Andrew:** Welcome to the show.", r.stdout)
        # Bill's cues 2 and 3 (labels 2 and 3) are adjacent, so they merge into one turn.
        self.assertIn("**Bill:** Thanks for having me. Back again.", r.stdout)
        self.assertIn("**Andrew:** Good to see you.", r.stdout)
        self.assertIn("coverage OK: 4 cues -> 3 turns", r.stderr)

    def test_missing_map_entry_fails_loudly(self):
        r = self.run_cli(self.ROWS, "--diarized", "--map", "1=Andrew", "--map", "2=Bill")
        self.assertEqual(r.returncode, 2)
        self.assertIn("unmapped speaker labels", r.stderr)

    def test_plain_mode_strips_labels_and_hints_at_diarized(self):
        r = self.run_cli(self.ROWS)
        self.assertIn("--diarized", r.stderr)
        self.assertNotIn("Speaker", r.stdout)

    def test_proper_nouns_ignore_labels(self):
        r = self.run_cli(self.ROWS, "--proper-nouns")
        self.assertNotIn("Speaker", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
