"""Shared helpers for the obsidian-article-enrichment scripts. Standard library only."""

from __future__ import annotations

import os
import re
import unicodedata
from pathlib import Path

TIMESTAMP_RE = re.compile(r" - (\d{4}-\d{2}-\d{2}T\d{6}-\d{4})$")
TOP_KEY_RE = re.compile(r"^([A-Za-z_][\w-]*):(.*)$")

PODCAST_HOSTS = ("sharptech.fm", "sharpchina.fm", "dithering", "podcast", "/episode")
NON_HEADLINE_RE = re.compile(
    r"(\bon (x|twitter|bluesky|threads|mastodon|linkedin)$)|(^untitled$)|(^\(\d+\) )",
    re.IGNORECASE,
)


# ---------- frontmatter ----------

class Frontmatter:
    """Line-level view of a note's YAML frontmatter.

    Keeps the original lines so a writer can replace one top-level key
    without reformatting anything else.
    """

    def __init__(self, text: str):
        self.text = text
        self.ok = False
        self.lines: list[str] = []
        self.body = text
        self.spans: dict[str, tuple[int, int]] = {}  # key -> [start, end) line indexes
        if not text.startswith("---"):
            return
        all_lines = text.split("\n")
        if all_lines[0].strip() != "---":
            return
        for end in range(1, len(all_lines)):
            if all_lines[end].strip() == "---":
                break
        else:
            return
        self.ok = True
        self.lines = all_lines[1:end]
        self.body = "\n".join(all_lines[end + 1 :])
        current = None
        for i, line in enumerate(self.lines):
            m = TOP_KEY_RE.match(line)
            if m and not line.startswith((" ", "\t")):
                if current:
                    self.spans[current] = (self.spans[current][0], i)
                current = m.group(1)
                self.spans[current] = (i, len(self.lines))
        # spans already end at len(lines) for the last key

    def raw(self, key: str) -> list[str]:
        if key not in self.spans:
            return []
        a, b = self.spans[key]
        return self.lines[a:b]

    def scalar(self, key: str) -> str:
        """Value of a scalar key, including `|`/`|-`/`>` block scalars."""
        raw = self.raw(key)
        if not raw:
            return ""
        first = raw[0].split(":", 1)[1].strip()
        if first in ("|", "|-", "|+", ">", ">-", ">+"):
            body = [l[2:] if l.startswith("  ") else l.strip() for l in raw[1:]]
            return "\n".join(body).strip()
        return unquote(first)

    def items(self, key: str) -> list[str]:
        """Items of a list key, in block (`- a`) or flow (`[a, b]`) style."""
        raw = self.raw(key)
        if not raw:
            return []
        first = raw[0].split(":", 1)[1].strip()
        if first.startswith("["):
            inner = first.strip("[]")
            return [unquote(x.strip()) for x in inner.split(",") if x.strip()]
        if first:
            return [unquote(first)]
        out = []
        for line in raw[1:]:
            s = line.strip()
            if s.startswith("- "):
                out.append(unquote(s[2:].strip()))
            elif s == "-":
                continue
        return [x for x in out if x]


def unquote(value: str) -> str:
    """Strip one pair of surrounding YAML quotes, undoing the escapes each quote style uses."""
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        inner = value[1:-1]
        if value[0] == '"':
            inner = inner.replace('\\"', '"').replace("\\\\", "\\")
        else:
            inner = inner.replace("''", "'")
        return inner
    return value


def clean_author(a: str) -> str:
    return re.sub(r"[\[\]\"]", "", a).strip().lstrip("@").strip()


# ---------- names and titles ----------

def split_stem(filename: str) -> tuple[str, str | None]:
    """'Title - 2026-01-01T120000-0500.md' -> ('Title', '2026-01-01T120000-0500')."""
    stem = filename[:-3] if filename.endswith(".md") else filename
    m = TIMESTAMP_RE.search(stem)
    if m:
        return stem[: m.start()], m.group(1)
    return stem, None


def norm(s: str) -> str:
    """Alphanumerics only, lowercase. Ignores the punctuation changes filenames force."""
    s = unicodedata.normalize("NFKC", s).lower()
    return re.sub(r"[^0-9a-z]+", "", s)


def is_renamed(title: str, stem: str) -> bool:
    """True when the filename carries a different headline than the frontmatter title."""
    t, f = norm(title), norm(stem)
    if not t or not f:
        return False
    if t == f:
        return False
    # Long titles are sometimes truncated in the filename; a prefix still counts as kept.
    if len(f) >= 20 and t.startswith(f):
        return False
    return True


def domain_of(url: str) -> str:
    m = re.match(r"https?://(?:www\.)?([^/?#]+)", url or "")
    return m.group(1).lower() if m else ""


def classify(title: str, source: str) -> str:
    """Format bucket used for rename history: weekly-roundup, interview, non-headline, podcast, update, or article."""
    t = title.strip()
    if re.match(r"^\d{4}\.\d{2}\b", t):
        return "weekly-roundup"
    if re.match(r"^(an )?interview with\b", t, re.IGNORECASE):
        return "interview"
    if NON_HEADLINE_RE.search(t) or not t:
        return "non-headline"
    src = (source or "").lower()
    if any(h in src for h in PODCAST_HOSTS):
        return "podcast"
    if t.count(",") >= 2 or t.count(";") >= 1:
        return "update"
    return "article"


# ---------- vault ----------

def find_vault_root(note: Path) -> Path | None:
    for parent in [note.parent, *note.parents]:
        if (parent / ".obsidian").is_dir():
            return parent
    return None


def iter_clippings(vault: Path, skip: Path | None = None):
    """Yield (path, Frontmatter) for every note tagged `clippings`."""
    skip = skip.resolve() if skip else None
    for root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        for name in files:
            if not name.endswith(".md"):
                continue
            p = Path(root) / name
            if skip and p.resolve() == skip:
                continue
            try:
                with open(p, encoding="utf-8") as fh:
                    head = fh.read(16000)
            except (OSError, UnicodeDecodeError):
                continue
            fm = Frontmatter(head)
            if not fm.ok:
                continue
            if "clippings" not in [t.lower() for t in fm.items("tags")]:
                continue
            yield p, fm
