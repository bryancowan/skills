# Codex Goals — Persistent Objectives for Long-Running Work

## Overview

A **Goal** is a thread-scoped persistent objective in Codex. It changes the contract with the agent:

> A normal prompt says: *do this next thing.* A Goal says: *keep working until this outcome is true.*

Prompts run `ask → work → result → wait`. Goals run `work → check → continue or complete`. The difference matters most when the path to the outcome is unknown at the start — optimization, flaky-test hunting, research reproduction — where you cannot enumerate the steps in advance because each attempt tells you what to try next.

Goals are **thread-scoped state, not global memory.** They do not persist across threads and are not a substitute for `AGENTS.md`.

Sourced: 2026-09-12

Sources:
- https://developers.openai.com/cookbook/examples/codex/using_goals_in_codex

Companion: `context/models/openai-codex/codex-prompting-guide` (starter prompt, AGENTS.md, compaction, tools, phase parameter).

---

## Commands

| Command | Effect |
|---|---|
| `/goal <text>` | Attach a Goal to the current thread |
| `/goal pause` | Suspend without discarding |
| `/goal resume` | Reactivate |
| `/goal clear` | Remove |

---

## What changes when a Goal is active

1. **The objective stays visible** across turns, even when intermediate results are inconclusive.
2. **Continuation becomes possible from an idle thread** — Codex can pick the work back up without you re-issuing instructions.
3. **Completion becomes evidence-based** — Codex audits progress against the verification surface rather than declaring itself done.

Point 3 is the one that earns the feature. It is also the one that silently fails if you skip the verification surface when writing the Goal.

---

## How to write a Goal

Six components. A Goal missing the **verification surface** or the **blocked stop condition** degrades into a vague prompt that runs forever.

| Component | What it is |
|---|---|
| **Outcome** | What should be true when the work is done |
| **Verification surface** | The test, benchmark, report, artifact, command output, or source material that *proves* it |
| **Constraints** | What must not regress while Codex works |
| **Boundaries** | Which files, tools, data, repositories, or resources Codex may use |
| **Iteration policy** | How Codex should decide what to try next after each attempt |
| **Blocked stop condition** | When to stop and report that no defensible path remains |

### Weak → strong

```text
/goal Improve performance
```

Nothing here is checkable: no target, no measurement, nothing protected. Codex will make plausible-looking changes and stop when it feels finished.

```text
/goal Reduce p95 latency below 120 ms on the checkout benchmark while keeping the correctness test suite green
```

Now the outcome is a number, the verification surface is a named benchmark, and the constraint is a named suite. Codex can audit itself against evidence instead of assumption.

A fuller shape adding the remaining three components:

```text
/goal Reduce p95 latency below 120 ms on the checkout benchmark while keeping the correctness
test suite green.

Boundaries: services/checkout/ and its tests only. Do not change the database schema or touch
services/payments/.
Iteration policy: after each attempt, re-run the benchmark and record the p95 delta. If a change
does not improve p95, revert it before trying the next one.
Stop and report if: three consecutive attempts fail to improve p95, or the only remaining path
requires a schema change.
```

---

## Rules of thumb

- **Define the evidence standard before the investigation starts**, not after. Retrofitting "how would we know this worked" onto a Goal in progress is how you end up accepting a confident summary as proof.
- **In research and reproduction work, require the report to separate confirmed findings from approximate reconstructions.** Without that instruction the two get blended into one authoritative-sounding narrative.
- The iteration policy is where you encode "revert what didn't work" — otherwise failed attempts accumulate in the diff.

---

## When *not* to use Goals

- A one-line edit, a simple explanation, a short code review, or any question where you want **one answer**.
- Objectives that aren't clear yet. Sharpen the objective first — a Goal makes a vague objective run longer, not better.
- Anything where **the finish line cannot be verified objectively.** If you can't name the artifact that proves completion, you don't have a Goal, you have a wish.
