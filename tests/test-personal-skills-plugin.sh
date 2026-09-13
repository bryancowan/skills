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

python3 - "$marketplace_file" "$plugin_file" "$plugin_root" "$repo_root" "${skill_dirs[@]}" <<'PY'
import json
import os
import pathlib
import re
import subprocess
import sys


def require(condition, message):
    if not condition:
        raise SystemExit(message)


def parse_semver(version):
    prerelease_identifier = r"(?:0|[1-9]\d*|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
    semantic_version = (
        r"(?P<major>0|[1-9]\d*)\.(?P<minor>0|[1-9]\d*)\.(?P<patch>0|[1-9]\d*)"
        rf"(?:-(?P<prerelease>{prerelease_identifier}(?:\.{prerelease_identifier})*))?"
        r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    )
    match = re.fullmatch(semantic_version, version) if isinstance(version, str) else None
    require(match, f"invalid portable plugin version: {version!r}")
    return match


def version_is_greater(current, previous):
    current_match = parse_semver(current)
    previous_match = parse_semver(previous)
    current_core = tuple(int(current_match.group(part)) for part in ("major", "minor", "patch"))
    previous_core = tuple(int(previous_match.group(part)) for part in ("major", "minor", "patch"))
    if current_core != previous_core:
        return current_core > previous_core

    current_pre = current_match.group("prerelease")
    previous_pre = previous_match.group("prerelease")
    if current_pre is None or previous_pre is None:
        return previous_pre is not None and current_pre is None

    current_parts = current_pre.split(".")
    previous_parts = previous_pre.split(".")
    for current_part, previous_part in zip(current_parts, previous_parts):
        if current_part == previous_part:
            continue
        current_numeric = current_part.isdigit()
        previous_numeric = previous_part.isdigit()
        if current_numeric and previous_numeric:
            return int(current_part) > int(previous_part)
        if current_numeric != previous_numeric:
            return not current_numeric
        return current_part > previous_part
    return len(current_parts) > len(previous_parts)


def frontmatter_name(skill_file):
    lines = skill_file.read_text(encoding="utf-8").splitlines()
    require(lines and lines[0] == "---", f"missing initial YAML frontmatter: {skill_file}")
    try:
        closing_index = lines.index("---", 1)
    except ValueError:
        raise SystemExit(f"unterminated YAML frontmatter: {skill_file}")

    frontmatter = "\n".join(lines[1:closing_index])
    name_match = re.search(r"(?m)^name:[ \t]*(?P<value>[^\r\n]*)$", frontmatter)
    require(name_match, f"missing frontmatter name: {skill_file}")
    name = name_match.group("value").strip()
    if len(name) >= 2 and name[0] == name[-1] and name[0] in "'\"":
        name = name[1:-1]
    require(
        re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name),
        f"invalid frontmatter name: {skill_file}",
    )


marketplace_path = pathlib.Path(sys.argv[1])
plugin_path = pathlib.Path(sys.argv[2])
plugin_root = pathlib.Path(sys.argv[3])
repo_root = pathlib.Path(sys.argv[4])
expected_dirs = sys.argv[5:]

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
plugin_version = plugin.get("version")
parse_semver(plugin_version)

base_revision = os.environ.get("PERSONAL_SKILLS_BASE_REVISION")
if base_revision:
    package_path = plugin_root.relative_to(repo_root).as_posix()
    base_manifest_path = f"{base_revision}:{package_path}/plugin.json"
    base_exists = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "--verify", f"{base_revision}^{{commit}}"],
        capture_output=True,
    )
    require(base_exists.returncode == 0, f"invalid base revision: {base_revision}")
    base_manifest_entry = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "ls-tree",
            "--name-only",
            base_revision,
            "--",
            f"{package_path}/plugin.json",
        ],
        capture_output=True,
        text=True,
    )
    require(base_manifest_entry.returncode == 0, f"could not inspect package at {base_revision}")
    if base_manifest_entry.stdout.strip():
        base_manifest = subprocess.run(
            ["git", "-C", str(repo_root), "show", base_manifest_path],
            capture_output=True,
            text=True,
        )
        require(base_manifest.returncode == 0, f"could not read package manifest at {base_revision}")
        package_changed = subprocess.run(
            ["git", "-C", str(repo_root), "diff", "--quiet", base_revision, "--", package_path]
        )
        require(package_changed.returncode in (0, 1), f"could not compare package with {base_revision}")
        if package_changed.returncode == 1:
            base_version = json.loads(base_manifest.stdout).get("version")
            require(
                version_is_greater(plugin_version, base_version),
                f"personal-skills package changed without a version increment: "
                f"{base_version} -> {plugin_version}",
            )

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

