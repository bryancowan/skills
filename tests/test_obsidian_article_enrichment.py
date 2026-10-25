#!/usr/bin/env python3
"""Regression tests for skills/obsidian-article-enrichment/scripts. Run: python3 tests/test_obsidian_article_enrichment.py"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "skills/obsidian-article-enrichment/scripts"
sys.path.insert(0, str(SCRIPTS))

from analyze_note import description_check  # noqa: E402
from notelib import Frontmatter, classify, is_renamed, rewrite_links, split_stem  # noqa: E402
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

    def test_rejects_wrong_json_shapes(self):
        for payload in ('{"add_tags": "analysis"}', '{"add_tags": [1, 2]}', '{"description": 5}', '["x"]'):
            r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json", payload)
            self.assertEqual(r.returncode, 2, payload)
            self.assertIn("error:", r.stderr, payload)
            self.assertNotIn("Traceback", r.stderr, payload)
        self.assertEqual(self.path.read_text(encoding="utf-8"), NOTE)

    def test_json_file_removed_after_write(self):
        values = Path(self.dir.name) / "values.json"
        values.write_text('{"add_tags": ["ecommerce"]}', encoding="utf-8")
        r = run(SCRIPTS / "apply_frontmatter.py", self.path, "--json-file", values)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(values.exists())

    def test_rename_refuses_very_long_headline(self):
        long = "Word " * 40
        r = run(SCRIPTS / "rename_note.py", self.path, "--headline", long, "--dry-run")
        self.assertEqual(r.returncode, 3)
        r = run(SCRIPTS / "rename_note.py", self.path, "--headline", long, "--dry-run", "--long-ok")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_analyze_without_vault(self):
        r = run(SCRIPTS / "analyze_note.py", self.path)
        d = json.loads(r.stdout)
        self.assertEqual(d["format"], "weekly-roundup")
        self.assertEqual(d["rename"]["lean"], "keep")
        self.assertTrue(d["fields"]["note"]["needs_work"])
        self.assertTrue(d["fields"]["tags"]["needs_work"])


TS = "2026-10-23T213234-0500"
OLD = f"The Birth & Rise of India - {TS}"
NEW = f"How India built a 194B-dollar IT export industry - {TS}"
DEAD_MSG = "The CLI is unable to find Obsidian. Please make sure Obsidian is running and try again."


def make_vault(root: Path) -> Path:
    """A tiny vault: the note to rename plus notes that link to it in every form we know of."""
    vault = root / "vault"
    (vault / ".obsidian").mkdir(parents=True)
    (vault / "Reading List").mkdir()
    (vault / "Reading List" / f"{OLD}.md").write_text("---\ntitle: Old\n---\nbody\n", encoding="utf-8")
    (vault / "Reading List" / "Linker A.md").write_text(
        "---\nrelated:\n"
        f'  - "[[{OLD}]]"\n'
        "---\n"
        f"plain [[{OLD}]], alias [[{OLD}|the piece]], heading [[{OLD}#Part 2]], block [[{OLD}^abc]],\n"
        f"path [[Reading List/{OLD}]], suffix [[{OLD}.md]], embed ![[{OLD}]], shouty [[{OLD.upper()}]]\n"
        f"near misses: [[{OLD} (copy)]] and [[{OLD}b]] and [[Other - {TS}]]\n",
        encoding="utf-8")
    (vault / "Unrelated.md").write_text("nothing to see\n", encoding="utf-8")
    return vault


def shim_env(root: Path) -> dict:
    """PATH with a fake `obsidian` first: it behaves like the CLI inside Codex's sandbox (message, exit 0)."""
    bin_dir = root / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "obsidian"
    shim.write_text(f"#!/bin/sh\necho '{DEAD_MSG}'\nexit 0\n", encoding="utf-8")
    shim.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "PYTHONDONTWRITEBYTECODE": "1"}


def run_env(env: dict, *args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, env=env)


