# Literature Note Template Specification

## Frontmatter

```yaml
---
Title: "[[{citationKey}]]"
Medium:
  - {medium}                    # Paper-peer-reviewed | Paper-not-reviewed
Category:
  - Literature-Review
  - {additional}                # Discovery | Must-Read | Method | Literature
tags: {list from Zotero tags + manual additions}
Keywords:
  - "[[HubNote1]]"
  - "[[HubNote2|Abbreviation]]"
Zotero-Key: "{zoteroKey}"
Source-Quality: "{sourceQuality}"  # pdf-full | abstract-only | metadata-only
Date Created: "{dateCreated}"     # ddd-MM-DD-YYYY format
Time Created: "{timeCreated}"     # hh:mm:ss a format
---
```

## Body Structure

```markdown
**Date Modified**: `$= dv.current().file.mtime`

## Citation

\`\`\`bibtex
{exported bibtex from cli-anything-zotero}
\`\`\`

---

## Information

**Paper link**: {DOI URL or paper URL}

\`\`\`ad-abstract
title: Take Home Message
collapse: open

{2-4 sentences: core contribution, key finding, practical impact}
\`\`\`

### Summary

{500 words MAX prose. Cover: problem/motivation, methodology, key results, significance.
This is the only section that counts toward the word limit.}

### Structured Details

#### Mathematical Expressions

{Key formulas in LaTeX: $inline$ and $$display$$}
{EVERY formula must have a variable reference table immediately below:}

| Variable | Description | Common Value(s) | Low Extreme | High Extreme |
|---|---|---|---|---|
| $\alpha$ | Learning rate | 1e-3 to 3e-4 | Slow convergence | May diverge |

#### Datasets

{Benchmarks and datasets used, with sizes and characteristics}

#### Simulations / Experimental Setup

{Environment details, hardware, hyperparameters}

#### Training Paradigm(s)

{How models were trained/fine-tuned}

#### Models / Policies

{What models/algorithms were evaluated}

#### Significance

{Why this work matters to the field}

#### Novelty

{What is new compared to prior work}

#### Contributions

{Numbered list of main contributions}

#### Key Tables

{Recreate main results/ablation/hyperparameter tables as Obsidian markdown.
Bold the best result per column/row. Preserve original table numbering.
Only include: main results, ablations, hyperparameter configs.
Skip: related work matrices, notation glossaries.}

### Strengths & Limitations

{Bullet points for each. Can use ad-tip/ad-warning admonitions.}

### Figures & Process Maps

{Embed extracted figures:}
![[{citationKey}-fig-N.png]]
*Figure N: Description of figure content.*

{At least 1 Mermaid diagram per note when applicable:}
\`\`\`mermaid
flowchart TD
  A[Step 1] --> B[Step 2]
  B --> C[Step 3]
\`\`\`

### Other Notes

{Additional observations, connections to other work, open questions}

### Related Papers

{Left empty -- Linker agent fills this}
```

## Structured Details: What Counts Toward 500-Word Limit

| Section | Counts? |
|---|---|
| Summary prose | YES |
| Mathematical expressions | No |
| Variable reference tables | No |
| Datasets, Simulations, Training, Models, Significance, Novelty, Contributions | No |
| Key Tables | No |
| Figures and captions | No |
| Mermaid diagrams | No |
| Strengths & Limitations | No |

## Medium Derivation

| Zotero itemType | Medium |
|---|---|
| journalArticle, conferencePaper, bookSection | Paper-peer-reviewed |
| preprint, report, thesis | Paper-not-reviewed |
| book, dataset, webpage, computerProgram | Misc-source |
