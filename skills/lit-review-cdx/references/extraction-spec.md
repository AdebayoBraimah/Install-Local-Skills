# Summarizer Extraction Specification

This document defines the full extraction spec for literature note creation. Summarizer agents follow this spec for every paper processed in Phase 3.

## Note Structure

Each note follows `template-literature-batch-1.md`:
- YAML frontmatter (Title, Medium, Category, tags, Keywords, Zotero-Key, Source-Quality, Date/Time Created)
- Citation (BibTeX block)
- Take Home Message (ad-abstract admonition, 2-3 sentences)
- Summary (500-word max prose)
- Structured Detail Blocks (excluded from word count)
- Strengths & Limitations
- Figures & Process Maps
- Other Notes
- Related Papers

## Summary Constraints

- **500 words max** for the prose summary section
- Structured detail blocks are EXCLUDED from the word count:
  - Mathematical expressions / derivations / proofs
  - Datasets used
  - Simulations / experimental setup
  - Training paradigm(s)
  - Models / policies (or equivalents)
  - Significance
  - Novelty
  - Contributions
  - Key tables

## Mathematical Expressions

All math must render in Obsidian using MathJax/LaTeX:
- Inline: `$...$`
- Display: `$$...$$`

Each formula must be accompanied by a **variable reference table** immediately below:

| Variable | Description | Common Value(s) | Low Extreme | High Extreme |
|---|---|---|---|---|
| `$\alpha$` | Learning rate | `1e-3` to `3e-4` (Adam default) | Slow convergence, stable | Fast convergence, may diverge |
| `$\gamma$` | Discount factor | `0.99` (standard RL) | Myopic (immediate rewards only) | Far-sighted (values future rewards) |

Column definitions:
- **Variable**: LaTeX symbol `$...$`
- **Description**: What it represents
- **Common Value(s)**: Practice values. Paper values need no annotation; literature values get a reference (e.g., `0.99 [Sutton & Barto, 2018]`)
- **Low Extreme**: Behavior at minimum
- **High Extreme**: Behavior at maximum

Variable reference tables do NOT count toward the 500-word limit.

## Tables

Recreate relevant tables as Obsidian markdown. Include only:
- **Main results / comparisons** -- benchmark performance across methods
- **Ablation studies** -- impact of individual components
- **Hyperparameter configurations** -- training settings, architecture specs

Each table must have:
- A label matching the paper's numbering (e.g., "Table 2: Main Results on CIFAR-10")
- Column headers preserved from the original
- Bold the best result per column/row where applicable

Tables do NOT count toward the 500-word limit.

## Figure Extraction

### Method A: pdfimages for raster figures (primary)

```bash
# List embedded images
/opt/homebrew/bin/pdfimages -list '/path/to/paper.pdf'

# Extract from specific pages as PNG
/opt/homebrew/bin/pdfimages -png -p -f FIRST_PAGE -l LAST_PAGE '/path/to/paper.pdf' 'Files/Images/{citationKey}-fig'
```

After extraction:
1. Delete `smask` files (alpha masks)
2. Read each image (multimodal) and discard non-figures (logos, watermarks, decorative elements)
3. Keep only actual figures (charts, diagrams, plots, schematics)
4. Rename to: `{citationKey}-fig-1.png`, `{citationKey}-fig-2.png`, etc.

### Method B: Vision+crop for vector figures (fallback)

For vector diagrams or pages where pdfimages finds nothing:

```bash
# Render full page as high-res PNG (PAGE_INDEX is 0-indexed)
/opt/homebrew/bin/magick -density 200 '/path/to/paper.pdf[PAGE_INDEX]' -quality 95 '/tmp/{citationKey}-fullpage.png'
```

Then: Read the full-page PNG, identify bounding box, crop:
```bash
/opt/homebrew/bin/magick '/tmp/{citationKey}-fullpage.png' -crop WxH+X+Y +repage 'Files/Images/{citationKey}-fig-N.png'
```

### Method C: Inkscape (Vector-Native SVG Handling)

Use when vector figures should be preserved as SVGs rather than rasterized. Valuable for architecture diagrams, flowcharts, and text-heavy figures.

```bash
# Extract page as SVG (preserves vectors)
/opt/homebrew/bin/inkscape --export-type=svg --export-plain-svg \
  --export-page=PAGE \
  --export-filename='Files/Images/{citationKey}-fig-N.svg' \
  '{pdfPath}'

# Query objects in the extracted SVG
/opt/homebrew/bin/inkscape --query-all 'Files/Images/{citationKey}-fig-N.svg'

# High-quality PNG from SVG (with text-to-path for font independence)
echo '
document open Files/Images/{citationKey}-fig-N.svg
export png Files/Images/{citationKey}-fig-N.png --dpi 200 --area drawing --background "#ffffff"
quit
' | cli-anything-inkscape
```

Decision: Use Method C over Method B when:
- Figure has text labels that need to stay crisp at any zoom
- Figure will be reused in publications (vector preferred)
- You need to edit the figure (change colors, labels, remove elements)

### Common rules

- Save to `Files/Images/{citationKey}-fig-N.png` (raster) or `.svg` (vector)
- Embed via `![[{citationKey}-fig-N.png]]` with caption below
- When saving SVGs, also export a PNG alongside for universal Obsidian rendering
- Minimum: 1 key figure + 1 process map per note (when applicable)
- Fallback: `[figure not extracted -- see page N of original PDF]`
- When fallback triggers, attempt **figure recreation** via `cli-anything-inkscape` for simple block diagrams (mark as `*Figure N (reconstructed): ...*`)
- Figures and captions do NOT count toward the 500-word limit

## Process Maps

- **Mermaid code blocks** for flowcharts, sequence diagrams, decision trees, state diagrams (Obsidian renders natively)
- **Excalidraw** `.excalidraw` files for architecture/system diagrams (saved to `Files/Images/`)
- **Inkscape** (read `~/.agents/skills/inkscape/SKILL.md` for full reference) for programmatic SVG creation with precise geometry, editing extracted vector figures, and figure recreation when extraction fails
- Prefer Mermaid when sequential/branching; Excalidraw when spatial; Inkscape when precise control or vector editing needed
- See `references/diagram-tools.md` (in lit-summarizer-cdx) for full decision logic

## Long PDF Strategy

| Pages | Strategy |
|---|---|
| 1-20 | Read full |
| 20-50 | Multiple Read calls with page ranges |
| 50+ | Selective: intro + methods + key results + conclusion |

## Item Type Handling

| Type | Action |
|---|---|
| journalArticle, conferencePaper | Full note, `Paper-peer-reviewed` |
| preprint | Full note, `Paper-not-reviewed` |
| bookSection | Full note if academic |
| book, webpage, computerProgram, dataset | Skip or metadata-only stub |

## Source Quality

| Quality | Condition |
|---|---|
| `pdf-full` | PDF read and processed |
| `abstract-only` | No PDF, abstract used (flagged for upgrade) |
| `metadata-only` | No PDF and no abstract; frontmatter + citation only |

## Deduplication

Before writing, each Summarizer checks:
1. Search with `rg 'Zotero-Key: "KEY"'` in `Ideas/Research/`
2. Use `rg --files` or `find` to look for `{citationKey}.md` in `Ideas/Research/`
3. If match found:
   - Empty shell -> upgrade in-place
   - Has user content -> additive merge only, do NOT overwrite
   - Already fully processed -> skip entirely

## Keywords

Assign Keywords as `[[wikilinks]]` to existing hub notes. If a concept has no hub, use a descriptive wikilink name anyway (it may become a hub later).
