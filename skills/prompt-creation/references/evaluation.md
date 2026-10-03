# Evaluation: Success Criteria and Test Design

How to tell whether a prompt works. Reach for this when a user is optimizing a prompt for production, comparing two versions, choosing a model or effort level, or says "it seems better." Every vendor's model-selection and effort guidance assumes an eval set exists; most users don't have one.

The method is Anthropic's, but nothing here is Claude-specific.

Sourced: 2026-10-03

Sources:
- https://platform.claude.com/docs/en/test-and-evaluate/develop-tests

---

## 1. Write the success criteria first

A usable criterion is **specific** (what exactly should happen), **measurable** (a number or a consistently applied scale), **achievable** (grounded in a benchmark, a prior experiment, or the current baseline), and **relevant** (tied to what the application needs).

| | Example |
|---|---|
| Bad | The model should classify sentiments well |
| Good | The sentiment analysis model should achieve an F1 score of at least 0.85 on a held-out test set of 10,000 diverse Twitter posts, which is a 5% improvement over the current baseline. |

Hazy goals can be made measurable too. "Safe outputs" becomes "less than 0.1% of outputs out of 10,000 trials flagged for toxicity by the content filter."

Most applications need **several criteria at once**. A fuller version of the same target:

```text
On a held-out test set of 10,000 diverse Twitter posts, the sentiment analysis model should achieve:
- an F1 score of at least 0.85
- 99.5% of outputs are non-toxic
- 90% of errors would cause inconvenience, not egregious error
- 95% response time < 200ms
```

Categories to consider, so the user doesn't only measure accuracy:

| Category | The question |
|---|---|
| Task fidelity | How well must it perform, including on rare or hard inputs? |
| Consistency | Should the same question asked twice get a semantically similar answer? |
| Relevance and coherence | Does it address the question, in a logical order? |
| Tone and style | Does the output suit the audience? |
| Privacy preservation | Does it follow instructions not to use or share certain details? |
| Context utilization | Does it use what's in the conversation history? |
| Latency | What response time does the product need? |
| Price | What is the budget per call and at volume? |

## 2. Design principles

1. **Be task-specific.** Mirror the real task distribution, and include edge cases: irrelevant or nonexistent input, overly long input, poor or harmful user input in chat, and ambiguous cases where humans would struggle to agree.
2. **Automate when possible.** Structure questions so they can be graded automatically: multiple choice, string match, code-graded, LLM-graded.
3. **Prioritize volume over quality.** More questions with slightly lower-signal automated grading beats fewer questions with high-quality hand grading.

## 3. Pick a grading method

Fastest and most reliable first. Use the cheapest method that captures the criterion.

| Criterion | Method | Fits | Example test set |
|---|---|---|---|
| Task fidelity | **Exact match** after normalizing whitespace and case | Categorical answers: classification, routing, extraction of a single value | 1,000 labeled items, with sarcasm and mixed cases |
| Consistency | **Cosine similarity** of sentence embeddings across paraphrases | FAQ bots; the same question worded several ways | 50 groups of paraphrases, with typos and rambling versions |
| Relevance and coherence | **ROUGE-L** against a reference | Summarization | 200 articles with reference summaries, including multitopic ones |
| Tone and style | **LLM-graded Likert scale** (1–5) | Empathy, professionalism, patience | 100 inquiries with a target tone, including an angry customer |
| Privacy | **LLM-graded binary classification** | Whether a response contains protected information | 500 queries, some with explicit, implicit, or hypothetical PHI |
| Context utilization | **LLM-graded ordinal scale** (1–5) | How well a response builds on earlier turns | 100 multi-turn conversations with context-dependent questions |

Anthropic's ranking: **code-based grading** (exact match, string match) is the fastest, most reliable, and most scalable, but lacks nuance. **Human grading** is the most flexible and highest quality, but slow and expensive; avoid it if possible. **LLM-based grading** is fast, flexible, and suited to complex judgment; test it for reliability first, then scale.

### Writing an LLM grader

- **Use a different model to grade than the one that generated the output.** Anthropic calls this general best practice.
- **Detailed, clear rubrics.** "The answer should always mention 'Acme Inc.' in the first sentence. If it does not, the answer is automatically graded as 'incorrect.'" One use case may need several rubrics.
- **Empirical or specific output.** Have the grader output only 'correct' or 'incorrect', or a 1–5 score. Purely qualitative evaluations are hard to assess at scale.
- **Let the grader reason, in its thinking.** Anthropic's current advice is to run the grader with thinking on so it reasons before producing a score; this helps most on complex judgments. Older versions of this advice asked the grader to write its reasoning in the response before the verdict — on current Claude models use thinking instead.
- Wrap the output being graded in tags.

```text
Rate this customer service response on a scale of 1-5 for being {target_tone}:
<response>{model_output}</response>
1: Not at all {target_tone}
5: Perfectly {target_tone}
Output only the number.
```

To audit why a grader gave a score, read its summarized thinking blocks (`display: "summarized"`).

## 4. Using an eval when iterating on a prompt

- Change one thing at a time and re-run the set. A prompt edit that fixes the case in front of you and regresses three others is the usual outcome of iterating without one.
- Re-run on **every model or effort change**. Effort level names don't transfer between models, so a comparison at "the same effort" isn't controlled.
- Compare on the dimension that matters, and on edge cases, not just typical inputs.
- Track latency and cost per task alongside quality, so "better" doesn't mean "twice the tokens."

## Related

- Summarization eval mix (ROUGE, BLEU, embedding similarity, LLM-as-judge): `guardrails.md` §6
- Model and effort selection that depends on having an eval: `model-selection.md`
- Latency as a criterion: `latency.md`
