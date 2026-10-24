#!/usr/bin/env python3
"""Report what a clipped Obsidian note needs, and whether its file should be renamed.

Usage:
    python3 analyze_note.py "<path/to/note.md>" [--vault <vault root>]

Prints one JSON object. Read-only: never modifies any file.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notelib import (  # noqa: E402
    Frontmatter,
    classify,
    clean_author,
    domain_of,
    find_vault_root,
    is_renamed,
    iter_clippings,
    norm,
    split_stem,
)

PUBLISHER_VOICE_RE = re.compile(
    r"^(we['’]re |we are |we['’]ve |in this (post|article|episode|issue)\b|subscribe\b|"
    r"read more\b|click\b|learn more\b|sign up\b|listen (to|now)\b|watch\b)",
    re.IGNORECASE,
)
TAG_THRESHOLD = 4
MIN_HISTORY = 3
RENAME_RATE = 0.70
KEEP_RATE = 0.30


def description_check(desc: str, title: str, boilerplate: bool) -> tuple[bool, str]:
    d = desc.strip()
    if not d:
        return True, "empty"
    if norm(d) == norm(title):
        return True, "same as title"
    if d.endswith(("…", "...")):
        return True, "truncated publisher blurb (ends in an ellipsis)"
    if PUBLISHER_VOICE_RE.search(d):
        return True, "publisher or marketing voice"
    if boilerplate:
        return True, "same text appears on other notes from this site (site boilerplate)"
    return False, "looks like a real subheading; keep it"


def bucket_lean(kept: int, renamed: int) -> str | None:
    n = kept + renamed
    if n < MIN_HISTORY:
        return None
    rate = renamed / n
    if rate >= RENAME_RATE:
        return "rename"
    if rate <= KEEP_RATE:
        return "keep"
    return "unclear"


def analyze(note: Path, vault: Path | None) -> dict:
    text = note.read_text(encoding="utf-8")
    fm = Frontmatter(text)
    if not fm.ok:
        return {"error": "no YAML frontmatter found", "path": str(note)}

    title = fm.scalar("title")
    source = fm.scalar("source")
    domain = domain_of(source)
    authors = [clean_author(a) for a in fm.items("author")]
    authors = [a for a in authors if a]
    tags = fm.items("tags")
    stem, timestamp = split_stem(note.name)
    fmt = classify(title, source)
    already = is_renamed(title, stem)

    # ---- walk the vault once: history + description boilerplate ----
    history = {a: defaultdict(lambda: [0, 0]) for a in authors}
    site = defaultdict(lambda: [0, 0])  # same site, any author
    examples: list[tuple[str, str, str, bool]] = []
    site_examples: list[tuple[str, str, str, bool]] = []
    desc_counts: Counter[str] = Counter()
    my_desc = norm(fm.scalar("description"))
    vault_rel = None
    if vault:
        try:
            vault_rel = str(note.resolve().relative_to(vault.resolve()))
        except ValueError:
            vault_rel = None
        for p, other in iter_clippings(vault, skip=note):
            o_src = other.scalar("source")
            o_dom = domain_of(o_src)
            if my_desc and o_dom == domain and norm(other.scalar("description")) == my_desc:
                desc_counts[my_desc] += 1
            if not other.scalar("note"):
                continue  # never enriched, so it says nothing about rename habits
            o_title = other.scalar("title")
            o_stem, _ = split_stem(p.name)
            renamed = is_renamed(o_title, o_stem)
            o_fmt = classify(o_title, o_src)
            if o_dom == domain and domain:
                site[(o_dom, "all")][renamed] += 1
                site[(o_dom, o_fmt)][renamed] += 1
                if o_fmt == fmt:
                    site_examples.append((other.scalar("created"), o_title, o_stem, renamed))
            o_auth = {clean_author(a) for a in other.items("author")}
            shared = [a for a in authors if a in o_auth]
            if not shared:
                continue
            for a in shared:
                h = history[a]
                h[("all", "all")][renamed] += 1
                h[(o_dom, "all")][renamed] += 1
                h[(o_dom, o_fmt)][renamed] += 1
            if o_dom == domain and o_fmt == fmt:
                examples.append((other.scalar("created"), o_title, o_stem, renamed))

    boilerplate = desc_counts[my_desc] >= 2 if my_desc else False
    d_need, d_reason = description_check(fm.scalar("description"), title, boilerplate)
    n_need = not fm.scalar("note")
    t_need = len(tags) <= TAG_THRESHOLD

    # ---- rename lean: hard rules first, then most specific history bucket ----
    hist_out = {}
    lean, basis = None, None
    for a in authors:
        h = history[a]
        hist_out[a] = {
            "all": dict(zip(("kept", "renamed"), h[("all", "all")])),
            f"site {domain}": dict(zip(("kept", "renamed"), h[(domain, "all")])),
            f"site {domain} + format {fmt}": dict(zip(("kept", "renamed"), h[(domain, fmt)])),
        }
    if already:
        lean, basis = "skip", "filename already differs from title; it was renamed before"
    elif fmt in ("interview", "weekly-roundup"):
        lean, basis = "keep", f"{fmt} titles are never renamed"
    elif fmt == "non-headline":
        lean, basis = "rename", "title is not a headline (e.g. 'Name on X')"
    else:
        for level, label in (((domain, fmt), "author + site + format"), ((domain, "all"), "author + site"), (("all", "all"), "author overall")):
            votes = [bucket_lean(*history[a][level]) for a in authors]
            votes = [v for v in votes if v]
            if votes:
                lean = votes[0] if len(set(votes)) == 1 else "unclear"
                basis = f"history at level: {label}"
                break
        if not lean:
            for level, label in (((domain, fmt), "site + format, any author"), ((domain, "all"), "site, any author")):
                v = bucket_lean(*site[level])
                if v:
                    lean, basis = v, f"history at level: {label} (author history too thin)"
                    break
        if not lean:
            lean, basis = "unclear", "fewer than 3 enriched notes by this author or from this site"
    hist_out[f"(any author) site {domain}"] = dict(zip(("kept", "renamed"), site[(domain, "all")]))
    hist_out[f"(any author) site {domain} + format {fmt}"] = dict(zip(("kept", "renamed"), site[(domain, fmt)]))
    if not examples:
        examples = site_examples

    examples.sort(key=lambda e: e[0] or "", reverse=True)
    return {
        "path": str(note),
        "vault_relative_path": vault_rel,
        "title": title,
        "authors": authors,
        "source_domain": domain,
        "format": fmt,
        "timestamp_suffix": timestamp,
        "existing_tags": tags,
        "fields": {
            "description": {"needs_work": d_need, "reason": d_reason},
            "note": {"needs_work": n_need, "reason": "empty" if n_need else "already written; never overwrite"},
            "tags": {"needs_work": t_need, "reason": f"{len(tags)} tags (generate when {TAG_THRESHOLD} or fewer)"},
        },
        "rename": {
            "already_renamed": already,
            "lean": lean,
            "basis": basis,
            "history": hist_out,
            "examples": [
                {"title": t, "filename": s, "renamed": r} for _, t, s, r in examples[:5]
            ],
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("note")
    ap.add_argument("--vault", help="vault root (default: nearest parent with .obsidian/)")
    args = ap.parse_args()
    note = Path(args.note).expanduser().resolve()
    if not note.is_file():
        print(json.dumps({"error": f"file not found: {note}"}))
        return 1
    vault = Path(args.vault).expanduser() if args.vault else find_vault_root(note)
    result = analyze(note, vault)
    if vault is None:
        result["warning"] = "vault root not found; no history used. Pass --vault."
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
