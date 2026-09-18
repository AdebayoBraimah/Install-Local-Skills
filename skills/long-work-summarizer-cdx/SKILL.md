---
name: long-work-summarizer-cdx
description: Study textbooks and research monographs from Zotero or local PDFs, producing rigorous chapter notes, page-level reading evidence, and resumable book synthesis. Use for book study, chapter summaries, monograph reading, and books in explicitly requested Zotero collections.
---

# Long-work study

Read the requested scope completely, then publish verified chapter notes and a book index. Default to all substantive chapters and appendices. Exercise solutions are optional and require a request. EPUB, web ingestion, theses, reports, scheduling, and Zotero writes are outside this skill.

## Setup and scope

Use `scripts/long_work.py` with `/Users/adebayobraimah/anaconda3/bin/python`, or a Python with PyMuPDF and PyYAML. Poppler and Tesseract with English data support extraction and visual checking. If absent, install local Tesseract with `HOMEBREW_NO_AUTO_UPDATE=1 brew install tesseract`; its default package includes English. No cloud OCR.

Read [records](references/records.md) for CLI operations and schemas. Read [reading](references/reading.md) before substantive study. Templates under `assets/` guide note content, without a word limit or mandatory diagrams.

- Resolve a Zotero key, BBT citation key, or PDF with `prepare`. Use `prepare --collection NAME` to inventory an explicit collection, then process its book entries sequentially. Return other item types to the paper workflow. A collection inventory is not reading completion.
- Revisit books in explicitly requested collections even if legacy progress calls them processed. Adopt their existing index paths. Citation-key changes do not rename established files.
- Repeated `prepare` resumes; `status` reports current scope and whole-book coverage. Dry-run preparation reads sources without writing state. An explicit local book ID allows a moved/replaced source to resume its identity.
- Missing or ambiguous attachments block that book until resolved. Continue other independent books, retaining the unresolved selector. Bibliographic unknowns stay unknown.

## Reading loop

1. Map every page, comparing bookmarks, contents, visible chapter headings, and printed labels. Record one-based PDF numbers separately. Confirm chapter boundaries before reading; unknown boundaries block the affected chapter. Use PDF citations when printed numbers remain unknown.
2. Record a mapping, then run `next`, optionally selecting chapter IDs. Read each returned chunk, at most eight pages. Save a `chunk` record immediately with specific section evidence and unresolved passages. Text extraction never establishes reading.
3. Process one chapter worker at a time, supplying prerequisite notes and shared notation. Use a bounded Codex subagent for a chapter when available; run sequentially yourself if delegation is disabled. The parent owns mapping, final synthesis, publication and notifications. Continue through requested scope without asking between chunks or chapters.
4. Visually inspect mathematics, diagrams, and unclear passages. Use `next --ocr` for unusable text, including mixed pages. OCR is cached by source hash, page and settings; it does not verify equations. Retry transient failures at most twice, then retain a blocker.
5. Write a section-aligned chapter explanation with numbered definitions/results, assumptions, proof explanations, algorithms, worked examples, exercise references and figures. Record the verified chapter result and `publish` it. Do not wait until the entire book is finished to preserve completed chapters.
6. Maintain notation, chapter dependencies and cross-chapter links. Record a scope synthesis only when its chapters are verified. Publish and `verify`. A selected scope can be complete while whole-book coverage remains partial. Full book coverage requires all substantive chapters and verified book synthesis.

## Preservation and recovery

Manifests, chunk evidence, results and publication hashes live under `.long-work-summarizer/works/`. Keep them durable. Ignore `cache/`, `renders/`, `locks/`, `drafts/` and `.tmp-*`; conflict proposals and source-history snapshots remain durable.

Publish only through the helper. It uses one writer per book, atomic writes and a write-ahead transaction. Resume reconciles note files before continuing. Keep personal writing outside the marked region; edited generated regions produce saved proposals and a blocked result. Never force-overwrite a conflict. Resolve by comparing the proposal and user edits, retaining both until the user chooses the combined content.

Changed PDF hashes archive prior state and invalidate reading. Remap chapter identities explicitly; retain unmatched old notes as stale. Supply `match_evidence` before reusing an old chapter ID/path. Legacy Extracted/Surveyed labels never prove full reading. Source-Quality measures availability, separately from Reading-Coverage.

Use distinctive chapter filenames, one Zotero-Key on the book index, and Book-ID/Chapter-ID/Parent-Book on chapters. Link only to relevant existing hubs or notes. Count all chapters of a book as one work for collection progress and hub thresholds. Do not run a library-wide linker for each book.

At completion or observed stop, use `alert-me` once. During a parent workflow, return the run result and let the parent send the single notification. Do not commit or push unless the active user request authorizes it.
