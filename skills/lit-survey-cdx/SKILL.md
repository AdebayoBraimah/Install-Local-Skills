---
name: lit-survey-cdx
description: |
  Large-scale academic literature survey orchestrator: plan, search, summarize, synthesize, verify.
  Auto-generates a survey plan from a topic, gets user approval, then executes a 6-phase pipeline
  across 100-350+ papers. Composes with lit-summarizer-cdx for batch summarization.
  Codex-adapted variant.
  Use when: user wants to conduct a comprehensive literature survey, says "literature survey",
  "survey the field of", "comprehensive survey on", "large-scale review", or "lit survey".
  Invoke as lit-survey-cdx "topic description" or lit-survey-cdx with no args for interactive setup.
  Optional flags: --papers N-M, --format internal|formal, --collection NAME, --no-notebooklm.
---

# Large-Scale Literature Survey Pipeline

You are an Orchestrator for a plan-then-execute comprehensive literature survey. You generate a scoped survey plan, get user approval, then execute a 6-phase pipeline: Search, Summarize, Hub Notes, Synthesis, NotebookLM Cross-Validation, Verification.

## Codex Execution Rules

- This is the Codex variant of the skill. Prefer local tools, `rg`, structured parsing, and the files in this skill directory.
- Do not use Claude Code commands or Claude-specific `Agent(...)` syntax.
- Spawn Codex subagents by default for search, summarization, hub writing, synthesis, and verification work unless the user explicitly instructs you not to use subagents.
- Use Codex `spawn_agent` with concrete, bounded prompts and disjoint write scopes.
- Never push changes to a remote repository. Local commits are allowed only when the user request or active repository instructions call for them.

## Configuration

| Setting | Value |
|---|---|
| Vault path | `$OBSIDIAN_VAULT` |
| CLI tool | `~/anaconda3/bin/cli-anything-zotero` |
| pdfimages | `/opt/homebrew/bin/pdfimages` |
| magick | `/opt/homebrew/bin/magick` |
| GIMP CLI | `~/anaconda3/bin/cli-anything-gimp` |
| Inkscape CLI | `~/anaconda3/bin/cli-anything-inkscape` |
| Python path | `~/anaconda3/bin/python` |
| NotebookLM CLI | `~/anaconda3/bin/notebooklm` |
| drawio skill | `~/.agents/skills/drawio/` |
| gimp skill | `~/.agents/skills/gimp/SKILL.md` |
| inkscape skill | `~/.agents/skills/inkscape/SKILL.md` |
| Batch summarize skill | `~/.agents/skills/lit-summarizer-cdx/` |
| Progress tracker | `Ideas/Research/_batch-progress.md` |
| Note output dir | `Ideas/Research/` |
| Figure output dir | `Files/Images/` |
| Max parallel agents | 5 |
| ntfy topic | `ab-mac` |

## Argument Parsing

Parse the user's invocation to extract:

- **Topic** (required): Research domain or question. Example: `"Large-scale cooperative multi-agent systems"`
- **Paper count** (optional, default: auto): Target total papers. Parse from `--papers N` or `--papers N-M`. If omitted, auto-estimated as ~20-30 per topic section.
- **Format** (optional, default: `internal`): `internal` (Obsidian living doc with wikilinks, Mermaid, admonitions) or `formal` (publication-ready prose, uses `research-paper-writer` skill in Phase 4).
- **Collection name** (optional): Zotero collection for new papers. If omitted, derive from topic (e.g., `Large-Scale-MAS-Survey`).
- **NotebookLM** (optional, default: on): Pass `--no-notebooklm` to skip Phase 4.5.

If the user provides no arguments, ask interactively:
1. What topic should the survey cover?
2. What is the research context? (infer from vault if not provided)
3. Approximate paper target? (default: auto)

## Resumability

Before starting any phase, check `_batch-progress.md` for the survey's collection name. If prior phases are logged as complete, skip them and resume from the last incomplete step. The plan file (`_lit-survey-plan-{collection}.md`) persists across sessions.

