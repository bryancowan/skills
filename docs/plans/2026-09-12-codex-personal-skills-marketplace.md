# Codex Personal Skills Marketplace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish one Codex marketplace plugin that installs exactly the five currently used personal skills from their canonical repository sources.

**Architecture:** Keep `skills/` authoritative and commit a generated five-skill bundle under `plugins/personal-skills/`. A fixed-allowlist synchronization script refreshes the bundle, a test script validates manifests and byte-for-byte equality, and CI prevents drift. Repository guidance tells future agents to edit canonical sources, regenerate the bundle, validate it, and bump the plugin version.

**Tech Stack:** POSIX shell with Bash arrays, Python 3 standard-library JSON parsing, Codex CLI, GitHub Actions YAML, Markdown, Agent Plugins JSON manifests

**Spec:** `docs/specs/2026-09-12-codex-personal-skills-marketplace-design.md`

## Global Constraints

- Bundle exactly `description-and-tags`, `good-documentation`, `obsidian-jd-organizer`, `obsidian-wiki-compiler`, and `prompt-creation`.
- Keep top-level `skills/` directories canonical; never edit generated plugin copies directly.
- Start `personal-skills` at version `1.0.0`.
- Do not change `.claude-plugin/marketplace.json` or the existing Claude marketplace behavior.
- Do not add the other four repository skills to the Codex plugin.
- Do not rewrite skill contents during packaging.
- Do not permanently delete direct installations; move them to timestamped backups only after post-merge marketplace verification.
- Do not merge the pull request without separate authorization.

---

### Task 1: Add a failing repository package validator

**Files:**
- Create: `tests/test-personal-skills-plugin.sh`

**Interfaces:**
- Consumes: canonical directories under `skills/`
- Produces: executable validation command `bash tests/test-personal-skills-plugin.sh`

- [ ] **Step 1: Create the validator**

Create `tests/test-personal-skills-plugin.sh` with this behavior:

```bash
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
```

- [ ] **Step 2: Mark the validator executable**

Run: `chmod +x tests/test-personal-skills-plugin.sh`

- [ ] **Step 3: Run the validator and verify the red state**

Run: `bash tests/test-personal-skills-plugin.sh`

Expected: FAIL because `.agents/plugins/marketplace.json` does not exist.

- [ ] **Step 4: Commit the failing validator**

```bash
git add tests/test-personal-skills-plugin.sh
git commit -m "test: define personal skills plugin contract"
```

---

### Task 2: Package the five canonical skills as one portable plugin

**Files:**
- Create: `.agents/plugins/marketplace.json`
- Create: `plugins/personal-skills/plugin.json`
- Create: `scripts/sync-personal-skills-plugin.sh`
- Generate: `plugins/personal-skills/skills/description-and-tags/**`
- Generate: `plugins/personal-skills/skills/good-documentation/**`
- Generate: `plugins/personal-skills/skills/obsidian-jd-organizer/**`
- Generate: `plugins/personal-skills/skills/obsidian-wiki-compiler/**`
- Generate: `plugins/personal-skills/skills/prompt-creation/**`

**Interfaces:**
- Consumes: the five canonical skill directories under `skills/`
- Produces: plugin `personal-skills@bryancowan-skills`; synchronization commands `bash scripts/sync-personal-skills-plugin.sh` and `bash scripts/sync-personal-skills-plugin.sh --check`

- [ ] **Step 1: Create the marketplace manifest**

Create `.agents/plugins/marketplace.json`:

