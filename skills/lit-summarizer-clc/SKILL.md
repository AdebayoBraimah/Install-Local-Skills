---
name: lit-summarizer-clc
description: |
  Batch-summarize Zotero papers into structured Obsidian literature notes with BibTeX citations,
  mathematical expressions, extracted figures, Mermaid/Excalidraw/Drawio diagrams, GIMP-enhanced
  figures, and concept hub notes. Use when: user wants to summarize Zotero collections, batch
  process papers, create literature notes from Zotero, summarize a paper, or says "summarize
  collection", "process papers", "batch literature review", "lit summarize", "summarize paper",
  or "lit-summarizer-clc". Invoke as /lit-summarizer-clc [collection-name] or /lit-summarizer-clc all.
disable-model-invocation: true
---

# Literature Summarization Pipeline

You are an Orchestrator. You coordinate a multi-agent pipeline that processes Zotero collections into structured Obsidian literature notes.

## Configuration

| Setting | Value |
|---|---|
| Vault path | `$OBSIDIAN_VAULT` |
| CLI tool | `~/anaconda3/bin/cli-anything-zotero` |
| pdfimages | `/opt/homebrew/bin/pdfimages` |
| magick | `/opt/homebrew/bin/magick` |
| GIMP CLI | `~/anaconda3/bin/cli-anything-gimp` |
| drawio skill | `~/.agents/skills/drawio/` |
| Progress tracker | `Ideas/Research/_batch-progress.md` |
| Note output dir | `Ideas/Research/` |
| Figure output dir | `Files/Images/` |
| Max parallel agents | 5 |

## Argument Parsing

Parse the user's request to determine scope:
- **Specific collection** (e.g., `/lit-summarizer-clc LLM pruning`): process only that collection
- **Multiple collections** (comma-separated): process each in order
- **`all`** or no argument: process all unprocessed collections from the progress tracker

## Initialization (Run Once at Start)

### 1. Gather Dynamic Context

Execute these in parallel:
- **Collection list**: Run `cli-anything-zotero collections` to get all collections with item counts
- **Progress state**: Read `Ideas/Research/_batch-progress.md` to get already-processed Zotero keys from the Item Log table
- **Existing notes**: Glob `Ideas/Research/*.md` to get all existing note filenames
- **Existing hub notes**: Grep for `ad-tldr` across `Ideas/` and `Ideas/Research/` to build the hub list

### 2. Read Skill Files for Embedding

Subagents CANNOT invoke skills. Read these files and store their content for embedding in dispatch prompts:

| Skill | File Path | Used By |
|---|---|---|
| academic-researcher | `~/.claude/skills/academic-researcher/SKILL.md` | Summarizer |
| research-engineer | `~/.claude/skills/research-engineer/SKILL.md` | Summarizer |
| mermaid-diagrams | `~/.claude/skills/mermaid-diagrams/SKILL.md` | Summarizer |
| excalidraw | `~/.claude/skills/excalidraw/SKILL.md` | Summarizer |
| drawio | `~/.agents/skills/drawio/SKILL.md` | Summarizer |
| gimp | `~/.claude/skills/gimp/SKILL.md` | Summarizer |
| deep-research-academic | `~/.claude/skills/deep-research-academic/SKILL.md` | Linker |
| deep-research | `~/.claude/skills/deep-research/SKILL.md` | Linker |

Read only the SKILL.md body (not reference subdirectories) to keep prompt sizes manageable.

### 3. Read Template Files

Read these skill template files for dispatch prompt construction:
- `templates/extractor-prompt.md`
- `templates/summarizer-prompt.md`
- `templates/linker-prompt.md`
- `references/note-template.md`
- `references/figure-extraction.md`
- `references/item-type-handling.md`
- `references/linking-rules.md`
- `references/zotero-cli-reference.md`
- `references/diagram-tools.md`

These paths are relative to this skill's directory (`~/.claude/skills/lit-summarizer-clc/`).

## Batch Loop (Per Collection)

For each collection to process, execute this cycle:

### Step 1: Extract Metadata

Read `templates/extractor-prompt.md` and substitute:
- `{COLLECTION_NAME}` -> collection name
- `{PROCESSED_KEYS_JSON}` -> JSON array of all Zotero keys from _batch-progress.md Item Log
- `{VAULT_PATH}` -> vault path from config
- `{CLI_PATH}` -> CLI tool path from config
- `{ITEM_TYPE_RULES}` -> content of `references/item-type-handling.md`

Dispatch: `Agent(subagent_type="general-purpose", name="extractor-{collection}", prompt=<substituted template>)`

Parse the returned JSON manifest. Filter to `isDuplicate: false` items.

### Step 2: Dispatch Summarizers (Parallel, Waves of 5)

For each non-duplicate item with a processable type (per item-type-handling rules):

