#!/usr/bin/env python3
"""Rename a clipped note to a new headline, keeping its timestamp suffix.

Usage:
    python3 rename_note.py "<note.md>" --headline "New headline" [--dry-run] [--vault PATH]
    python3 rename_note.py "<note.md>" --headline-file /tmp/headline.txt

Cleans the headline for filenames, then renames through the Obsidian CLI so
wikilinks in other notes (e.g. `related:`) are updated. If the CLI is
unavailable or can't reach Obsidian (as in Codex's sandbox), renames on disk
and rewrites the links itself, so no note is left pointing at the old name.
Headlines usually contain an apostrophe or a `$`, both of which the shell mangles
inside quotes, so --headline-file (a text file holding just the headline) is the
safe way to pass one. The file is deleted after a successful rename.
The last line printed is `new_path: <absolute path>`; use it instead of retyping.
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
from notelib import find_vault_root, iter_markdown, rewrite_links, split_stem  # noqa: E402

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


def describe_links(changes: list[tuple[str, int]]) -> str:
    """One line for the report: how many links in how many notes, naming up to five of them."""
    links = sum(n for _, n in changes)
    notes = len(changes)
    if not notes:
        return "0 links in 0 notes"
    names = ", ".join(Path(p).stem for p, _ in changes[:5]) + (", ..." if notes > 5 else "")
    return f"{links} link{'s' if links != 1 else ''} in {notes} note{'s' if notes != 1 else ''} ({names})"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("note")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--headline", help="the new headline (mind shell quoting: apostrophes and $)")
    src.add_argument("--headline-file", help="text file holding the new headline; no quoting needed")
    ap.add_argument("--keep-headline-file", action="store_true", help="don't delete --headline-file after renaming")
    ap.add_argument("--vault", help="vault root (default: nearest parent with .obsidian/)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--long-ok", action="store_true",
                    help=f"accept a headline over {LONG_HEADLINE} characters when every detail is essential")
    args = ap.parse_args()

    old = Path(args.note).expanduser().resolve()
    if not old.is_file():
        print(f"error: file not found: {old}", file=sys.stderr)
        return 1
    raw_headline = args.headline if args.headline is not None else Path(args.headline_file).expanduser().read_text(encoding="utf-8")
    headline = clean_headline(raw_headline)
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

    vault = Path(args.vault).expanduser().resolve() if args.vault else find_vault_root(old)
    if vault and not old.is_relative_to(vault):
        vault = None  # the note isn't in that vault, so the CLI can't reach it
    old_full = old.name[:-3]  # full stem, timestamp included: what other notes link to
    only_folder = None
    if vault:
        twins = [p for p in iter_markdown(vault) if p != old and p.stem.lower() == old_full.lower()]
        if twins:  # a bare [[old name]] could mean either note, so only touch links that name the folder
            only_folder = old.parent.relative_to(vault).as_posix()
            only_folder = "" if only_folder == "." else only_folder
            print(f"warning: {len(twins)} other note(s) share the name '{old_full}'; only links that include the "
                  f"folder '{only_folder or '/'}' will be updated, bare links are left alone", file=sys.stderr)

    print(f"old: {old.name}\nnew: {new.name}")
    if args.dry_run:
        if vault:
            print(f"links that would be updated: {describe_links(rewrite_links(vault, old_full, new_stem, apply=False, only_folder=only_folder))}")
        print("(dry run: nothing renamed)")
        print(f"new_path: {new}")
        return 0

    if vault and shutil.which("obsidian"):
        rel = old.relative_to(vault).as_posix()
        # The CLI exits 0 even on failure, so success is judged by the files on disk.
        cli_said = ""
        try:
            res = subprocess.run(["obsidian", "rename", f"path={rel}", f"name={new_stem}"],
                                 capture_output=True, text=True, timeout=30)
            cli_said = (res.stdout + res.stderr).strip().splitlines()[0] if (res.stdout + res.stderr).strip() else ""
        except subprocess.TimeoutExpired:
            cli_said = "the CLI timed out after 30 seconds"
        except OSError as e:
            cli_said = f"the CLI could not start: {e}"
        if new.exists() and not old.exists():
            print("renamed with the Obsidian CLI")
        else:
            print(f"warning: Obsidian CLI rename did not take effect ({cli_said or 'no output'}); "
                  "renaming on disk and fixing links myself", file=sys.stderr)

    if not new.exists():
        if not old.exists():
            # The CLI may still be mid-rename after a timeout; don't guess.
            print(f"error: {old.name} is gone but {new.name} doesn't exist yet; check the folder before retrying", file=sys.stderr)
            return 1
        os.rename(old, new)
        print("renamed on disk")
    if vault:
        # Obsidian updates links itself when IT renames a note; after an on-disk rename (or if the CLI
        # missed any) the links still point at the old name, and following one creates an empty stub note.
        print(f"links updated: {describe_links(rewrite_links(vault, old_full, new_stem, only_folder=only_folder))}")
    else:
        print("links: not checked (the note is outside a vault; pass --vault to fix links in other notes)")
    if args.headline_file and not args.keep_headline_file:
        Path(args.headline_file).expanduser().unlink(missing_ok=True)
    print(f"new_path: {new}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