## Skill Embedding for Subagents

Do not assume subagents can dynamically load additional skills. Read these SKILL.md files and embed relevant excerpts in agent dispatch prompts:

| Agent Type | Embedded Skills | Read From |
|---|---|---|
| Search Agents | `deep-research-academic` | `~/.agents/skills/deep-research-academic/SKILL.md` |
| Hub Writer Agents | `academic-researcher` + `mermaid-diagrams` | `~/.agents/skills/academic-researcher/SKILL.md`, `~/.agents/skills/mermaid-diagrams/SKILL.md` |
| Synthesis Agents | `academic-researcher` | `~/.agents/skills/academic-researcher/SKILL.md` |
| Triage, Comparison, Verification | None (use tools directly) | — |

Read only the SKILL.md body (not reference subdirectories) to keep prompt sizes manageable.

---

## Phase 0: Plan Generation

**Goal**: Auto-generate a complete survey plan from the topic, present for user approval.

### Step 0.1: Gather Context (parallel)

Execute these in parallel:
- Use `rg` in `Ideas/Research/` for notes related to the topic (search Keywords, tags, titles)
- Use `rg` for existing hub notes (`ad-tldr` tag or `hub-note` tag) across `Ideas/` and `Ideas/Research/`
- Run `cli-anything-zotero collections` to check for existing related collections
- Run `cli-anything-zotero search "topic keywords"` to estimate existing library coverage
- Run `cli-anything-zotero fulltext "topic keywords"` for content-based coverage
- Read `_batch-progress.md` if it exists to check for prior survey work

### Step 0.2: Auto-Generate Survey Structure

Using the topic, vault context, and ACM Computing Surveys conventions, generate:

| Component | Logic |
|---|---|
| **Survey sections** (8-20) | Decompose topic into Intro, Background/Foundations, Taxonomy, 5-12 topic sections, Open Problems, Conclusion |
| **Search runs** (4-10) | One per topic cluster, grouping related subtopics |
| **Keywords per run** | 4-6 primary + 3-5 secondary, derived from section headings + domain vocabulary |
| **Hub note plan** | Create new hubs for areas with no existing hub; update existing hubs; merge when topics overlap |
| **Synthesis agent splits** | Assign sections to 2-4 agents, balanced by hub count per agent |
| **Paper target** | If not specified: ~20-30 per topic section × section count, minus existing vault coverage |
| **Source tier targets** | T1 (top venues) ≥60%, T2 (solid venues) 10-15%, T3 (preprints >50 cites) 10-15%, T4 (grey lit) ≤5% |

### Step 0.3: Deployment Pre-Checks (parallel)

- Zotero running: `cli-anything-zotero stats` (should return without error)
- CLI tools exist: `which pdfimages magick cli-anything-zotero cli-anything-gimp cli-anything-inkscape`
- `scholarly` functional: `~/anaconda3/bin/python -c "from scholarly import scholarly; print('OK')"`
- `notebooklm` available: `notebooklm list --json 2>&1` — warn but don't fail if unavailable
- Vault path writable: `test -w "{VAULT_PATH}"`
- Git initialized: `git -C "{VAULT_PATH}" status`
- ntfy reachable: `curl -s -o /dev/null -w "%{http_code}" https://ntfy.sh/ab-mac`

### Step 0.4: Write Plan File

Read `templates/plan-template.md` and substitute placeholders. Write to `Ideas/Research/_lit-survey-plan-{collection}.md`.

If Zotero collection does not exist, create it:
```bash
cli-anything-zotero create-collection "{COLLECTION_NAME}"
```

### Step 0.5: Request Approval

Present the plan summary to the user:
- Survey title and section count
- Search run count and keywords per run
- Paper target (new + existing)
- Hub note plan (new/update/merge counts)
- NotebookLM availability status
- Runtime estimate

Send ntfy: `"SURVEY: Plan ready for '{TOPIC}'. {N} sections, {M} search runs, ~{P} papers. Awaiting approval."`

**WAIT for user approval.** User may approve, modify sections/keywords/paper counts, or reject.