```json
{
  "name": "bryancowan-skills",
  "interface": {
    "displayName": "Bryan Cowan Skills"
  },
  "plugins": [
    {
      "name": "personal-skills",
      "source": {
        "source": "local",
        "path": "./plugins/personal-skills"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

- [ ] **Step 2: Create the portable plugin manifest**

Create `plugins/personal-skills/plugin.json`:

```json
{
  "$schema": "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
  "name": "personal-skills",
  "version": "1.0.0",
  "description": "Bryan Cowan's selected documentation, Obsidian, and prompt-development skills.",
  "author": {
    "name": "Bryan Cowan",
    "email": "bryan@bryancowan.com",
    "url": "https://github.com/bryancowan"
  },
  "homepage": "https://github.com/bryancowan/skills",
  "repository": "https://github.com/bryancowan/skills",
  "keywords": [
    "documentation",
    "obsidian",
    "prompts",
    "skills"
  ],
  "extensions": {
    "com.openai": {
      "interface": {
        "displayName": "Personal Skills",
        "shortDescription": "Documentation, Obsidian, and prompt-development workflows.",
        "longDescription": "Five selected personal skills for documentation, Obsidian reading-list enrichment and organization, wiki compilation, and prompt development.",
        "developerName": "Bryan Cowan",
        "category": "Productivity",
        "capabilities": [
          "Read",
          "Write"
        ],
        "websiteURL": "https://github.com/bryancowan/skills",
        "defaultPrompt": [
          "Help me improve this documentation.",
          "Organize these notes in my Obsidian vault.",
          "Help me create a precise prompt."
        ],
        "brandColor": "#5B5BD6"
      }
    }
  }
}
```

- [ ] **Step 3: Create the fixed-allowlist synchronization script**

Create `scripts/sync-personal-skills-plugin.sh`:

```bash
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
```

- [ ] **Step 4: Mark the synchronization script executable**

Run: `chmod +x scripts/sync-personal-skills-plugin.sh`

- [ ] **Step 5: Generate the committed bundle**

Run: `bash scripts/sync-personal-skills-plugin.sh`

Expected: the five explicit directories appear under `plugins/personal-skills/skills/`; no other skill directory appears.

- [ ] **Step 6: Verify the green state**

Run: `bash tests/test-personal-skills-plugin.sh`

Expected: PASS with exit code 0 and no differences.

Run: `bash scripts/sync-personal-skills-plugin.sh --check`

Expected: PASS with exit code 0 and no differences.

- [ ] **Step 7: Commit the plugin package**

```bash
git add .agents/plugins/marketplace.json plugins/personal-skills scripts/sync-personal-skills-plugin.sh
git commit -m "feat: package personal skills for Codex"
```

---

### Task 3: Document and continuously enforce the marketplace workflow

**Files:**
- Create: `AGENTS.md`
- Create: `.github/workflows/validate-personal-skills-plugin.yml`
- Modify: `CLAUDE.md`
- Modify: `README.md`

**Interfaces:**
- Consumes: synchronization and validation commands from Tasks 1 and 2
- Produces: durable agent instructions, user installation guidance, and CI enforcement

- [ ] **Step 1: Add root agent guidance**

Create `AGENTS.md` with these sections and requirements:

```markdown
# Repository guidance

## Canonical skill sources

Treat `skills/` as authoritative. The files under `plugins/personal-skills/skills/` are generated copies for the Codex marketplace plugin; never edit them directly.

The Codex plugin intentionally bundles only `description-and-tags`, `good-documentation`, `obsidian-jd-organizer`, `obsidian-wiki-compiler`, and `prompt-creation`.

## Keep the Codex bundle synchronized

After changing one of the five bundled skills, run:

`bash scripts/sync-personal-skills-plugin.sh`

Before committing, run:

`bash scripts/sync-personal-skills-plugin.sh --check`
`bash tests/test-personal-skills-plugin.sh`

Increment `plugins/personal-skills/plugin.json` whenever published plugin contents or metadata change. Do not change `.claude-plugin/marketplace.json` unless the Claude marketplace itself changes.
```

- [ ] **Step 2: Update Claude guidance**

Add a `## Codex marketplace bundle` section to `CLAUDE.md` after its Claude marketplace section. State that canonical edits happen under `skills/`, name the five generated directories, prohibit direct edits under `plugins/personal-skills/skills/`, provide both synchronization commands, and require a plugin version increment for published content or metadata changes.

