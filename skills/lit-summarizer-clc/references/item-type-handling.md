# Item Type Handling Rules

## Decision Table

| itemType | Action | Medium Value | Source-Quality | Notes |
|---|---|---|---|---|
| `journalArticle` | Full note | `Paper-peer-reviewed` | `pdf-full` | Standard processing |
| `conferencePaper` | Full note | `Paper-peer-reviewed` | `pdf-full` | Standard processing |
| `preprint` | Full note | `Paper-not-reviewed` | `pdf-full` | Same detail level as peer-reviewed |
| `bookSection` | Full note if academic | `Paper-peer-reviewed` | `pdf-full` | Summarize key concepts |
| `book` | Concept extraction | `Misc-source` | `pdf-full` | Full study guide: TOC, definitions, theorems, algorithms (see Book Processing below) |
| `webpage` | Skip | -- | -- | Log as `skipped` in progress tracker |
| `computerProgram` | Skip | -- | -- | Log as `skipped` in progress tracker |
| `dataset` | Metadata-only stub | `Misc-source` | `metadata-only` | Frontmatter + description |
| `report` | Full note | `Paper-not-reviewed` | `pdf-full` | Technical reports get full treatment |
| `thesis` | Full note | `Paper-not-reviewed` | `pdf-full` | Full treatment |

## No-PDF Handling

| Condition | Source-Quality | Action |
|---|---|---|
| Has PDF | `pdf-full` | Full note with figures |
| No PDF, has abstract | `abstract-only` | Note from abstract: frontmatter, citation, take-home, brief summary. No figures, no structured details. |
| No PDF, no abstract | `metadata-only` | Minimal stub: frontmatter + citation + empty sections |

## Book Processing (Concept Extraction)

Textbooks and research monographs receive a **concept extraction** note — a comprehensive study guide that captures the book's key intellectual content. This is a multi-pass process requiring selective reading across the full book.

### Reading Strategy

Books are too long for a single read. Use this phased approach:

1. **Pass 1 — Structure** (TOC + preface): Read the table of contents, preface, and introduction to understand scope, audience, and organization. Build the Chapter Map.
2. **Pass 2 — Definitions & Theorems**: Scan each chapter for boxed definitions, theorems, lemmas, propositions, corollaries, and formal problem statements. Extract these verbatim with LaTeX formatting.
3. **Pass 3 — Algorithms**: Identify all pseudocode blocks, algorithmic procedures, and named methods. Extract with step-by-step descriptions.
4. **Pass 4 — Key Figures**: Extract the most informative diagrams (architecture overviews, taxonomy trees, comparison tables, conceptual illustrations). Prioritize figures referenced across multiple chapters.

For very large books (500+ pages), focus passes 2-4 on the chapters most relevant to the user's research (check the book's Zotero collection and tags for context).

### Book Note Template

```markdown
---
Title: "[[{citationKey}]]"
Medium:
  - Misc-source
Category:
  - Must-Read
  - Literature
tags: {derived from Zotero tags + "textbook"}
Keywords: {wikilinks to relevant hubs}
Zotero-Key: "{zoteroKey}"
Source-Quality: "pdf-full"
Date Created: "{dateCreated}"
Time Created: "{timeCreated}"
---
**Date Modified**: `$= dv.current().file.mtime`

## Citation

\`\`\`bibtex
{bibtex}
\`\`\`

---

## Information

**Paper link**: {url or doi}

\`\`\`ad-abstract
title: Take Home Message
collapse: open

{3-5 sentences: what the book covers, target audience, why it matters, key distinguishing perspective}
\`\`\`

### Chapter Map

| Ch | Title | Topics | Key Concepts | Status |
|---|---|---|---|---|
| 1 | {title} | {topics} | {concepts} | Extracted |
| ... | ... | ... | ... | ... |

### Definitions

\`\`\`ad-note
title: Definition {N}: {Name}
collapse: closed

{Verbatim or near-verbatim definition in LaTeX.}
Source: Chapter {X}, p. {Y}
\`\`\`

{Repeat for each definition. Group by chapter.}

### Theorems & Propositions

\`\`\`ad-tip
title: Theorem {N}: {Name}
collapse: closed

**Statement**: {Formal statement in LaTeX}

**Intuition**: {1-2 sentence plain-language interpretation}

**Key assumptions**: {List assumptions}

Source: Chapter {X}, p. {Y}
\`\`\`

{Repeat for each theorem, lemma, proposition, corollary.}

### Algorithms

\`\`\`ad-note
title: Algorithm {N}: {Name}
collapse: closed

**Input**: {inputs}
**Output**: {outputs}

{Pseudocode or step-by-step description}

**Complexity**: {time/space if stated}

Source: Chapter {X}, p. {Y}
\`\`\`

{Repeat for each algorithm.}

### Key Figures

{Extracted figures with chapter references:}
![[{citationKey}-fig-N.png]]
*Figure from Ch. {X}: {Description}.*

### Cross-Chapter Connections

{How concepts build on each other across chapters. Mermaid dependency diagram:}
\`\`\`mermaid
flowchart TD
  Ch1[Ch 1: Foundations] --> Ch3[Ch 3: Core Method]
  Ch2[Ch 2: Background] --> Ch3
  Ch3 --> Ch6[Ch 6: Extensions]
  Ch3 --> Ch7[Ch 7: Applications]
\`\`\`

### Summary

{500-word overview of the entire book: scope, structure, main contributions, how it fits in the literature}

### Other Notes

### Related Papers
```

### Orchestrator Handling for Books

Because concept extraction is expensive (many Read calls across the full PDF), the Orchestrator should:
- Dispatch book Summarizers **one at a time** (not in parallel waves)
- Give the agent a higher page budget (allow reading 50-100 pages across multiple calls)
- Set `mode="auto"` to allow all necessary tool calls

## Metadata-Only Stub Template

```markdown
---
Title: "[[{citationKey}]]"
Medium:
  - Misc-source
Category:
  - Discovery
tags: {derived from Zotero tags}
Keywords: {wikilinks to relevant hubs}
Zotero-Key: "{zoteroKey}"
Source-Quality: "metadata-only"
Date Created: "{dateCreated}"
Time Created: "{timeCreated}"
---
**Date Modified**: `$= dv.current().file.mtime`

## Citation

\`\`\`bibtex
{bibtex}
\`\`\`

---

## Information

**Paper link**: {url or doi}

\`\`\`ad-abstract
title: Take Home Message
collapse: open

{1-2 sentence description from title/tags/abstract if available}
\`\`\`

### Summary

### Related Papers
```
