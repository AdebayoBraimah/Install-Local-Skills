# Synthesis Patterns

This document defines how Phase 4 creates hub notes and the master review document.

## Hub Note Structure

Hub notes use `template-concept-hub-1.md` or match existing hub patterns in the vault:

```markdown
---
Title: "[[Concept-Name]]"
Medium:
  - Atomic idea
Category:
  - Discovery
tags:
  - relevant-tag
  - hub-note
Keywords:
  - "[[Related-Concept]]"
Date Created: "{date}"
Time Created: "{time}"
---

# Concept Name

```ad-tldr
title: Concept Overview
collapse: open

2-4 sentence overview of the concept and its significance.
```

## Key Papers

- [[citationKey1]] -- one-line description
- [[citationKey2]] -- one-line description

## Subtopics

- [[Related-Hub-1]] -- relationship description
- [[Related-Hub-2]] -- relationship description

## Connections

Cross-domain links to other concept hubs.

## Diagrams

(Mermaid code blocks for concept landscape)
```

## Hub Note Creation Rules

- Create a new hub when 3+ papers share a concept with no existing hub
- Create sub-topic hubs FIRST, master hub LAST (it links to sub-hubs)
- Every hub must have: Concept Overview, Key Papers (3+), at least 1 Mermaid diagram
- Use `hub-note` tag in frontmatter for discoverability

## Master Review Document Structure

The review document is a synthesis narrative, NOT a collection of summaries. Typical sections:

1. **Introduction & Motivation**: Research context, guiding questions, scope
2. **Background & Mathematical Foundations**: Key formalisms, theorems, notation
3. **Methods Taxonomy**: Classification tree with comparison tables and Mermaid flowchart
4. **[Domain-Specific Sections]**: 2-4 sections based on topic areas (e.g., Communication, Scalability, Applications)
5. **Benchmarks & Infrastructure**: Evaluation landscape, tools, frameworks
6. **Open Problems & Experimental Directions**: Prioritized research directions, hypotheses to test
7. **Bibliography**: Organized by topic with wikilinks to literature notes

## Required Diagrams in Review Document

| Section | Diagram Type | Content |
|---|---|---|
| Methods Taxonomy | Flowchart | Full methods classification tree |
| Domain section(s) | Flowchart or Sequence | Architecture or process specific to domain |
| Scalability/Comparison | Graph or Table | Method comparison across dimensions |
| Open Problems | Mindmap | Research directions organized by theme |

All diagrams use Mermaid syntax (renders natively in Obsidian).

## Writing Style

- **Internal research doc** (default): Actionable insights, experiment-guiding analysis, not publication-polish. First person acceptable. Wikilinks throughout.
- **Formal** (if requested): IEEE/ACM formatting via `research-paper-writer` skill. Third person, formal citations.

## Cross-Referencing Protocol

After hub notes and review doc are created:
1. Each new literature note gets a Related Papers section with links to 3-5 related vault papers
2. Each hub note references all papers in its cluster
3. The review document wikilinks to both hub notes and individual papers
4. Existing hub notes are updated with new paper references (additive only)

## Skill Embedding for Phase 4 Agents

Phase 4 agents need these skills embedded in their dispatch prompts:
- `academic-researcher` -- scholarly structure and content
- `mermaid-diagrams` -- diagram syntax and best practices

Read SKILL.md content from `~/.agents/skills/` and embed the essential instructions in the agent prompt. Do not assume subagents can dynamically load additional skills.
