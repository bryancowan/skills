#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
marketplace_file="$repo_root/.agents/plugins/marketplace.json"
plugin_root="$repo_root/plugins/personal-skills"
plugin_file="$plugin_root/plugin.json"
bundle_root="$plugin_root/skills"
skill_dirs=(
  description-and-tags
  good-documentation
  obsidian-jd-organizer
  obsidian-wiki-compiler
  prompt-creation
)

python3 - "$marketplace_file" "$plugin_file" "$plugin_root" "${skill_dirs[@]}" <<'PY'
import json
import pathlib
import re
import sys

marketplace_path = pathlib.Path(sys.argv[1])
plugin_path = pathlib.Path(sys.argv[2])
plugin_root = pathlib.Path(sys.argv[3])
expected_dirs = sys.argv[4:]

with marketplace_path.open(encoding="utf-8") as handle:
    marketplace = json.load(handle)
with plugin_path.open(encoding="utf-8") as handle:
    plugin = json.load(handle)

assert marketplace["name"] == "bryancowan-skills"
assert len(marketplace["plugins"]) == 1
entry = marketplace["plugins"][0]
assert entry["name"] == "personal-skills"
assert entry["source"] == {"source": "local", "path": "./plugins/personal-skills"}
assert plugin["name"] == "personal-skills"
assert plugin["version"] == "1.0.0"

actual_dirs = sorted(path.name for path in (plugin_root / "skills").iterdir() if path.is_dir())
assert actual_dirs == sorted(expected_dirs), (actual_dirs, expected_dirs)

for directory in expected_dirs:
    skill_file = plugin_root / "skills" / directory / "SKILL.md"
    text = skill_file.read_text(encoding="utf-8")
    assert re.search(r"(?m)^name:\s*['\"]?[^'\"\n]+", text), skill_file
PY

for skill_dir in "${skill_dirs[@]}"; do
  diff -qr "$repo_root/skills/$skill_dir" "$bundle_root/$skill_dir"
done
