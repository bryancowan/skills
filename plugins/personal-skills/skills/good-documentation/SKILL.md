---
name: good-documentation
description: Use this skill when writing or reviewing any documentation — user
  guides, READMEs, tutorials, workflow docs, onboarding materials, release
  notes, or any content explaining how something works to stakeholders. Trigger
  on phrases like "write docs for", "document this", "help me write a guide",
  "write a README", "review my docs", "improve this documentation", "write a
  tutorial", "create onboarding material", "help me explain this feature",
  "draft a user guide", or "write instructions for". Use it even when the user
  doesn't say "documentation" explicitly — if they're asking you to explain a
  product, feature, or workflow in written form for an audience, this skill
  applies. Applies proven principles to produce clear, skimmable content that
  works for both technical and non-technical readers.
metadata:
  copilot-enabled-agents: opencode,claude,codex
---

# Good Documentation Skill

Documentation puts useful information inside other people's heads. This skill helps write and review documentation that actually works — for user guides, READMEs, workflow docs, and tutorials aimed at mixed technical and non-technical audiences.

## Two modes

**Write mode**: When the user asks you to write documentation, apply all the principles below as you draft. Don't wait to be reminded — structure, tone, and skimmability should be built in from the start. Use only facts you were given. Write the doc around what you know, and prefer wording that stays true without the missing detail ("choose a filter" rather than "click the Filters button"). Use a [bracketed placeholder] only where the reader needs an exact detail to act, such as a button name, number, or path, and keep these to a handful so the text stays readable. List every assumption in a short "To confirm" list at the end. Don't add features or sections the reader's task doesn't need. Before delivering, scan the draft for the patterns in "Don't compress to be brief" and check that no lead sentence carries more than one idea.

**Review mode**: When the user asks you to review or improve existing documentation, go through each principle category and give specific, actionable feedback. Quote the problem text, name the principle it violates, and suggest a concrete fix. Don't give generic praise — be specific about what's working and what isn't. In any suggested rewrite, keep to facts the author stated. Mark a detail the author left out as a [bracketed placeholder], such as "[how often]", but don't add steps, frequencies, or system behavior of your own, even in brackets.

---

## Principles

### Make docs easy to skim

Most readers don't read top to bottom. They scan to find the part that solves their problem. Make that search fast.

**Write section titles as informative sentences, not abstract nouns.** A title like "Results" forces readers to hop into the body to learn what the results are. A title like "Smart Filters reduce dashboard setup time by 60%" gives the answer immediately. The extra words are worth it.

**Include a table of contents** for anything longer than a few sections. A TOC helps readers navigate and also signals at a glance whether the doc is relevant to them.

**Keep paragraphs short.** If you have an essential point, put it in its own one-sentence paragraph so it can't be buried. Long paragraphs hide information.

**Put the topic word at the start of topic sentences.** Readers skim disproportionately at the first word or two. "Smart Filters speed up dashboard setup" is easier to skim than "Dashboard setup can be sped up with Smart Filters."

**Put the most important information first.** Don't build up to a conclusion — state it, then explain it. Don't introduce your procedure before your results. First means first in order, not compressed. See "Don't compress to be brief" below.

**Use bullets and tables.** Lists are faster to scan than prose. When you have three or more parallel items, reach for a list.

**Bold important text.** Highlight key terms, warnings, or actions so readers who are scanning don't miss them.

---

### Write well

Badly written text is taxing to read. Minimize the tax.

**Keep sentences simple.** When a sentence gets long, split it into two. Cut filler phrases ("it's important to note that", "in order to"), but keep function words like *that*, *the*, and *of* when they help the reader parse. Use imperative mood for instructions ("Click Save" not "You will need to click Save"). See "Don't compress to be brief" below.

**Write sentences that parse unambiguously.** If a reader might misread the subject or verb for even a moment, rewrite. "Write section titles as sentences" is clearer than "Title sections with sentences" even though it's longer.

**Avoid left-branching sentences.** Don't make readers hold a list in memory before knowing what the list is for. Instead of "You need a name, email, and role to invite a user," write "To invite a user, you need a name, email, and role."

**Replace demonstrative pronouns with the actual noun.** "This makes the process faster" is ambiguous. "Caching makes the process faster" is clear. When in doubt, cut the pronoun entirely.

**Be consistent.** Inconsistency distracts readers from the content. If you title one section "How to add a user", don't title the next "User deletion". Pick a pattern and stick to it across all headings, terms, and formatting.

