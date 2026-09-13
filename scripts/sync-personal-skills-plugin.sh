#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
bundle_root="$repo_root/plugins/personal-skills/skills"
mode="${1:-sync}"
skill_dirs=(
  description-and-tags
  good-documentation
  obsidian-jd-organizer
  obsidian-wiki-compiler
  prompt-creation
)

is_allowed_skill() {
  local candidate="$1"
  local skill_dir

  for skill_dir in "${skill_dirs[@]}"; do
    [[ "$candidate" == "$skill_dir" ]] && return 0
  done
  return 1
}

require_real_directory() {
  local directory="$1"
  local expected_physical_path="$2"
  local label="$3"
  local physical_path

  if [[ -L "$directory" || ! -d "$directory" ]]; then
    echo "$label must be a real directory: $directory" >&2
    return 1
  fi
  physical_path="$(cd "$directory" && pwd -P)" || return 1
  if [[ "$physical_path" != "$expected_physical_path" ]]; then
    echo "$label escapes its expected path: $directory" >&2
    return 1
  fi
}

validate_bundle_root() (
  local require_complete="$1"
  local bundled_entry
  local bundled_name
  local skill_dir

  require_real_directory "$bundle_root" "$bundle_root" "bundle root" || return 1
  shopt -s nullglob dotglob
  for bundled_entry in "$bundle_root"/*; do
    bundled_name="${bundled_entry##*/}"
    if ! is_allowed_skill "$bundled_name"; then
      echo "unexpected bundle entry: $bundled_entry" >&2
      return 1
    fi
    require_real_directory \
      "$bundled_entry" \
      "$bundle_root/$bundled_name" \
      "bundled skill" || return 1
  done

  if [[ "$require_complete" == true ]]; then
    for skill_dir in "${skill_dirs[@]}"; do
      if [[ ! -d "$bundle_root/$skill_dir" || -L "$bundle_root/$skill_dir" ]]; then
        echo "missing bundled skill: $skill_dir" >&2
        return 1
      fi
    done
  fi
)

if [[ "$mode" != "sync" && "$mode" != "--check" ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

if [[ "$mode" == "--check" ]]; then
  result_code=0
  validate_bundle_root true || result_code=1
  for skill_dir in "${skill_dirs[@]}"; do
    source_dir="$repo_root/skills/$skill_dir"
    bundled_dir="$bundle_root/$skill_dir"
    if [[ ! -d "$bundled_dir" || -L "$bundled_dir" ]]; then
      echo "missing bundled skill: $skill_dir" >&2
      result_code=1
      continue
    fi
    diff -qr "$source_dir" "$bundled_dir" || result_code=1
  done

  exit "$result_code"
fi

mkdir -p "$bundle_root"
validate_bundle_root false || exit 1
for skill_dir in "${skill_dirs[@]}"; do
  source_dir="$repo_root/skills/$skill_dir"
  bundled_dir="$bundle_root/$skill_dir"
  require_real_directory "$source_dir" "$source_dir" "canonical skill" || exit 1
  mkdir -p "$bundled_dir"
  require_real_directory "$bundled_dir" "$bundle_root/$skill_dir" "bundled skill" || exit 1
  rsync -a --delete "$source_dir/" "$bundled_dir/"
done

validate_bundle_root true
