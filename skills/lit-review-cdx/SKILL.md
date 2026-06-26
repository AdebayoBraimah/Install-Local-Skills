---
name: lit-review-cdx
description: |
  Scoped academic literature review pipeline: search, triage, summarize, synthesize, verify.
  Generates a review plan for user approval, then executes it autonomously. Codex-adapted variant.
  Use when: user wants to conduct a literature review on a topic, says "literature review",
  "review the literature on", "survey papers about", "lit review on", or "research review".
  Invoke as lit-review-cdx "topic description" or lit-review-cdx with no args for interactive setup.
---

# Scoped Literature Review Pipeline

You are an Orchestrator for a plan-then-execute literature review. You generate a scoped review plan, get user approval, then execute a 5-phase pipeline: Search, Triage, Summarize, Synthesize, Verify.

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
| Progress tracker | `Ideas/Research/_batch-progress.md` |
| Note output dir | `Ideas/Research/` |
| Figure output dir | `Files/Images/` |
| Max parallel agents | 5 |
| GIMP CLI | `~/anaconda3/bin/cli-anything-gimp` |
| Inkscape CLI | `~/anaconda3/bin/cli-anything-inkscape` |
| drawio skill | `~/.agents/skills/drawio/` |
| gimp skill | `~/.agents/skills/gimp/SKILL.md` |
| inkscape skill | `~/.agents/skills/inkscape/SKILL.md` |
| Batch summarize skill | `~/.agents/skills/lit-summarizer-cdx/` |
| ntfy topic | `ab-mac` |

## Argument Parsing

Parse the user's invocation to extract:

- **Topic**: The research topic or question (required). Example: `"Conformal prediction for sequential decision-making"`
- **Context** (optional): How the review supports the user's research. If omitted, infer from vault contents and user memory.
- **Paper count** (optional, default: 40-60): Target number of new papers. Parse from `--papers N` or `--papers N-M`.
- **Collection name** (optional): Zotero collection name for import. If omitted, derive from topic (e.g., `CP-Sequential-Review`).
- **Format** (optional, default: `internal`): `internal` for research doc, `formal` for publication-ready (uses `research-paper-writer` skill in Phase 4).

If the user provides no arguments or an incomplete topic, ask them for:
1. What topic should the review cover?
2. What research does this support? (context)
3. How many papers? (default: 40-60)

## Phase 0: Plan Generation

Generate a review plan for user approval. This plan is the single most important output of the skill — it scopes the entire review.

### Step 0.1: Gather Vault Context

Execute in parallel:
- **Existing notes**: Use `rg` in `Ideas/Research/` for notes related to the topic (search Keywords, tags, titles)
- **Existing hubs**: Use `rg` for `hub-note` tags across `Ideas/` and `Ideas/Research/`
- **Zotero collections**: Run `cli-anything-zotero collections` to check for existing related collections
- **Zotero search**: Run `cli-anything-zotero search "topic keywords"` to estimate how many papers already exist in the library
- **Full-text check**: Run `cli-anything-zotero fulltext "topic keywords"` to find papers already in the library matching by content (not just title)

### Step 0.2: Identify Topic Areas

Based on the topic, context, and vault gaps, decompose into 6-12 topic areas with:
- **Name**: Short label (e.g., "Mean-Field MARL")
- **Priority**: Critical / High / Medium
- **In vault**: Estimated count of existing papers
- **New target**: Number of new papers to find
- **Search queries**: 3-5 queries per topic for Phase 1

Assign topics to **4 search agent clusters** (A, B, C, D) based on thematic overlap to minimize redundancy.

### Step 0.3: Identify Hub Notes

Plan which concept hub notes to:
- **Create**: New hub notes for topic areas with 3+ expected papers and no existing hub
- **Update**: Existing hub notes that should incorporate new papers

### Step 0.4: Write the Plan

Write the plan to `Ideas/Research/_lit-review-plan-{collection}.md` using the structure in `templates/review-plan.md`. The plan must include:

