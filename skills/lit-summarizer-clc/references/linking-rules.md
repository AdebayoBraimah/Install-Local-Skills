# Linking and Hub Creation Rules

## Hub Note Creation

### Criteria

- **Threshold**: 3+ papers sharing a concept with NO existing hub note
- **Concept must be substantive** -- not a generic term like "deep learning" unless no hub exists
- **Check existing hubs first**: Grep for `ad-tldr` in `Ideas/` and `Ideas/Research/`

### Hub Note Location

- Match existing hub patterns: `Ideas/{ConceptName}.md` for broad concepts, `Ideas/Research/{ConceptName}.md` for research-specific topics
- Use hyphenated names: `Multi-Agent-Communication`, `Loss-Landscapes`, `Active-Learning`

### Hub Note Structure

```yaml
---
Title: "[[{ConceptName}]]"
Medium:
  - Atomic idea
Category:
  - Discovery
  - Method
tags:
  - hub-note
Keywords: {wikilinks to parent concepts}
Date Created: "{dateCreated}"
Time Created: "{timeCreated}"
---
```

Sections (in order):
1. **Date Modified** dataview inline
2. **Concept Overview** (`ad-tldr` admonition, 2-4 sentences)
3. **Key Papers** -- grouped by sub-theme, each as `- [[citationKey]] -- one-line description (venue year)`
4. **Subtopics** -- wikilinks to related hub/concept notes
5. **Thoughts & Ideas** (with `ad-note` admonition)
6. **Notes**
7. **References**
8. **Checklist** (with `ad-note` follow-up admonition)

## Cross-Reference Rules

### Format

```markdown
### Related Papers

- [[citationKey]] -- one-line description of relationship
```

### Inclusion Criteria (any of these)

- Shares 2+ Keywords with the note
- Uses similar methodology or extends the work
- Builds on / critiques / is cited by the paper
- Uses the same dataset or benchmark
- Same research group or lineage (e.g., CommNet -> TarMAC -> T2MAC)

### Exclusions

- Do NOT add self-references
- Do NOT duplicate entries already present
- Do NOT add more than 5 related papers per note (keep focused)
- Skip notes that already have a populated Related Papers section

### Strength Priority

When selecting which papers to link, prioritize:
1. Direct predecessors/successors (strongest)
2. Same-cluster papers sharing methods
3. Cross-cluster papers sharing themes
4. Survey papers providing taxonomic context

## Keyword Assignment

### Format

```yaml
Keywords:
  - "[[ConceptName]]"
  - "[[ConceptName|Abbreviation]]"
```

### Rules

- Use wikilinks to existing hub notes where possible
- If no hub exists, use a descriptive name that could become a hub
- Maximum ~8 Keywords per note
- Prefer established abbreviations: `[[Large-Language-Model|LLM]]`, `[[Markov-Decision-Process|MDP]]`

## Semantic Clustering Algorithm (for Linker agents)

1. Extract Keywords + Take Home Message from each batch note via Grep (NOT full Read)
2. Build keyword co-occurrence: which papers share which keywords
3. Identify clusters of 3+ papers sharing keywords with no existing hub
4. Cross-check Take Home Messages for thematic similarity beyond keyword overlap
5. Create hubs for new clusters
6. Add cross-references for strongest connections within and across clusters
