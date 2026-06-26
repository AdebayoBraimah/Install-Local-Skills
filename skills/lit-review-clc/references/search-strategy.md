# Search Strategy

This document defines how Phase 1 search agents construct and execute queries.

## Search Agent Architecture

4 parallel agents (A, B, C, D), each covering 2-4 topic areas. Assignment based on thematic overlap to minimize redundancy.

Typical clustering pattern:
- **Agent A**: Theory, foundations, mathematical methods
- **Agent B**: Communication, networking, infrastructure
- **Agent C**: Applications, benchmarks, deployment
- **Agent D**: Methods, architectures, algorithms

## Per-Agent Search Protocol

Each agent uses `deep-research-academic` skill capabilities to search:
- Google Scholar
- Semantic Scholar
- arXiv
- IEEE Xplore
- ACM Digital Library

Plus citation graph traversal (forward + backward from seed papers already in vault).

## Output Format (Per Paper)

Each candidate must include:
- Title, authors, year, venue
- DOI or arXiv ID (for deduplication)
- Abstract (or first 2-3 sentences)
- Source tier: peer-reviewed / preprint / workshop / technical report
- Relevance score: 1-5 with brief justification
- BibTeX entry (when available)
- Primary topic area assignment

## Output Persistence

Each agent writes its report to `Ideas/Research/_search-results-{letter}.md`. These are temporary working files consumed by Phase 2. Phase 2 merges, deduplicates, and produces:
- `_search-results-filtered.md` (final candidate list)
- `_import-{collection}.bib` (for Zotero batch import)

## Query Construction Guidelines

For each topic area, generate 3-5 queries:
- Start with the most specific terms, broaden if needed
- Use quoted phrases for multi-word concepts: `"mean-field game"`
- Combine domain terms with method terms: `"conformal prediction" "reinforcement learning"`
- Include venue-specific searches for top conferences when relevant
- Add recency filters where appropriate (last 3-5 years for methods, broader for foundational)

## Seed Paper Strategy

For each agent, provide 2-4 seed papers already in the vault. The agent should:
1. Check the seed papers' reference lists (backward citation)
2. Check who cites the seed papers (forward citation via Semantic Scholar)
3. Use seed paper keywords to refine queries

## Deduplication During Search

Each agent should track DOIs/arXiv IDs within its own output to avoid listing the same paper twice. Cross-agent deduplication happens in Phase 2.
