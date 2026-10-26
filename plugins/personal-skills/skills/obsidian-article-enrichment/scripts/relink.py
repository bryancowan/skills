#!/usr/bin/env python3
"""Find and repair dead links to renamed clippings, and the empty notes those dead links leave behind.

Usage:
    python3 relink.py [--vault PATH]                          # report only (default)
    python3 relink.py [--vault PATH] --apply                  # rewrite the dead links
    python3 relink.py [--vault PATH] --apply --delete-stubs   # also remove the empty stub notes
    python3 relink.py --apply --delete-stubs --only "Birth & Rise"   # limit everything to matching names

Clipped notes end in a unique ` - YYYY-MM-DDTHHMMSS-ZZZZ` timestamp that survives a rename, so a link to a
name that no longer exists can be matched to the one live note with the same timestamp.

A *ghost stub* is a 0-byte note that shares a timestamp with a real note: following a dead link in Obsidian
creates one, in the vault root, under the old name. Stubs are only removed with --delete-stubs, only when
0 bytes, and only after nothing links to them any more. They go to the Obsidian trash (or `.trash/`).
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from notelib import TIMESTAMP_RE, find_vault_root, iter_markdown, rewrite_links  # noqa: E402

LINK_RE = re.compile(r"!?\[\[([^\]|#^\[]+)")


def scan(vault: Path) -> dict:
    """Index the vault; return dead timestamp links (with the live note each should point at) and ghost stubs."""
    by_stem: dict[str, list[Path]] = defaultdict(list)
    by_ts: dict[str, list[Path]] = defaultdict(list)
    for p in iter_markdown(vault):
        by_stem[p.stem.lower()].append(p)
        m = TIMESTAMP_RE.search(p.stem)
        if m:
            by_ts[m.group(1).lower()].append(p)

    stubs = {}
    for ts, paths in by_ts.items():
        real = [p for p in paths if p.stat().st_size > 0]
        if len(real) == 1:
            for p in paths:
                if p.stat().st_size == 0:
                    stubs[p] = real[0]
    live_stems = {s for s, ps in by_stem.items() if any(p not in stubs for p in ps)}

    targets: dict[str, str] = {}  # lowercase dead stem -> stem as first written
    for p in iter_markdown(vault):
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for m in LINK_RE.finditer(text):
            target = m.group(1).strip().rstrip("\\").strip().split("/")[-1]  # [[x\|alias]] in a table leaves a "\" on the target
            target = target[:-3] if target.lower().endswith(".md") else target
            tm = TIMESTAMP_RE.search(target)
            if tm and target.lower() not in live_stems:
                targets.setdefault(target.lower(), target)

    dead = []
    for low, target in sorted(targets.items()):
        ts = TIMESTAMP_RE.search(target).group(1).lower()
        real = [p for p in by_ts.get(ts, []) if p not in stubs and p.stat().st_size > 0]
        dead.append({"target": target, "live": real[0].stem if len(real) == 1 else None,
                     "why": None if len(real) == 1 else ("no live note has this timestamp" if not real
                                                         else f"{len(real)} live notes share this timestamp")})
    return {"dead": dead, "stubs": stubs}


def describe(changes: list[tuple[str, int]]) -> str:
    links, notes = sum(n for _, n in changes), len(changes)
    names = ", ".join(Path(p).stem[:50] for p, _ in changes[:3]) + (", ..." if notes > 3 else "")
    return f"{links} link{'s' if links != 1 else ''} in {notes} note{'s' if notes != 1 else ''} ({names})"


def delete_stub(vault: Path, stub: Path) -> str:
    """Trash a stub through Obsidian when possible, else move it to .trash/. Returns where it went."""
    rel = stub.relative_to(vault).as_posix()
    if shutil.which("obsidian"):
        try:
            subprocess.run(["obsidian", "delete", f"path={rel}"], capture_output=True, text=True, timeout=30)
        except (subprocess.TimeoutExpired, OSError):
            pass
        if not stub.exists():  # the CLI exits 0 even on failure, so check the disk
            return "Obsidian trash"
    trash = vault / ".trash"
    trash.mkdir(exist_ok=True)
    dest, n = trash / stub.name, 1
    while dest.exists():
        n += 1
        dest = trash / f"{stub.stem} {n}{stub.suffix}"
    shutil.move(str(stub), str(dest))
    return f".trash/{dest.name}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault", help="vault root (default: nearest parent of the current folder with .obsidian/)")
    ap.add_argument("--apply", action="store_true", help="rewrite the dead links that have exactly one live match")
    ap.add_argument("--only", action="append", metavar="TEXT",
                    help="only act on dead links and stubs whose name contains TEXT (repeatable, case-insensitive)")
    ap.add_argument("--delete-stubs", action="store_true", help="with --apply, remove empty ghost stubs that nothing links to")
    args = ap.parse_args()
    vault = Path(args.vault).expanduser().resolve() if args.vault else find_vault_root(Path.cwd().resolve() / "_")
    if not vault or not vault.is_dir():
        print("error: vault not found; pass --vault <path>", file=sys.stderr)
        return 2

    found = scan(vault)
    dead, stubs = found["dead"], found["stubs"]
    if args.only:
        keep = lambda name: any(o.lower() in name.lower() for o in args.only)  # noqa: E731
        hidden = len(dead) - sum(keep(d["target"]) for d in dead) + len(stubs) - sum(keep(s.name) for s in stubs)
        dead = [d for d in dead if keep(d["target"])]
        stubs = {s: r for s, r in stubs.items() if keep(s.name)}
        if hidden:
            print(f"(--only: {hidden} other dead link target(s) or stub(s) not shown and not touched)")
    print(f"vault: {vault}")
    print(f"dead links: {len(dead)} target{'s' if len(dead) != 1 else ''}")
    for d in dead:
        if d["live"]:
            would = rewrite_links(vault, d["target"], d["live"], apply=False)
            print(f"  fixable   {d['target']}\n         -> {d['live']}\n            {describe(would)}")
        else:
            print(f"  UNFIXABLE {d['target']}\n            {d['why']}; edit by hand or remove the link")
    print(f"ghost stubs (empty notes Obsidian made from a dead link): {len(stubs)}")
    for stub, real in sorted(stubs.items()):
        print(f"  {stub.relative_to(vault).as_posix()}  (0 bytes)\n         real note: {real.relative_to(vault).as_posix()}")

    if not args.apply:
        print("\nnothing changed. Re-run with --apply (and --delete-stubs) to repair."
              if (dead or stubs) else "\nnothing to repair.")
        if args.delete_stubs:
            print("note: --delete-stubs only takes effect together with --apply.")
        return 0

    print()
    for d in dead:
        if d["live"]:
            print(f"fixed: {describe(rewrite_links(vault, d['target'], d['live']))}")
    if args.delete_stubs:
        for stub, real in sorted(stubs.items()):
            if stub.stat().st_size != 0:
                print(f"kept {stub.name}: no longer empty")
            elif rewrite_links(vault, stub.stem, real.stem, apply=True):
                print(f"fixed and kept for now: links to {stub.name} were still present; run again to remove it")
            else:
                print(f"deleted {stub.relative_to(vault).as_posix()} -> {delete_stub(vault, stub)}")
    elif stubs:
        print(f"{len(stubs)} ghost stub(s) left in place (add --delete-stubs to remove them)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
