#!/usr/bin/env python3
"""Compare the skill's prompt copies with the Obsidian Copilot prompts they came from.

Usage:
    python3 check_prompt_drift.py [--vault-prompts DIR] [--update]

Exit 0 when every copy matches, 1 when any differ. --update copies the vault
versions into references/prompts/ (Copilot frontmatter removed).
"""

from __future__ import annotations

import argparse
import difflib
import sys
from pathlib import Path

PROMPTS = ("rewrite-headline", "generate-tags", "article-summarize", "description-as-author")
DEFAULT_DIR = Path.home() / "Obsidian/vault/copilot/copilot-custom-prompts"
HERE = Path(__file__).resolve().parent.parent / "references" / "prompts"


def strip_frontmatter(text: str) -> str:
    lines = text.split("\n")
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return "\n".join(lines[i + 1 :])
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--vault-prompts", type=Path, default=DEFAULT_DIR)
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    if not args.vault_prompts.is_dir():
        print(f"vault prompt folder not found: {args.vault_prompts}")
        return 2
    drift = False
    for name in PROMPTS:
        src = args.vault_prompts / f"{name}.md"
        dst = HERE / f"{name}.md"
        want = strip_frontmatter(src.read_text(encoding="utf-8")).rstrip() + "\n"
        have = dst.read_text(encoding="utf-8").rstrip() + "\n" if dst.exists() else ""
        if want == have:
            print(f"ok       {name}")
            continue
        drift = True
        if args.update:
            dst.write_text(want, encoding="utf-8")
            print(f"updated  {name}")
        else:
            print(f"DRIFT    {name}")
            sys.stdout.writelines(difflib.unified_diff(
                have.splitlines(True), want.splitlines(True), f"skill/{name}", f"vault/{name}", n=1))
    return 1 if drift and not args.update else 0


if __name__ == "__main__":
    raise SystemExit(main())
