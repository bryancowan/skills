# Compilation Workflow

Step-by-step details for the wiki compilation pipeline.

## Phase 1: Source Analysis

For each file in `context/`:

1. Read the full content
2. Extract structured data:
   - **Title**: The main topic or headline
   - **Key claims**: Factual statements, findings, or arguments
   - **Entities**: People, organizations, technologies, concepts mentioned
   - **Data points**: Numbers, statistics, dates, measurements
   - **Relationships**: How entities/concepts relate to each other
   - **Source quality**: Is this a primary source, opinion piece, tutorial, research paper?

Create a mental model of how all sources connect before writing any articles.

## Phase 2: Topic Clustering

Group extracted concepts into article topics:

1. Identify **themes** that span multiple sources — these become articles
2. Avoid 1:1 mapping of source → article. A good wiki article synthesizes across sources.
3. Aim for natural clusters:
   - **Concept articles**: Explain a single idea in depth (e.g., "Attention Mechanism")
   - **Comparison articles**: Compare related approaches (e.g., "RAG vs Fine-tuning")
   - **Overview articles**: Survey a broad area (e.g., "LLM Training Approaches")
   - **Timeline articles**: Track evolution (e.g., "History of Transformer Models")

4. Target 5-15 articles per wiki. Fewer than 5 suggests the sources are too narrow; more than 15 suggests the scope is too broad (split into multiple wiki compilations).

## Phase 3: Article Generation

For each article topic:

1. Write the **Summary** first — 2-3 sentences that stand alone
2. Write **Details** organized by subheadings, not by source. Synthesize information from multiple sources into coherent narrative.
3. Use Obsidian callouts for standout findings:
   - `> [!info]` for key facts
   - `> [!tip]` for practical advice
   - `> [!warning]` for caveats or limitations
   - `> [!quote]` for notable quotes from sources
4. Add **Sources** section with wikilinks to raw files and a note about what each source contributed
5. Add **Related** section with wikilinks to other wiki articles

Cross-reference rules:
- If article A mentions a concept that article B covers in depth, link to B
- If two articles share a source, they likely should cross-reference each other
- The concept map in `_index.md` should match these cross-references

## Phase 4: Index Generation

After all articles are written:

1. Create `_index.md` with:
   - Article listing table (name + one-line summary)
   - Mermaid concept map showing article relationships
   - Source count and compilation date
   - Compilation log for tracking changes over time

2. Verify completeness:
   - Every raw source is cited by at least one article
   - Every article is listed in `_index.md`
   - Every cross-reference in articles matches a link in the concept map

## Phase 5: Visualization

After articles and index exist:

1. Generate a **concept map** (mermaid graph in `_index.md`) — always do this
2. For articles with quantitative data, generate **charts**:
   - Bar/column: comparisons between items
   - Line: trends over time
   - Pie: proportional breakdowns
   - Use `scripts/generate_chart.py` for matplotlib output
3. For articles describing processes, generate **flowcharts** (mermaid in the article itself)

## Incremental Compilation

When new sources are added to an existing wiki:

1. Ingest new sources into `context/`, update `_manifest.md`
2. Re-analyze: which existing articles need updates? What new articles are needed?
3. Update existing articles with new information (add to Details, add new Sources entries)
4. Create new articles for new concepts
5. Update `_index.md`: table, concept map, compilation log
6. Run a health check to catch any broken links or inconsistencies
