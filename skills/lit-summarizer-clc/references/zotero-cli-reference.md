# Zotero CLI Reference

Complete command reference for `~/anaconda3/bin/cli-anything-zotero`.

Global options: `--json` (machine-readable output), `--data-dir PATH` (Zotero data directory), `--version`, `--help`.

---

## Command Overview

| Command | Description | Key Flags |
|---|---|---|
| `search "query"` | Search items by title | `-n/--limit` |
| `items` | List items with filters | `-t/--type`, `-c/--collection`, `-n/--limit`, `--types` |
| `info KEY` | Full metadata for item | (none) |
| `cite KEY` | Get Better BibTeX citation key | (none) |
| `export KEY [KEY...]` | Export to BibTeX/JSON/CSV | `-f/--format`, `-c/--collection`, `-o/--output` |
| `attachments KEY` | List attachments for item | `--open` |
| `notes KEY` | View notes for item | `--raw` |
| `tags` | List tags with usage counts | `-q/--query`, `--min-count` |
| `collections` | List all collections | `--tree`, `--bbt`, `--selected` |
| `fulltext "query"` | Full-text search across indexed PDFs | `-n/--limit`, `--stats` |
| `pdf KEY` | Locate or open PDF for item | `--open`, `--bbt` |
| `stats` | Show database statistics | (none) |
| `create-collection NAME` | Create a new collection | `--parent` |

---

## New Commands (not in CLAUDE.md)

### `fulltext "query"`

Search the full text of indexed PDFs. Multiple words are treated as AND (all must appear). Searches Zotero's word index built from PDF content.

```bash
cli-anything-zotero fulltext "conformal prediction"
cli-anything-zotero fulltext "multi-agent reinforcement" -n 20
cli-anything-zotero fulltext "loss landscape" --stats   # show index statistics
```

Flags:
- `-n/--limit` — max results to return
- `--stats` — show full-text index statistics (total indexed items, word count)

### `pdf KEY`

Locate or open the PDF attachment for an item. Returns the file path directly.

```bash
cli-anything-zotero pdf ABC12345                 # by Zotero key
cli-anything-zotero pdf bao2025escape --bbt      # by BBT citation key (requires Zotero running)
cli-anything-zotero pdf ABC12345 --open          # open in default PDF viewer
```

Flags:
- `--open` — open the PDF in the system viewer
- `--bbt` — treat KEY as a Better BibTeX citation key (requires Zotero running with local API)

### `stats`

Show database statistics (total items, collections, tags, attachment counts).

```bash
cli-anything-zotero stats
```

### `create-collection NAME`

Create a new collection in Zotero (requires Zotero running with local API enabled).

```bash
cli-anything-zotero create-collection "CP-Sequential-Review"
cli-anything-zotero create-collection "Sub-Topic" --parent "Parent-Collection"
```

Flags:
- `--parent TEXT` — create as a child of an existing collection

---

## Enhanced Flags on Existing Commands

### `collections`

```bash
cli-anything-zotero collections                  # flat list (default)
cli-anything-zotero collections --tree           # hierarchical tree view
cli-anything-zotero collections --bbt            # richer data via BBT API
cli-anything-zotero collections --selected       # currently selected collection in Zotero UI
```

### `notes KEY`

```bash
cli-anything-zotero notes ABC12345               # stripped text (default)
cli-anything-zotero notes ABC12345 --raw         # raw HTML output
```

### `tags`

```bash
cli-anything-zotero tags                         # all tags
cli-anything-zotero tags -q "reinforcement"      # filter by name
cli-anything-zotero tags --min-count 5           # only tags used 5+ times
```

### `items`

```bash
cli-anything-zotero items -c "LLM pruning"       # by collection
cli-anything-zotero items -t journalArticle       # by type
cli-anything-zotero items --types                 # list all available item types
```

---

## PDF Path Resolution

### Preferred approach (new)

Use the `pdf` command to get the PDF path directly:

```bash
# By Zotero key:
cli-anything-zotero pdf ABC12345

# By BBT citation key (requires Zotero running):
cli-anything-zotero pdf bao2025escape --bbt
```

### Fallback approach (legacy)

If `pdf` returns no result (e.g., cloud-only storage, missing attachment):

```bash
cli-anything-zotero attachments KEY
# Parse output to find PDF path
```

### Resolution order

1. Try `pdf KEY` (or `pdf KEY --bbt`)
2. If no result, try `attachments KEY` and parse for `.pdf` paths
3. If neither returns a PDF, proceed as `abstract-only`

---

## Common Workflows

### Find a paper and get its citation

```bash
cli-anything-zotero search "conformal prediction" -n 5
cli-anything-zotero cite ABC12345
cli-anything-zotero export ABC12345 -f bibtex
```

### Get full metadata + PDF path for summarization

```bash
cli-anything-zotero info ABC12345 --json
cli-anything-zotero pdf ABC12345
cli-anything-zotero export ABC12345 -f bibtex
```

### Search by content (not just title)

```bash
cli-anything-zotero fulltext "multi-agent communication" -n 10
```

### Export an entire collection

```bash
cli-anything-zotero export -c "MARL" -f bibtex -o marl.bib
cli-anything-zotero items -c "MARL" --json
```
