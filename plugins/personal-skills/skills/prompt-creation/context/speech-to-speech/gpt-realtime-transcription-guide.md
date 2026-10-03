# Realtime Transcription Prompting Guide (Speech-to-Text)

## Overview

Streaming transcription over the Realtime API. This is **speech-to-text**, not a voice agent: there is no personality, no tools, and no conversation flow to write. The "prompt" is three small context fields plus a latency setting. For speech-to-speech agents see `gpt-realtime-prompting-guide`; for a voice layer that delegates to a backend see `gpt-live-prompting-guide.md`.

Sourced: 2026-10-03

Sources:
- https://developers.openai.com/api/docs/guides/realtime-transcription

---

## Models

| Model | Use it when |
|---|---|
| `gpt-live-transcribe` | Default for realtime transcription. Returns transcript deltas as speech arrives and a final transcript when the audio turn is committed. |
| `gpt-transcribe` | Transcription should begin after a committed audio turn, or you need detected-language output (its completion events include a `languages` array). It also uses earlier transcribed turns as context automatically. |

**`gpt-live-transcribe` does not return word-level timestamps, speaker labels, or confidence scores.** If the application needs them, use a compatible file transcription model or an application-level fallback. Settle this before writing anything else; no prompt adds them.

## The three context fields

Set them in a `session.update` event on a `type: "transcription"` session. Send another `session.update` to change them mid-session.

| Field | What goes in it | Notes |
|---|---|---|
| `prompt` | A description of the recording or its setting | Describe the situation, don't give instructions |
| `keywords` | Product names, acronyms, and other literal terms that may appear in the audio | "Keywords are hints, not required output" |
| `languages` | Expected input languages as ISO 639-1 or 639-3 codes; regional Chinese codes `zh-cn`, `zh-tw`, `zh-hk` | Plural. `gpt-live-transcribe` uses `languages`, not the singular `language` field |

OpenAI's example values (shown flat here; they sit in the transcription configuration of the `session.update` event):

```json
{
  "prompt": "A customer support call about a premium plan and account AC-42.",
  "keywords": ["premium plan", "AC-42", "billing"],
  "languages": ["en", "fr"]
}
```

Add context when the audio contains specialized vocabulary or more than one expected language. Writing guidance:

- Keep `prompt` to a sentence about who is speaking and about what. It is context, so an instruction like "transcribe accurately" adds nothing.
- Put the exact spellings you need in `keywords`: account ID formats, product names, people's names, acronyms.
- List only languages you expect. Test each one.

## `delay`: the latency/accuracy setting

Lower delay produces earlier partial text. Higher delay gives the model more audio context before it emits text and can improve word error rate.

| `delay` | Start here for |
|---|---|
| `minimal` | The most latency-sensitive interactions |
| `low` | Low-latency live captions |
| `medium` | A balanced tradeoff |
| `high` | Accuracy matters more than immediate display |
| `xhigh` | Workflows that can tolerate maximum delay for more context |

Don't choose from synthetic audio alone. Test with representative microphones, telephony audio, accents, background noise, code-switching, domain vocabulary, and long sessions.

## Session mechanics that affect design

- Audio format `audio/pcm` at 24 kHz; `turn_detection: null` on transcription sessions.
- Append audio with `input_audio_buffer.append`; commit a turn with `input_audio_buffer.commit` to get the final transcript.
- Delta events carry incremental text; completion events carry the full `transcript`. Later deltas can correct earlier text, so decide how the UI revises partials.
- Use `item_id` to order and reconcile final transcripts across turns.

## Production checklist

- Pick a target latency and accuracy threshold before tuning.
- Test against real production audio, not only clean samples, and each target language.
- Include numbers, dates, currency, email addresses, product names, and domain terms in the eval set.
- Track empty, truncated, and delayed transcripts separately from word error rate.
- Keep a fallback path for timestamps, speaker labels, or confidence fields.

## Downstream cleanup

Turning a raw transcript into speaker-labeled notes is a text-model task with its own prompt. Give that model the same keyword list so it corrects misheard terms consistently, and tell it to mark unclear passages rather than guess.
