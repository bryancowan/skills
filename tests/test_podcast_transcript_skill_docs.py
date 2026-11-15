"""Run the commands in skills/podcast-transcript/SKILL.md exactly as written.

The scripts have unit tests, but an agent follows the *document*. Reviews of the diarized-SRT PR
found commands that failed or misbehaved as written (an append guard that printed ABORT and then
appended anyway, literal [--flag] brackets, a snippet using an undefined variable). This extracts the
fenced blocks and executes them so that drift between SKILL.md and the scripts fails CI.

Run from the repo root:  python3 -m unittest tests/test_podcast_transcript_skill_docs.py
"""

import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.dont_write_bytecode = True  # keep __pycache__ out of the bundled skill dir
ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "podcast-transcript"
SCRIPTS = SKILL / "scripts"
DOC = (SKILL / "SKILL.md").read_text(encoding="utf-8")
BLOCKS = re.findall(r"```(bash|python)\n(.*?)```", DOC, re.S)

SRT = (
    "1\n00:00:01,000 --> 00:00:03,000\nSpeaker 1: Welcome to the show, I'm Andrew.\n\n"
    "2\n00:00:04,000 --> 00:00:06,000\nSpeaker 2: Thanks for having me, Andrew.\n\n"
    "3\n00:00:07,000 --> 00:00:09,000\nSpeaker 3: Great to be here.\n\n"
    "4\n00:00:10,000 --> 00:00:12,000\nSpeaker 4: Let's get started.\n"
)


def block(lang, needle):
    found = [b for lng, b in BLOCKS if lng == lang and needle in b]
    assert len(found) == 1, f"expected exactly one {lang} block containing {needle!r}, found {len(found)}"
    return found[0]


class SkillDocCommands(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-docs-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "ep.srt").write_text(SRT, encoding="utf-8")
        self.body = self.tmp / "transcript_body.md"
        self.env = {**os.environ, "SRT_FILE": str(self.tmp / "ep.srt")}

    def sh(self, cmd, env=None, cwd=None):
        return subprocess.run(["bash", "-c", cmd], cwd=cwd or self.tmp, env=env or self.env,
                              capture_output=True, text=True)

    def build_body(self):
        cmd = block("bash", "--fixes-file fixes.txt")
        cmd = cmd.replace("scripts/parse_srt.py", str(SCRIPTS / "parse_srt.py"))
        cmd = cmd.replace("/tmp/transcript_body.md", str(self.body)).replace(
            "/tmp/transcript_review.txt", str(self.tmp / "review.txt"))
        r = self.sh(cmd)
        self.assertEqual(r.returncode, 0, r.stderr)
        return self.body.read_text(encoding="utf-8")

    def test_step_1d_build_command_runs_as_written(self):
        body = self.build_body()
        self.assertIn("**Andrew:** Welcome to the show", body)
        self.assertIn("**Bill:** Thanks for having me, Andrew. Great to be here.", body)

    def test_step_5_snippet_builds_labeled_paragraphs_from_the_body(self):
        body = self.build_body()
        snippet = block("python", "labeled_paragraphs = re.findall").replace("/tmp/transcript_body.md", str(self.body))
        ns = {}
        exec(snippet, ns)  # noqa: S102 - executing our own documentation snippet is the point
        self.assertEqual(len(ns["labeled_paragraphs"]), len(re.findall(r"^\*\*", body, re.M)))
        self.assertEqual(ns["labeled_paragraphs"][0][0], "Andrew")

    def test_step_6_verifies_the_output_file_in_new_file_mode(self):
        body = self.build_body()
        out = self.tmp / "out.md"
        out.write_text("---\ntitle: T\n---\n\n## Transcript\n\n" + body, encoding="utf-8")
        cmd = block("bash", "TARGET_MD=").replace("scripts/verify_transcript.py", str(SCRIPTS / "verify_transcript.py"))
        env = {k: v for k, v in self.env.items() if k != "NOTE_FILE"}   # new-file mode has no NOTE_FILE
        env.update(OUTPUT_MODE="new-file", OUTPUT_FILE=str(out))
        r = self.sh(cmd, env=env)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TypeWhisperSyncReference(unittest.TestCase):
    """references/typewhisper-sync.md states the prune thresholds; they must match the script."""

    def test_documented_prune_numbers_match_the_script_constants(self):
        sys.path.insert(0, str(SCRIPTS))
        import sync_typewhisper as sync

        ref = (SKILL / "references" / "typewhisper-sync.md").read_text(encoding="utf-8")
        self.assertIn(f"{sync.SWAP_RATIO}×", ref)
        self.assertIn(f"beat it by {sync.SWAP_MIN_GAIN}", ref)
        self.assertIn(f"{sync.DEFAULT_MAX_PRUNE} terms", ref)
        self.assertIn(f"at least {sync.MIN_CORPUS_EPISODES}", ref)
        self.assertTrue(str(sync.BACKUP_DIR).endswith(".podcast-transcript/backups"))
        self.assertIn("term_entries", ref)
        self.assertIn("never pruned", ref)
        self.assertIn(".podcast-transcript/backups", ref)

    def test_skill_md_points_at_the_reference_and_it_exists(self):
        self.assertIn("references/typewhisper-sync.md", DOC)
        self.assertTrue((SKILL / "references" / "typewhisper-sync.md").is_file())
        self.assertTrue((SKILL / "references" / "typewhisper-keep.txt").is_file())


