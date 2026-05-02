---
name: good-documentation
description: Use this skill when writing or reviewing any documentation — user guides, READMEs, tutorials, workflow docs, onboarding materials, release notes, or any content explaining how something works to stakeholders. Trigger on phrases like "write docs for", "document this", "help me write a guide", "write a README", "review my docs", "improve this documentation", "write a tutorial", "create onboarding material", "help me explain this feature", "draft a user guide", or "write instructions for". Use it even when the user doesn't say "documentation" explicitly — if they're asking you to explain a product, feature, or workflow in written form for an audience, this skill applies. Applies proven principles to produce clear, skimmable content that works for both technical and non-technical readers.
---

# Good Documentation Skill

Documentation puts useful information inside other people's heads. This skill helps write and review documentation that actually works — for user guides, READMEs, workflow docs, and tutorials aimed at mixed technical and non-technical audiences.

## Two modes

**Write mode**: When the user asks you to write documentation, apply all the principles below as you draft. Don't wait to be reminded — structure, tone, and skimmability should be built in from the start.

**Review mode**: When the user asks you to review or improve existing documentation, go through each principle category and give specific, actionable feedback. Quote the problem text, name the principle it violates, and suggest a concrete fix. Don't give generic praise — be specific about what's working and what isn't.

---

## Principles

### Make docs easy to skim

Most readers don't read top to bottom. They scan to find the part that solves their problem. Make that search fast.

**Write section titles as informative sentences, not abstract nouns.** A title like "Results" forces readers to hop into the body to learn what the results are. A title like "Smart Filters reduce dashboard setup time by 60%" gives the answer immediately. The extra words are worth it.

**Include a table of contents** for anything longer than a few sections. A TOC helps readers navigate and also signals at a glance whether the doc is relevant to them.

**Keep paragraphs short.** If you have an essential point, put it in its own one-sentence paragraph so it can't be buried. Long paragraphs hide information.

**Put the topic word at the start of topic sentences.** Readers skim disproportionately at the first word or two. "Smart Filters speed up dashboard setup" is easier to skim than "Dashboard setup can be sped up with Smart Filters."

**Put the most important information first.** Don't build up to a conclusion — state it, then explain it. Don't introduce your procedure before your results.

**Use bullets and tables.** Lists are faster to scan than prose. When you have three or more parallel items, reach for a list.

**Bold important text.** Highlight key terms, warnings, or actions so readers who are scanning don't miss them.

---

### Write well

Badly written text is taxing to read. Minimize the tax.

**Keep sentences simple.** When a sentence gets long, split it into two. Cut adverbs. Cut filler phrases ("it's important to note that", "in order to"). Use imperative mood for instructions ("Click Save" not "You will need to click Save").

**Write sentences that parse unambiguously.** If a reader might misread the subject or verb for even a moment, rewrite. "Write section titles as sentences" is clearer than "Title sections with sentences" even though it's longer.

**Avoid left-branching sentences.** Don't make readers hold a list in memory before knowing what the list is for. Instead of "You need a name, email, and role to invite a user," write "To invite a user, you need a name, email, and role."

**Replace demonstrative pronouns with the actual noun.** "This makes the process faster" is ambiguous. "Caching makes the process faster" is clear. When in doubt, cut the pronoun entirely.

**Be consistent.** Inconsistency distracts readers from the content. If you title one section "How to add a user", don't title the next "User deletion". Pick a pattern and stick to it across all headings, terms, and formatting.

**Don't presume the reader's state of mind.** Avoid "Now you probably want to know how to..." or "Next, you'll need to...". These can feel patronizing. Write "To configure X, ..." instead.

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
- Start with a brief intro that explains what the doc covers and who it's for
- Include a table of contents for docs with 3+ sections
- Use H2 (`##`) for major sections, H3 (`###`) for subsections
- Write section titles as informative sentences (not abstract nouns)
- Keep paragraphs to 3–5 sentences max; shorter for key points
- End with a "Next steps" or "What to do if something goes wrong" section when relevant

**When reviewing existing documentation:**
- Lead with a summary of overall strengths and the 2–3 most impactful things to fix
- Organize feedback by principle category (skimmability, writing quality, helpfulness)
- For each issue: quote the problematic text, name the principle it violates, and provide a rewritten version
- Focus on the changes that will have the biggest impact — not every minor issue

---

## Break these rules when you have a good reason

Documentation is an exercise in empathy. Put yourself in the reader's position and do what will help them the most. These principles exist to serve readers, not to be followed mechanically. A longer sentence is fine if it's genuinely clearer. A more technical term is fine if your audience already knows it. Use judgment.
