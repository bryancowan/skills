"""Tests for skills/podcast-transcript/scripts/sync_typewhisper.py (stdlib only).

Run from the repo root:  python3 -m unittest tests/test_sync_typewhisper.py
"""

import contextlib
import io
import json
import shutil
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the bundled skill dir
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "skills" / "podcast-transcript" / "scripts"))

import sync_typewhisper as sync  # noqa: E402

FIXTURE = """# Podcast Profile: Fixture

| Heard as | Correct |
|----------|---------|
| "she" / "she's" (when referring to the leader) | "Xi" / "Xi's" |
| "Wahooning" / "Wong Ning" | "Wang Huning" |
| "cynicism" | "Sinocism" (Bill's newsletter) |
| "Ten Cent" | "Tencent" |
| "Guangju Biennial" / "ASA Society" | "Gwangju Biennale" / "Asia Society" |
| "off cycle" heard as "auto cycle" | "off-cycle" |
| "Ram" (as in "Jimmy Goodrich of Ram") | "RAND" (a "think tank") |
| "Baedaye hub" / "Beyday Huh" | "Beidaihe" |
| "dubbish" | "dovish" |
| "export curves" | "export curbs" |
| "Kratos" | "Kratsios" |
| "Jan was out at Facebook" | "Yann LeCun" |
| "sell Trainium" | "sell Trainium" |
| "Ursula van Lion" | "Ursula von der Leyen" |
"""

# "curve" (not "curves") so the inflection check is what has to catch "export curves".
WORDS = {"she", "cynicism", "ten", "cent", "ram", "off", "cycle", "auto", "dubbish", "export", "curve"}


def fixture_rows():
    with tempfile.TemporaryDirectory() as tmp:
        Path(tmp, "fixture.md").write_text(FIXTURE, encoding="utf-8")
        return sync.parse_profiles(Path(tmp))


class ParseTests(unittest.TestCase):
    def test_parses_variants_and_strips_parentheticals(self):
        rows = {r.heard[0]: r for r in fixture_rows()}
        she = rows["she"]
        self.assertEqual(she.heard, ["she", "she's"])
        self.assertEqual(she.correct, ["Xi", "Xi's"])
        self.assertTrue(she.has_context)
        # Quoted text inside a note must not leak in as an extra value.
        self.assertEqual(rows["Ram"].heard, ["Ram"])
        self.assertEqual(rows["Ram"].correct, ["RAND"])
        self.assertFalse(rows["Wahooning"].has_context)

    def test_flags_heard_as_rows_as_ambiguous(self):
        rows = {r.heard[0]: r for r in fixture_rows()}
        self.assertTrue(rows["off cycle"].ambiguous)


