# GPT-Live Prompting Guide (`gpt-live-1`)

## Overview

`gpt-live-1` ($0.05/minute) is OpenAI's model for **continuous, natural voice conversation**. Its defining architectural feature is that it **does not do the hard thinking itself** — it handles the speech and delegates reasoning and data lookup to a backend, then speaks the result.

That single fact determines how you prompt it. The prompt is not a task description; it is a **delegation policy**. Most failures are the model answering from its own head when it should have handed off, or stalling silently while the backend works.

**Not the same as the `gpt-realtime-*` family.** Use this guide for `gpt-live-1`. For `gpt-realtime-2.1` / `gpt-realtime-1.5` (speech-to-speech models that reason themselves), use `context/speech-to-speech/gpt-realtime-prompting-guide`.

Sourced: 2026-09-12

Sources:
- https://developers.openai.com/api/docs/guides/live-prompting
- https://developers.openai.com/api/docs/pricing

---

## Recommended prompt structure

Goes in `session.instructions`. Keep it short — OpenAI's guidance is to stay concise, avoid conflicting rules, and test against real conversations rather than piling on prescriptive instructions.

```text
You are [name], a calm, friendly voice assistant for [service].
Speak warmly and naturally, at an unhurried pace. Be clear and direct, not overly cheerful.
If the user is frustrated, acknowledge it briefly and focus on the next helpful step.

Backchannel policy: Use moderate backchannels. Acknowledge naturally without competing with the main response.

Interruption policy: Stop speaking when the user interrupts. Listen to what they say.

Delegation policy:
Backend tools:
- [capability]: [what the backend can do]

Delegate to the backend when:
- The request needs a backend capability or careful reasoning.
- A correction changes the work already requested.

Do not delegate to the backend when:
- You can answer from the conversation or a still-current result.
- You need a brief clarification to understand the request.

Delegate before giving an answer that depends on backend work.
Do not guess the result while waiting.
```

---

## The four sections

**Personality** — a few short sentences setting role, tone, and pace. Voice needs pace stated explicitly; text prompting has no equivalent.

**Backchannels** — the listening sounds ("mm-hm", "right") that make a voice feel present. Tune the policy line to your product, then test that the backchannels don't override conversational turns. Too many and the assistant talks over the user; too few and it feels dead on the line.

**Interruptions** — stop speaking, listen. Important detail: **backend work continues independently of the interruption.** Stopping mid-sentence doesn't cancel the delegated task, so don't write instructions that assume it does.

**Delegation** — three labelled lists: what the backend can do, when to delegate, when not to. The two load-bearing lines are the last two:

> Delegate before giving an answer that depends on backend work.
> Do not guess the result while waiting.

Without them the model fills the latency gap with a plausible guess, and the real result arrives afterwards and contradicts it.

Note the asymmetry: **a clarifying question is not a delegation.** "Which account did you mean?" should be answered by the voice model directly — routing it to the backend adds a round trip to something the model already has in context.

---

## Optional controls (add only when needed)

OpenAI's appendix treats these as opt-in, not defaults. Add a rule only after you've observed the problem:

- Response length
- Language and translation
- Silence handling
- Selected / scoped requests
- Unclear details
- Reuse of a prior result

Every rule you add is a rule that can conflict with another one mid-conversation. Prefer testing over pre-emptive coverage.