---

## Phase 1: Gap-Targeted Search

### Search Runs (sequential, 4 agents parallel per run)

For each search run in the plan (4-10 runs):

1. Read `templates/search-agent-prompt.md` and substitute per-agent placeholders
2. Read `references/search-strategy.md` for inclusion/exclusion criteria
3. Read the `deep-research-academic` SKILL.md and embed in prompt
4. Dispatch up to 4 Codex `spawn_agent` workers by default, one per database. If the user explicitly instructed not to use subagents, execute the 4 search assignments locally or sequentially:

| Agent | Database | Tool |
|---|---|---|
| A | Google Scholar | `scholarly` via `scripts/scholarly_search.py` (Bash) |
| B | Semantic Scholar | API fetch via web fetch, `curl`, or Python HTTP (`api.semanticscholar.org`) |
| C | arXiv | Web search/fetch when available; otherwise arXiv pages/API |
| D | IEEE/ACM + DBLP | Web search/fetch when available; otherwise site queries + DBLP |

Each agent writes to `Ideas/Research/_search-results-survey-{topic_slug}-{agent_id}.md`.

Send ntfy after each run: `"SURVEY: Search run {N}/{TOTAL} ({topic}) complete."`

**Error recovery**: Retry-once per agent. If still failing, log to `_batch-progress.md` and continue.

### Final Run: Snowball Search

The last search run uses `scripts/scholarly_snowball.py` on survey papers found in earlier runs. Agent A runs snowball via `citedby()`; Agents B-D do gap-fill queries on undertarget topics.

### Triage (1 agent, after all runs)

Read `templates/triage-agent-prompt.md` and substitute. Triage Agent:
1. Merges all per-agent search result files (4 agents × N runs)
2. Deduplicates against existing vault notes and `_search-results-filtered.md` (if exists from prior work)
3. Enriches BibTeX via 3-source fallback: `scholarly` → CrossRef API → Semantic Scholar API
4. Applies inclusion/exclusion criteria from `references/search-strategy.md`
5. Outputs: `_search-results-survey-filtered.md` + `_import-survey-extension.bib`

**Git commit**: `ENH: Completed survey search — {N} candidates from {R} runs`

Send ntfy: `"SURVEY: Triage complete. {N} papers selected. BibTeX ready for Zotero import."`

**BLOCKING CHECKPOINT**: User must:
1. Import `_import-survey-extension.bib` into Zotero collection
2. Right-click → Find Available PDF
3. Manually download unavailable PDFs
4. Confirm ready

Verify import: `cli-anything-zotero items -c "{COLLECTION_NAME}"` — check item count and PDF attachment counts.

---

## Phase 2: Batch Summarization

**Delegate to `lit-summarizer-cdx`**.

The orchestrator reads `~/.agents/skills/lit-summarizer-cdx/SKILL.md` and embeds the essential pipeline instructions in prompts instead of assuming subagents can dynamically load additional skills. `lit-summarizer-cdx` handles:
1. **Extractor Agent** (1) — pulls Zotero metadata for the collection, builds paper queue
2. **Summarizer Agents** (5 per wave) — creates structured literature notes with figures, vector cleanup, Mermaid, math, tables
3. **Linker Agent** (1, after all waves) — cross-references, keyword assignment, hub linking

### Post-Phase 2 (orchestrator)

Auto-spot-check: read 3 random new notes, verify required sections exist (summary, figures, Mermaid, math, strengths/limitations). Log results to `_batch-progress.md`.

**Git commit**: `ENH: Completed survey batch summarization — {N} notes created`

Send ntfy: `"SURVEY: Phase 2 complete — {N} notes created. Spot-check at your convenience. Proceeding to Phase 3."`

**Non-blocking**: pipeline continues; user reviews async.

---

## Phase 3: Hub Notes & Comparison Tables

### Step 3.1: Hub Writers (2-4 agents in parallel)

Read `templates/hub-writer-prompt.md` and substitute per-agent. Each agent handles a subset of hubs from the plan:

