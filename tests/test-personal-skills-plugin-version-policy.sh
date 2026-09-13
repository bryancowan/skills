#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
skill_dirs=(
  description-and-tags
  construction-near-me
  good-documentation
  obsidian-jd-organizer
  obsidian-wiki-compiler
  podcast-transcript
  prompt-creation
)

fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-version-policy.XXXXXX")"
trap 'rm -rf "$fixture_root"' EXIT

mkdir -p \
  "$fixture_root/.agents/plugins" \
  "$fixture_root/plugins/personal-skills/skills" \
  "$fixture_root/scripts" \
  "$fixture_root/tests"
cp "$repo_root/.agents/plugins/marketplace.json" "$fixture_root/.agents/plugins/marketplace.json"
cp "$repo_root/plugins/personal-skills/plugin.json" "$fixture_root/plugins/personal-skills/plugin.json"
cp "$repo_root/scripts/sync-personal-skills-plugin.sh" "$fixture_root/scripts/"
cp "$repo_root/tests/test-personal-skills-plugin.sh" "$fixture_root/tests/"

set_fixture_version() {
  python3 - "$fixture_root/plugins/personal-skills/plugin.json" "$1" <<'PY_MUTATE'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["version"] = sys.argv[2]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY_MUTATE
}

for skill_dir in "${skill_dirs[@]}"; do
  mkdir -p "$fixture_root/skills/$skill_dir"
  cp -a "$repo_root/skills/$skill_dir/." "$fixture_root/skills/$skill_dir/"
  cp -a \
    "$repo_root/plugins/personal-skills/skills/$skill_dir" \
    "$fixture_root/plugins/personal-skills/skills/"
done

set_fixture_version "1.0.0"
git -C "$fixture_root" init -q
git -C "$fixture_root" config user.name "Version Policy Test"
git -C "$fixture_root" config user.email "version-policy@example.invalid"
git -C "$fixture_root" config commit.gpgsign false
git -C "$fixture_root" add .
git -C "$fixture_root" commit -qm "base package"
base_revision="$(git -C "$fixture_root" rev-parse HEAD)"

printf '\nVersion policy regression fixture.\n' >> \
  "$fixture_root/skills/description-and-tags/SKILL.md"
printf '\nVersion policy regression fixture.\n' >> \
  "$fixture_root/plugins/personal-skills/skills/description-and-tags/SKILL.md"
git -C "$fixture_root" add .
git -C "$fixture_root" commit -qm "change package without bumping version"

if PERSONAL_SKILLS_BASE_REVISION="$base_revision" \
  bash "$fixture_root/tests/test-personal-skills-plugin.sh" \
  > "$fixture_root/validator.log" 2>&1; then
  cat "$fixture_root/validator.log" >&2
  echo "validator accepted package changes without a version increment" >&2
  exit 1
fi

grep -F \
  "personal-skills package changed without a version increment: 1.0.0 -> 1.0.0" \
  "$fixture_root/validator.log" > /dev/null

set_fixture_version "1.0.1"
git -C "$fixture_root" add plugins/personal-skills/plugin.json
git -C "$fixture_root" commit -qm "increment package version"
PERSONAL_SKILLS_BASE_REVISION="$base_revision" \
  bash "$fixture_root/tests/test-personal-skills-plugin.sh"

set_fixture_version "0.9.0"
git -C "$fixture_root" add plugins/personal-skills/plugin.json
git -C "$fixture_root" commit -qm "lower package version"
if PERSONAL_SKILLS_BASE_REVISION="$base_revision" \
  bash "$fixture_root/tests/test-personal-skills-plugin.sh" \
  > "$fixture_root/validator.log" 2>&1; then
  cat "$fixture_root/validator.log" >&2
  echo "validator accepted a lower package version" >&2
  exit 1
fi

grep -F \
  "personal-skills package changed without a version increment: 1.0.0 -> 0.9.0" \
  "$fixture_root/validator.log" > /dev/null
