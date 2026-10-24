#!/usr/bin/env python3
"""Write description, note, and new tags into a clipped note's frontmatter.

Usage:
    python3 apply_frontmatter.py "<note.md>" --json '{"description": "...", "note": "...", "add_tags": ["a", "b"]}'
    python3 apply_frontmatter.py "<note.md>" --json-file /tmp/values.json [--dry-run]

Every key in the JSON is optional; include only what you generated.
A --json-file is deleted after a successful write, so no scratch files are
left behind (pass --keep-json-file to keep it).
Only the description, note, and tags lines change. Every other line in the
file, including title, status, source, and related, stays byte-identical.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notelib import Frontmatter  # noqa: E402

TAG_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]*$")
YAML_RESERVED = {"true", "false", "yes", "no", "on", "off", "null", "~"}


def yaml_scalar(value: str) -> str:
    v = " ".join(value.split())  # one line, single spaces
    needs_quotes = (
        not v
        or v[0] in "-?:,[]{}#&*!|>'\"%@`"
        or ": " in v
        or " #" in v
        or v.endswith(":")
        or v.lower() in YAML_RESERVED
        or re.fullmatch(r"[-+]?[\d._]+", v) is not None
    )
    return json.dumps(v, ensure_ascii=False) if needs_quotes else v


def note_block(value: str) -> list[str]:
    paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", value.strip()) if p.strip()]
    out = ["note: |-"]
    for i, p in enumerate(paragraphs):
        if i:
            out.append("")
        out.append("  " + p)
    return out


def clean_tag(tag: str) -> str:
    t = tag.strip().lstrip("#").strip()
    if not TAG_RE.match(t):
        raise ValueError(f"invalid tag {tag!r}: use lowerCamelCase letters and digits, no spaces or '/'")
    return t


def merged_tags(existing: list[str], new: list[str]) -> list[str]:
    seen = {t.lower() for t in existing}
    out = list(existing)
    for t in new:
        c = clean_tag(t)
        if c.lower() not in seen:
            out.append(c)
            seen.add(c.lower())
    # clippings stays first when present
    clip = [t for t in out if t.lower() == "clippings"]
    return clip[:1] + [t for t in out if t.lower() != "clippings"]


def replace_key(lines: list[str], key: str, new_lines: list[str]) -> list[str]:
    """Return lines with key's block replaced (or inserted before `related:` / at the end)."""
    current = Frontmatter("---\n" + "\n".join(lines) + "\n---\n")
    if key in current.spans:
        a, b = current.spans[key]
        # keep blank lines that trail the old block
        while b > a + 1 and lines[b - 1].strip() == "":
            b -= 1
        return lines[:a] + new_lines + lines[b:]
    if "related" in current.spans:
        a, _ = current.spans["related"]
        return lines[:a] + new_lines + lines[a:]
    return lines + new_lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("note")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--json", help="JSON object with description / note / add_tags")
    src.add_argument("--json-file", help="path to a file holding that JSON object")
    ap.add_argument("--dry-run", action="store_true", help="print the diff, write nothing")
    ap.add_argument("--keep-json-file", action="store_true", help="don't delete --json-file after writing")
    ap.add_argument("--force-note", action="store_true", help="allow replacing a non-empty note")
    args = ap.parse_args()

    path = Path(args.note).expanduser().resolve()
    raw = args.json if args.json is not None else Path(args.json_file).read_text(encoding="utf-8")
    try:
        values = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"error: --json is not valid JSON: {e}", file=sys.stderr)
        return 2
    if not isinstance(values, dict):
        print('error: JSON must be an object like {"note": "...", "add_tags": ["a", "b"]}', file=sys.stderr)
        return 2
    unknown = set(values) - {"description", "note", "add_tags"}
    if unknown:
        print(f"error: unsupported keys {sorted(unknown)}; only description, note, add_tags", file=sys.stderr)
        return 2
    for key in ("description", "note"):
        if key in values and not isinstance(values[key], str):
            print(f"error: {key} must be a string", file=sys.stderr)
            return 2
    if "add_tags" in values and not (
        isinstance(values["add_tags"], list) and all(isinstance(t, str) for t in values["add_tags"])
    ):
        print('error: add_tags must be a list of strings, e.g. ["analysis", "antitrust"]', file=sys.stderr)
        return 2

    text = path.read_text(encoding="utf-8")
    fm = Frontmatter(text)
    if not fm.ok:
        print("error: note has no YAML frontmatter", file=sys.stderr)
        return 1
    lines = list(fm.lines)

    if "description" in values:
        lines = replace_key(lines, "description", ["description: " + yaml_scalar(values["description"])])
    if "note" in values:
        if fm.scalar("note") and not args.force_note:
            print("error: note already has a summary; refusing to overwrite (use --force-note if the user asked)", file=sys.stderr)
            return 1
        lines = replace_key(lines, "note", note_block(values["note"]))
    if "add_tags" in values:
        try:
            tags = merged_tags(fm.items("tags"), list(values["add_tags"]))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        lines = replace_key(lines, "tags", ["tags:"] + [f"  - {t}" for t in tags])

    new_text = "\n".join(["---", *lines, "---"]) + "\n" + fm.body
    if new_text == text:
        print("no changes")
        return 0
    diff = difflib.unified_diff(text.splitlines(), new_text.splitlines(), "before", "after", lineterm="", n=0)
    print("\n".join(diff))
    if args.dry_run:
        print("(dry run: nothing written)")
        return 0
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".enrich-", suffix=".md")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    os.replace(tmp, path)
    print(f"written: {path}")
    if args.json_file and not args.keep_json_file:
        Path(args.json_file).unlink(missing_ok=True)
        print(f"removed {args.json_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