1. **Context**: What the review supports, research questions
2. **Scope**: Paper count target, inclusion/exclusion criteria, date range
3. **Topic table**: All topic areas with priority, counts, search queries
4. **Search agent assignments**: 4 agents (A-D) with topic clusters and queries
5. **Hub note plan**: Which hubs to create/update
6. **Synthesis plan**: Master review document sections
7. **Timeline estimate**: Days per phase
8. **Checkpoint protocol**: Which phases pause for user input

### Step 0.5: Request Approval

Present the plan to the user with a summary:
- Total topic areas and their priorities
- Target paper count
- Zotero collection name
- Estimated timeline
- Number of user checkpoints

Send ntfy notification: `"Lit review plan ready for {topic}. {N} topic areas, {M} target papers. Awaiting approval."`

**WAIT for user approval before proceeding.** The user may:
- Approve as-is
- Modify topic areas, priorities, or paper counts
- Add seed papers or force-include/exclude specific works
- Change the scope or collection name

Update the plan file with any changes.

---

## Phase 1: Systematic Search

Dispatch 4 parallel search agents using `deep-research-academic` skill. Each agent searches Google Scholar, Semantic Scholar, arXiv, IEEE Xplore, and ACM DL.

### Search Agent Dispatch

Read `templates/search-agent-prompt.md` and substitute:
- `{AGENT_LETTER}` -> A, B, C, or D
- `{TOPIC_CLUSTERS}` -> topic areas assigned to this agent (from plan)
- `{SEARCH_QUERIES}` -> queries for each topic (from plan)
- `{SEED_PAPERS}` -> existing vault papers related to this agent's topics
- `{EXCLUSION_CRITERIA}` -> from plan
- `{INCLUSION_CRITERIA}` -> from plan
- `{OUTPUT_PATH}` -> `Ideas/Research/_search-results-{AGENT_LETTER}.md`

Execution: dispatch up to 4 Codex `spawn_agent` workers by default, one per search assignment, with the substituted template and embedded `deep-research-academic` guidance. If the user explicitly instructed not to use subagents, run the four search assignments locally or sequentially.

### After All Search Agents Complete

Send ntfy: `"Search complete: {N} candidates found across 4 agents. Ready for triage."`

**CHECKPOINT 1**: User reviews search results. They can:
- Force-include or force-exclude papers
- Add papers from personal knowledge
- Redirect queries for underrepresented topics

---

## Phase 2: Filter & Triage

### Step 2.1: Merge & Deduplicate

Combine all 4 search result files. Deduplicate by DOI/title (fuzzy match). Each paper assigned to primary topic.

### Step 2.2: Check Against Vault

For each candidate:
- `cli-anything-zotero search "title"` to check if already in Zotero
- Use `rg` in `Ideas/Research/` for matching titles or citation keys

Mark existing papers as "existing -- skip" or "existing -- update".

### Step 2.3: Apply Inclusion/Exclusion Criteria

From the plan. Default inclusion criteria:
- Published within date range (from plan, typically 2018-present + foundational pre-2018)
- Algorithmic contribution, applied system, or comprehensive survey
- Relevant to at least one topic area

Default exclusion criteria:
- Already in vault (unless marked for update)
- Single-agent only (unless directly informing multi-agent extension)
- Non-English
- Retracted or superseded

### Step 2.4: Generate BibTeX for Zotero Import

Concatenate all accepted papers' BibTeX entries into `_import-{collection}.bib`. Write to vault root.

### Step 2.5: Source Quality Tiers

Tag each paper:
- **Tier 1** (target >=60%): Peer-reviewed journals + top conferences
- **Tier 2** (target <=30%): Recent preprints (<18 months)
- **Tier 3** (target <=10%): Workshop papers, technical reports

Send ntfy: `"Triage complete: {N} papers selected. BibTeX file ready for Zotero import."`

**CHECKPOINT 2**: User approves final paper list and imports to Zotero:
1. Connect to VPN (if needed for paywalled PDFs)
2. Create Zotero collection: `cli-anything-zotero create-collection "{COLLECTION_NAME}"`
3. File -> Import -> select `.bib` file
4. Right-click imported items -> Find Available PDF
5. Wait for PDF downloads -> confirm

