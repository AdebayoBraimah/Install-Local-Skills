# Literature Survey Plan: {TOPIC}

## Context

**Topic**: {TOPIC}
**Research context**: {CONTEXT}
**Collection name**: `{COLLECTION_NAME}`
**Paper target**: {PAPER_TARGET} total ({EXISTING_COUNT} existing + {NEW_TARGET} new)
**Format**: {FORMAT}

---

## Survey Structure ({SECTION_COUNT} sections)

{SECTIONS}

---

## Existing Vault Coverage

### Existing Literature Notes ({EXISTING_COUNT} papers)

{EXISTING_NOTES_SUMMARY}

### Existing Hub Notes

{EXISTING_HUBS}

---

## Search Runs ({RUN_COUNT} runs, 4 agents per run)

| Run | Topic Focus | Target Papers | Primary Keywords | Secondary Keywords |
|-----|-------------|---------------|------------------|--------------------|
{SEARCH_RUN_TABLE}

### Agent Database Assignments (fixed)

| Agent | Database | Tool |
|-------|----------|------|
| A | Google Scholar | `scholarly` (Python) |
| B | Semantic Scholar | WebFetch API |
| C | arXiv | WebSearch + WebFetch |
| D | IEEE/ACM + DBLP | WebSearch + WebFetch |

---

## Source Tier Targets

| Tier | Description | Target % |
|------|-------------|----------|
| T1 | Top venues | ≥ 60% |
| T2 | Solid venues | 10-15% |
| T3 | Preprints (>50 cites) | 10-15% |
| T4 | Grey literature | ≤ 5% |

---

## Hub Note Plan

### New Hubs to Create

{NEW_HUBS}

### Existing Hubs to Update

{UPDATE_HUBS}

### Hubs to Merge

{MERGE_HUBS}

---

## Synthesis Agent Assignments

| Agent | Sections | Hub Notes to Read | Output File |
|-------|----------|-------------------|-------------|
{SYNTHESIS_AGENT_TABLE}

---

## Checkpoints

| Checkpoint | Phase | Blocking? | User Action |
|---|---|---|---|
| Plan approval | Phase 0 | Yes | Review this plan, approve/modify/reject |
| Zotero import | Phase 1 | Yes | Import `.bib` into Zotero, download PDFs, confirm ready |
| Note spot-check | Phase 2 | No | Review 10-15 notes at convenience |
| Draft review | Phase 4 | No | Review survey draft at convenience |

---

## NotebookLM

**Status**: {NOTEBOOKLM_STATUS}
**Notebooks planned**: {NOTEBOOK_COUNT}

---

## Runtime Estimate

| Phase | Estimated Duration | Notes |
|-------|-------------------|-------|
| Phase 0 (Setup) | ~15 min | Pre-checks + plan generation |
| Phase 1 (Search) | ~{SEARCH_HOURS} hours | {RUN_COUNT} runs × ~20-25 min + triage |
| *User checkpoint* | *variable* | *Zotero import + PDF download* |
| Phase 2 (Summarize) | ~{SUMMARIZE_HOURS} hours | {NEW_TARGET} papers, waves of 5 |
| Phase 3 (Hubs) | ~2-3 hours | Hub writers + comparison table |
| Phase 4 (Synthesis) | ~3-5 hours | Synthesis agents + assembly |
| Phase 4.5 (NotebookLM) | ~2-3 hours | If available |
| Phase 5 (Verify) | ~1-2 hours | Read-only checks |
| **Total** | **~{TOTAL_HOURS} hours** | **1 blocking checkpoint** |

---

**Plan status**: Generated {DATE}. Awaiting user approval.