- [ ] **Step 3: Replace Codex direct-copy instructions with marketplace instructions**

Update the `### Codex CLI` section in `README.md` so its primary instructions are:

```bash
codex plugin marketplace add bryancowan/skills
codex plugin add personal-skills@bryancowan-skills
```

State that the plugin contains the selected five skills and that future updates use:

```bash
codex plugin marketplace upgrade bryancowan-skills
```

Retain a clearly labeled manual direct-install fallback for repository skills outside the five-skill plugin.

- [ ] **Step 4: Add CI validation**

Create `.github/workflows/validate-personal-skills-plugin.yml`:

```yaml
name: Validate personal skills plugin

on:
  pull_request:
  push:
    branches:
      - main

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate manifests and bundled skills
        run: bash tests/test-personal-skills-plugin.sh
      - name: Check generated bundle drift
        run: bash scripts/sync-personal-skills-plugin.sh --check
```

- [ ] **Step 5: Run repository validation**

Run: `bash tests/test-personal-skills-plugin.sh`

Expected: PASS with exit code 0.

Run: `bash scripts/sync-personal-skills-plugin.sh --check`

Expected: PASS with exit code 0.

Run: `git diff --check`

Expected: PASS with exit code 0.

- [ ] **Step 6: Commit documentation and CI**

```bash
git add AGENTS.md CLAUDE.md README.md .github/workflows/validate-personal-skills-plugin.yml
git commit -m "docs: explain Codex marketplace maintenance"
```

---

### Task 4: Prove Codex can discover and install the plugin in isolation

**Files:**
- Modify only if validation exposes a defect: `.agents/plugins/marketplace.json`, `plugins/personal-skills/plugin.json`, `tests/test-personal-skills-plugin.sh`

**Interfaces:**
- Consumes: repository marketplace and portable plugin from Task 2
- Produces: CLI evidence that the marketplace and plugin are discoverable, installable, and enabled without changing the active Codex configuration

- [ ] **Step 1: Create a temporary Codex configuration root**

Run:

```bash
task_codex_dir="$(mktemp -d)"
test -d "$task_codex_dir"
```

Expected: PASS; the path is under the operating system temporary directory.

- [ ] **Step 2: Add the checkout as a local marketplace in the temporary configuration**

Run:

```bash
CODEX_HOME="$task_codex_dir" codex plugin marketplace add "$PWD" --json
```

Expected: JSON reports marketplace name `bryancowan-skills` with `alreadyAdded` false.

- [ ] **Step 3: Verify the available plugin before installation**

Run:

```bash
CODEX_HOME="$task_codex_dir" codex plugin list --marketplace bryancowan-skills --available --json
```

Expected: `available` contains only `personal-skills@bryancowan-skills` at version `1.0.0`; `installed` is empty.

- [ ] **Step 4: Install and verify the plugin**

Run:

```bash
CODEX_HOME="$task_codex_dir" codex plugin add personal-skills@bryancowan-skills
CODEX_HOME="$task_codex_dir" codex plugin list --marketplace bryancowan-skills --json
```

Expected: `installed` contains only `personal-skills@bryancowan-skills`, with version `1.0.0`, `installed: true`, and `enabled: true`.

- [ ] **Step 5: Verify the installed cache contains exactly five skills**

Run:

```bash
installed_root="$task_codex_dir/plugins/cache/bryancowan-skills/personal-skills/1.0.0/skills"
test -d "$installed_root"
for skill_dir in description-and-tags good-documentation obsidian-jd-organizer obsidian-wiki-compiler prompt-creation; do
  test -f "$installed_root/$skill_dir/SKILL.md"
done
```

Expected: every check exits 0.

- [ ] **Step 6: Remove the temporary configuration**

Run:

