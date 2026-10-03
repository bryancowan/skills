# Research, Web Search, and Citation Prompting

Prompting patterns for agents that gather information and have to show their work. Covers OpenAI's deep research models, the web search tool, and citation formatting — the mechanics are OpenAI-specific but the prompting patterns port.

Sourced: 2026-10-03 (citation formatting and web-search model support re-read; the deep research section was last checked 2026-07-26)

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

1. **Clarify** — a fast cheap model (`gpt-6-luna`) asks qualifying questions until the brief is complete.
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

**Supported:** the Responses API tool is `{ "type": "web_search" }` (`web_search_preview` remains for legacy integrations); OpenAI's current examples use `gpt-6-astra`. Chat Completions uses `gpt-5-search-api` (200k context). `gpt-4o-search-preview` and `gpt-4o-mini-search-preview` shut down 2026-07-23; `o4-mini` shuts down 2026-10-23. The page gives no full per-model support list, so check the target model's page.

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
- **Remove language that discourages tool use.** "Only use tools when strictly necessary" makes Claude Sonnet 5.5 answer from stale training knowledge. Its guide has Anthropic's replacement snippet; Fable 5.1 at `low` effort has a similar one for unfamiliar names.
- **Summaries that lift source wording unmarked** (Fable 5.1): fix with one complete worked example plus a rationale, in `context/models/anthropic-claude/claude-5-family-guide.md`.

---

## Citation formatting

### Decide what can be cited before writing the prompt

| Citable unit | Precision | Notes |
|---|---|---|
| Document | Least | Easy for the model, hard for a reader to verify |
| **Block / chunk** | Middle | **OpenAI's recommended default** |
| Line range | Most | Hardest for the model to get right |

A good unit keeps the **same ID across runs**, is readable in context by a person, and is large enough to make sense but small enough to stay precise.

**The model can't cite what it wasn't shown clearly.** Each source needs a stable ID (`file1`, `block1`), readable text, and optional metadata (URL, title, timestamp).

**Use a format the model already knows.** OpenAI warns that custom or unfamiliar citation formats raise citation errors, especially at low reasoning effort and on complex tasks where the reasoning budget goes to the task itself. If citations are wrong at `low`, raise effort or simplify the format before rewording the instructions.

### Marker format

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

OpenAI publishes two templates. Pick by where the sources come from.

**Sources returned by a tool** (IDs like `turn0file0`; replace `tool_1` with your tool's name):

```md
## Citations

Results are returned by "tool_1". Each message from `tool_1` is called a "source" and identified by its reference ID, which is the first occurrence of `turn\\d+file\\d+` (for example, `turn0file0` or `turn2file1`). In this example, the string `turn0file0` would be the source reference ID.

Citations are references to `tool_1` sources. Citations may be used to refer to either a single source or multiple sources.

A citation to a single source must be written as:
{CITATION_START}cite{CITATION_DELIMITER}turn\d+file\d+{CITATION_STOP}

If line-level citations are supported, a citation to a specific line range must be written as:
{CITATION_START}cite{CITATION_DELIMITER}turn\d+file\d+{CITATION_DELIMITER}L\d+-L\d+{CITATION_STOP}

Citations to multiple sources must be written by emitting multiple citation markers, one for each supporting source.

You must NOT write reference IDs like `turn0file0` verbatim in the response text without putting them between {CITATION_START}...{CITATION_STOP}.

- Place citations at the end of the supported sentence, or inline if the sentence is long and contains multiple supported clauses.
- Citations must be placed after punctuation.
- Cite only retrieved sources that directly support the cited text.
- Never invent source IDs, line ranges, or block locators that were not returned by the tool.
- If multiple retrieved sources materially support a proposition, cite all of them.
- If the retrieved sources disagree, cite the conflicting sources and describe the disagreement accurately.
```

**Sources injected into the prompt** (wrap each in `<BLOCK id="block5"> ... </BLOCK>`; no `turn#` prefix needed, but the marker must match the injected ID exactly):

```md
## Citations

Supporting context is provided directly in the prompt as citable units. Each citable unit is identified by the value of its `id` attribute in the first occurrence of a tag such as `<BLOCK id="block5"> ... </BLOCK>`. In this example, `block5` would be the source reference ID.

Citations are references to these provided citable units. Citations may be used to refer to either a single source or multiple sources.

A citation to a single source must be written as:
{CITATION_START}cite{CITATION_DELIMITER}<block_id>{CITATION_STOP}

Citations to multiple sources must be written by emitting multiple citation markers, one for each supporting block.

You must NOT write block IDs verbatim in the response text without putting them between {CITATION_START}...{CITATION_STOP}.

- Place citations at the end of the supported sentence, or inline if the sentence is long and contains multiple supported clauses.
- Citations must be placed after punctuation.
- Cite only blocks that appear in the provided context.
- Never invent new block IDs.
- Never cite outside knowledge or outside authorities.
- If multiple blocks materially support a proposition, cite all of them.
- If the provided blocks conflict, cite the conflicting blocks and describe the conflict accurately.
```

**Optional source-quality block** for web research, where relevance and balance matter:

```xml
<extra_considerations_for_citations>
- **Relevance:** Include only search results and citations that support the cited response text. Irrelevant sources permanently degrade user trust.
- **Diversity:** You must base your answer on sources from diverse domains, and cite accordingly.
- **Trustworthiness:** To produce a credible response, you must rely on high quality domains, and ignore information from less reputable domains unless they are the only source.
- **Accurate Representation:** Each citation must accurately reflect the source content. Selective interpretation of the source content is not allowed.

Remember, the quality of a domain/source depends on the context.
- When multiple viewpoints exist, cite sources covering the spectrum of opinions to ensure balance and comprehensiveness.
- When reliable sources disagree, cite at least one high-quality source for each major viewpoint.
- Ensure more than half of citations come from widely recognized authoritative outlets on the topic.
- For debated topics, cite at least one reliable source representing each major viewpoint.
- Do not ignore the content of a relevant source because it is low quality.
</extra_considerations_for_citations>
```

The injected-context template is abridged by one paragraph and one example line from OpenAI's page; the rules are complete.

### Parsing

Use a regex to extract citations, capture the source ID and any locator, and preserve character offsets so you can strip the raw markers before display while still rendering links at the right positions.

---

## Related

- Grounding and quote-based anti-hallucination techniques: `guardrails.md` §1
- Anthropic's research prompt (competing hypotheses, confidence tracking, hypothesis tree): `context/models/anthropic-claude/claude-5-family-guide.md`
- Gemini's Google Search grounding: `context/models/google-gemini/gemini-prompting-strategies.md`
- Cost control for long research runs: `caching-and-cost.md`