run_executable_bit_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-mode.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"

  source_file="$fixture_root/skills/good-documentation/payload"
  bundled_file="$fixture_root/plugins/personal-skills/skills/good-documentation/payload"
  chmod +x "$source_file"
  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" || return 1
  if [[ ! -f "$bundled_file" || ! -x "$bundled_file" ]]; then
    echo "sync did not preserve the canonical executable bit" >&2
    return 1
  fi
  chmod -x "$source_file"

  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" --check \
    > "$fixture_root/check.log" 2>&1; then
    cat "$fixture_root/check.log" >&2
    echo "--check accepted executable-bit drift" >&2
    return 1
  fi

  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" || return 1
  if [[ ! -f "$bundled_file" || -x "$bundled_file" ]]; then
    echo "sync did not repair executable-bit drift" >&2
    return 1
  fi
)

run_nested_symlink_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-nested-link.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"

  source_dir="$fixture_root/skills/good-documentation"
  bundled_dir="$fixture_root/plugins/personal-skills/skills/good-documentation"
  failed=0

  ln -s payload "$source_dir/nested-link" || return 1
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" \
    > "$fixture_root/canonical-link.log" 2>&1; then
    cat "$fixture_root/canonical-link.log" >&2
    echo "sync accepted a nested canonical symlink" >&2
    failed=1
  fi
  grep -F "canonical skill must not contain symlinks" \
    "$fixture_root/canonical-link.log" > /dev/null || return 1
  rm "$source_dir/nested-link" || return 1

  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" || return 1
  rm "$bundled_dir/payload" || return 1
  ln -s "$source_dir/payload" "$bundled_dir/payload" || return 1

  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" --check \
    > "$fixture_root/bundled-check.log" 2>&1; then
    cat "$fixture_root/bundled-check.log" >&2
    echo "--check accepted a nested bundled symlink" >&2
    failed=1
  fi
  grep -F "bundled skill must not contain symlinks" \
    "$fixture_root/bundled-check.log" > /dev/null || return 1
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" \
    > "$fixture_root/bundled-sync.log" 2>&1; then
    cat "$fixture_root/bundled-sync.log" >&2
    echo "sync accepted a nested bundled symlink" >&2
    failed=1
  fi
  grep -F "bundled skill must not contain symlinks" \
    "$fixture_root/bundled-sync.log" > /dev/null || return 1

  return "$failed"
)

run_symlink_scan_failure_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-find-failure.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"
  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" || return 1

  mkdir -p "$fixture_root/fake-bin" || return 1
  printf '%s\n' '#!/usr/bin/env bash' 'exit 73' > "$fixture_root/fake-bin/find" || return 1
  chmod +x "$fixture_root/fake-bin/find" || return 1

  if PATH="$fixture_root/fake-bin:$PATH" \
    bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" --check \
    > "$fixture_root/check.log" 2>&1; then
    cat "$fixture_root/check.log" >&2
    echo "--check accepted a failed symlink scan" >&2
    return 1
  fi
  grep -F "could not inspect symlinks" "$fixture_root/check.log" > /dev/null || return 1
)

run_symlink_preflight_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-preflight.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_fixture "$fixture_root"
  bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" || return 1

  printf '%s\n' changed >> "$fixture_root/skills/description-and-tags/payload" || return 1
  ln -s payload "$fixture_root/skills/prompt-creation/nested-link" || return 1
  if bash "$fixture_root/scripts/sync-personal-skills-plugin.sh" \
    > "$fixture_root/sync.log" 2>&1; then
    cat "$fixture_root/sync.log" >&2
    echo "sync accepted a later nested canonical symlink" >&2
    return 1
  fi
  grep -F "canonical skill must not contain symlinks" \
    "$fixture_root/sync.log" > /dev/null || return 1
  if [[ "$(cat "$fixture_root/plugins/personal-skills/skills/description-and-tags/payload")" \
    != "description-and-tags" ]]; then
    echo "sync modified an earlier skill before symlink preflight completed" >&2
    return 1
  fi
)

