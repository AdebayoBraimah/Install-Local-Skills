# Verification Checklist

Phase 5 runs these checks after all synthesis is complete. Use a general-purpose agent with Bash, Grep, Glob, Read access.

## Coverage Completeness

Build a topic-by-paper matrix. For each topic area in the plan:
- Count papers assigned to that topic via Keywords grep
- Verify Critical topics have >= minimum count from plan
- Verify High topics have >= 80% of target count
- Flag any topic with 0 papers as a gap

```bash
# Example: count papers with a specific keyword
grep -rl '[[Topic-Hub]]' Ideas/Research/*.md | wc -l
```

## Vault Link Integrity

Find broken wikilinks:
1. Grep for all `[[wikilinks]]` in new notes
2. For each unique target, Glob to verify the file exists
3. Report broken links (target file does not exist)

```bash
# Extract wikilinks from a file
grep -oE '\[\[[^\]]+\]\]' Ideas/Research/note.md
```

## Deduplication Check

Verify no duplicate notes exist (same paper, different filenames):
1. Grep for all `Zotero-Key:` values in `Ideas/Research/`
2. Check for duplicates (same key in multiple files)
3. Check for duplicate titles in frontmatter

## Mathematical Accuracy

Spot-check 3-5 key theorems or equations from the review:
1. Select papers with the most mathematical content
2. Read the note's mathematical expressions
3. Open the PDF via `cli-anything-zotero attachments KEY`
4. Compare key equations against the original

## Source Quality Distribution

Count the distribution across new notes:
```bash
grep -c 'Paper-peer-reviewed' Ideas/Research/*.md  # Should be >= 60%
grep -c 'Paper-not-reviewed' Ideas/Research/*.md    # Should be <= 30%
grep -c 'Misc-source' Ideas/Research/*.md           # Should be <= 10%
```

## Recency Check

For each Critical and High priority topic:
- Grep for papers from the last 2 years (check Date Created or year in citation)
- Each topic should have >= 2 recent papers

## Hub Note Completeness

For each hub note (new and updated):
1. Read the note
2. Verify Key Papers section has >= 3 entries
3. Verify Concept Overview (ad-tldr) is non-empty
4. Verify at least 1 Mermaid diagram exists
5. Verify Subtopics/Connections sections link to other hubs

## Figure Integrity

Verify all embedded figures exist:
1. Grep for `![[*.png]]` patterns in new notes
2. For each, Glob to verify the image file exists in `Files/Images/`
3. Report missing images

## Mermaid Syntax Validation

For each Mermaid code block in new notes:
1. Extract the block content
2. Check for common syntax errors (unclosed brackets, invalid node names, unsupported diagram types)
3. Flag `quadrantChart` usage (not supported in Obsidian -- use `graph` alternatives)

## Review Document Completeness

For the master review document:
1. Verify all planned sections exist
2. Verify each section has substantive content (not just headers)
3. Verify Mermaid diagrams render (check syntax)
4. Verify bibliography wikilinks resolve to existing notes
5. Count total wikilinks to verify cross-referencing density

## Report Format

The verification agent returns a structured report:

```markdown
## Verification Report

### Coverage
- [x] All Critical topics meet minimum count
- [ ] Topic "X" has only 2/5 target papers (gap)

### Link Integrity
- {N} wikilinks checked, {M} broken
- Broken: [[missing-note-1]], [[missing-note-2]]

### Deduplication
- No duplicates found / {N} duplicates found

### Source Quality
- Peer-reviewed: {N}% (target: >= 60%)
- Preprint: {N}% (target: <= 30%)
- Other: {N}%

### Figures
- {N}/{M} figure embeds resolve correctly

### Overall: PASS / PASS WITH WARNINGS / NEEDS ATTENTION
```
