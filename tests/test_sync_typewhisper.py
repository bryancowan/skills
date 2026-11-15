"""Tests for skills/podcast-transcript/scripts/sync_typewhisper.py (stdlib only).

Run from the repo root:  python3 -m unittest tests/test_sync_typewhisper.py
"""

import contextlib
import io
import json
import os
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
    omit_count = False  # simulate an API version that does not report a total count
    meta: dict[str, dict] = {}  # per-term settings, e.g. {"Accessibility": {"ctc_min_similarity": 0.8}}
    strip_meta_on_replace = False  # simulate an app that drops settings even when sent term_entries

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
            payload = {"terms": self.terms, "term_entries": [{"term": t, **self.meta.get(t, {})} for t in self.terms]}
            if not self.omit_count:
                payload["count"] = len(self.terms)
            self._send(payload)
        else:
            items = [{"original": k, "replacement": v, "caseSensitive": False} for k, v in self.corrections.items()]
            self._send({"corrections": items, "count": len(items)})

    def do_PUT(self):
        payload = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        self.log.append(("PUT", self.path))
        if self.path == "/v1/dictionary/terms":
            # the real app: "Use either 'terms' or 'term_entries', not both" / "Missing 'terms' or 'term_entries'"
            if ("terms" in payload) == ("term_entries" in payload):
                self.send_response(400)
                self.end_headers()
                return
            if payload["replace"]:
                entries = payload.get("term_entries")
                names = [e["term"] for e in entries] if entries is not None else payload["terms"]
                # Pessimistic model: replacing with bare strings RESETS every term's settings; only
                # term_entries carries them across. Pruning must therefore always send term_entries.
                kept_meta = {e["term"]: {k: v for k, v in e.items() if k != "term"} for e in (entries or [])}
                self.terms[:] = [t for t in names if t not in self.drop_on_replace]
                self.meta.clear()
                if not self.strip_meta_on_replace:
                    self.meta.update({k: v for k, v in kept_meta.items() if v and k in self.terms})
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
        StubTypeWhisper.meta, StubTypeWhisper.strip_meta_on_replace = {}, False
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

    @unittest.skipUnless(hasattr(os, "symlink"), "needs symlinks")
    def test_symlinks_cannot_fake_extra_episodes_or_read_outside_the_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp, "vault")
            root.mkdir()
            outside = Path(tmp, "outside.md")
            outside.write_text("x\n## Transcript\n\nFlern Flern\n", encoding="utf-8")
            (root / "real.md").write_text("x\n## Transcript\n\nSomething else\n", encoding="utf-8")
            try:
                for i in range(10):
                    (root / f"link{i}.md").symlink_to(outside)
            except OSError:
                self.skipTest("cannot create symlinks here")
            self.assertEqual(len(sync.corpus_bodies(root)), 1)  # only the real file
            self.assertEqual(sync.corpus_usage(["Flern"], root)["Flern"], (0, 0))

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

    def test_compatibility_look_alikes_are_distinct_terms(self):
        # reviewer's repro: NFKC made "Ⅳ" (roman numeral) equal "IV", so removing one dropped both
        self.assertNotEqual(sync._key("Ⅳ"), sync._key("IV"))
        self.assertNotEqual(sync._key("Straße"), sync._key("Strasse"))
        plan = sync.plan_prune({"IV": 1, "New": 10}, ["Ⅳ", "IV"], budget=2)
        self.assertEqual([t for t, _ in plan.removals], ["IV"])
        self.assertEqual(plan.left_alone, ["Ⅳ"])  # no profile evidence for the look-alike: never removed

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
    """A tiny in-memory TypeWhisper that can misbehave on cue, for apply_prune's failure paths.
    apply_prune reads term_entries three times (planning snapshot, the final read, the verifying read)."""

    def __init__(self, live, fail_read=None, fail_first_write=False, transform=None, meta=None):
        self.live, self.reads, self.writes = list(live), 0, []
        self.meta = dict(meta or {})
        self.fail_read, self.fail_first_write, self.transform = fail_read, fail_first_write, transform

    def term_entries(self):
        self.reads += 1
        if self.fail_read and self.fail_read(self):
            raise sync.ApiUnavailable("lost GET")
        return [{"term": t, **self.meta.get(t, {})} for t in self.live]

    def terms(self):
        return [e["term"] for e in self.term_entries()]

    def replace_terms(self, items):
        self.writes.append(list(items))
        if self.fail_first_write and len(self.writes) == 1:
            self.live, self.meta = ["half-applied"], {}
            raise RuntimeError("PUT /v1/dictionary/terms failed: HTTP 500")
        names = [i["term"] if isinstance(i, dict) else i for i in items]
        self.meta = {i["term"]: {k: v for k, v in i.items() if k != "term"} for i in items if isinstance(i, dict) and len(i) > 1}
        self.live = [self.transform(n) for n in names] if self.transform else names