```bash
test -n "$task_codex_dir"
case "$task_codex_dir" in
  /tmp/*|/private/tmp/*|/private/var/folders/*/T/*) ;;
  *) echo "refusing to remove non-temporary path: $task_codex_dir" >&2; exit 1 ;;
esac
test -d "$task_codex_dir"
rm -rf -- "$task_codex_dir"
test ! -e "$task_codex_dir"
```

Expected: the validated temporary path is removed and the final existence check exits 0.

- [ ] **Step 7: Commit any validation-driven corrections**

If Task 4 required corrections, commit only those files:

```bash
git add .agents/plugins/marketplace.json plugins/personal-skills/plugin.json tests/test-personal-skills-plugin.sh
git commit -m "fix: make personal skills plugin installable"
```

If no correction was required, do not create an empty commit.

---

### Task 5: Verify the branch and open the pull request

**Files:**
- No new repository files

**Interfaces:**
- Consumes: all implementation commits and verification evidence
- Produces: signed commits, pushed feature branch, and a reviewable pull request

- [ ] **Step 1: Run the full verification gate**

Run:

```bash
bash tests/test-personal-skills-plugin.sh
bash scripts/sync-personal-skills-plugin.sh --check
git diff --check
git status --short --branch
```

Expected: both scripts and `git diff --check` exit 0; status shows a clean `codex/personal-skills-marketplace` branch.

- [ ] **Step 2: Verify every branch commit signature**

Run: `git log --format='%H' main..HEAD`

Run `git verify-commit <commit>` for every returned commit.

Expected: each verification exits 0 with a good signature.

- [ ] **Step 3: Push the feature branch**

Run: `git push -u origin codex/personal-skills-marketplace`

Expected: the remote branch is created and local tracking is configured.

- [ ] **Step 4: Open the pull request**

Run `gh pr create` with:

- Title: `Add Codex marketplace for personal skills`
- Base: `main`
- Head: `codex/personal-skills-marketplace`
- Body sections: Summary, Bundled skills, Validation, and Post-merge migration.

Expected: GitHub returns the new pull request URL.

- [ ] **Step 5: Verify pull request state**

Run: `gh pr view --json url,state,headRefName,baseRefName,title`

Expected: state `OPEN`, head `codex/personal-skills-marketplace`, base `main`, and the requested title.

---

### Task 6: Migrate direct installs after the pull request is merged

**Files:**
- Move after explicit merge confirmation: matching directories under `~/.codex/skills` and `~/.agents/skills`
- Create outside active skill roots: timestamped backup directory containing the moved direct installations

**Interfaces:**
- Consumes: merged `personal-skills@bryancowan-skills` version `1.0.0`
- Produces: marketplace-managed active skills with recoverable inactive backups

- [ ] **Step 1: Confirm the pull request is merged**

Run: `gh pr view --json state,mergedAt,mergeCommit`

Expected: state `MERGED`, a non-null `mergedAt`, and a merge commit identifier. Stop if the pull request is still open or closed without merge.

- [ ] **Step 2: Add the GitHub marketplace and install the plugin**

Run:

```bash
codex plugin marketplace add bryancowan/skills --json
codex plugin add personal-skills@bryancowan-skills
codex plugin list --marketplace bryancowan-skills --json
```

Expected: the marketplace resolves from `https://github.com/bryancowan/skills.git`; the plugin is version `1.0.0`, installed, and enabled.

- [ ] **Step 3: Verify installed plugin contents before moving direct copies**

Run:

```bash
repo_root="/Users/bryan/Documents/repos/skills"
plugin_skills_root="/Users/bryan/.codex/plugins/cache/bryancowan-skills/personal-skills/1.0.0/skills"
test -d "$plugin_skills_root"
for skill_dir in description-and-tags good-documentation obsidian-jd-organizer obsidian-wiki-compiler prompt-creation; do
  diff -qr "$repo_root/skills/$skill_dir" "$plugin_skills_root/$skill_dir"
done
actual_skills=()
for bundled_dir in "$plugin_skills_root"/*; do
  [[ -d "$bundled_dir" ]] || continue
  actual_skills+=("$(basename "$bundled_dir")")
done
test "${actual_skills[*]}" = "description-and-tags good-documentation obsidian-jd-organizer obsidian-wiki-compiler prompt-creation"
```

