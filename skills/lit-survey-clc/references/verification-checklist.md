# Verification Checklist

Phase 5 runs these checks after all synthesis is complete. Use a general-purpose agent with Bash, Grep, Glob, Read access.

## Coverage Completeness

Build a topic-by-paper matrix. For each section in the survey plan:
- Count papers assigned to that section via Keywords grep
- Verify Critical topics have >= minimum count from plan
- Verify High topics have >= 80% of target count
- Flag any section with 0 papers as a gap

```bash
# Count papers linked to a hub note
grep -rl '[[Hub-Name]]' Ideas/Research/*.md | wc -l
```

## Vault Link Integrity

Find broken wikilinks in all new and modified notes:
1. Grep for all `[[wikilinks]]` in survey-related notes
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

## Source Quality Distribution

Count the distribution across new survey notes:
```bash
grep -c 'Paper-peer-reviewed' Ideas/Research/*.md  # Should be >= 60%
grep -c 'Paper-not-reviewed' Ideas/Research/*.md    # Should be <= 30%
grep -c 'Misc-source' Ideas/Research/*.md           # Should be <= 10%
```

## Recency Check

For each Critical and High priority topic:
- Grep for papers from the last 2-3 years (check Date Created or year in citation)
- Each topic should have >= 2 recent papers

## Hub Note Completeness

For each hub note (new and updated):
1. Read the note
2. Verify Key Papers section has >= 3 entries
3. Verify Concept Overview (`ad-tldr`) is non-empty
4. Verify at least 1 Mermaid diagram exists
5. Verify Subtopics/Connections sections link to other hubs

## Figure Integrity

Verify all embedded figures exist:
1. Grep for `![[*.png]]` and `![[*.drawio]]` patterns in new notes
2. For each, Glob to verify the image file exists in `Files/Images/`
3. Report missing images

## Mermaid Syntax Validation

For each Mermaid code block in new notes:
1. Extract the block content
2. Check for common syntax errors (unclosed brackets, invalid node names)
3. Flag usage of unsupported diagram types (`quadrantChart`, `xychart`, `timeline`, `mindmap`, `sankey`, `packet`)

## Survey Document Completeness

For the master survey document:
1. Verify all planned sections exist
2. Verify each section has substantive content (not just headers)
3. Verify Mermaid diagrams have valid syntax
4. Verify bibliography wikilinks resolve to existing notes
5. Count total wikilinks to verify cross-referencing density (target: ≥ 2 citations per paragraph)

## Cross-Reference Consistency

- Every paper in the comparison table should have a corresponding literature note
- Every hub note Key Papers entry should have a corresponding literature note
- The survey document should reference all hub notes

## NotebookLM Artifact Completeness (if Phase 4.5 ran)

- Verify all planned notebooks exist: `notebooklm list --json`
- Each topic notebook has: mind map, study guide, briefing doc
- Master notebook has: briefing doc, gap detection response, cross-validation response
- Review gap detection: flag gaps either addressed in survey text or documented as known limitations
- Review cross-validation: contradictions either resolved or logged as open items

## Report Format

The verification agent produces a structured report:

```markdown
# Survey Verification Report

**Survey**: {survey title}
**Date**: {date}
**Total papers**: {N}

## Coverage
- [x] All Critical topics meet minimum count
- [ ] Topic "X" has only {N}/{target} papers (gap)

## Link Integrity
- {N} wikilinks checked, {M} broken
- Broken: [[missing-note-1]], [[missing-note-2]]

## Deduplication
- No duplicates found / {N} duplicates: {list}

## Source Quality
- Peer-reviewed: {N}% (target: ≥ 60%)
- Preprint: {N}% (target: ≤ 30%)
- Other: {N}%

## Recency
- {N}/{M} critical topics have recent papers (last 2-3 years)

## Hub Completeness
- {N}/{M} hub notes meet all requirements

## Figures
- {N}/{M} figure embeds resolve correctly

## Mermaid
- {N} diagrams checked, {M} syntax errors

## Survey Document
- {N}/{M} sections have substantive content
- Cross-reference density: {avg} citations per paragraph

## NotebookLM (if applicable)
- Notebooks: {N}/{expected}
- Artifacts: {N}/{expected}
- Gaps flagged: {list or "none"}
- Contradictions: {list or "none"}

## Overall: PASS / PASS WITH WARNINGS / NEEDS ATTENTION

### Action Items (if any)
1. {issue and recommended fix}
```

## Severity Levels

| Level | Meaning | Action |
|-------|---------|--------|
| Critical | Coverage gap, broken links, missing sections | Must fix before survey is usable |
| Warning | Low citation density, minor Mermaid errors, sub-target tier distribution | Should fix but not blocking |
| Info | Suggestions for improvement, optional enhancements | Nice to have |