- **Mode `create`**: New hub notes with ad-tldr, Key Papers, Subtopics, Mermaid flowchart, Connections
- **Mode `update`**: Append new papers to existing hubs, add new subtopics, update Mermaid if needed
- **Mode `merge`**: Combine topics into existing hub, rename file. Orchestrator updates wikilinks vault-wide after.

Completion detection: sentinel comment `<!-- HUB-COMPLETE: {agent-id} -->` at end of last file. Orchestrator checks with `rg`.

After all hub writers complete:
- If any hub was merged/renamed, orchestrator runs vault-wide grep+edit to update `[[OldName]]` → `[[NewName|OldName]]`
- **Git commit**: `ENH: Created/updated survey hub notes`

### Step 3.2: Comparison Table (1 agent)

Read `templates/comparison-table-prompt.md` and substitute. Agent:
- Reads Key Papers sections from ALL hub notes (grep for `hub-note` tag)
- Builds master Markdown comparison table (10+ columns)
- Creates taxonomy `flowchart` (Mermaid) + PRISMA `flowchart` (Mermaid)
- Token budget: ~100K. If >150 rows, split into 2 agents.

**Git commit**: `ENH: Added survey comparison table and taxonomy diagrams`

### Step 3.3: Visual Artifacts (orchestrator)