class LinkRewrite(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.vault = make_vault(self.root)
        self.linker = self.vault / "Reading List" / "Linker A.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_every_link_form_is_rewritten_and_near_misses_are_not(self):
        changes = rewrite_links(self.vault, OLD, NEW)
        self.assertEqual(changes, [("Reading List/Linker A.md", 9)])
        text = self.linker.read_text(encoding="utf-8")
        for form in (f'"[[{NEW}]]"', f"[[{NEW}|the piece]]", f"[[{NEW}#Part 2]]", f"[[{NEW}^abc]]",
                     f"[[Reading List/{NEW}]]", f"[[{NEW}.md]]", f"![[{NEW}]]"):
            self.assertIn(form, text)
        self.assertIn(f"[[{OLD} (copy)]]", text)
        self.assertIn(f"[[{OLD}b]]", text)
        self.assertIn(f"[[Other - {TS}]]", text)

    def test_dry_run_reports_but_writes_nothing(self):
        before = self.linker.read_text(encoding="utf-8")
        self.assertEqual(rewrite_links(self.vault, OLD, NEW, apply=False), [("Reading List/Linker A.md", 9)])
        self.assertEqual(self.linker.read_text(encoding="utf-8"), before)

    def test_rename_falls_back_and_fixes_links_when_the_cli_cannot_reach_obsidian(self):
        env = shim_env(self.root)
        old = self.vault / "Reading List" / f"{OLD}.md"
        r = run_env(env, SCRIPTS / "rename_note.py", old, "--headline", "How India built a 194B-dollar IT export industry")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("unable to find Obsidian", r.stderr)  # the CLI's own message is surfaced
        new = self.vault / "Reading List" / f"{NEW}.md"
        self.assertTrue(new.exists() and not old.exists())
        self.assertNotIn(f"[[{OLD}]]", self.linker.read_text(encoding="utf-8"))
        self.assertIn(f"[[{NEW}]]", self.linker.read_text(encoding="utf-8"))
        self.assertEqual(r.stdout.strip().splitlines()[-1], f"new_path: {new}")
        self.assertEqual(sorted(p.name for p in (self.vault / "Reading List").iterdir()),
                         sorted([new.name, "Linker A.md"]))  # no stray files

    def test_dry_run_rename_previews_link_updates(self):
        old = self.vault / "Reading List" / f"{OLD}.md"
        r = run_env(shim_env(self.root), SCRIPTS / "rename_note.py", old, "--headline", "Short new headline", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("9 links in 1 note", r.stdout)
        self.assertTrue(old.exists())


class Relink(unittest.TestCase):
    """relink.py: repair dead timestamp links and ghost stubs left by on-disk renames."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name).resolve()
        self.vault = make_vault(self.root)
        rl = self.vault / "Reading List"
        (rl / f"{OLD}.md").rename(rl / f"{NEW}.md")                      # renamed on disk; links now dead
        (self.vault / f"{OLD}.md").write_text("", encoding="utf-8")       # Obsidian's empty note at the root
        (rl / "Linker B.md").write_text("[[Gone Title - 2026-01-02T030405-0500]] and [[Lost - 2026-02-02T020202-0500]]\n", encoding="utf-8")
        (rl / "Moved On - 2026-01-02T030405-0500.md").write_text("real\n", encoding="utf-8")
        self.env = shim_env(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def audit(self, *flags):
        return run_env(self.env, SCRIPTS / "relink.py", "--vault", self.vault, *flags)

    def test_dry_run_reports_everything_and_changes_nothing(self):
        snapshot = {p: p.read_bytes() for p in self.vault.rglob("*.md")}
        r = self.audit()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(OLD, r.stdout)
        self.assertIn("ghost stub", r.stdout)
        self.assertIn("Gone Title", r.stdout)
        self.assertIn("Lost - 2026-02-02", r.stdout)  # dead, but no live note to point at
        self.assertIn("nothing changed", r.stdout)
        self.assertEqual(snapshot, {p: p.read_bytes() for p in self.vault.rglob("*.md")})

    def test_apply_fixes_links_and_delete_stubs_moves_the_stub_to_trash(self):
        r = self.audit("--apply", "--delete-stubs")
        self.assertEqual(r.returncode, 0, r.stderr)
        text = (self.vault / "Reading List" / "Linker A.md").read_text(encoding="utf-8")
        self.assertNotIn(f"[[{OLD}]]", text)
        self.assertIn(f"[[{NEW}]]", text)
        self.assertIn("[[Moved On - 2026-01-02T030405-0500]]", (self.vault / "Reading List" / "Linker B.md").read_text(encoding="utf-8"))
        self.assertIn("[[Lost - 2026-02-02T020202-0500]]", (self.vault / "Reading List" / "Linker B.md").read_text(encoding="utf-8"))
        self.assertFalse((self.vault / f"{OLD}.md").exists())
        self.assertTrue((self.vault / ".trash" / f"{OLD}.md").exists())

    def test_apply_without_delete_stubs_leaves_the_stub(self):
        self.audit("--apply")
        self.assertTrue((self.vault / f"{OLD}.md").exists())

    def test_an_empty_note_with_no_real_twin_is_never_treated_as_a_stub(self):
        # 0 bytes but no live note shares its timestamp, so it might be a deliberate placeholder: leave it alone
        (self.vault / "Lonely - 2026-03-03T030303-0500.md").write_text("", encoding="utf-8")
        (self.vault / "Reading List" / "Linker C.md").write_text("[[Lonely - 2026-03-03T030303-0500]]\n", encoding="utf-8")
        self.audit("--apply", "--delete-stubs")
        self.assertTrue((self.vault / "Lonely - 2026-03-03T030303-0500.md").exists())


if __name__ == "__main__":
    unittest.main(verbosity=1)
