# Synthesis Style Guide

This document defines writing conventions for survey section drafts and the final manuscript.

## Prose Style

- **Objective, third-person**: "This section surveys..." NOT "We review..." or "Our analysis..."
- **No project-specific framing**: Do NOT mention any specific research program, lab, or project. This is a general survey.
- **Formal but readable**: Academic prose accessible to a graduate student in CS/ML
- **Synthesis over summary**: Each paragraph should compare, contrast, or connect multiple papers — do NOT summarize papers one-by-one
- **Specific over vague**: "MAPPO achieves 95% win rate on SMAC 3m" NOT "several methods show promising results"
- **Avoid hedging**: "X outperforms Y" not "X appears to potentially outperform Y in some cases"

## Citation Format

- **Internal format** (`--format internal`): Cite via wikilinks `[[citationKey]]`. Every factual claim must link to a paper.
- **Formal format** (`--format formal`): Cite via `[@citationKey]` (pandoc-compatible). Collect all references in a bibliography section.

## Standard Notation

Use this notation consistently across all sections. When introducing section-specific notation, define it inline and add to a local notation table.

| Symbol | Meaning |
|--------|---------|
| $s \in S$ | State in state space |
| $a \in A_i$ | Action for agent $i$ in its action space |
| $\pi_i : O_i \to \Delta(A_i)$ | Stochastic policy for agent $i$ |
| $V^\pi(s)$ | State value function under joint policy $\pi$ |
| $Q^\pi(s, \mathbf{a})$ | Joint action-value function |
| $r : S \times \mathbf{A} \to \mathbb{R}$ | Shared reward function |
| $\mathcal{N} = \{1, \ldots, N\}$ | Agent set with $N$ agents |
| $\mu \in \Delta(S)$ | Mean-field distribution over states |
| $\gamma \in [0, 1)$ | Discount factor |
| $T : S \times \mathbf{A} \to \Delta(S)$ | Transition function |
| $o_i \in O_i$ | Observation for agent $i$ |
| $\Omega : S \times \mathbf{A} \to \Delta(\mathbf{O})$ | Joint observation function |

## Section Structure

For each survey section:

1. **Section heading**: `## N. Section Title`
2. **Subsection headings**: `### N.M Subsection Title`
3. **Opening paragraph**: 2-3 sentences framing scope and significance
4. **Body**: Synthesize across papers using hub notes as source material
5. **Comparison tables**: At least 1 Markdown table per major section
6. **Mermaid diagrams**: At least 1 per major section where appropriate
7. **Key takeaways**: Use admonitions for important findings
8. **Transitions**: 1-2 sentences connecting to the next section

## Admonition Types (Internal Format Only)

| Type | Use For |
|------|---------|
| `ad-tldr` | Executive summaries, section overviews |
| `ad-note` | Key findings, important observations |
| `ad-tip` | Practical recommendations, decision guides |
| `ad-question` | Open questions, identified gaps |
| `ad-warning` | Limitations, caveats, known issues |

## Mermaid Diagram Rules

**Allowed types**: `graph`, `flowchart`, `sequenceDiagram`, `classDiagram`, `stateDiagram`, `gantt`, `pie`

**FORBIDDEN types** (will NOT render in Obsidian): `quadrantChart`, `xychart`, `timeline`, `mindmap`, `sankey`, `packet`

Use `flowchart TD` for classification trees, `flowchart LR` for process flows, `sequenceDiagram` for protocol interactions.

## Table Formatting

- Use Markdown pipe tables
- Align columns for readability
- Include citation keys as wikilinks in method/paper columns
- Use "N/R" for not reported, "N/A" for not applicable
- Keep tables under ~15 columns for readability

## ACM Computing Surveys Conventions

- Typical section ordering: Introduction, Background, Taxonomy/Classification, Topic Sections, Open Problems, Conclusion
- Include comparison with prior surveys in the Introduction
- PRISMA-style search methodology documentation
- Taxonomy figures as visual aids
- Gap analysis in Open Problems section
