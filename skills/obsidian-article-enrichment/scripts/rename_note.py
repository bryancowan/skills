#!/usr/bin/env python3
"""Rename a clipped note to a new headline, keeping its timestamp suffix.

Usage:
    python3 rename_note.py "<note.md>" --headline "New headline" [--dry-run] [--vault PATH]

Cleans the headline for filenames, then renames through the Obsidian CLI so
wikilinks in other notes (e.g. `related:`) are updated. If the CLI is
unavailable or fails, falls back to a plain rename and lists the notes whose
links now point at the old name.
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notelib import find_vault_root, split_stem  # noqa: E402

MAX_NAME_BYTES = 255
# Bryan's own renamed headlines: median ~119 characters, 11% over 150, 2% over 180.
LONG_HEADLINE = 180


def clean_headline(h: str) -> str:
    """Apply the filename rules from references/prompts/rewrite-headline.md."""
    h = "".join(ch for ch in h if unicodedata.category(ch) not in ("Cf", "Cc"))
    h = h.strip()
    # A model may wrap the whole headline in double quotes; single quotes are left
    # alone because a headline can legitimately end on a quoted phrase.
    if len(h) >= 2 and h[0] in "\"“" and h[-1] in "\"”":
        h = h[1:-1].strip()
    h = re.sub(r"\s*:\s*", " - ", h)
    h = re.sub(r"[\"“”‘’]", "'", h)
    h = re.sub(r"[?*<>|\\/$`!\[\]{}]", "", h)
    h = re.sub(r"\s+", " ", h).strip()
    return h.rstrip(". ").strip()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("note")
    ap.add_argument("--headline", required=True)
    ap.add_argument("--vault", help="vault root (default: nearest parent with .obsidian/)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--long-ok", action="store_true",
                    help=f"accept a headline over {LONG_HEADLINE} characters when every detail is essential")
    args = ap.parse_args()

    old = Path(args.note).expanduser().resolve()
    if not old.is_file():
        print(f"error: file not found: {old}", file=sys.stderr)
        return 1
    headline = clean_headline(args.headline)
    if not headline:
        print("error: headline is empty after cleaning", file=sys.stderr)
        return 2
    if len(headline) > LONG_HEADLINE and not args.long_ok:
        print(f"error: headline is {len(headline)} characters. Bryan's renamed headlines are usually 100-135 and only "
              f"2% exceed {LONG_HEADLINE}. Cut the least essential clause (often whatever follows a semicolon) and try "
              f"again, or rerun with --long-ok if every detail is essential.", file=sys.stderr)
        return 3
    old_stem, ts = split_stem(old.name)
    new_stem = f"{headline} - {ts}" if ts else headline
    new = old.with_name(new_stem + ".md")
    if len(new.name.encode("utf-8")) > MAX_NAME_BYTES:
        print(f"error: filename would be {len(new.name.encode())} bytes (limit {MAX_NAME_BYTES}); shorten the headline", file=sys.stderr)
        return 2
    if new == old:
        print("unchanged: headline matches the current filename")
        return 0
    if new.exists():
        print(f"error: a file with that name already exists: {new.name}", file=sys.stderr)
        return 1

    print(f"old: {old.name}\nnew: {new.name}")
    if args.dry_run:
        print("(dry run: nothing renamed)")
        return 0

    vault = Path(args.vault).expanduser().resolve() if args.vault else find_vault_root(old)
    if vault and not old.is_relative_to(vault):
        vault = None  # the note isn't in that vault, so the CLI can't reach it
    if vault and shutil.which("obsidian"):
        rel = old.relative_to(vault).as_posix()
        # The CLI exits 0 even on failure, so success is judged by the files on disk.
        try:
            subprocess.run(["obsidian", "rename", f"path={rel}", f"name={new_stem}"],
                           capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            pass  # the disk check below decides whether the CLI rename took effect
        if new.exists() and not old.exists():
            print("renamed with the Obsidian CLI; links in other notes were updated")
            return 0
        print("warning: Obsidian CLI rename did not take effect (is Obsidian running?); falling back", file=sys.stderr)

    if not old.exists():
        # The CLI may still be mid-rename after a timeout; don't guess.
        print(f"error: {old.name} is gone but {new.name} doesn't exist yet; check the folder before retrying", file=sys.stderr)
        return 1
    os.rename(old, new)
    print("renamed on disk (links in other notes were NOT updated)")
    if vault:
        needle = f"[[{old_stem}{' - ' + ts if ts else ''}"
        stale = []
        for root, dirs, files in os.walk(vault):
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            for f in files:
                if f.endswith(".md"):
                    p = Path(root) / f
                    try:
                        if needle in p.read_text(encoding="utf-8"):
                            stale.append(p.relative_to(vault).as_posix())
                    except (OSError, UnicodeDecodeError):
                        pass
        if stale:
            print("notes still linking to the old name (tell the user):")
            for s in stale:
                print(f"  {s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