**Don't presume the reader's state of mind.** Avoid "Now you probably want to know how to..." or "Next, you'll need to...". These can feel patronizing. Write "To configure X, ..." instead.

---

### Don't compress to be brief

Shorter is not always easier. Writing that packs the most meaning into the fewest words, which is the default style of many AI models, is harder to read. Front-loading is about the *order* of information. Density is about how each sentence is *built*. Do the first without the second. Padding is the opposite failure: add words that help the reader parse, not words that say nothing.

**Front-load the answer, not the density.** Put the conclusion first, in full, plain sentences. Keep the lead to 1–3 short sentences with one idea each. Define a term before the lead depends on it.

**Cut filler words, keep function words.** "In order to" and "it's important to note" go. *That*, *the*, *of*, and *to* stay when they help the reader parse: "Check the settings that you changed", not "Check the settings you changed".

**Add signposts before surprising or technical content.** When the next part is hard to predict, spell out the connecting words. "To invite a user, you need…" beats a bare list of nouns.

**Spread the information out.** If a sentence carries three or more new terms or numbers, split it. Aim for even density, not maximum density.

**Use the plainer form of these patterns.** They are legal English but cost the reader extra effort, and they are overused in AI-generated text:

| Pattern | Harder to read | Easier to read |
|---|---|---|
| Coined or unusual word pairs | "a reader-patience budget" | "how long readers will keep reading" |
| Verbs made from nouns on the spot | "Calendar it." "Ticket this." | "Add it to your calendar." "Open a ticket for this." |
| Code or things acting like people | "The cache swallows the error." "This edge case bites." | "The cache hides the error." "This edge case causes problems." |
| Three or more stacked nouns | "dashboard filter permission settings" | "the permission settings for dashboard filters" |
| Dropped *that* in dense text | "the file you saved" | "the file that you saved" |
| Subject far from its verb | "Users who, after setting up the filter, reload the page can see…" | "Users can see the results after they set up the filter and reload the page." |

When in doubt, choose the plainer form. A familiar short phrase is fine; the goal is a sentence the reader can parse the first time.

---

### Be broadly helpful

Your readers have varying levels of technical knowledge, English proficiency, and patience. Write as if a smart newcomer might also be reading — even if your primary audience is experienced.

**Write simpler than you think you need to.** Not everyone speaks English as a first language. Not everyone is familiar with your product's terminology. Simple writing costs experts nothing — they skim right past it. Complex writing costs beginners everything.

**Spell out abbreviations.** Write "product requirements document (PRD)" not "PRD". Write "single sign-on (SSO)" not "SSO". The cost to experts is near zero; the benefit to newcomers is high.

**Proactively address potential problems.** If some readers might get stuck at a particular step, address it. A short note like "If you don't see this option, you may need admin permissions" saves those readers from abandoning the doc.

**Prefer plain, specific language over jargon.** "Input" is clearer than "prompt." "The maximum number of words the system can process" is clearer than "context limit." Optimize for the person reading it for the first time.

**Introduce narrow topics with a broad opening.** Before diving into a specific workflow, briefly orient the reader: what is this for, when would they use it, why does it matter? This helps people who are unfamiliar feel secure before entering uncertain territory.

**Prioritize by reader value.** Cover the most common tasks and questions thoroughly. Don't spend equal time on edge cases that affect 1% of readers and core workflows that affect 80%.

---

## Output format guidance

**When writing new documentation:**
- Open with one to three plain sentences that say what the doc covers, who it's for, and what the reader gets. Name the audience here, not in a later paragraph.
- Include a table of contents for docs with 3+ sections
- Use H2 (`##`) for major sections, H3 (`###`) for subsections
- Write section titles as informative sentences (not abstract nouns)
- Keep paragraphs to 3–5 sentences max; shorter for key points
- End with a "Next steps" or "What to do if something goes wrong" section when relevant

**When reviewing existing documentation:**
- Lead with a summary of overall strengths and the 2–3 most impactful things to fix
- Organize feedback by principle category (skimmability, writing quality, density, helpfulness)
- For each issue: quote the problematic text, name the principle it violates, and provide a rewritten version
- Focus on the changes that will have the biggest impact — not every minor issue

---

## Break these rules when you have a good reason

Documentation is an exercise in empathy. Put yourself in the reader's position and do what will help them the most. These principles exist to serve readers, not to be followed mechanically. A longer sentence is fine if it's genuinely clearer. A more technical term is fine if your audience already knows it. Use judgment.
