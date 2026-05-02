---
description: Commit + push + open PR, then poll CI every 5 min and auto-fix failures until green
---

# /ship-and-watch

You are the entry point for an automated ship-then-watch workflow. Execute the
phases below in order. Each phase has a hard gate — do not skip.

## Phase 1 — Sanity check

1. Run `git status --porcelain` and `git rev-parse --abbrev-ref HEAD`.
2. **Refuse to proceed** if the current branch is `main`, `master`, or `develop`.
   Tell the user to switch to a feature branch first and stop.
3. If there are no changes AND the branch is already pushed AND a PR already
   exists, skip Phase 2/3 and jump straight to Phase 4 (start the watch loop).

## Phase 2 — Commit + push

1. Stage and commit any uncommitted changes with a descriptive message that
   summarizes the change (read the diff to write it). Use the project's normal
   commit conventions. End the message with the standard `Co-Authored-By:
   Claude` trailer.
2. Push the branch with `-u` if it has no upstream, otherwise plain `git push`.
   **Never** use `--force` or `--no-verify`.

## Phase 3 — Open PR

1. If a PR already exists for this branch (`gh pr view --json number,url`),
   skip to Phase 4.
2. Otherwise run `gh pr create` against the repo's default base branch with a
   title and body that explain the change. Use a HEREDOC for the body.
3. Capture and print the PR URL.

## Phase 4 — Initialize watch state

1. Ensure `.claude/.ship-and-watch-state.json` exists (create with
   `{"iterations": 0, "lastFailureSignature": null, "consecutiveSame": 0,
   "prNumber": <N>}`). Add `.claude/.ship-and-watch-state.json` to
   `.gitignore` if it isn't already.
2. Print the PR URL and tell the user the watch loop is starting.

## Phase 5 — Start the loop

Invoke this exact command: `/loop 5m /ship-and-watch-tick`

That's the last thing you do. The tick command handles polling + fixing +
self-termination.