class TermTests(unittest.TestCase):
    def test_only_proper_nouns_and_scored_by_variants(self):
        cands = sync.term_candidates(fixture_rows())
        self.assertEqual(cands["Wang Huning"], 2)
        self.assertEqual(cands["Beidaihe"], 2)
        self.assertIn("Sinocism", cands)
        self.assertNotIn("Xi", cands)  # too short to boost usefully
        self.assertNotIn("dovish", cands)
        self.assertNotIn("off-cycle", cands)

    def test_phrases_with_lowercase_words_are_not_terms(self):
        cands = sync.term_candidates(fixture_rows())
        self.assertNotIn("sell Trainium", cands)
        self.assertIn("Ursula von der Leyen", cands)  # lowercase connectors are fine

    def test_generic_words_need_stronger_evidence_and_lists_are_not_terms(self):
        rows = [
            sync.ProfileRow("f", ["Dew oh"], ["Duo"], False, False),
            sync.ProfileRow("f", ["Clawed", "Cloud"], ["Claude"], False, False),
            sync.ProfileRow("f", ["Clod", "Clawd"], ["Claude"], False, False),
            sync.ProfileRow("f", ["Best in career"], ["Bessent, Greer"], False, False),
        ]
        cands = sync.term_candidates(rows, {"duo", "claude"})
        self.assertNotIn("Duo", cands)  # one mis-hearing of an ordinary word
        self.assertEqual(cands["Claude"], 4)  # same word, enough evidence
        self.assertNotIn("Bessent, Greer", cands)

    def test_ties_prefer_longer_more_specific_terms(self):
        to_add, _, overflow = sync.plan_terms({"Duo": 2, "Demis Hassabis": 2}, [], budget=1)
        self.assertEqual((to_add, overflow), (["Demis Hassabis"], ["Duo"]))

    def test_possessive_is_folded_into_the_base_term(self):
        self.assertNotIn("Xi's", sync.term_candidates(fixture_rows()))

    def test_plan_fills_only_free_slots_highest_score_first(self):
        cands = {"A Term": 5, "B Term": 3, "C Term": 3, "D Term": 1}
        to_add, present, overflow = sync.plan_terms(cands, ["existing", "b term"], budget=4)
        self.assertEqual(to_add, ["A Term", "C Term"])
        self.assertEqual(present, ["B Term"])
        self.assertEqual(overflow, ["D Term"])

    def test_plan_with_no_free_slots_adds_nothing(self):
        to_add, _, overflow = sync.plan_terms({"New Name": 9}, ["x"] * 256)
        self.assertEqual(to_add, [])
        self.assertEqual(overflow, ["New Name"])


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.accepted, self.skipped = sync.safe_corrections(fixture_rows(), WORDS)
        self.reasons = {orig: reason for orig, _, reason in self.skipped}

    def test_accepts_distinctive_garbles(self):
        self.assertEqual(self.accepted["wahooning"], ("Wahooning", "Wang Huning"))
        self.assertEqual(self.accepted["wong ning"], ("Wong Ning", "Wang Huning"))
        self.assertEqual(self.accepted["baedaye hub"], ("Baedaye hub", "Beidaihe"))

    def test_rejects_context_dependent_rows(self):
        self.assertNotIn("she", self.accepted)
        self.assertIn("needs context", self.reasons["she"])
        self.assertIn("needs context", self.reasons["Ram"])

    def test_rejects_real_english_words(self):
        self.assertNotIn("cynicism", self.accepted)  # legitimate word in everyday dictation
        self.assertIn("ordinary English", self.reasons["cynicism"])
        self.assertIn("ordinary English", self.reasons["Ten Cent"])

    def test_rejects_inflected_english_the_word_list_misses(self):
        self.assertNotIn("export curves", self.accepted)  # "curves" is not in the system list
        self.assertIn("ordinary English", self.reasons["export curves"])

    def test_rejects_long_one_off_phrases(self):
        self.assertNotIn("jan was out at facebook", self.accepted)
        self.assertEqual(self.reasons["Jan was out at Facebook"], "long one-off phrase")

    def test_denylist_blocks_real_names(self):
        self.assertIn("kratos", sync.safe_corrections(fixture_rows(), WORDS)[0])
        accepted, skipped = sync.safe_corrections(fixture_rows(), WORDS, {"kratos"})
        self.assertNotIn("kratos", accepted)
        self.assertIn(("Kratos", "Kratsios", "on the denylist (real name or word)"), skipped)

    def test_rejects_multi_value_and_heard_as_rows(self):
        self.assertNotIn("guangju biennial", self.accepted)
        self.assertEqual(self.reasons["Guangju Biennial"], "multiple correct values")
        self.assertNotIn("off cycle", self.accepted)

    def test_plan_corrections_is_idempotent_and_never_overwrites(self):
        existing = {"Wahooning": "Wang Huning", "Wong Ning": "Something Else"}
        to_add, present, conflicts = sync.plan_corrections(self.accepted, existing)
        self.assertEqual(present, ["Wahooning"])
        self.assertEqual(conflicts, [("Wong Ning", "Wang Huning", "Something Else")])
        added = {o for o, _ in to_add}
        self.assertTrue({"Baedaye hub", "Beyday Huh"} <= added)
        self.assertFalse({"Wahooning", "Wong Ning"} & added)