@unittest.skipUnless(shutil.which("rg"), "ripgrep (rg) is what SKILL.md uses for the guard")
class AppendGuard(unittest.TestCase):
    """The duplicate-transcript guard must actually stop the append, not just print ABORT."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="skill-guard-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        (self.tmp / "vault" / "Reading List").mkdir(parents=True)
        (self.tmp / "bin").mkdir()
        stub = self.tmp / "bin" / "obsidian"
        stub.write_text(f'#!/bin/bash\necho "$@" >> "{self.tmp}/obsidian.log"\n')
        stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
        (self.tmp / "transcript_body.md").write_text("**Andrew:** hi\n", encoding="utf-8")
        self.note = self.tmp / "vault" / "Reading List" / "My Note.md"

    def run_guard(self):
        cmd = block("bash", 'rg -q "^## Transcript"')
        cmd = cmd.replace("/abs/vault/$NOTEP", f"{self.tmp}/vault/$NOTEP")
        cmd = cmd.replace("/tmp/transcript_body.md", str(self.tmp / "transcript_body.md"))
        cmd = cmd.replace("/tmp/note_before_transcript.md", str(self.tmp / "before.md"))
        env = {**os.environ, "PATH": f"{self.tmp / 'bin'}{os.pathsep}{os.environ['PATH']}"}
        r = subprocess.run(["bash", "-c", cmd], cwd=self.tmp, env=env, capture_output=True, text=True)
        return r, (self.tmp / "obsidian.log").exists()

    def test_existing_transcript_aborts_and_never_appends(self):
        self.note.write_text("---\ntitle: T\n---\n\n## Transcript\n\n**Andrew:** already here.\n", encoding="utf-8")
        r, appended = self.run_guard()
        self.assertIn("ABORT: note already has", r.stdout)
        self.assertFalse(appended)

    def test_clean_note_is_appended(self):
        self.note.write_text("---\ntitle: T\n---\nIntro.\n", encoding="utf-8")
        r, appended = self.run_guard()
        self.assertTrue(appended, r.stdout + r.stderr)
        self.assertNotIn("ABORT", r.stdout)

    def test_unreadable_note_aborts_instead_of_appending(self):
        # rg exits 2 for a missing file; that must not be mistaken for "no transcript yet"
        r, appended = self.run_guard()
        self.assertIn("ABORT: could not read", r.stdout)
        self.assertFalse(appended)


if __name__ == "__main__":
    unittest.main(verbosity=2)
