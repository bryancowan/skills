# Repository guidance

## Canonical skill sources

Treat `skills/` as authoritative. The files under `plugins/personal-skills/skills/` are generated copies for the Codex marketplace plugin; never edit them directly.

The seven canonical and generated skill directories must contain real files and directories only; nested symlinks are unsupported.

The Codex plugin intentionally bundles only `description-and-tags`, `construction-near-me`, `good-documentation`, `obsidian-jd-organizer`, `obsidian-wiki-compiler`, `podcast-transcript`, and `prompt-creation`.

## Keep the Codex bundle synchronized

After changing one of the seven bundled skills, run:

`bash scripts/sync-personal-skills-plugin.sh`

Before committing, run:

`bash scripts/sync-personal-skills-plugin.sh --check`
`bash tests/test-personal-skills-plugin.sh`
`bash tests/test-personal-skills-plugin-version-policy.sh`

Increment `plugins/personal-skills/plugin.json` whenever published plugin contents or metadata change. Do not change `.claude-plugin/marketplace.json` unless the Claude marketplace itself changes.