class StubTypeWhisper(BaseHTTPRequestHandler):
    terms: list[str] = []
    corrections: dict[str, str] = {}
    log: list[tuple[str, str]] = []
    drop_on_replace: set[str] = set()  # simulate an app that silently ignores some terms on replace

    def _send(self, payload):
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        self.log.append(("GET", self.path))
        if self.path == "/v1/dictionary/terms":
            self._send({"terms": self.terms, "count": len(self.terms)})
        else:
            items = [{"original": k, "replacement": v, "caseSensitive": False} for k, v in self.corrections.items()]
            self._send({"corrections": items, "count": len(items)})

    def do_PUT(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.log.append(("PUT", self.path))
        if self.path == "/v1/dictionary/terms":
            if payload["replace"]:
                self.terms[:] = [t for t in payload["terms"] if t not in self.drop_on_replace]
            else:
                have = {t.lower() for t in self.terms}
                self.terms.extend(t for t in payload["terms"] if t.lower() not in have)
            self._send({"terms": self.terms, "count": len(self.terms)})
        else:
            self.corrections[payload["original"]] = payload["replacement"]
            self._send({"corrections": [], "count": 0})

    def log_message(self, *args):
        pass


class ClientTests(unittest.TestCase):
    def setUp(self):
        StubTypeWhisper.terms, StubTypeWhisper.corrections, StubTypeWhisper.log = ["RAG"], {}, []
        self.server = HTTPServer(("127.0.0.1", 0), StubTypeWhisper)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = sync.TypeWhisperClient(self.server.server_address[1], "token")

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()

    def apply_once(self):
        rows = fixture_rows()
        accepted, _ = sync.safe_corrections(rows, WORDS)
        terms, _, _ = sync.plan_terms(sync.term_candidates(rows), self.client.terms())
        corrections, _, _ = sync.plan_corrections(accepted, self.client.corrections())
        if terms:
            self.client.add_terms(terms)
        for original, replacement in corrections:
            self.client.put_correction(original, replacement)
        return terms, corrections

    def test_second_apply_adds_nothing_and_never_deletes(self):
        first_terms, first_corrections = self.apply_once()
        self.assertTrue(first_terms and first_corrections)
        self.assertIn("RAG", StubTypeWhisper.terms)  # existing term untouched
        second_terms, second_corrections = self.apply_once()
        self.assertEqual((second_terms, second_corrections), ([], []))
        self.assertNotIn("DELETE", {method for method, _ in StubTypeWhisper.log})

    def test_unreachable_server_raises_api_unavailable(self):
        dead = sync.TypeWhisperClient(1, None)
        with self.assertRaises(sync.ApiUnavailable):
            dead.terms()


class RankingTests(unittest.TestCase):
    def test_profile_prose_stops_before_the_artifact_tables(self):
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "show.md").write_text(
                "# Podcast Profile: Show\n\n## Speakers\n\n- **Bill** reads his Sinocism newsletter.\n\n"
                "## Known STT artifacts\n\n| Heard as | Correct |\n| \"x\" | \"Qwen\" |\n",
                encoding="utf-8",
            )
            prose = sync.profile_prose(Path(tmp))
        self.assertIn("Sinocism", prose)
        self.assertNotIn("Qwen", prose)

    def test_score_combines_mishearings_prose_bonus_and_episode_spread(self):
        cands = {"Sinocism": 1, "Qwen": 1, "Busan": 1}
        usage = {"Sinocism": (15, 9), "Qwen": (0, 0), "Busan": (9, 8)}
        scores = sync.rank_scores(cands, "reads his Sinocism newsletter", usage)
        self.assertEqual(scores["Sinocism"], (1 + sync.PROSE_BONUS) * 10)
        self.assertEqual(scores["Busan"], 9)
        self.assertEqual(scores["Qwen"], 1)

    def test_without_a_corpus_ranking_is_mishearings_plus_prose_bonus(self):
        scores = sync.rank_scores({"A Name": 3, "Other": 3}, "about A Name only")
        self.assertEqual(scores, {"A Name": 3 + sync.PROSE_BONUS, "Other": 3})

    def test_prose_match_respects_word_boundaries(self):
        self.assertEqual(sync.rank_scores({"Xi": 1}, "Xi Jinping spoke")["Xi"], 1 + sync.PROSE_BONUS)
        self.assertEqual(sync.rank_scores({"Xi": 1}, "Xinhua only")["Xi"], 1)  # not inside another word

    def test_usage_in_episodes_beats_an_alphabetical_tie(self):
        # The case that left Sinocism out: every term scored 1 and ties fell to length/alphabet.
        base = {"Mount Kailash": 1, "Sinocism": 1}
        scores = sync.rank_scores(base, "", {"Mount Kailash": (2, 1), "Sinocism": (15, 9)})
        to_add, _, overflow = sync.plan_terms(scores, [], budget=1)
        self.assertEqual((to_add, overflow), (["Sinocism"], ["Mount Kailash"]))