Read `templates/summarizer-prompt.md` and substitute all `{PLACEHOLDER}` tokens with paper metadata from the manifest. Also substitute:
- `{FIGURE_EXTRACTION_INSTRUCTIONS}` -> content of `references/figure-extraction.md`
- `{EXISTING_HUB_NOTES}` -> the hub list gathered at init
- `{MEDIUM_VALUE}` -> derived from itemType per note-template.md rules
- `{SOURCE_QUALITY}` -> `pdf-full`, `abstract-only`, or `metadata-only` based on PDF/abstract availability
- `{DATE_CREATED}` / `{TIME_CREATED}` -> current date/time in vault format
- `{CLI_PATH}` -> CLI tool path

For the first 2 Summarizers per session, also append the embedded skill content:
```
## Embedded Skill Instructions
### Academic Researcher
{content of academic-researcher SKILL.md}
### Research Engineer
{content of research-engineer SKILL.md}
### Mermaid Diagrams
{content of mermaid-diagrams SKILL.md}
### Drawio (for publication-quality diagrams)
{content of drawio SKILL.md — condensed: Create Flow + academic-paper route only}
### GIMP (for figure post-processing)
{content of gimp SKILL.md — Academic Figure Post-Processing section only}
### Diagram Tool Selection
{content of references/diagram-tools.md}
```

After the first few agents demonstrate the note style, subsequent Summarizers can omit the full skill embeddings to save tokens — the template instructions alone are sufficient.

Dispatch in parallel waves of 5: `Agent(subagent_type="general-purpose", name="summarizer-{citationKey}", mode="auto", prompt=...)`

Wait for each wave to complete before dispatching the next.

For items that are books, webpages, computerPrograms, or datasets: create metadata-only stubs directly (no agent needed) following the stub template in `references/item-type-handling.md`.

### Step 3: Dispatch Linker

After ALL Summarizer waves complete:

Read `templates/linker-prompt.md` and substitute:
- `{BATCH_NOTE_PATHS}` -> newline list of note paths created in this batch
- `{EXISTING_HUB_NOTES}` -> current hub list (may have grown from this batch)
- `{HUB_TEMPLATE}` -> the concept hub structure from `references/linking-rules.md`
- `{VAULT_PATH}` -> vault path
- `{LINKING_RULES}` -> content of `references/linking-rules.md`

Dispatch: `Agent(subagent_type="general-purpose", name="linker-{collection}", mode="auto", prompt=<substituted template>)`

### Step 4: Update Progress Tracker

Edit `Ideas/Research/_batch-progress.md`:
- Update the Collection Status table row (increment Summarized count, set Pending to 0)
- Append rows to the Item Log table for all items processed in this batch

### Step 5: Git Commit

```bash
cd "{VAULT_PATH}"
git add Ideas/Research/*.md "Ideas/Research/Conformal-Prediciton/"*.md Ideas/*.md "Files/Images/"*.png
git commit -m "ENH: Summarized {collection} collection ({N} papers) with cross-refs"
```

Follow `contributing.md`: `ENH:` prefix, past-tense, 8-12 words, NO `Co-Authored-By`.

### Step 6: Auto-Advance

Immediately proceed to the next collection. No pause between batches.

## After All Collections

### Final Linker Pass

Run a Linker agent across the ENTIRE library for cross-collection concept connections. To avoid context limits:
- Grep frontmatter Keywords + Take Home Message (not full content)
- Process in sub-batches of ~50 notes
- Focus on cross-collection connections missed by per-batch linking

### Final Commit

```bash
git commit -m "ENH: Completed final cross-library concept linking pass"
```

### Notification

Send completion notification via ntfy:
```bash
bash ~/.claude/skills/ntfy-notify/scripts/ntfy_send.sh \
  --topic ab-mac \
  --title "Literature Summarization Complete" \
  --priority 4 \
  --tags "white_check_mark,books" \
  "Pipeline finished: {total_papers} papers, {total_hubs} hubs, {abstract_only_count} abstract-only."
```

## Error Handling

- **Summarizer failure**: Log status as `error` in _batch-progress.md. Continue with remaining papers.
- **Extractor failure**: Report error, skip collection, continue to next.
- **Git conflict**: Stage and commit quickly to minimize Google Drive sync conflicts.
- **Session interruption**: On resume, _batch-progress.md Item Log provides dedup state. Re-invoking the skill picks up where it left off.

## Commit Convention

All commits follow `contributing.md`:
- Format: `PREFIX: Short past-tense description` (8-12 words max)
- Capitalize first letter after colon
- Use `ENH:` for new notes, `MNT:` for tracker updates
- **Do NOT append `Co-Authored-By: Claude`**

## Collection Processing Order

When processing `all`, follow this priority:
1. **Small** (1-6 items): quick wins, validate pipeline
2. **Medium** (7-20 items): standard batches
3. **Large** (20+ items): sub-batched in waves of 5
4. **Remaining**: any partially-completed or newly-added collections
