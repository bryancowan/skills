---
description: One iteration of the ship-and-watch loop — check PR CI, fix one failure if any, or stop the loop when green
---

# /ship-and-watch-tick

This is the recurring body invoked by `/loop 5m /ship-and-watch-tick`. Run
exactly one iteration, then end your turn (the loop harness will fire you
again in 5 minutes unless you tell it to stop).

## Step 1 — Load state

Read `.claude/.ship-and-watch-state.json`. If it doesn't exist, the loop was
started without `/ship-and-watch` first — print an error and call
`/loop stop` (or instruct the user to stop the loop manually) and exit.

## Step 2 — Check guardrails

- If `iterations >= 12`: print "ship-and-watch: 12 iterations reached, stopping
  loop. PR <url> still has failing checks — please look manually." Stop the
  loop and exit.
- If `consecutiveSame >= 2`: print "ship-and-watch: same failure twice in a
  row, stopping loop to avoid infinite churn. Failure: <signature>." Stop the
  loop and exit.

Increment `iterations` and persist immediately.

## Step 3 — Poll PR status

Run `gh pr checks <prNumber> --json name,state,conclusion,link`. Parse the
result.

- If every check has `conclusion == "SUCCESS"` (or state SUCCESS): print
  "ship-and-watch: PR <url> is green. Stopping loop." Stop the loop, delete
  `.claude/.ship-and-watch-state.json`, and exit.
- If any check is still `IN_PROGRESS` or `QUEUED`: print "ship-and-watch:
  iteration N — checks still running, will re-check in 5 min." Exit (do
  nothing else this tick).
- If any check has `conclusion == "FAILURE"` (or `CANCELLED`, `TIMED_OUT`):
  proceed to Step 4.

## Step 4 — Diagnose one failure

Pick the first failing check. Fetch its logs with `gh run view --log-failed`
(or `gh pr checks --watch=false` then drill in). Extract the error.

Build a failure signature: a short hash of `<check-name>:<first-error-line>`.

- If signature equals the stored `lastFailureSignature`, increment
  `consecutiveSame` and persist. (Guardrail in Step 2 will catch a second hit
  next iteration.)
- Otherwise reset `consecutiveSame` to 0, store the new signature, and persist.

## Step 5 — Fix the failure

**Scope: only CI failures (lint, typecheck, test, build).** Do NOT respond to
review comments — that was explicitly out of scope for this loop.

1. Read the failing logs and locate the root cause in the codebase.
2. Apply the minimal fix. Don't refactor adjacent code, don't "clean up".
3. Run the same check locally if possible (`pnpm lint`, `pnpm typecheck`,
   `pnpm test`, `pnpm build`) to confirm the fix.
4. Commit with a message like `fix(ci): <short description>` and the standard
   `Co-Authored-By: Claude` trailer. Push with plain `git push` — no
   `--force`, no `--no-verify`.

## Step 6 — Hand back to the loop

Print "ship-and-watch: iteration N — pushed fix for <check-name>, will
re-check in 5 min." End your turn. The loop will fire again automatically.

## Hard rules

- **Never** run `gh pr merge`, `gh pr review --approve`, or any merge/approve
  command. The loop only fixes CI; the human merges.
- **Never** use `git push --force`, `--force-with-lease`, or `--no-verify`.
- **Never** edit files outside the repo or touch `.git/` internals.
- If any step needs information you don't have, stop the loop and ask the
  user — don't guess.