class CorpusTests(unittest.TestCase):
    def make_corpus(self, tmp):
        root = Path(tmp)
        (root / "ep1.md").write_text(
            "Intro mentions Sinocism before the transcript.\n\n## Transcript\n\nSinocism is great. Xinhua said so. Sinocism!\n",
            encoding="utf-8",
        )
        (root / "ep2.md").write_text("## Notes\n\nno transcript heading here, Sinocism Sinocism\n", encoding="utf-8")
        (root / "sub").mkdir()
        (root / "sub" / "ep3.md").write_text("x\n## Transcript\n\nXi Jinping and sinocism again.\n", encoding="utf-8")
        (root / ".obsidian").mkdir()
        (root / ".obsidian" / "ep4.md").write_text("x\n## Transcript\n\nSinocism Sinocism Sinocism\n", encoding="utf-8")
        (root / "binary.md").write_bytes(b"\xff\xfe\x00bad")
        return root

    def test_counts_only_transcript_sections_and_skips_tool_folders(self):
        with tempfile.TemporaryDirectory() as tmp:
            usage = sync.corpus_usage(["Sinocism", "Xi", "Xinhua"], self.make_corpus(tmp))
        self.assertEqual(usage["Sinocism"], (3, 2))  # ep1 twice + ep3 once; not ep2 (no heading) or .obsidian
        self.assertEqual(usage["Xinhua"], (1, 1))
        self.assertEqual(usage["Xi"], (1, 1))  # "Xi Jinping" counts; "Xinhua" does not

    def test_cli_rejects_a_corpus_that_is_not_a_folder(self):
        argv, sys.argv = sys.argv, ["sync_typewhisper.py", "--corpus", "/definitely/not/a/folder"]
        try:
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(sync.main(), 2)
        finally:
            sys.argv = argv


class ApplyFailureTests(unittest.TestCase):
    """main() must not traceback when the API fails after the planning reads succeed."""

    def run_main(self, failure):
        class Flaky:
            def terms(self):
                return ["RAG"]

            def corrections(self):
                return {}

            def add_terms(self, terms):
                raise failure

            put_correction = add_terms

        original, sync.TypeWhisperClient.discover = sync.TypeWhisperClient.discover, classmethod(lambda cls: Flaky())
        argv, sys.argv = sys.argv, ["sync_typewhisper.py", "--apply"]
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return sync.main()
        finally:
            sync.TypeWhisperClient.discover, sys.argv = original, argv

    def test_server_vanishing_mid_apply_exits_zero(self):
        self.assertEqual(self.run_main(sync.ApiUnavailable("connection refused")), 0)

    def test_http_error_mid_apply_exits_nonzero(self):
        self.assertEqual(self.run_main(RuntimeError("PUT /v1/dictionary/terms failed: HTTP 500")), 1)


class PlanPruneTests(unittest.TestCase):
    """plan_prune: which weak terms give up their slot to which stronger deferred ones."""

    CANDS = {"Moolenaar": 28, "Zhipu": 10, "Opus 5": 6, "Marginal": 3, "Akin Gump": 2, "Allen Iverson": 2, "Keeper": 1}

    def test_swaps_the_weakest_existing_for_the_strongest_deferred(self):
        plan = sync.plan_prune(self.CANDS, ["Akin Gump", "Allen Iverson", "Keeper", "Adobe XD"], budget=4)
        self.assertEqual([t for t, _ in plan.removals], ["Keeper", "Akin Gump", "Allen Iverson"])
        self.assertEqual([t for t, _ in plan.additions], ["Moolenaar", "Zhipu", "Opus 5"])
        self.assertEqual([t for t, _ in plan.deferred], ["Marginal"])

    def test_free_slots_are_filled_before_anything_is_removed(self):
        plan = sync.plan_prune(self.CANDS, ["Akin Gump", "Keeper"], budget=3)  # one free slot
        self.assertEqual([t for t, _ in plan.additions][0], "Moolenaar")
        self.assertEqual(len(plan.additions), len(plan.removals) + 1)

    def test_no_churn_for_a_marginal_gain(self):
        for new, old in ((3, 2), (2, 1)):  # ratio ok but gain too small / gain ok but ratio too small
            plan = sync.plan_prune({"New": new, "Old": old}, ["Old"], budget=1)
            self.assertEqual(plan.removals, [], f"{new} vs {old}")
        plan = sync.plan_prune({"New": 4, "Old": 2}, ["Old"], budget=1)  # exactly 2x and +2: the minimum swap
        self.assertEqual([t for t, _ in plan.removals], ["Old"])

    def test_terms_without_profile_evidence_are_never_removed(self):
        plan = sync.plan_prune({"New": 99}, ["Adobe XD", "Keras"], budget=2)
        self.assertEqual(plan.removals, [])
        self.assertEqual(plan.left_alone, ["Adobe XD", "Keras"])
        self.assertEqual([t for t, _ in plan.deferred], ["New"])

    def test_keep_list_protects_a_term_case_insensitively(self):
        plan = sync.plan_prune({"New": 99, "Old": 1}, ["Old"], budget=1, keep={"old"})
        self.assertEqual(plan.removals, [])
        self.assertEqual(plan.protected, ["Old"])

    def test_max_removals_caps_a_run(self):
        cands = {f"New{i}": 50 for i in range(5)} | {f"Old{i}": 1 for i in range(5)}
        plan = sync.plan_prune(cands, [f"Old{i}" for i in range(5)], budget=5, max_removals=2)
        self.assertEqual(len(plan.removals), 2)
        self.assertEqual(len(plan.additions), 2)

    def test_score_ties_are_settled_by_mentions_not_the_alphabet(self):
        cands = {"New": 50, "Aardvark": 2, "Zebra": 2}
        # Aardvark sorts first alphabetically but is said far more often, so Zebra goes
        plan = sync.plan_prune(cands, ["Aardvark", "Zebra"], budget=2, mentions={"Aardvark": 9, "Zebra": 1})
        self.assertEqual([t for t, _ in plan.removals], ["Zebra"])

    def test_keep_list_and_matching_ignore_unicode_composition_and_extra_spaces(self):
        # "Café" with a combining accent, and "Old  Name" with two spaces, must still be protected
        plan = sync.plan_prune({"Café": 1, "New": 10}, ["Café"], budget=1, keep={"cafe\u0301"})
        self.assertEqual((plan.removals, plan.protected), ([], ["Café"]))
        plan = sync.plan_prune({"Old Name": 1, "New": 10}, ["Old Name"], budget=1, keep={"old  name"})
        self.assertEqual(plan.removals, [])
        # an existing term spelled with a combining accent is the SAME term as the profile's precomposed one,
        # so it has evidence (a score) and is not mistaken for an orphan
        plan = sync.plan_prune({"Café": 1}, ["Cafe\u0301"], budget=1)
        self.assertEqual(plan.left_alone, [])

    def test_load_keeplist_normalizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "keep.txt")
            path.write_text("# c\nCafe\u0301   Society\n", encoding="utf-8")
            self.assertEqual(sync.load_keeplist(path), {"café society"})

    def test_inputs_are_not_mutated(self):
        existing, cands = ["Old"], {"New": 50, "Old": 1}
        sync.plan_prune(cands, existing, budget=1)
        self.assertEqual((existing, cands), (["Old"], {"New": 50, "Old": 1}))