class PruneApplyTests(unittest.TestCase):
    """apply_prune writes through the API's only removal path (replace the whole list) defensively."""

    def setUp(self):
        StubTypeWhisper.terms = ["Akin Gump", "Adobe XD", "Keeper"]
        StubTypeWhisper.corrections, StubTypeWhisper.log, StubTypeWhisper.drop_on_replace = {}, [], set()
        StubTypeWhisper.meta, StubTypeWhisper.strip_meta_on_replace, StubTypeWhisper.omit_count = {}, False, False
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
        self.assertEqual(self.puts(), [])  # nothing written to the dictionary
        self.assertEqual(list(self.tmp.iterdir()), [])  # stale from the start: not even a backup

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
        fake = self.make_fake(["Akin Gump", "Adobe XD", "Keeper"], fail_read=lambda f: f.reads == 3)
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

    def test_a_response_without_a_count_is_refused_when_pruning(self):
        # reviewer's repro: with no count a partial list is indistinguishable from a complete one
        client = sync.TypeWhisperClient(1, None, require_count=True)
        client._request = lambda method, path, body=None: {"terms": ["Old", "Private"]}  # "Unseen" missing
        with self.assertRaises(RuntimeError) as ctx:
            client.terms()
        self.assertIn("count", str(ctx.exception))
        lenient = sync.TypeWhisperClient(1, None)  # the add-only path keeps working without a count
        lenient._request = client._request
        self.assertEqual(lenient.terms(), ["Old", "Private"])

    def test_a_partial_terms_read_aborts_before_any_write(self):
        class Partial:
            writes = 0

            def term_entries(inner):
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
        fake = self.make_fake(["Akin Gump", "Orphan"], transform=str.lower)  # an app that lowercases what it stores
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

    def test_a_plan_that_would_remove_more_than_it_names_is_refused(self):
        # two entries collapse to the key of the one removal (duplicate-by-case): removing "Old" would drop both
        fake = self.make_fake(["Old", "old", "Keeper"])
        plan = sync.PrunePlan(removals=[("Old", 1)], additions=[("New", 9)])
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(fake, plan, ["Old", "old", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertIn("duplicates or look-alike", str(ctx.exception))
        self.assertEqual(fake.writes, [])

    def test_the_backup_is_written_before_the_final_read_so_a_slow_backup_cannot_widen_the_race(self):
        fake = self.make_fake(["Akin Gump", "Keeper"])
        real = sync._write_backup

        def backup_then_user_adds_a_term(*args, **kwargs):
            path = real(*args, **kwargs)
            fake.live.append("Added While Backup Was Written")  # the user edits the dictionary mid-backup
            return path

        sync._write_backup = backup_then_user_adds_a_term
        try:
            plan = sync.PrunePlan(removals=[("Akin Gump", 2)], additions=[("Moolenaar", 28)])
            with self.assertRaises(sync.PruneError) as ctx:
                sync.apply_prune(fake, plan, ["Akin Gump", "Keeper"], budget=5, backup_dir=self.tmp)
        finally:
            sync._write_backup = real
        self.assertIn("changed", str(ctx.exception))
        self.assertEqual(fake.writes, [])  # caught by the final read, not silently overwritten
        self.assertIn("Added While Backup Was Written", fake.live)

    def test_a_restore_that_changes_spelling_is_not_reported_as_a_clean_restore(self):
        live = ["Old", "Kept"]
        fake = self.make_fake(live, fail_read=lambda f: f.reads == 3, transform=str.lower)
        plan = sync.PrunePlan(removals=[("Old", 1)], additions=[("New", 9)])
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(fake, plan, list(live), budget=5, backup_dir=self.tmp)
        self.assertIn("different spelling", str(ctx.exception))
        self.assertIn("exact copy at", str(ctx.exception))

    @unittest.skipUnless(os.name == "posix", "POSIX file modes")
    def test_backups_are_private(self):
        target = self.tmp / "fresh" / "backups"
        backup, _ = sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=5, backup_dir=target)
        self.assertEqual(backup.stat().st_mode & 0o777, 0o600)
        self.assertEqual(target.stat().st_mode & 0o777, 0o700)

    # ---- per-term settings (found live: 53 of 256 real terms carry ctc_min_similarity) ----
    TUNED = {"Keeper": {"ctc_min_similarity": 0.8}, "Adobe XD": {"ctc_min_similarity": 0.8}}

    def test_per_term_settings_of_kept_terms_survive_the_write(self):
        StubTypeWhisper.meta = {k: dict(v) for k, v in self.TUNED.items()}
        sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=5, backup_dir=self.tmp)
        self.assertEqual(StubTypeWhisper.terms, ["Adobe XD", "Keeper", "Moolenaar"])
        self.assertEqual(StubTypeWhisper.meta, self.TUNED)  # still tuned after the whole-list replace

    def test_the_stub_really_resets_settings_on_a_bare_string_replace(self):
        # documents WHY apply_prune must send term_entries: the pessimistic (and plausible) reading of the API
        StubTypeWhisper.meta = {k: dict(v) for k, v in self.TUNED.items()}
        self.client.replace_terms(["Adobe XD", "Keeper"])
        self.assertEqual(StubTypeWhisper.meta, {})

    def test_a_write_that_loses_settings_is_detected_and_flagged(self):
        StubTypeWhisper.meta = {k: dict(v) for k, v in self.TUNED.items()}
        StubTypeWhisper.strip_meta_on_replace = True  # an app that drops settings even when sent term_entries
        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=5, backup_dir=self.tmp)
        self.assertIn("per-term settings changed", str(ctx.exception))
        self.assertIn("exact copy at", str(ctx.exception))  # the restore could not bring the settings back: say so
        (backup,) = self.tmp.iterdir()
        saved = json.loads(backup.read_text(encoding="utf-8"))
        self.assertIn({"term": "Keeper", "ctc_min_similarity": 0.8}, saved["term_entries"])  # settings are backed up

    def test_a_setting_edited_in_the_app_just_before_the_write_aborts(self):
        real = sync._write_backup

        def backup_then_user_retunes(*args, **kwargs):
            path = real(*args, **kwargs)
            StubTypeWhisper.meta["Keeper"] = {"ctc_min_similarity": 0.5}  # same terms, one setting changed
            return path

        StubTypeWhisper.meta = {"Keeper": {"ctc_min_similarity": 0.8}}
        sync._write_backup = backup_then_user_retunes
        try:
            with self.assertRaises(sync.PruneError) as ctx:
                sync.apply_prune(self.client, self.plan, list(StubTypeWhisper.terms), budget=5, backup_dir=self.tmp)
        finally:
            sync._write_backup = real
        self.assertIn("changed just before the write", str(ctx.exception))
        self.assertEqual(self.puts(), [])

    def test_term_entries_must_agree_with_terms_and_be_well_formed(self):
        client = sync.TypeWhisperClient(1, None)
        for payload in ({"terms": ["a"], "term_entries": [{"term": "b"}]},   # disagree
                        {"terms": ["a"], "term_entries": ["a"]},             # not objects
                        {"terms": ["a"], "term_entries": [{"nope": "a"}]}):  # no "term"
            client._request = lambda method, path, body=None, p=payload: p
            with self.assertRaises(RuntimeError, msg=str(payload)):
                client.term_entries()
        client._request = lambda method, path, body=None: {"terms": ["a", "b"]}  # an API without settings
        self.assertEqual(client.term_entries(), [{"term": "a"}, {"term": "b"}])

    def test_replace_sends_term_entries_for_objects_and_terms_for_strings_never_both(self):
        sent = []
        client = sync.TypeWhisperClient(1, None)
        client._request = lambda method, path, body=None: sent.append(body)
        client.replace_terms([{"term": "a", "ctc_min_similarity": 0.8}, {"term": "b"}])
        client.replace_terms(["a", "b"])
        self.assertEqual(sent[0], {"term_entries": [{"term": "a", "ctc_min_similarity": 0.8}, {"term": "b"}], "replace": True})
        self.assertEqual(sent[1], {"terms": ["a", "b"], "replace": True})

    def test_a_failed_restore_points_at_the_backup(self):
        class Broken:
            writes = 0

            def term_entries(self_inner):
                names = ["Akin Gump", "Adobe XD", "Keeper"] if self_inner.writes == 0 else ["Adobe XD"]
                return [{"term": n} for n in names]

            def replace_terms(self_inner, terms):
                self_inner.writes += 1
                if self_inner.writes > 1:
                    raise sync.ApiUnavailable("gone")

        with self.assertRaises(sync.PruneError) as ctx:
            sync.apply_prune(Broken(), self.plan, ["Akin Gump", "Adobe XD", "Keeper"], budget=5, backup_dir=self.tmp)
        self.assertIn("RESTORE FAILED", str(ctx.exception))
        self.assertTrue(any(self.tmp.glob("terms-before-prune-*.json")))

    def test_backups_in_the_same_second_do_not_overwrite_each_other(self):
        a = sync._write_backup(self.tmp, [{"term": "x", "ctc_min_similarity": 0.8}], [], [])
        b = sync._write_backup(self.tmp, [{"term": "y"}], [], [])
        self.assertNotEqual(a, b)
        saved = json.loads(a.read_text())
        self.assertEqual(saved["terms"], ["x"])
        self.assertEqual(saved["term_entries"], [{"term": "x", "ctc_min_similarity": 0.8}])  # settings are backed up


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
        self.settings = {}  # per-term settings, e.g. {"Tencent": {"ctc_min_similarity": 0.8}}
        self.calls = {"replace": [], "add": [], "put": 0}
        self.stored_corrections = {}

        outer = self

        class Fake:
            def terms(self):
                return list(outer.dictionary)

            def term_entries(self):
                return [{"term": t, **outer.settings.get(t, {})} for t in outer.dictionary]

            def corrections(self):
                return dict(outer.stored_corrections)  # main() reads these back to verify its writes

            def replace_terms(self, items):
                outer.calls["replace"].append(list(items))
                outer.dictionary[:] = [i["term"] if isinstance(i, dict) else i for i in items]
                outer.settings = {i["term"]: {k: v for k, v in i.items() if k != "term"}
                                  for i in items if isinstance(i, dict) and len(i) > 1}

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

    def test_a_real_client_is_made_strict_for_prune_but_not_for_a_plain_sync(self):
        StubTypeWhisper.terms, StubTypeWhisper.corrections, StubTypeWhisper.log = list(self.dictionary), {}, []
        StubTypeWhisper.drop_on_replace, StubTypeWhisper.omit_count = set(), True
        server = HTTPServer(("127.0.0.1", 0), StubTypeWhisper)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        sync.TypeWhisperClient.discover = classmethod(
            lambda cls: sync.TypeWhisperClient(server.server_address[1], "token"))
        try:
            code, _, err = self.run_main("--prune", "--apply")
            self.assertEqual(code, 1)
            self.assertIn("total count", err)
            self.assertEqual([e for e in StubTypeWhisper.log if e[0] == "PUT"], [])  # nothing written
            code, _, _ = self.run_main()  # a plain (add-only) dry run still works without a count
            self.assertEqual(code, 0)
        finally:
            StubTypeWhisper.omit_count = False
            server.shutdown()
            server.server_close()

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

    def test_a_term_with_custom_settings_is_never_pruned_and_keeps_them(self):
        self.settings = {"Gwangju Biennale": {"ctc_min_similarity": 0.8}}  # the WEAKEST removable term, but tuned
        code, out, err = self.run_main("--prune", "--apply")
        self.assertEqual(code, 0, err)
        self.assertIn("Gwangju Biennale", self.dictionary)
        self.assertEqual(self.settings, {"Gwangju Biennale": {"ctc_min_similarity": 0.8}})
        self.assertNotIn("Tencent", self.dictionary)   # the next-weakest, untuned term gave up its slot instead
        self.assertIn("Wang Huning", self.dictionary)
        self.assertIn("Custom Word", self.dictionary)

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
