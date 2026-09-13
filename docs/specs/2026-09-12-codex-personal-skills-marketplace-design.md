# Codex Personal Skills Marketplace Design

## Summary

Publish a Codex-compatible `personal-skills` plugin from this repository and use it as the authoritative installation source for the five skills currently installed directly on Bryan's machine. Preserve the existing cross-agent source layout and Claude Code marketplace while adding Codex-native packaging, drift protection, and a recoverable migration path.

## Goals

- Expose one Codex marketplace plugin named `personal-skills` from `bryancowan/skills`.
- Bundle exactly these five canonical skills:
  - `skills/description-and-tags` (`obsidian-reading-list-enrichment`)
  - `skills/good-documentation`
  - `skills/obsidian-jd-organizer`
  - `skills/obsidian-wiki-compiler`
  - `skills/prompt-creation`
- Keep the existing top-level `skills/` directories authoritative for every supported agent.
- Detect any drift between canonical skills and the committed Codex plugin bundle.
- Replace active direct installations only after the GitHub marketplace plugin is available and verified.
- Retain timestamped, recoverable backups of every replaced direct installation.
- Document the maintenance workflow for future Claude and Codex sessions.

## Non-goals

- Do not add the repository's other four skills to the Codex plugin.
- Do not change the existing Claude Code marketplace contents or behavior.
- Do not rewrite the selected skills during packaging.
- Do not merge the pull request; repository changes stop at an opened PR unless separately authorized.
- Do not delete prior direct installations permanently.

## Current State

The repository has a Claude Code marketplace at `.claude-plugin/marketplace.json` but no Codex repository marketplace at `.agents/plugins/marketplace.json`. Canonical skill sources live under `skills/`.

Matching direct installations currently exist at:

- `~/.codex/skills/good-documentation`
- `~/.codex/skills/obsidian-jd-organizer`
- `~/.codex/skills/obsidian-wiki-compiler`
- `~/.codex/skills/prompt-creation`
- `~/.agents/skills/good-documentation`
- `~/.agents/skills/obsidian-reading-list-enrichment`
- `~/.agents/skills/prompt-creation`

Several direct copies differ from the repository. The repository versions are authoritative; the installed copies are retained only as rollback artifacts during migration.

## Repository Architecture

### Portable plugin

Add a portable Agent Plugins package at `plugins/personal-skills/`:

```text
plugins/personal-skills/
├── plugin.json
└── skills/
    ├── description-and-tags/
    ├── good-documentation/
    ├── obsidian-jd-organizer/
    ├── obsidian-wiki-compiler/
    └── prompt-creation/
```

`plugin.json` supplies stable identity and install-surface metadata. It starts at version `1.0.0`. The five directories under the plugin's `skills/` directory are generated, committed copies of the canonical directories. The folder `description-and-tags` retains its existing folder name; its `SKILL.md` continues to declare the runtime skill name `obsidian-reading-list-enrichment`.

### Repository marketplace

Add `.agents/plugins/marketplace.json` with marketplace name `bryancowan-skills`. It exposes one available plugin, `personal-skills`, sourced from `./plugins/personal-skills`.

The resulting commands are:

```text
codex plugin marketplace add bryancowan/skills
codex plugin add personal-skills@bryancowan-skills
```

### Generated-copy synchronization

Add `scripts/sync-personal-skills-plugin.sh` with two modes:

- Default mode refreshes the five explicit generated directories from their canonical sources.
- `--check` mode performs a read-only recursive comparison and exits nonzero for missing, extra, or changed files.

The script uses a fixed allowlist of the five source directories and a fixed destination root. It must not accept arbitrary deletion targets. Synchronization never changes the canonical directories.

Add `.github/workflows/validate-personal-skills-plugin.yml` to run the `--check` mode on pull requests and pushes. This makes drift a CI failure instead of relying on documentation alone.

## Maintainer Documentation

Add a root `AGENTS.md` for Codex and other AGENTS-aware sessions. It will state:

- Top-level `skills/` directories are canonical.
- The Codex bundle contains only the selected five skills.
- Generated plugin copies must not be edited directly.
- Run the synchronization command after changing a selected skill.
- Run the drift check before committing.
- Increment the plugin version when publishing changed plugin contents.

Update `CLAUDE.md` with the same canonical-source, synchronization, validation, and versioning rules so Claude Code sessions cannot unknowingly leave the Codex bundle stale.

Update `README.md` with Codex marketplace installation and upgrade instructions while preserving existing instructions for direct installation and other agents.

## Versioning

The plugin begins at `1.0.0`. Any published change to bundled skill contents or plugin metadata requires a version increment in `plugins/personal-skills/plugin.json`. Marketplace-only descriptive changes that do not change the installed package may retain the plugin version.

The synchronization script does not increment versions automatically. Version choice remains an intentional release decision and is documented in both agent-guidance files.

## Validation

Repository validation must prove:

1. All JSON manifests parse successfully.
2. Marketplace source paths resolve within the repository.
3. The plugin contains exactly the selected five skill directories.
4. Every generated directory is recursively identical to its canonical source.
5. Every bundled skill contains a readable `SKILL.md` with a declared name.
6. `codex plugin marketplace add` recognizes a clean checkout as `bryancowan-skills`.
7. `codex plugin list --marketplace bryancowan-skills --available --json` reports `personal-skills` at version `1.0.0` before installation.
8. After installation in an isolated test configuration, Codex reports the plugin installed and enabled and its cache contains exactly the five expected skills.

Local marketplace and isolated configuration tests must not alter Bryan's active Codex installation.

## Delivery

Create a feature branch, commit the design and implementation, push the branch, and open a pull request. The PR description will include the selected skill list, manifest layout, synchronization workflow, validation evidence, and the post-merge migration steps.

## Post-merge Migration

Do not replace direct installations from a temporary PR branch. After the PR is merged to `main`:

1. Add `bryancowan/skills` as a Git-backed Codex marketplace.
2. Install `personal-skills@bryancowan-skills`.
3. Verify the plugin is installed and enabled at the expected version and contains exactly the five skills.
4. Move each matching direct installation into a timestamped backup root outside `~/.codex/skills` and `~/.agents/skills`.
5. Re-run plugin inventory and cache-content checks after the moves.
6. Start a new Codex session so skill discovery is rebuilt without the direct copies.

The migration stops immediately if marketplace addition, plugin installation, skill enumeration, or content equality fails.

## Rollback

If the marketplace plugin fails after direct copies are moved:

1. Disable or remove only `personal-skills@bryancowan-skills` as appropriate.
2. Move the timestamped backups back to their original active paths.
3. Verify the restored directories and start a new Codex session.

Backups remain untouched until Bryan explicitly requests their deletion.
