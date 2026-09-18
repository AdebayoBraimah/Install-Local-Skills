# Reading and verification

Start from the source, not a legacy summary. Inspect contents and visible boundary pages; bookmarks and embedded labels can be wrong. Store printed-to-PDF mapping explicitly and distinguish frontmatter Roman numbering. Account for all chapters, appendices, examples and exercises; exclusions require page-specific reasons. A selected-chapter request keeps the rest unread.

Read every substantive passage in chunks of up to eight pages. For each section record what was read, definitions, main argument, assumptions, examples and page evidence. Retain unresolved passages and OCR failures. A passage remains unresolved until a visual or reliable source check resolves it; a successful extraction is not enough.

Use precise mathematical notation and explanatory paraphrase. Preserve original numbering when referring to a definition, equation, theorem, algorithm or figure. State assumptions before conclusions and distinguish a source proof from your explanation. Do not invent unstated complexity, a missing proof, or exercise solutions. If the source appears mistaken, quote only a short necessary fragment, identify the equation/page, explain the issue, and label any proposed correction. Do not silently repair the source.

Chapter templates have no paper-summary word limit, compulsory diagrams, or variable-extreme tables. Cover sections proportionately. Record not-applicable categories explicitly instead of inventing content. Synthesis must identify its chapter scope and any prerequisite chapter not read.

For figures, reuse `~/.agents/skills/lit-summarizer-cdx/references/figure-extraction.md` and linking guidance. Render pages with PyMuPDF or Poppler; inspect mathematical glyphs with a local image viewer. Prefer extracting original diagrams to redrawing them. Use chapter-specific filenames. If an inspected figure cannot export, retain its numbered reference, page, description and error. No need for an invented replacement graphic.

Useful sources checked 2026-09-10:

- [PyMuPDF OCR](https://pymupdf.readthedocs.io/en/latest/recipes-ocr.html): local Tesseract, reuse OCR TextPage, visual checks still needed.
- [Zotero local API](https://www.zotero.org/support/dev/web_api/v3/local_api): read-only GET identity and server header; personal library users/0.

Full verification checks all section coverage, representative displayed mathematics against rendered pages, citations against PDF and printed labels, original figure numbering, assumptions, source-versus-explanation distinctions, and generated links. Verify all unresolved substantive content is cleared before asserting full coverage.