Create diagrams that require drawio (Mermaid can't render these):
- Coverage heat map → `Files/Images/survey-coverage-heatmap-{collection}.drawio`
- Overlap/Venn diagrams (if applicable) → `Files/Images/`
- Vector figure cleanup or SVG exports → use `~/.agents/skills/inkscape/SKILL.md` and `cli-anything-inkscape`

**Git commit** and ntfy: `"SURVEY: Phase 3 complete — hub notes, comparison table, and diagrams done."`

---

## Phase 4: Synthesis & Manuscript Draft

### Step 4.1: Synthesis Agents (2-4 in parallel)

Read `templates/synthesis-agent-prompt.md` and substitute per-agent. Read `references/synthesis-style.md` for prose conventions and embed in prompt.

Each agent:
- Writes assigned survey sections
- Reads hub notes using selective strategy: ad-tldr + Key Papers + Subtopics only (~3K tokens per hub)
- Token budget: ~150K per agent
- Writes to `Ideas/Research/_survey-sections-{agent_id}.md`

Completion detection: check for all output files with `rg --files` or `find`.

**Git commit**: `ENH: Completed survey section drafts`

### Step 4.2: Assembly (orchestrator)

1. Merge `_survey-sections-*.md` into `Ideas/Research/Survey-{Collection-Name}.md`
2. Write cross-cutting sections: Open Problems (read all hub ad-tldrs for gap analysis), Conclusion
3. Add unified notation table (consolidated from all sections)
4. Add 3-5 representative algorithm pseudocode blocks
5. Remove temp `_survey-sections-*.md` files
6. **Git commit**: `ENH: Assembled survey manuscript draft`

Send ntfy: `"SURVEY: Draft complete. Review at your convenience. Running Phase 4.5 now."`

**Non-blocking**: user reviews async, pipeline continues.

---

## Phase 4.5: NotebookLM Cross-Validation

### Guard

If `--no-notebooklm` flag was passed, skip this phase.

Otherwise, test: `notebooklm list --json 2>&1`. If fails:
- Log: "NotebookLM unavailable, skipping Phase 4.5"
- Send ntfy: `"SURVEY: NotebookLM unavailable — skipping cross-validation. Proceeding to Phase 5."`
- Skip to Phase 5.

### Notebook Creation

Create section-grouped notebooks (≤50 sources each) + 1 Master notebook. Map papers to notebooks via synthesis agent assignments from the plan.

```bash
notebooklm create "Survey-{Collection}-{SectionGroup}"
```

### Source Addition

Add Obsidian literature notes (.md) as text sources (NOT raw PDFs). Let auto-detection handle `.md` → text:

```bash
notebooklm source add "./Ideas/Research/{citationKey}.md" -n {NOTEBOOK_ID} --json
notebooklm source wait {SOURCE_ID}
```

**50-source overflow guard**: If a notebook reaches 45 sources, split into sub-notebooks.

For the Master notebook, add hub notes and the survey manuscript.

### Artifact Generation

Per topic notebook: mind map, study guide, briefing doc.

```bash
notebooklm generate mind-map --wait -n {NOTEBOOK_ID} --json
notebooklm generate report --format study-guide --wait --retry 3 -n {NOTEBOOK_ID}
notebooklm generate report --format briefing-doc --wait --retry 3 -n {NOTEBOOK_ID}
```

For Master notebook:
```bash
notebooklm generate report --format briefing-doc --append "Synthesize across all topics. Identify the 5 most critical open problems." --wait --retry 3 -n {MASTER_ID}
notebooklm ask "What topics or methods are underrepresented? What important papers might be missing?" -n {MASTER_ID}
notebooklm ask "Are there contradictions between papers? Do any claims lack sufficient evidence?" -n {MASTER_ID}
```

### Download Artifacts

```bash
notebooklm download mind-map "./Ideas/Research/_notebooklm-mindmap-{topic}.json" -n {NOTEBOOK_ID}
notebooklm download report "./Ideas/Research/_notebooklm-briefing-{topic}.md" -n {NOTEBOOK_ID}
```

Rate limiting: 10-second delays between `generate` commands.

**Git commit**: `ENH: Added NotebookLM cross-validation artifacts`

Send ntfy: `"SURVEY: Phase 4.5 complete — NotebookLM artifacts generated."`

---

## Phase 5: Verification

Dispatch **1 Verification Agent**. Read `references/verification-checklist.md` and embed in prompt.

The agent runs all quality checks:
- Coverage completeness (topic-by-paper matrix vs. plan sections)
- Wikilink integrity (all `[[links]]` resolve)
- Zotero-Key deduplication
- Source tier distribution (≥60% peer-reviewed)
- Recency (critical topics have papers from last 2-3 years)
- Hub completeness (every planned hub exists with required sections)
- Figure/Mermaid syntax validation
- Cross-reference consistency (hub notes ↔ survey document)
- If Phase 4.5 ran: NotebookLM artifact completeness, gap/contradiction review

Output: `Ideas/Research/_survey-verification-report.md`

**Git commit**: `DOC: Added survey verification report`

Send ntfy: `"SURVEY COMPLETE: Verification {PASS/FAIL}. Report at _survey-verification-report.md"`

---

## Cross-Cutting Concerns

### Concurrency
- Max **5 concurrent agents** at any time
- Search runs: sequential (1 at a time), 4 agents per run
- Summarizer waves: 5 per wave (via lit-summarizer-cdx)
- Hub writers: 2-4 parallel
- Synthesis agents: 2-4 parallel
- All other agents: 1 at a time

### Git Discipline
Git commits as phase boundaries: each phase commits before the next begins. This prevents inter-phase file conflicts and provides rollback points.

### Notifications
Send ntfy at `https://ntfy.sh/ab-mac` at every milestone:
```bash
curl -d "SURVEY: {message}" https://ntfy.sh/ab-mac
```

### Error Recovery
- **Retry-once** per agent for transient failures
- **Log-and-continue** for persistent failures: log to `_batch-progress.md`, continue with remaining agents
- **Scholarly rate limiting**: scripts enforce delays; proxy support available if blocked

### Phase Execution Order (strict)

```
Phase 0 — Plan Generation → user approval
Phase 1 — Search (sequential runs) → triage → git commit → BLOCKING: Zotero import
Phase 2 — Summarize (via lit-summarizer-cdx) → git commit → non-blocking spot-check
Phase 3 — Hub Notes → Comparison Table → Visual Artifacts → git commit
Phase 4 — Synthesis → Assembly → git commit → non-blocking review
Phase 4.5 — NotebookLM (if available) → git commit
Phase 5 — Verification → git commit → SURVEY COMPLETE
```
