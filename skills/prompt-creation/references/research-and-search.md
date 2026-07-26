# Research, Web Search, and Citation Prompting

Prompting patterns for agents that gather information and have to show their work. Covers OpenAI's deep research models, the web search tool, and citation formatting — the mechanics are OpenAI-specific but the prompting patterns port.

Sourced: 2026-07-26

Sources:
- https://developers.openai.com/api/docs/guides/deep-research
- https://developers.openai.com/api/docs/guides/tools-web-search
- https://developers.openai.com/api/docs/guides/citation-formatting

---

## Deep research

**Models:** `o3-deep-research`, `o4-mini-deep-research`. Responses API only, and **the request must include at least one data source tool** — web search, file search, or a remote MCP server.

| Parameter | Purpose |
|---|---|
| `background: true` | Strongly recommended — tasks run for tens of minutes |
| `max_tool_calls` | The cost ceiling. Set it. |
| `instructions` | System-level guidance |
| `tools` | `web_search_preview`, `file_search` (max 2 `vector_store_ids`), `code_interpreter`, remote MCP (`require_approval: "never"`) |

Without background mode, set client timeouts high (3600s). Background mode is incompatible with Zero Data Retention.

### The three-step pattern

ChatGPT's Deep Research runs a pipeline the API **does not** implement for you. If you want comparable quality, build it:

1. **Clarify** — a fast cheap model (`gpt-4.1`, `gpt-5.6-luna`) asks qualifying questions until the brief is complete.
2. **Rewrite** — expand the user's request into detailed researcher instructions.
3. **Research** — pass the enriched prompt to the deep research model.

The rewriting step is where most of the quality comes from. The documented framing for it:

```text
Your job is to produce a set of instructions for a researcher that will complete the task. Do NOT complete the task yourself.
```

Include in those generated instructions: specificity requirements, which dimensions are open-ended versus fixed, an explicit instruction not to assume facts not in the request, table formatting expectations, and source prioritization rules.

**This pattern generalizes.** Any expensive long-running agent benefits from a cheap model clarifying and expanding the brief first — it's far cheaper to ask a question up front than to burn 30 minutes of tool calls on the wrong interpretation.

### Output

The `output` array interleaves `web_search_call`, `code_interpreter_call`, `mcp_tool_call`, and `file_search_call` items with a final `message` carrying inline citations and annotations (URL, title, start/end indices).

### Security

Deep research agents read untrusted content by design — this is the indirect prompt injection threat model. Connect only to trusted MCP servers, log every tool call and model message, validate tool arguments against a schema, stage workflows so public and private data access are separated, and screen links before rendering them. See `guardrails.md` §4.

---

## Web search tool

| Parameter | Notes |
|---|---|
| `search_context_size` | `low` / `medium` / `high` — the main cost/quality dial |
| `return_token_budget` | `unlimited` for extended research; default `default` |
| `filters` | `allowed_domains` or `blocked_domains`, up to 100 entries each |
| `search_content_types` | `["image", "text"]` to include images |
| `image_settings` | `max_results`, `caption: true` |
| `user_location` | `country` (ISO), `city`, `region`, `timezone` |
| `external_web_access` | `false` for cached-only |

**Supported:** Responses API on `gpt-5.6`, `gpt-5.5`, `gpt-5.4`, `gpt-4.1`, `gpt-4.1-mini`. Chat Completions via `gpt-5-search-api` (200k context); `gpt-4o-search-preview` is deprecated (sunset 2026-07-23).

**Limits:** search context caps at **128k regardless of the model's window**; 100 domains per filter list; no image search or user location on deep research models.

**Cost:** billed per search action, on the model's tiered rate limits — no separate quota. Anthropic's equivalent is $10 per 1,000 searches.

Output: a `web_search_call` item (action `search`, `open_page`, or `find_in_page`, with optional `queries`) plus a `message` with a `url_citation` annotations array. **Citations must be clearly visible and clickable in your UI** — this is a stated requirement, not a suggestion.

### Prompting for search

- **`allowed_domains` beats prompt instructions.** "Only use reputable sources" is a wish; a domain allowlist is enforcement.
- **Set a stopping condition.** From GPT-5.5's guidance: *"After each result, ask: 'Can I answer the user's core request now with useful evidence and citations?'"*
- **Say what a complete answer contains** — evidence, caveats, next action — rather than "be thorough."
- **Match `search_context_size` to the task.** `low` for a fact lookup, `high` for synthesis across sources. It is a direct cost multiplier.
- **Name the recency requirement explicitly.** "Prioritize sources from the last 12 months; note the publication date of each source you cite."
- **Ask for conflicting viewpoints** where they exist, rather than a single synthesized narrative that hides disagreement.

---

## Citation formatting

Citations are emitted as markers embedded in the response text:

```
{CITATION_START}cite{CITATION_DELIMITER}source_id{CITATION_STOP}
```

With an optional locator:

```
{CITATION_START}cite{CITATION_DELIMITER}turn0file1{CITATION_DELIMITER}L8-L13{CITATION_STOP}
```

**Recommended markers:** `CITATION_START` = ``, `CITATION_DELIMITER` = ``, `CITATION_STOP` = ``.

**Source ID patterns:** file-based (`turn0file0`), block-based (`block1`), or any `[A-Za-z0-9_-]+`. **Locators:** line ranges (`L8-L13`) or block references (`Block1`).

### Rules to state in the prompt

- Place citations at the end of the sentence, or inline for longer passages — always **after** punctuation.
- Never write a source ID verbatim in the response text outside a citation marker.
- Never cite anything outside the provided sources.
- Cite multiple supporting sources when more than one applies.
- Keep citations diverse and relevant — don't cite the same source for every sentence.
- Prioritize trustworthy sources; represent conflicting viewpoints; make sure each citation actually supports the sentence it's attached to.

### Parsing

Use a regex to extract citations, capture the source ID and any locator, and preserve character offsets so you can strip the raw markers before display while still rendering links at the right positions.

---

## Related

- Grounding and quote-based anti-hallucination techniques: `guardrails.md` §1
- Anthropic's research prompt (competing hypotheses, confidence tracking, hypothesis tree): `context/models/anthropic-claude/claude-5-family-guide.md`
- Gemini's Google Search grounding: `context/models/google-gemini/gemini-prompting-strategies.md`
- Cost control for long research runs: `caching-and-cost.md`
