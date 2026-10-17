"""Tests for skills/podcast-transcript/scripts/sync_typewhisper.py (stdlib only).

Run from the repo root:  python3 -m unittest tests/test_sync_typewhisper.py
"""

import contextlib
import io
import json
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
            assert payload["replace"] is False
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


class RealProfileTests(unittest.TestCase):
    def test_real_profiles_keep_known_unsafe_rows_out(self):
        rows = sync.parse_profiles(sync.PROFILES_DIR)
        self.assertGreater(len(rows), 200)  # parser sanity: the real tables are large
        accepted, _ = sync.safe_corrections(rows, sync.load_system_words(), sync.load_denylist())
        for unsafe in ("she", "she's", "UN", "C", "Ram", "Huawei", "Holland", "cynicism",
                       "chip wars", "export curves", "marking videos", "kratos"):
            self.assertNotIn(unsafe.lower(), accepted)
        self.assertIn("Sinocism", sync.term_candidates(rows))


if __name__ == "__main__":
    unittest.main()
