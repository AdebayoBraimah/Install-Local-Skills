# Search Strategy

This document defines how search agents construct and execute queries, and the criteria for paper selection.

## Source Tier Definitions

| Tier | Description | Vault Label | Target % |
|------|-------------|-------------|----------|
| T1 | Top venues (NeurIPS, ICML, ICLR, AAAI, AAMAS, JMLR, IEEE TPAMI, ACM CSUR, IJCAI, CoRL, RSS) | `Paper-peer-reviewed` | ≥ 60% |
| T2 | Solid venues (IEEE Trans., MDPI, workshops, 2nd-tier conferences, domain-specific journals) | `Paper-peer-reviewed` | 10-15% |
| T3 | Preprints with significant citations (arXiv, >50 cites or from recognized research groups) | `Paper-not-reviewed` | 10-15% |
| T4 | Grey literature (agency reports, tech reports, blog posts, documentation) | `Misc-source` | ≤ 5% |

All T3/T4 sources must be explicitly labeled in comparison tables and text.

## Inclusion Criteria

- Published within relevant date range (typically 10-20 years; foundational through current)
- Addresses the survey's topic domain (2+ agents for MAS surveys)
- Focuses on learning-based methods, formally grounded approaches, OR provides foundational theory/infrastructure
- Available in English
- Peer-reviewed OR preprint with >50 citations OR from recognized research group (DeepMind, OpenAI, FAIR, AFRL, etc.)

## Exclusion Criteria

- Off-topic: does not address the survey domain
- Purely orthogonal domains with no cooperative/collaborative element
- Incremental improvements without novel insight for survey scope
- Non-English publications
- Duplicate content: same work published as preprint then conference — keep venue version
- Retracted or superseded

## Prioritization Order

1. Peer-reviewed papers at top venues (T1)
2. Peer-reviewed at solid venues (T2)
3. Recent preprints with significant impact (>50 cites or from known groups) (T3)
4. Grey literature — explicitly labeled (T4)

## Search Agent Architecture

4 parallel agents (A, B, C, D), each assigned a database:

| Agent | Database | Tool | Notes |
|-------|----------|------|-------|
| A | Google Scholar | `scholarly` Python library (via Bash) | Structured metadata + citation counts. Cap ~20-30 queries per run. 5-10s delays. |
| B | Semantic Scholar | API fetch via web fetch, `curl`, or Python HTTP (`api.semanticscholar.org`) | Free API, no auth. Returns DOI, abstract, citation count, venue. |
| C | arXiv | Web search/fetch when available, otherwise arXiv pages/API via `curl` or Python HTTP | Preprints and recent work. |
| D | IEEE/ACM + DBLP | Web search/fetch when available, otherwise site queries and DBLP via `curl` or Python HTTP | Peer-reviewed venues. |

## Query Construction Guidelines

For each topic area, generate 4-6 primary + 3-5 secondary queries:
- Start with the most specific terms, broaden if needed
- Use quoted phrases for multi-word concepts: `"mean-field game"`
- Combine domain terms with method terms: `"conformal prediction" "reinforcement learning"`
- Include venue-specific searches for top conferences when relevant
- Add recency filters where appropriate (last 3-5 years for methods, broader for foundational)

## Scholarly Usage Guide

### Rate Limiting
Google Scholar blocks aggressive automated access. Mitigations:
- Insert 5-10 second delays between `scholarly` queries
- Use `scholarly`'s proxy support if needed: `from scholarly import ProxyGenerator; pg = ProxyGenerator(); pg.FreeProxies(); scholarly.use_proxy(pg)`
- Limit queries to ~20-30 per search run
- `citedby()` is the most rate-limited function — use sparingly, only for high-value seed papers

### Python Path
All scripts must use: `~/anaconda3/bin/python`

## BibTeX Enrichment (Triage Agent)

For each candidate paper, the Triage Agent enriches metadata via a 3-source fallback chain:

1. **scholarly** (primary): `scholarly.search_pubs("{title}")` → `scholarly.fill(pub)` → extract title, authors, year, venue, abstract, citation count
2. **CrossRef** (fallback for DOI): fetch `https://api.crossref.org/works/{doi}` with web fetch if available, otherwise `curl` or Python HTTP, for authoritative venue/volume/pages
3. **Semantic Scholar** (fallback for abstract/citations): fetch `https://api.semanticscholar.org/graph/v1/paper/search?query={title}` with web fetch if available, otherwise `curl` or Python HTTP, for abstract, DOI, citation count

Ensure each BibTeX entry has: author, title, year, venue/journal, DOI (if available), citation count.

## Deduplication

### Within search agents
Each agent tracks DOIs/arXiv IDs within its own output to avoid listing the same paper twice.

### Triage cross-agent dedup
- Title + author fuzzy match (80% similarity threshold)
- DOI exact match
- arXiv ID exact match
- Check against existing vault: `cli-anything-zotero search "{title}"` and `rg` in `Ideas/Research/` for matching citation keys

## Output Format (Per Paper)

Each candidate must include:
- Title, authors, year, venue
- DOI or arXiv ID (for deduplication)
- Abstract (or first 2-3 sentences)
- Source tier: `peer-reviewed` / `preprint` / `workshop` / `technical-report`
- Relevance score: 1-5 with brief justification
- BibTeX entry (when available)
- Primary topic area assignment

## Output Persistence

Each agent writes to `Ideas/Research/_search-results-survey-{topic_slug}-{agent_id}.md`. These are temporary working files consumed by the Triage Agent, which merges and produces:
- `_search-results-survey-filtered.md` (final candidate list)
- `_import-survey-extension.bib` (for Zotero batch import)