class ScriptedClient:
    """A tiny in-memory TypeWhisper that can misbehave on cue, for apply_prune's failure paths."""

    def __init__(self, live, fail_read=None, fail_first_write=False):
        self.live, self.reads, self.writes = list(live), 0, []
        self.fail_read, self.fail_first_write = fail_read, fail_first_write

    def terms(self):
        self.reads += 1
        if self.fail_read and self.fail_read(self):
            raise sync.ApiUnavailable("lost GET")
        return list(self.live)

    def replace_terms(self, terms):
        self.writes.append(list(terms))
        if self.fail_first_write and len(self.writes) == 1:
            self.live = ["half-applied"]
            raise RuntimeError("PUT /v1/dictionary/terms failed: HTTP 500")
        self.live = list(terms)


class PruneApplyTests(unittest.TestCase):
    """apply_prune writes through the API's only removal path (replace the whole list) defensively."""

    def setUp(self):
        StubTypeWhisper.terms = ["Akin Gump", "Adobe XD", "Keeper"]
        StubTypeWhisper.corrections, StubTypeWhisper.log, StubTypeWhisper.drop_on_replace = {}, [], set()
        self.server = HTTPServer(("127.0.0.1", 0), StubTypeWhisper)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.client = sync.TypeWhisperClient(self.server.server_address[1], "token")
        self.tmp = Path(tempfile.mkdtemp(prefix="prune-"))
        self.plan = sync.PrunePlan(removals=[("Akin Gump", 2)], additions=[("Moolenaar", 28)])

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def puts(self):
        return [entry for entry in StubTypeWhisper.log if entry[0] == "PUT"]

    def test_happy_path_replaces_once_keeps_everything_else_and_saves_a_backup(self):
        original = list(StubTypeWhisper.terms)
        backup, notes = sync.apply_prune(self.client, self.plan, original, budget=5, backup_dir=self.tmp)
        self.assertEqual(notes, [])
        self.assertEqual(StubTypeWhisper.terms, ["Adobe XD", "Keeper", "Moolenaar"])
        self.assertEqual(len(self.puts()), 1)
        saved = json.loads(backup.read_text(encoding="utf-8"))
        self.assertEqual(saved["terms"], original)  # the COMPLETE previous list
        self.assertEqual((saved["removed"], saved["added"]), (["Akin Gump"], ["Moolenaar"]))

    def test_refuses_when_the_dictionary_changed_since_planning(self):
        StubTypeWhisper.terms.append("Added In The App Meanwhile")
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(self.client, self.plan, ["Akin Gump", "Adobe XD", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertIn("changed", str(ctx.exception))
        self.assertEqual(self.puts(), [])  # nothing written
        self.assertEqual(list(self.tmp.iterdir()), [])  # not even a backup

    def test_refuses_to_exceed_the_cap(self):
        with self.assertRaises(sync.PruneError):
            sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=2, backup_dir=self.tmp)
        self.assertEqual(self.puts(), [])

    def test_a_failed_verification_rolls_back(self):
        StubTypeWhisper.drop_on_replace = {"Moolenaar"}  # the app silently ignores the new term
        original = list(StubTypeWhisper.terms)
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(self.client, self.plan, original, budget=5, backup_dir=self.tmp)
        self.assertIn("restored", str(ctx.exception))
        self.assertEqual(StubTypeWhisper.terms, original)
        self.assertEqual(len(self.puts()), 2)  # the write, then the restore

    @staticmethod
    def make_fake(live, **kwargs):
        return ScriptedClient(live, **kwargs)

    def test_a_failed_verifying_read_triggers_a_restore_instead_of_reporting_success(self):
        # reviewer's repro: the write lands, then the verification read fails
        fake = self.make_fake(["Akin Gump", "Adobe XD", "Keeper"], fail_read=lambda f: f.reads == 2)
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(fake, self.plan, ["Akin Gump", "Adobe XD", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertIn("could not be confirmed", str(ctx.exception))
        self.assertIn("restored", str(ctx.exception))
        self.assertEqual(fake.live, ["Akin Gump", "Adobe XD", "Keeper"])
        self.assertEqual(len(fake.writes), 2)  # the write, then the restore

    def test_a_failing_write_is_restored_too(self):
        live = ["Akin Gump", "Adobe XD", "Keeper"]
        fake = self.make_fake(live, fail_first_write=True)  # half-applies the write, then HTTP 500
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(fake, self.plan, list(live), budget=5, backup_dir=self.tmp)
        self.assertIn("restored", str(ctx.exception))
        self.assertEqual(fake.live, live)

    def test_an_incomplete_or_malformed_terms_response_is_refused(self):
        client = sync.TypeWhisperClient(1, None)
        for payload in ({"count": 3, "terms": ["only one"]}, {"terms": "nope"}, {"terms": ["ok", " "]}, {"count": 0}):
            client._request = lambda method, path, body=None, p=payload: p
            with self.assertRaises(RuntimeError, msg=str(payload)):
                client.terms()
        client._request = lambda method, path, body=None: {"count": 2, "terms": ["a", "b"]}
        self.assertEqual(client.terms(), ["a", "b"])

    def test_a_partial_terms_read_aborts_before_any_write(self):
        class Partial:
            writes = 0

            def terms(inner):
                raise RuntimeError("GET /v1/dictionary/terms is incomplete: count=2 but 1 terms were returned")

            def replace_terms(inner, terms):
                inner.writes += 1

        client = Partial()
        with self.assertRaises(RuntimeError):
            sync.apply_prune(client, self.plan, ["Akin Gump"], budget=5, backup_dir=self.tmp)
        self.assertEqual(client.writes, 0)

    def test_an_unwritable_backup_is_a_clean_error_and_nothing_is_written(self):
        occupied = self.tmp / "not-a-dir"
        occupied.write_text("in the way", encoding="utf-8")
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=5, backup_dir=occupied)
        self.assertIn("backup", str(ctx.exception))
        self.assertEqual(self.puts(), [])

    def test_a_changed_spelling_is_noted_not_fatal(self):
        fake = self.make_fake(["Akin Gump", "Orphan"])
        original = fake.replace_terms
        fake.replace_terms = lambda terms: original([t.lower() for t in terms])  # an app that lowercases what it stores
        plan = sync.PrunePlan(removals=[("Akin Gump", 2)], additions=[("Moolenaar", 28)])
        _, notes = sync.apply_prune(fake, plan, ["Akin Gump", "Orphan"], budget=5, backup_dir=self.tmp)
        self.assertEqual(fake.live, ["orphan", "moolenaar"])
        self.assertTrue(any("capitalization" in n for n in notes))

    def test_terms_that_appear_during_the_sync_are_reported(self):
        fake = self.make_fake(["Akin Gump", "Keeper"])
        original = fake.replace_terms
        fake.replace_terms = lambda terms: original(list(terms) + ["Added In The App"])
        plan = sync.PrunePlan(removals=[("Akin Gump", 2)], additions=[("Moolenaar", 28)])
        _, notes = sync.apply_prune(fake, plan, ["Akin Gump", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertTrue(any("Added In The App" in n for n in notes))

    def test_a_failed_restore_points_at_the_backup(self):
        class Broken:
            writes = 0

            def terms(self_inner):
                return ["Akin Gump", "Adobe XD", "Keeper"] if self_inner.writes == 0 else ["Adobe XD"]

            def replace_terms(self_inner, terms):
                self_inner.writes += 1
                if self_inner.writes > 1:
                    raise sync.ApiUnavailable("gone")

        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(Broken(), self.plan, ["Akin Gump", "Adobe XD", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertIn("RESTORE FAILED", str(ctx.exception))
        self.assertTrue(any(self.tmp.glob("terms-before-prune-*.json")))

    def test_backups_in_the_same_second_do_not_overwrite_each_other(self):
        a = sync._write_backup(self.tmp, ["x"], [], [])
        b = sync._write_backup(self.tmp, ["y"], [], [])
        self.assertNotEqual(a, b)
        self.assertEqual(json.loads(a.read_text())["terms"], ["x"])


class PruneCliTests(unittest.TestCase):
    """main() --prune: guards, dry-run really is read-only, --apply swaps through apply_prune."""

    PROFILE = (
        "# Podcast Profile: Prune Fixture\n\n| Heard as | Correct |\n|---|---|\n"
        '| "Wahooning" / "Wong Ning" / "Wahoo Ning" | "Wang Huning" |\n'
        '| "Ten Cent" | "Tencent" |\n'
        '| "Gwangju Biennial" | "Gwangju Biennale" |\n'
        '| "Zhipu Zee" | "Zhipu" |\n'
    )

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="prune-cli-"))
        (self.tmp / "profiles").mkdir()
        (self.tmp / "profiles" / "p.md").write_text(self.PROFILE, encoding="utf-8")
        self.corpus = self.tmp / "vault"
        self.corpus.mkdir()
        for i in range(10):  # 10 finished transcripts: Wang Huning in all, Zhipu in 3, Tencent in 1
            said = "Wang Huning spoke." + (" Zhipu is a lab." if i < 3 else "") + (" Tencent too." if i == 0 else "")
            (self.corpus / f"ep{i}.md").write_text(f"intro\n\n## Transcript\n\n{said}\n", encoding="utf-8")
        self.dictionary = ["Gwangju Biennale", "Tencent", "Custom Word"]
        self.calls = {"replace": [], "add": [], "put": 0}
        self.stored_corrections = {}

        outer = self

        class Fake:
            def terms(self):
                return list(outer.dictionary)

            def corrections(self):
                return dict(outer.stored_corrections)  # main() reads these back to verify its writes

            def replace_terms(self, terms):
                outer.calls["replace"].append(list(terms))
                outer.dictionary[:] = terms

            def add_terms(self, terms):
                outer.calls["add"].append(list(terms))
                outer.dictionary.extend(terms)

            def put_correction(self, original, replacement):
                outer.calls["put"] += 1
                outer.stored_corrections[original] = replacement

        self._orig = (sync.TypeWhisperClient.discover, sync.BACKUP_DIR)
        sync.TypeWhisperClient.discover = classmethod(lambda cls: Fake())
        sync.BACKUP_DIR = self.tmp / "backups"

    def tearDown(self):
        sync.TypeWhisperClient.discover, sync.BACKUP_DIR = self._orig
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_main(self, *extra, corpus=True):
        argv = ["sync_typewhisper.py", "--profiles", str(self.tmp / "profiles"), "--budget", "3",
                "--keep-file", str(self.tmp / "no-keep.txt"), *extra]
        if corpus:
            argv += ["--corpus", str(self.corpus)]
        old, sys.argv = sys.argv, argv
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                code = sync.main()
        finally:
            sys.argv = old
        return code, out.getvalue(), err.getvalue()

    def test_prune_without_a_corpus_is_refused(self):
        code, _, err = self.run_main("--prune", corpus=False)
        self.assertEqual(code, 2)
        self.assertIn("--corpus", err)

    def test_nonsense_limits_are_refused(self):
        for extra in (("--max-prune", "-1"), ("--budget", "0")):
            code, _, err = self.run_main("--prune", *extra)
            self.assertEqual(code, 2, extra)
            self.assertIn("--max-prune", err)

    def test_prune_needs_enough_transcripts(self):
        for path in list(self.corpus.glob("ep*.md"))[:5]:
            path.unlink()
        code, _, err = self.run_main("--prune")
        self.assertEqual(code, 2)
        self.assertIn("at least 10", err)

    def test_dry_run_reports_the_swap_and_writes_nothing(self):
        code, out, _ = self.run_main("--prune")
        self.assertEqual(code, 0)
        self.assertIn("Terms to REMOVE", out)
        self.assertIn("Gwangju Biennale", out)
        self.assertIn("Custom Word", out.split("Left alone")[1])  # orphans are listed as left alone
        self.assertEqual((self.calls["replace"], self.calls["add"]), ([], []))
        self.assertEqual(self.dictionary, ["Gwangju Biennale", "Tencent", "Custom Word"])

    def test_apply_swaps_weak_terms_for_strong_and_never_touches_orphans(self):
        code, out, err = self.run_main("--prune", "--apply")
        self.assertEqual(code, 0, err)
        self.assertEqual(len(self.calls["replace"]), 1)
        self.assertEqual(self.calls["add"], [])
        self.assertEqual(sorted(self.dictionary), ["Custom Word", "Wang Huning", "Zhipu"])
        self.assertTrue(any((self.tmp / "backups").glob("terms-before-prune-*.json")))

    def test_keep_file_stops_a_term_being_removed(self):
        (self.tmp / "keep.txt").write_text("# keep\nTencent\n", encoding="utf-8")
        code, _, err = self.run_main("--prune", "--apply", "--keep-file", str(self.tmp / "keep.txt"))
        self.assertEqual(code, 0, err)
        self.assertIn("Tencent", self.dictionary)
        self.assertIn("Custom Word", self.dictionary)

    def test_without_prune_nothing_is_ever_removed(self):
        code, _, _ = self.run_main("--apply")
        self.assertEqual(code, 0)
        self.assertEqual(self.calls["replace"], [])
        self.assertEqual(self.dictionary, ["Gwangju Biennale", "Tencent", "Custom Word"])

    def test_dry_run_without_prune_hints_that_swapping_is_available(self):
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        self.assertIn("--prune", out)


class NoWordListTests(unittest.TestCase):
    """Without a system word list the ordinary-English filter cannot run, so corrections must be
    skipped: with an empty list ~100 ordinary phrases leak through as global dictation fixes."""

    def run_main(self, words):
        pushed = {"terms": [], "corrections": {}}

        class Recorder:
            def terms(self):
                return list(pushed["terms"])

            def corrections(self):
                return dict(pushed["corrections"])

            def add_terms(self, terms):
                pushed["terms"].extend(terms)

            def put_correction(self, original, replacement):
                pushed["corrections"][original] = replacement

        orig_discover, orig_words = sync.TypeWhisperClient.discover, sync.load_system_words
        sync.TypeWhisperClient.discover = classmethod(lambda cls: Recorder())
        sync.load_system_words = lambda *a, **k: words
        argv, sys.argv = sys.argv, ["sync_typewhisper.py", "--apply"]
        err = io.StringIO()
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(err):
                code = sync.main()
        finally:
            sync.TypeWhisperClient.discover, sync.load_system_words, sys.argv = orig_discover, orig_words, argv
        return code, pushed, err.getvalue()

    def test_empty_word_list_skips_corrections_but_still_syncs_terms(self):
        code, pushed, err = self.run_main(set())
        self.assertEqual(code, 0)
        self.assertEqual(pushed["corrections"], {})
        self.assertGreater(len(pushed["terms"]), 0)
        self.assertIn("no system word list", err)

    def test_with_a_word_list_corrections_are_pushed(self):
        code, pushed, err = self.run_main({"cynicism", "chip", "wars"})
        self.assertEqual(code, 0)
        self.assertGreater(len(pushed["corrections"]), 0)
        self.assertNotIn("no system word list", err)
        self.assertNotIn("cynicism", {k.lower() for k in pushed["corrections"]})   # filtered as ordinary English


class RealProfileTests(unittest.TestCase):
    def test_real_profiles_keep_known_unsafe_rows_out(self):
        rows = sync.parse_profiles(sync.PROFILES_DIR)
        self.assertGreater(len(rows), 200)  # parser sanity: the real tables are large
        # An explicit word list, not sync.load_system_words(): that reads /usr/share/dict/words, which
        # macOS has and CI runners don't, so the test passed on a laptop and failed on Linux. These are
        # the only words the listed rows need the dictionary for.
        english = {"cynicism", "chip", "wars", "export", "curves", "marking", "videos"}
        accepted, _ = sync.safe_corrections(rows, english, sync.load_denylist())
        for unsafe in ("she", "she's", "UN", "C", "Ram", "Huawei", "Holland", "cynicism",
                       "chip wars", "export curves", "marking videos", "kratos"):
            self.assertNotIn(unsafe.lower(), accepted)
        self.assertIn("Sinocism", sync.term_candidates(rows))


if __name__ == "__main__":
    unittest.main()
