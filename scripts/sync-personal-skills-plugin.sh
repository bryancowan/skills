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

if [[ "$mode" != "sync" && "$mode" != "--check" ]]; then
  echo "usage: $0 [--check]" >&2
  exit 2
fi

if [[ "$mode" == "--check" ]]; then
  result_code=0
  for skill_dir in "${skill_dirs[@]}"; do
    source_dir="$repo_root/skills/$skill_dir"
    bundled_dir="$bundle_root/$skill_dir"
    if [[ ! -d "$bundled_dir" ]]; then
      echo "missing bundled skill: $skill_dir" >&2
      result_code=1
      continue
    fi
    diff -qr "$source_dir" "$bundled_dir" || result_code=1
  done

  actual_dirs=()
  for bundled_dir in "$bundle_root"/*; do
    [[ -d "$bundled_dir" ]] || continue
    actual_dirs+=("$(basename "$bundled_dir")")
  done
  if [[ "${actual_dirs[*]}" != "${skill_dirs[*]}" ]]; then
    echo "bundled skill set differs from the fixed allowlist" >&2
    result_code=1
  fi
  exit "$result_code"
fi

mkdir -p "$bundle_root"
for skill_dir in "${skill_dirs[@]}"; do
  source_dir="$repo_root/skills/$skill_dir"
  bundled_dir="$bundle_root/$skill_dir"
  [[ -d "$source_dir" ]] || {
    echo "missing canonical skill: $source_dir" >&2
    exit 1
  }
  mkdir -p "$bundled_dir"
  rsync -a --delete "$source_dir/" "$bundled_dir/"
done

for bundled_dir in "$bundle_root"/*; do
  [[ -d "$bundled_dir" ]] || continue
  bundled_name="$(basename "$bundled_dir")"
  keep=false
  for skill_dir in "${skill_dirs[@]}"; do
    [[ "$bundled_name" == "$skill_dir" ]] && keep=true
  done
  if [[ "$keep" == false ]]; then
    echo "unexpected bundled directory: $bundled_dir" >&2
    exit 1
  fi
done