**WAIT for user confirmation** that Zotero import is complete.

Verify import: `cli-anything-zotero items -c '{COLLECTION_NAME}'` and check PDF attachment counts.

---

## Phase 3: Summarize

Delegate to the existing `lit-summarizer-cdx` pipeline. Embed the required workflow instructions in prompts instead of assuming subagents can dynamically load additional skills:

### Step 3.1: Read Skill Infrastructure

Read these files from `~/.agents/skills/lit-summarizer-cdx/`:
- `templates/extractor-prompt.md`
- `templates/summarizer-prompt.md`
- `templates/linker-prompt.md`
- `references/note-template.md`
- `references/figure-extraction.md`
- `references/item-type-handling.md`
- `references/linking-rules.md`

Also read skill files for embedding:
- `~/.agents/skills/academic-researcher/SKILL.md`
- `~/.agents/skills/research-engineer/SKILL.md`
- `~/.agents/skills/mermaid-diagrams/SKILL.md`
- `~/.agents/skills/excalidraw/SKILL.md`
- `~/.agents/skills/drawio/SKILL.md`
- `~/.agents/skills/inkscape/SKILL.md`
- `~/.agents/skills/gimp/SKILL.md`

### Step 3.2: Run the Batch Loop

For the review collection, execute the `lit-summarizer-cdx` cycle:

1. **Extract**: Dispatch Extractor agent for the collection
2. **Summarize**: Dispatch Summarizers in waves of 5 (parallel). Each Summarizer processes one paper end-to-end following the full extraction spec in `references/extraction-spec.md`:
   - Read PDF (chunked strategy: 1-20 full, 20-50 multi-call, 50+ selective)
   - Write structured note: 500-word summary + structured detail blocks
   - Extract figures (pdfimages raster + magick vision/crop + Inkscape vector fallback)
   - Create process maps (Mermaid flowcharts, Excalidraw, Drawio, or Inkscape diagrams)
   - Render math ($/$$ MathJax) with variable reference tables
   - Recreate key tables (main results, ablations, hyperparams)
   - Assign Keywords as wikilinks to existing hub notes
3. **Link**: Dispatch Linker agent for semantic clustering and cross-references
4. **Checkpoint**: Update `_batch-progress.md`, git commit

Send ntfy after each wave: `"Summarized {N}/{Total} papers. Wave {W} complete."`

After all summarization complete:
Send ntfy: `"All {N} literature notes created. Starting synthesis."`

---

## Phase 4: Synthesize

Create hub notes and a master review document. Read `references/synthesis-patterns.md` for hub note and review document structure.

### Step 4.1: Create Hub Notes

For each planned hub note (from Phase 0 plan):

Dispatch a Codex `spawn_agent` by default, unless the user explicitly instructed not to use subagents. Include embedded `academic-researcher` and `mermaid-diagrams` skill content:

```
Codex worker prompt:
"
  Create a concept hub note at Ideas/Research/{ConceptName}.md.
  
  ## Hub Template
  {template-concept-hub-1.md content}
  
  ## Papers in This Cluster
  {list of note paths with Keywords and Take Home Messages}
  
  ## Instructions
  1. Write Concept Overview (ad-tldr): 2-4 sentences
  2. Populate Key Papers section with wikilinks and one-line descriptions
  3. Add Subtopics section linking to related hubs
  4. Create at least 1 Mermaid diagram for the concept landscape
  5. Add Connections section linking to related existing hubs
  
  {embedded academic-researcher SKILL.md}
  {embedded mermaid-diagrams SKILL.md}
"
```

Create sub-topic hubs FIRST, then the master hub LAST (it links to all sub-hubs).

### Step 4.2: Update Existing Hub Notes

For each existing hub identified in the plan, dispatch an agent to add new paper references and update sections.

### Step 4.3: Write Master Review Document

Dispatch a synthesis agent to create `Ideas/Research/Literature-Review-{Topic}.md`:

