#!/usr/bin/env python3
"""Regression tests for skills/obsidian-article-enrichment/scripts. Run: python3 tests/test_obsidian_article_enrichment.py"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills/obsidian-article-enrichment/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_note import description_check  # noqa: E402
from notelib import Frontmatter, classify, is_renamed, split_stem  # noqa: E402
from rename_note import clean_headline  # noqa: E402

NOTE = """---
title: "2026.39: Begun, the Aggregator Wars Have"
source: https://stratechery.com/2026/begun/
author:
  - "[[Ben Thompson]]"
description:
tags:
  - clippings
  - stratechery
status: Unread
note:
related:
  - "[[Some Other Note - 2026-09-26T130805-0500]]"
---
Body with ==a highlight==.
"""


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True)


class NameRules(unittest.TestCase):
    def test_split_stem(self):
        self.assertEqual(split_stem("A - B - 2026-09-26T130801-0500.md"), ("A - B", "2026-09-26T130801-0500"))
        self.assertEqual(split_stem("No stamp.md"), ("No stamp", None))

    def test_punctuation_only_change_is_not_a_rename(self):
        self.assertFalse(is_renamed("2026.42: Home At Last", "2026.42 Home At Last"))
        self.assertFalse(is_renamed("Pacing the Frontier, AI’s Limits", "Pacing the Frontier, AI's Limits"))
        self.assertTrue(is_renamed("Some of All Fears", "Andrew Sharp calls AI risk panic absurd"))

    def test_classify(self):
        self.assertEqual(classify("2026.42: Home At Last", ""), "weekly-roundup")
        self.assertEqual(classify("An Interview with Jane Doe", ""), "interview")
        self.assertEqual(classify("Joe (@joedaroo) on X", "https://x.com/a"), "non-headline")
        self.assertEqual(classify("A, B, C", "https://stratechery.com/x"), "update")

    def test_clean_headline(self):
        self.assertEqual(clean_headline('"Sources: Anthropic met “leaders”?."'), "Sources - Anthropic met 'leaders'")
        self.assertEqual(clean_headline("a culture of ‘reasonable paranoia’"), "a culture of 'reasonable paranoia'")
        self.assertEqual(clean_headline("costs $5! [x] {y} a/b﻿"), "costs 5 x y ab")

    def test_generic_description(self):
        self.assertTrue(description_check("We’re sharing details about GEM …", "GEM", False)[0])
        self.assertTrue(description_check("Title", "Title", False)[0])
        self.assertFalse(description_check("AI anxiety is rational, but the conversation is absurd.", "Some of All Fears", False)[0])


class ApplyFrontmatter(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.path = Path(self.dir.name) / "2026.39 Begun, the Aggregator Wars Have - 2026-09-26T130801-0500.md"
        self.path.write_text(NOTE, encoding="utf-8")

    def tearDown(self):
        self.dir.cleanup()

    def test_noop_is_byte_identical(self):
        r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", "{}")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.path.read_text(encoding="utf-8"), NOTE)

    def test_writes_only_three_keys(self):
        vals = {"description": "Meta: the agent war", "note": "One\nline.\n\nTwo.", "add_tags": ["#ecommerce", "Stratechery", "aiAgents"]}
        r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", json.dumps(vals))
        self.assertEqual(r.returncode, 0, r.stderr)
        fm = Frontmatter(self.path.read_text(encoding="utf-8"))
        self.assertEqual(fm.scalar("description"), "Meta: the agent war")
        self.assertEqual(fm.scalar("note"), "One line.\n\nTwo.")
        self.assertEqual(fm.items("tags"), ["clippings", "stratechery", "ecommerce", "aiAgents"])
        for key in ("title", "source", "status", "related", "author"):
            self.assertEqual(fm.raw(key), Frontmatter(NOTE).raw(key), key)
        self.assertTrue(self.path.read_text(encoding="utf-8").endswith("---\nBody with ==a highlight==.\n"))

    def test_refuses_to_overwrite_note_and_bad_tags(self):
        run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", '{"note": "first"}')
        r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", '{"note": "second"}')
        self.assertNotEqual(r.returncode, 0)
        r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", '{"add_tags": ["two words"]}')
        self.assertNotEqual(r.returncode, 0)

    def test_analyze_without_vault(self):
        r = run(SCRIPTS / "analyze_note.py", self.path)
        d = json.loads(r.stdout)
        self.assertEqual(d["format"], "weekly-roundup")
        self.assertEqual(d["rename"]["lean"], "keep")
        self.assertTrue(d["fields"]["note"]["needs_work"])
        self.assertTrue(d["fields"]["tags"]["needs_work"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
