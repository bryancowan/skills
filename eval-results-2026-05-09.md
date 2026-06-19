# Prompt-Creation Skill Eval Regression — 2026-05-09

## Method

**Manual fallback was used.** The automated `run_loop` path described in the task brief was not runnable because `skills/skill-creator/` does not exist in this repository (only `skills/prompt-creation/`, `skills/good-documentation/`, etc.). There is no `scripts/run_loop.py` to invoke. Manual eval was performed by reading the skill's `SKILL.md` and `references/techniques.md` into context, then for each of the 8 cases in `skills/prompt-creation/evals/evals.json` drafting the response the skill would produce and grading it against the case's `expected_output`.

Note: the task brief referenced `skills/bryan/prompt-creation/`. That path does not exist; the skill lives at `skills/prompt-creation/`. The eval set, SKILL.md, and references at that path were used.

This is a read-only audit. No skill files were modified.

## Summary

| ID | Case theme                                    | Status | Reason if FAIL |
|----|-----------------------------------------------|--------|----------------|
| 1  | Claude product-photo description prompt       | PASS   | —              |
| 2  | Improve vague coding-assistant prompt         | PASS   | —              |
| 3  | 3-agent Claude Code blog-post pipeline        | PASS   | —              |
| 4  | o3 anti-CoT hard rule                         | PASS   | —              |
| 5  | ToT + MoE single-prompt refusal hard rule     | PASS   | —              |
| 6  | Cursor scope-locked refactor                  | PASS   | —              |
| 7  | Midjourney Quick Paste discipline             | PASS   | —              |
| 8  | Claude Opus 4.7 over-engineering guard        | PASS   | —              |

**Result: 8/8 PASS.**

## Special-attention cases (#4–#8)

Each of the new hard-rule cases was checked against the corresponding rule in `SKILL.md` "Hard rules — never violate" and the Mode 5 diagnostic checklist.

### #4 — Anti-CoT on o3 — fires correctly

The hard rule "Never add Chain-of-Thought to reasoning-native models" lists o3 explicitly and instructs: "give short clean instructions stating only the goal and desired output format." The Mode 5 diagnostic also has "CoT on reasoning-native model → REMOVE IT." A response under this skill would (a) decline the user's CoT request, (b) explain that o3 reasons internally and CoT scaffolding degrades output, and (c) deliver a short prompt with only goal + output format. All three requirements in `expected_output` are met.

### #5 — ToT/MoE single-prompt refusal — fires correctly

The hard rule covers both Tree of Thought and Mixture of Experts under "Never embed fabrication-prone techniques in a single prompt," with the rationale ("the model role-plays the structure and fabricates the content"). `references/techniques.md` reinforces this with the multi-pass-only table, listing both ToT and MoE, and explicitly suggests single-pass alternatives: "Few-Shot, Skeleton-of-Thought, RCI within one response, or Decomposed Prompting." A response under this skill would refuse the embed, explain the fabrication trap, offer the named alternatives, and ask whether the user has real orchestration. All requirements in `expected_output` are met.

### #6 — Cursor routing (scope lock + binary done-when) — fires correctly

The skill routes Cursor to `context/tools-and-services/cursor-windsurf/`. The Mode 5 diagnostic checklist also bakes in the required pieces independent of any file load: "no file/function boundaries for IDE AI → add scope lock" and "no success criteria → derive binary pass/fail." Combined with the "default to Quick paste when the request is concrete" rule, a response would include: file path (`src/pages/Login.tsx`), function name (`handleSubmit`), scope lock + do-not-touch list, version constraints (TypeScript 5.4 strict, React 18), explicit `react-hook-form` dependency add (or no-new-deps guard), and a binary "Done when" block — without long pedagogical commentary. All requirements met.

### #7 — Quick Paste discipline — fires correctly

User says "No explanation needed" — a hard trigger phrase listed in Mode 5 ("don't explain", "no explanation"). The skill's Mode 5 output format is `[fenced block]` then `🎯 Target:` and `💡 [one-line optimization note]` — nothing else. A response would be a single Midjourney prompt (comma-separated descriptors, `--ar 16:9 --v 6`, `--no` for negatives) followed by the two-line target/optimization note, with zero design-choices section and zero iteration hooks. All requirements met.

### #8 — Opus 4.7 over-engineering guard — fires correctly

The hard rule is verbatim explicit: "Add an over-engineering guard to any Claude Opus 4.x prompt. ... Always include: 'Only make changes directly requested. Do not add features, refactor, or introduce abstractions beyond what was asked.'" A response under this skill would include that exact sentence, plus scope (which file/files), allowed vs. forbidden actions, `✅` per-step checkpoint output, and stop conditions for destructive actions. All requirements met.

## Per-case detail

**#1 — Claude product photography (PASS).** Mode 1 produces: clear role (SEO copywriter for handmade goods), Claude XML-tag structure, length window (~150 words), SEO instruction, a sample output using the user's ceramic mug, Professional personality. Sample output requirement in `expected_output` is satisfied by the Mode 1 anatomy step that explicitly recommends 2–5 examples.

**#2 — Improve vague coding-assistant prompt (PASS).** Mode 3 review path produces: improved prompt with the over-engineering guard verbatim, Efficient personality, positive reframing of "be thorough" (which is what was producing rambling), explicit output format, plus the required `Revision Notes` block per Mode 3's deliverable spec.

**#3 — 3-agent blog-post pipeline (PASS).** Mode 2 produces: three labeled agents (Researcher / Drafter / Editor), each with role, defined input, defined output, structured handoff (research_brief → draft → final), tool/limit specs (Researcher: web search + cap; Drafter: skeleton-of-thought + style; Editor: RCI), and Claude XML tags throughout. Matches `expected_output` techniques mapping exactly.

**#4 — o3 anti-CoT (PASS).** See special-attention block.

**#5 — ToT + MoE refusal (PASS).** See special-attention block.

**#6 — Cursor refactor (PASS).** See special-attention block.

**#7 — Midjourney Quick Paste (PASS).** See special-attention block.

**#8 — Opus 4.7 guard (PASS).** See special-attention block.

## Recommendations

No FAILs to remediate. Two low-priority observations from this audit (not requested fixes — flagged for the next intentional pass):

1. The Cursor case (#6) relies on the user's request being "concrete" enough to trigger Quick Paste discipline. The current `SKILL.md` uses a soft phrasing ("default to Quick paste"). If a future eval introduces a Cursor case with intentionally less-concrete framing, the skill could plausibly drop into Mode 1 and emit pedagogical commentary that would fail the `expected_output`. A targeted hardening would be a Mode 5 / tool-routing line: "Cursor / Windsurf / IDE-agent prompts ALWAYS use Quick Paste output discipline regardless of phrasing."
2. The hard-rule list at the top of `SKILL.md` is the single point of truth for cases #4, #5, and #8. Any future edit that reorders or trims that section would silently regress these three cases at once. Worth keeping fenced behind a comment marker so it's obvious to future editors.

## Source references

- Skill: `skills/prompt-creation/SKILL.md`
- Techniques reference: `skills/prompt-creation/references/techniques.md`
- Eval set: `skills/prompt-creation/evals/evals.json`
- Method: manual fallback (no `skills/skill-creator/` available)