Read `templates/synthesis-agent-prompt.md` and substitute:
- `{REVIEW_TITLE}` -> from plan
- `{RESEARCH_CONTEXT}` -> from plan
- `{TOPIC_AREAS}` -> topic table from plan
- `{HUB_NOTES}` -> list of all hub notes (new + existing)
- `{ALL_NOTE_PATHS}` -> paths of all literature notes in the review
- `{SECTION_OUTLINE}` -> from plan's synthesis plan

The review document follows the structure from the plan (typically 10-12 sections). It must include:
- Executive summary (ad-tldr)
- Background & mathematical foundations
- Methods taxonomy with comparison tables
- Mermaid diagrams: taxonomy tree, communication spectrum, scale regime matrix, open problems mindmap
- Scalability analysis by regime
- Benchmark landscape
- Open problems & experimental directions
- Bibliography organized by topic with wikilinks

Send ntfy: `"Master review document drafted: Literature-Review-{Topic}.md"`

**CHECKPOINT 3**: User reviews synthesis document and hub notes:
- Are insights actionable for their research?
- Any topics missing or mischaracterized?
- Do open problems align with research direction?

### Step 4.4: Git Commit

```bash
git add Ideas/Research/*.md Ideas/*.md Files/Images/*.png
git commit -m "ENH: Created hub notes and synthesis document for {Topic} review"
```

---

## Phase 5: Verification

Dispatch a verification agent with shell and file-read access.

Read `references/verification-checklist.md` for the full checklist. Key checks:

| Check | Method |
|---|---|
| Coverage completeness | Topic-by-paper matrix -- every Critical/High topic meets minimum count |
| Vault link integrity | Search for `[[wikilinks]]` with `rg`, verify targets exist with `rg --files` or `find` |
| Deduplication | Search for duplicate Zotero-Keys in frontmatter with `rg` |
| Mathematical accuracy | Spot-check 3-5 key theorems against PDFs |
| Source quality distribution | Count peer-reviewed vs preprint vs misc |
| Recency | Every Critical/High topic has >=2 papers from last 2 years |
| Hub note completeness | Each hub has Key Papers, Subtopics, Connections populated |
| Figure integrity | All `![[*.png]]` embeds resolve to existing files |
| Mermaid rendering | Validate Mermaid syntax in all new notes |

### Final Commit

```bash
git commit -m "ENH: Completed {Topic} literature review (figures, hub updates, verification)"
```

### Final Notification

Send ntfy:
```bash
bash ~/.agents/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "Literature Review Complete" \
  --priority 4 \
  --tags "white_check_mark,books" \
  "Review finished: {N} new notes, {H} hub notes, 1 synthesis doc. Topic: {Topic}"
```

**CHECKPOINT 4**: User final sign-off.

---

## Notification Summary

| When | Message | Blocks? |
|---|---|---|
| Plan ready (Phase 0) | "Plan ready for {topic}. {N} topics, {M} papers." | **YES** |
| Search complete (Phase 1) | "Search complete: {N} candidates. Ready for triage." | **YES** |
| Triage complete (Phase 2) | "Triage complete: {N} selected. BibTeX ready." | **YES** |
| Each summarization wave | "Summarized {N}/{Total}. Wave {W} complete." | No |
| Summarization complete | "All {N} notes created. Starting synthesis." | No |
| Synthesis complete (Phase 4) | "Review document drafted." | **YES** |
| Verification complete (Phase 5) | "Review complete: {N} notes, {H} hubs." | End |

## Error Handling

- If a search agent fails: retry once, then log the gap and continue with other agents
- If a Summarizer fails on a paper: log as `error` in `_batch-progress.md`, continue with remaining papers
- If Zotero import has missing PDFs: process as `abstract-only`, flag for later upgrade
- If any phase stalls: send ntfy `"PAUSED: {reason}. Awaiting input."` and wait

## Resumption

If the pipeline is interrupted:
1. Read `_batch-progress.md` to determine what was completed
2. Read `_lit-review-plan-{collection}.md` to restore the plan
3. Resume from the last incomplete phase
4. Do NOT re-process papers already marked as `summarized` in the tracker