Expected: five comparisons and the exact-directory assertion exit 0. Stop without moving anything if a check fails.

- [ ] **Step 4: Create a timestamped backup root**

Run:

```bash
backup_stamp="$(date +%Y%m%dT%H%M%S)"
backup_root="/Users/bryan/.codex/skill-backups/${backup_stamp}-personal-skills-marketplace"
mkdir -p "$backup_root/codex" "$backup_root/agents"
printf '%s\n' "$backup_root"
test -d "$backup_root/codex"
test -d "$backup_root/agents"
```

Expected: the printed, resolved backup path exists with both source-root groupings before any move.

- [ ] **Step 5: Move the seven direct installations into the backup**

First verify every expected source directory:

```bash
test -d /Users/bryan/.codex/skills/good-documentation
test -d /Users/bryan/.codex/skills/obsidian-jd-organizer
test -d /Users/bryan/.codex/skills/obsidian-wiki-compiler
test -d /Users/bryan/.codex/skills/prompt-creation
test -d /Users/bryan/.agents/skills/good-documentation
test -d /Users/bryan/.agents/skills/obsidian-reading-list-enrichment
test -d /Users/bryan/.agents/skills/prompt-creation
```

Then move exactly those directories:

```bash
mv /Users/bryan/.codex/skills/good-documentation "$backup_root/codex/good-documentation"
mv /Users/bryan/.codex/skills/obsidian-jd-organizer "$backup_root/codex/obsidian-jd-organizer"
mv /Users/bryan/.codex/skills/obsidian-wiki-compiler "$backup_root/codex/obsidian-wiki-compiler"
mv /Users/bryan/.codex/skills/prompt-creation "$backup_root/codex/prompt-creation"
mv /Users/bryan/.agents/skills/good-documentation "$backup_root/agents/good-documentation"
mv /Users/bryan/.agents/skills/obsidian-reading-list-enrichment "$backup_root/agents/obsidian-reading-list-enrichment"
mv /Users/bryan/.agents/skills/prompt-creation "$backup_root/agents/prompt-creation"
```

Expected: all seven moves succeed. If any pre-move check fails, stop before moving the first directory.

- [ ] **Step 6: Verify the migration**

Run `codex plugin list --marketplace bryancowan-skills --json`, then run:

```bash
test ! -e /Users/bryan/.codex/skills/good-documentation
test ! -e /Users/bryan/.codex/skills/obsidian-jd-organizer
test ! -e /Users/bryan/.codex/skills/obsidian-wiki-compiler
test ! -e /Users/bryan/.codex/skills/prompt-creation
test ! -e /Users/bryan/.agents/skills/good-documentation
test ! -e /Users/bryan/.agents/skills/obsidian-reading-list-enrichment
test ! -e /Users/bryan/.agents/skills/prompt-creation
test -d "$backup_root/codex/good-documentation"
test -d "$backup_root/codex/obsidian-jd-organizer"
test -d "$backup_root/codex/obsidian-wiki-compiler"
test -d "$backup_root/codex/prompt-creation"
test -d "$backup_root/agents/good-documentation"
test -d "$backup_root/agents/obsidian-reading-list-enrichment"
test -d "$backup_root/agents/prompt-creation"
```

Verify from the JSON and filesystem evidence that:

- `personal-skills@bryancowan-skills` remains installed and enabled at `1.0.0`.
- All seven original direct paths are absent.
- All seven corresponding backup paths exist.
- The installed plugin cache still contains exactly the five expected skills.

- [ ] **Step 7: Report the restart and rollback boundary**

Tell Bryan to start a new Codex session so discovery excludes the removed direct copies. Report the exact backup path and do not delete it. If the plugin fails in the new session, restore the seven paths from that backup and disable or remove only `personal-skills@bryancowan-skills`.
