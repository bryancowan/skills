# Reducing Latency

Read this when the user says a prompt is too slow, the first token takes too long, or a voice or chat product feels laggy.

**Get quality first.** Anthropic's guidance is to engineer a prompt that works well without constraints, then reduce latency. Cutting early can hide what top performance looks like.

Sourced: 2026-10-03

Sources:
- https://platform.claude.com/docs/en/test-and-evaluate/strengthen-guardrails/reduce-latency
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-opus-5-5
- https://platform.claude.com/docs/en/build-with-claude/prompt-engineering/prompting-claude-sonnet-5-5

---

## What to measure

- **Time to first token (TTFT):** from request to the first token of the response. This is what a streaming UI feels like.
- **Baseline latency:** total time to process the prompt and generate the response.

On models that think before answering, TTFT includes the thinking. A slow start is often a thinking problem, not a prompt-length problem.

## Levers, in the order to try them

1. **Lower effort.** On Claude 5.x and GPT-6 this is the main latency control, and it works more reliably than telling the model to think less.
   - Sonnet 5.5 thinks briefly before almost every reply from `medium` up; at `low` it skips thinking on most simple requests. For chat, start at `medium` or `low`.
   - Opus 5.5 always thinks. Start latency-sensitive work at `low`. As a last resort, "Answer directly without deliberating." in the system prompt can cut thinking further; measure quality.
   - Use a per-message effort change (Claude) or `configuration_update` (GPT-6) to raise effort only for hard turns. Changing the top-level value invalidates the cache on Claude.
2. **Delete "think carefully before answering" from chat system prompts.** On Opus 5.5, removing such a line made replies start sooner with no clear quality decline. If follow-up turns are slow because the model re-examines earlier answers, see the "treat that answer as done" snippet in `context/models/anthropic-claude/claude-opus-5-5-guide.md`.
3. **Pick a faster model.** Claude Haiku 4.5 is Anthropic's fastest; `gpt-6-luna` is OpenAI's. Check the cheap model against the eval before assuming it fails.
4. **Shorten the prompt and the output.** Fewer tokens in and out is faster. Be concise without stripping context the model needs.
   - Ask for a shorter response directly.
   - **Limit by sentences or paragraphs, not words.** Models count tokens, so word-count limits are followed less well.
   - `max_tokens` is a hard cutoff that can stop mid-sentence. It suits multiple-choice and short answers where the answer comes first. On thinking models, thinking counts toward it, so a tight limit can cut the reply off or leave none.
5. **Stream.** Streaming doesn't make generation faster; it improves perceived responsiveness.
6. **Cache the static prefix.** OpenAI measured up to 67% faster TTFT on prompts of 150k+ tokens with caching. See `caching-and-cost.md`.
7. **Parallelize.** Batch independent tool calls in one turn; in multi-agent work, a time budget keeps more agents working in parallel (Opus 5.5 guide).

## Stale advice to skip

Anthropic's latency page still suggests experimenting with `temperature`. On current Claude models (Fable 5 / 5.1, Opus 5 / 5.5, Sonnet 5 / 5.5) a non-default value returns a 400. GPT-6 rejects it whenever reasoning is on. Don't recommend it as a latency lever.

## Voice and realtime

Latency rules differ in speech: keep preambles to one short sentence and see `context/speech-to-speech/`. For streaming transcription, the `delay` setting is the latency/accuracy control (`context/speech-to-speech/gpt-realtime-transcription-guide.md`).