make_metadata_fixture() {
  local fixture_root="$1"
  local fixture_skill

  mkdir -p \
    "$fixture_root/.agents/plugins" \
    "$fixture_root/plugins/personal-skills/skills"
  cp "$marketplace_file" "$fixture_root/.agents/plugins/marketplace.json"
  cp "$plugin_file" "$fixture_root/plugins/personal-skills/plugin.json"
  for fixture_skill in "${skill_dirs[@]}"; do
    mkdir -p "$fixture_root/plugins/personal-skills/skills/$fixture_skill"
    cp \
      "$bundle_root/$fixture_skill/SKILL.md" \
      "$fixture_root/plugins/personal-skills/skills/$fixture_skill/SKILL.md"
  done
}

run_embedded_validator() {
  local fixture_root="$1"

  awk '
    /^python3 - / { in_python = 1; next }
    in_python && $0 == "PY" { exit }
    in_python { print }
  ' "$repo_root/tests/test-personal-skills-plugin.sh" | \
    env -u PERSONAL_SKILLS_BASE_REVISION python3 - \
    "$fixture_root/.agents/plugins/marketplace.json" \
    "$fixture_root/plugins/personal-skills/plugin.json" \
    "$fixture_root/plugins/personal-skills" \
    "$fixture_root" \
    "${skill_dirs[@]}"
}

run_future_version_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-version.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_metadata_fixture "$fixture_root"

  python3 - "$fixture_root/plugins/personal-skills/plugin.json" <<'PY_MUTATE'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["version"] = "1.0.1"
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY_MUTATE

  run_embedded_validator "$fixture_root"
)

run_invalid_version_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-invalid-version.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_metadata_fixture "$fixture_root"

  for invalid_version in 1.0.0-01 1.0.0-alpha.01; do
    python3 - "$fixture_root/plugins/personal-skills/plugin.json" "$invalid_version" <<'PY_MUTATE'
import json
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
manifest = json.loads(path.read_text(encoding="utf-8"))
manifest["version"] = sys.argv[2]
path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
PY_MUTATE

    if run_embedded_validator "$fixture_root" > "$fixture_root/validator.log" 2>&1; then
      cat "$fixture_root/validator.log" >&2
      echo "validator accepted invalid plugin version: $invalid_version" >&2
      return 1
    fi
  done
)

run_blank_name_regression() (
  set -euo pipefail
  umask 077
  fixture_root="$(mktemp -d "${TMPDIR:-/tmp}/personal-skills-plugin-name.XXXXXX")"
  trap 'rm -rf "$fixture_root"' EXIT
  make_metadata_fixture "$fixture_root"

  python3 - "$fixture_root/plugins/personal-skills/skills/description-and-tags/SKILL.md" <<'PY_MUTATE'
import pathlib
import re
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(encoding="utf-8")
text, replacements = re.subn(r"(?m)^name:.*$", "name:", text, count=1)
if replacements != 1:
    raise SystemExit("fixture could not blank the frontmatter name")
path.write_text(text, encoding="utf-8")
PY_MUTATE

  if run_embedded_validator "$fixture_root" > "$fixture_root/validator.log" 2>&1; then
    cat "$fixture_root/validator.log" >&2
    echo "validator accepted a blank frontmatter name" >&2
    return 1
  fi
)

regression_failures=0
run_symlink_regression || regression_failures=1
run_unexpected_entry_regression || regression_failures=1
run_executable_bit_regression || regression_failures=1
run_nested_symlink_regression || regression_failures=1
run_symlink_scan_failure_regression || regression_failures=1
run_symlink_preflight_regression || regression_failures=1
run_future_version_regression || {
  echo "validator rejected a valid future plugin version" >&2
  regression_failures=1
}
run_invalid_version_regression || regression_failures=1
run_blank_name_regression || regression_failures=1
[[ "$regression_failures" == 0 ]]
