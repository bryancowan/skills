# Visualization Formats

## Mermaid Diagrams

Mermaid renders natively in Obsidian — no plugins needed. Use fenced code blocks with `mermaid` language tag.

### Concept Maps (most common)

Show relationships between wiki articles or concepts:

```markdown
` ``mermaid
graph LR
  A[Concept A] --> B[Concept B]
  A --> C[Concept C]
  B --> D[Shared Detail]
  C --> D
  
  style A fill:#4a9eff,color:#fff
  style D fill:#ff6b6b,color:#fff
` ``
```

### Flowcharts

For processes or decision trees:

```markdown
` ``mermaid
flowchart TD
  Start[Input Data] --> Process{Analyze}
  Process -->|Pattern A| ResultA[Outcome A]
  Process -->|Pattern B| ResultB[Outcome B]
  ResultA --> Summary[Combined Results]
  ResultB --> Summary
` ``
```

### Timelines

For chronological data:

```markdown
` ``mermaid
timeline
  title Evolution of Topic
  2020 : Event A : Detail
  2021 : Event B : Detail
  2022 : Event C : Detail
  2023 : Event D : Detail
` ``
```

### Mind Maps

For topic hierarchies:

```markdown
` ``mermaid
mindmap
  root((Main Topic))
    Branch A
      Detail 1
      Detail 2
    Branch B
      Detail 3
    Branch C
` ``
```

### Class Diagrams (for entity relationships)

```markdown
` ``mermaid
classDiagram
  class ConceptA {
    +attribute1
    +attribute2
    +method()
  }
  class ConceptB {
    +attribute3
  }
  ConceptA --> ConceptB : relates to
` ``
```

### Tips for Obsidian Mermaid

- Keep diagrams focused — 5-15 nodes is readable, 30+ becomes noise
- Use `style` to highlight key nodes
- Use descriptive labels, not abbreviations
- Test rendering in Obsidian's preview mode — some advanced mermaid features may not render in all versions
- For complex diagrams, prefer multiple smaller diagrams over one massive one

## Matplotlib Charts

For quantitative data that needs proper charts (bar, line, pie, scatter).

### Usage

Pass JSON to `scripts/generate_chart.py`:

```bash
echo '{"type": "bar", "title": "Results", "labels": ["A","B","C"], "values": [10,20,30]}' | \
  python scripts/generate_chart.py --output "/path/to/chart.png"
```

### Supported Chart Types

**Bar chart:**
```json
{
  "type": "bar",
  "title": "Chart Title",
  "xlabel": "Categories",
  "ylabel": "Values",
  "labels": ["A", "B", "C"],
  "values": [10, 20, 30],
  "colors": ["#4a9eff", "#ff6b6b", "#4ecdc4"]
}
```

**Line chart:**
```json
{
  "type": "line",
  "title": "Trend Over Time",
  "xlabel": "Time",
  "ylabel": "Value",
  "x": [1, 2, 3, 4, 5],
  "series": [
    {"label": "Series A", "values": [10, 15, 13, 17, 20]},
    {"label": "Series B", "values": [5, 8, 12, 15, 18]}
  ]
}
```

**Pie chart:**
```json
{
  "type": "pie",
  "title": "Distribution",
  "labels": ["Part A", "Part B", "Part C"],
  "values": [45, 30, 25]
}
```

**Horizontal bar:**
```json
{
  "type": "barh",
  "title": "Comparison",
  "labels": ["Item 1", "Item 2", "Item 3"],
  "values": [100, 75, 50]
}
```

### Embedding in Obsidian

After generating a chart, embed it in a wiki article:

```markdown
![[chart-name.png]]
```

Or with a specific width:

```markdown
![[chart-name.png|500]]
```

Save charts to the vault's central attachments folder (`00.05 Attachments`) with descriptive names including the wiki topic, e.g., `wiki-llm-training-comparison-chart.png`.
