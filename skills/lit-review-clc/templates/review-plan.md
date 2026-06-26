# Literature Review Plan: {REVIEW_TITLE}

## Context

{RESEARCH_CONTEXT}

## Constraints

- **Format**: {FORMAT} (internal research doc / formal publication)
- **Paper count target**: {PAPER_COUNT_MIN}-{PAPER_COUNT_MAX} new papers
- **Date range**: {DATE_RANGE} (e.g., 2018-present + foundational pre-2018)
- **Zotero collection**: `{COLLECTION_NAME}`
- **Notifications**: ntfy at every milestone and checkpoint

---

## Topic Areas

| # | Topic | Priority | In Vault | New Target | Week |
|---|-------|----------|----------|------------|------|
{TOPIC_TABLE}

**Totals**: ~{EXISTING_COUNT} existing, ~{NEW_TARGET} new

## Inclusion / Exclusion Criteria

### Include
{INCLUSION_CRITERIA}

### Exclude
{EXCLUSION_CRITERIA}

## Source Quality Targets

- **Tier 1** (>=60%): Peer-reviewed journals + top conferences
- **Tier 2** (<=30%): Recent preprints (<18 months)
- **Tier 3** (<=10%): Workshop papers, technical reports

---

## Search Agent Assignments

### Agent A -- {AGENT_A_LABEL}
**Topics**: {AGENT_A_TOPICS}

Search queries:
{AGENT_A_QUERIES}

Seed papers: {AGENT_A_SEEDS}

### Agent B -- {AGENT_B_LABEL}
**Topics**: {AGENT_B_TOPICS}

Search queries:
{AGENT_B_QUERIES}

Seed papers: {AGENT_B_SEEDS}

### Agent C -- {AGENT_C_LABEL}
**Topics**: {AGENT_C_TOPICS}

Search queries:
{AGENT_C_QUERIES}

Seed papers: {AGENT_C_SEEDS}

### Agent D -- {AGENT_D_LABEL}
**Topics**: {AGENT_D_TOPICS}

Search queries:
{AGENT_D_QUERIES}

Seed papers: {AGENT_D_SEEDS}

---

## Hub Note Plan

### New Hub Notes to Create

| Hub Note | Core Content | Creation Order |
|----------|-------------|----------------|
{NEW_HUBS_TABLE}

### Existing Hub Notes to Update

| Hub | Updates |
|-----|---------|
{UPDATE_HUBS_TABLE}

---

## Synthesis Plan

Master review document: `Ideas/Research/Literature-Review-{TOPIC_SLUG}.md`

### Sections

{SECTION_OUTLINE}

### Diagrams

| Section | Diagram Type | Content |
|---------|-------------|---------|
{DIAGRAMS_TABLE}

---

## Timeline

```
{TIMELINE}
```

## Checkpoints

| # | After Phase | User Action | Blocks? |
|---|-------------|-------------|---------|
| 1 | Phase 1 (Search) | Review candidate list, add/remove papers | YES |
| 2 | Phase 2 (Triage) | Approve final list, import to Zotero | YES |
| 3 | Phase 4 (Synthesis) | Review hub notes and review document | YES |
| 4 | Phase 5 (Verify) | Final sign-off | YES |

---

## Critical Files

| File | Role |
|------|------|
| `Ideas/Research/_lit-review-plan-{COLLECTION_SLUG}.md` | This plan |
| `Ideas/Research/_batch-progress.md` | Progress tracker |
| `Ideas/Research/_search-results-{A,B,C,D}.md` | Search agent outputs (temporary) |
| `Ideas/Research/_search-results-filtered.md` | Merged/filtered candidate list |
| `_import-{COLLECTION_SLUG}.bib` | BibTeX for Zotero import |
| `Ideas/Research/Literature-Review-{TOPIC_SLUG}.md` | Master review document |
| `contributing.md` | Commit conventions |
