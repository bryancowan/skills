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


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def frontmatter_name(skill_file):
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0] == "---", f"missing initial YAML frontmatter: {skill_file}")
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        raise SystemExit(f"unterminated YAML frontmatter: {skill_file}")

    frontmatter = "\n".join(lines[1:closing_index])
    require(
        re.search(r"(?m)^name:\s*['\"]?[^'\"\n]+", frontmatter),
        f"missing frontmatter name: {skill_file}",
    )


marketplace_path = pathlib.Path(sys.argv[1])
plugin_path = pathlib.Path(sys.argv[2])
plugin_root = pathlib.Path(sys.argv[3])
expected_dirs = sys.argv[4:]

with marketplace_path.open(encoding="utf-8") as handle:
    marketplace = json.load(handle)
with plugin_path.open(encoding="utf-8") as handle:
    plugin = json.load(handle)

require(marketplace["name"] == "bryancowan-skills", "unexpected marketplace name")
require(len(marketplace["plugins"]) == 1, "expected exactly one marketplace plugin")
entry = marketplace["plugins"][0]
require(entry["name"] == "personal-skills", "unexpected plugin name")
require(
    entry["source"] == {"source": "local", "path": "./plugins/personal-skills"},
    "unexpected plugin source",
)
require(plugin["name"] == "personal-skills", "unexpected portable plugin name")
require(plugin["version"] == "1.0.0", "unexpected portable plugin version")

bundle_root = plugin_root / "skills"
require(bundle_root.is_dir() and not bundle_root.is_symlink(), f"invalid bundle root: {bundle_root}")
entries = list(bundle_root.iterdir())
actual_entries = sorted(path.name for path in entries)
require(actual_entries == sorted(expected_dirs), f"unexpected bundle entries: {actual_entries}")

for entry_path in entries:
    require(not entry_path.is_symlink(), f"bundled skill must not be a symlink: {entry_path}")
    require(entry_path.is_dir(), f"bundled skill must be a directory: {entry_path}")
    require(
        entry_path.resolve() == bundle_root.resolve() / entry_path.name,
        f"bundled skill escapes bundle root: {entry_path}",
    )

for directory in expected_dirs:
    skill_file = plugin_root / "skills" / directory / "SKILL.md"
    frontmatter_name(skill_file)
PY

for skill_dir in "${skill_dirs[@]}"; do
  diff -qr "$repo_root/skills/$skill_dir" "$bundle_root/$skill_dir"
done

make_fixture() {
  local fixture_root="$1"
  local fixture_skill

  mkdir -p "$fixture_root/scripts" "$fixture_root/plugins/personal-skills/skills"
  cp "$repo_root/scripts/sync-personal-skills-plugin.sh" "$fixture_root/scripts/"
  for fixture_skill in "${skill_dirs[@]}"; do
    mkdir -p "$fixture_root/skills/$fixture_skill"
    printf '%s\n' "$fixture_skill" > "$fixture_root/skills/$fixture_skill/payload"
  done
}

run_symlink_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-symlink.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"

  bundle_fixture="$fixture_root/plugins/personal-skills/skills"
  external_target="$fixture_root/external-target/description-and-tags"
  mkdir -p "$external_target"
  cp -a "$fixture_root/skills/description-and-tags/." "$external_target/"
  ln -s "$external_target" "$bundle_fixture/description-and-tags"
  printf '%s\n' sentinel > "$external_target/sentinel"

  for fixture_skill in "${skill_dirs[@]:1}"; do
    mkdir -p "$bundle_fixture/$fixture_skill"
    cp -a "$fixture_root/skills/$fixture_skill/." "$bundle_fixture/$fixture_skill/"
  done

  failed=0
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" > "$fixture_root/sync.log" 2>&1; then
    cat "$fixture_root/sync.log" >&2
    echo "sync accepted a symlinked bundled skill" >&2
    failed=1
  fi
  if [[ ! -f "$external_target/sentinel" ]]; then
    echo "sync deleted an external sentinel through a bundled-skill symlink" >&2
    failed=1
  fi
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" --check > "$fixture_root/check.log" 2>&1; then
    cat "$fixture_root/check.log" >&2
    echo "--check accepted a symlinked bundled skill" >&2
    failed=1
  fi
  return "$failed"
)

run_unexpected_entry_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-entry.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"
  bundle_fixture="$fixture_root/plugins/personal-skills/skills"

  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh"
  printf '%s\n' unexpected > "$bundle_fixture/unexpected-file"
  printf '%s\n' unexpected > "$bundle_fixture/.unexpected-file"

  failed=0
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" --check > "$fixture_root/check.log" 2>&1; then
    cat "$fixture_root/check.log" >&2
    echo "--check accepted unexpected bundle-root files" >&2
    failed=1
  fi
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" > "$fixture_root/sync.log" 2>&1; then
    cat "$fixture_root/sync.log" >&2
    echo "sync accepted unexpected bundle-root files" >&2
    failed=1
  fi
  if [[ ! -f "$bundle_fixture/unexpected-file" || ! -f "$bundle_fixture/.unexpected-file" ]]; then
    echo "sync modified unexpected bundle-root files instead of rejecting them" >&2
    failed=1
  fi
  return "$failed"
)

regression_failures=0
run_symlink_regression || regression_failures=1
run_unexpected_entry_regression || regression_failures=1
[[ "$regression_failures" == 0 ]]
