# Figure Extraction Procedures

## Tool Paths

- **pdfimages**: `/opt/homebrew/bin/pdfimages`
- **magick**: `/opt/homebrew/bin/magick`
- **inkscape**: `/opt/homebrew/bin/inkscape` (backend)
- **cli-anything-inkscape**: `~/anaconda3/bin/cli-anything-inkscape` (harness CLI)
- **Inkscape skill**: `~/.agents/skills/inkscape/SKILL.md` — read for full command reference and workflows

## Method A: pdfimages (Primary -- Raster Figures)

Use for embedded raster images (photos, plots, screenshots).

```bash
# Step 1: List all embedded images
/opt/homebrew/bin/pdfimages -list '{pdfPath}'
# Output columns: page, num, type, width, height, color, comp, bpc, enc, interp, object ID, x-ppi, y-ppi, size, ratio

# Step 2: Extract images from specific pages as PNG
/opt/homebrew/bin/pdfimages -png -p -f FIRST_PAGE -l LAST_PAGE '{pdfPath}' '{vaultPath}/Files/Images/{citationKey}-fig'
# Output: {citationKey}-fig-{page}-{num}.png
```

### Filtering After Extraction

1. **Delete smask files** -- identifiable by filename pattern or very small file size
2. **Inspect each image** with available multimodal/file-viewing support and discard:
   - Logos and watermarks
   - Decorative elements and page backgrounds
   - Icons and bullets
   - Very small images (< 50px in either dimension)
3. **Keep only actual figures**: charts, diagrams, plots, photographs, schematics, algorithm pseudocode
4. **Rename** kept files sequentially: `{citationKey}-fig-1.png`, `{citationKey}-fig-2.png`, etc.

## Method B: magick Vision+Crop (Fallback -- Vector Figures)

Use when `pdfimages -list` shows no images on a page that visually contains a figure (vector graphics, path-based charts).

```bash
# Step 1: Render full page as high-res PNG (0-indexed: page 1 = [0])
/opt/homebrew/bin/magick -density 200 '{pdfPath}[PAGE_0IDX]' -quality 95 '/tmp/{citationKey}-fullpage.png'

# Step 2: Inspect the full-page image and identify bounding box (x, y, width, height in pixels)

# Step 3: Crop to figure region
/opt/homebrew/bin/magick '/tmp/{citationKey}-fullpage.png' -crop WxH+X+Y +repage '{vaultPath}/Files/Images/{citationKey}-fig-N.png'

# Step 4: Clean up temp file
rm '/tmp/{citationKey}-fullpage.png'
```

## Method C: Inkscape (Vector-Native SVG Handling)

Use when figures are vector graphics and you want to **preserve vector quality** rather than rasterize. Particularly valuable for architecture diagrams, flowcharts, and any figure with text labels (keeps text crisp at any zoom).

### When to Use Method C Over Method B

- The PDF contains SVG-origin vector figures (common in LaTeX-generated papers)
- You need to **edit** the extracted figure (change colors, labels, fonts for consistency)
- The figure will be used in a publication or presentation (vector > raster)
- Method B produces blurry text at the required resolution

### Extraction via Inkscape CLI

```bash
# Step 1: Extract a specific page as SVG (PAGE is 1-indexed)
/opt/homebrew/bin/inkscape --export-type=svg --export-plain-svg \
  --export-page=PAGE \
  --export-filename='{vaultPath}/Files/Images/{citationKey}-fig-N.svg' \
  '{pdfPath}'

# Step 2: Query all objects to identify figure elements
/opt/homebrew/bin/inkscape --query-all '{vaultPath}/Files/Images/{citationKey}-fig-N.svg'
# Output: id,x,y,width,height (CSV per object)
```

### Editing Extracted SVGs via Harness (REPL)

When figures need cleanup (strip page chrome, isolate diagram, fix labels):

```bash
# Open, inspect, and clean up
echo '
document open {vaultPath}/Files/Images/{citationKey}-fig-N.svg
object list
object delete unwanted_element_id
style set label_text --fill black --font-family sans-serif
document save
quit
' | cli-anything-inkscape
```

### Export to PNG (High-Quality from Vector Source)

When Obsidian embedding requires PNG but source is vector:

```bash
echo '
document open {vaultPath}/Files/Images/{citationKey}-fig-N.svg
export png {vaultPath}/Files/Images/{citationKey}-fig-N.png --dpi 200 --area drawing --background "#ffffff"
quit
' | cli-anything-inkscape
```

Advantages over magick render:
- **Text-to-path**: `export png ... --text-to-path` produces font-independent output
- **Selective export**: `--object-id FIG_GROUP --id-only` exports just the figure, excluding page elements
- **Drawing-area export**: `--area drawing` auto-crops to content bounds (no manual bbox needed)

### Dual Output (SVG + PNG)

For maximum flexibility, save both:
- `{citationKey}-fig-N.svg` — editable vector (for future use, drawio import, publication)
- `{citationKey}-fig-N.png` — raster for Obsidian embed

Embed the PNG in the note (universal rendering), keep the SVG alongside it.

## Decision Logic

```
For each figure-bearing page:
  1. Check pdfimages -list output for that page
  2. If images found with reasonable dimensions → Method A (pdfimages)
  3. If no images found (vector graphics):
     a. If figure has text labels or will be edited/reused → Method C (Inkscape)
     b. Otherwise → Method B (magick render+crop)
  4. If all methods fail → text fallback with figure recreation (see below)
```

### Figure Recreation (Last Resort)

When extraction fails entirely (corrupt PDF, permissions, encrypted), instead of only writing `[figure not extracted]`, attempt to **recreate simple figures** programmatically:

```bash
# Example: recreate a simple block diagram from the paper's description
echo '
document new --width 600 --height 400
shape rect --x 50 --y 50 --width 120 --height 60 --fill "#e3f2fd" --stroke "#1565c0" --stroke-width 2 --id input
text add "Input" --x 110 --y 85 --anchor middle --fill "#1565c0" --font-size 14 --id input_label
shape rect --x 240 --y 50 --width 120 --height 60 --fill "#e8f5e9" --stroke "#2e7d32" --stroke-width 2 --id encoder
text add "Encoder" --x 300 --y 85 --anchor middle --fill "#2e7d32" --font-size 14 --id enc_label
shape line --x1 170 --y1 80 --x2 240 --y2 80 --stroke "#333" --stroke-width 2 --id arrow1
export png {vaultPath}/Files/Images/{citationKey}-fig-N.png --dpi 150 --area drawing --background "#ffffff"
document save --path {vaultPath}/Files/Images/{citationKey}-fig-N.svg
quit
' | cli-anything-inkscape
```

Use figure recreation only for:
- Simple block/pipeline diagrams (≤8 blocks)
- When the paper's text description is sufficient to reconstruct the layout
- Mark recreated figures clearly: `*Figure N (reconstructed): ...*`

## Failure Fallback

If neither method works (corrupt PDF, permissions error, encrypted):

```markdown
[figure not extracted -- see page N of original PDF]
```

Include a text description of the figure content based on reading the PDF.

## Priority Figures

Extract these first (most useful for reference):
1. Architecture/system diagrams
2. Main results tables/plots
3. Algorithm pseudocode
4. Training pipeline diagrams
5. Ablation study results

## Embedding Format

```markdown
![[{citationKey}-fig-N.png]]
*Figure N: Description of figure content.*
```

## Save Location

All figures go to: `{vaultPath}/Files/Images/{citationKey}-fig-N.png`

## Post-Processing with GIMP CLI

Tool: `~/anaconda3/bin/cli-anything-gimp`

After extraction (Method A or B), enhance each figure:

### Auto-Crop Whitespace

Remove excess whitespace borders around extracted figures:

```bash
cli-anything-gimp crop --auto '{figure_path}' -o '{figure_path}'
```

### Contrast Enhancement (scanned/low-quality PDFs)

```bash
cli-anything-gimp color --autocontrast '{figure_path}' -o '{figure_path}'
```

### Resize Oversized Images (>3000px either dimension)

```bash
cli-anything-gimp info '{figure_path}'   # check dimensions first
cli-anything-gimp resize --percent 50 '{figure_path}' -o '{figure_path}'
```

### Format Normalization

```bash
cli-anything-gimp convert '{figure_path}' '{output_path}.png'
```

### Decision Logic

Inspect each extracted figure with available multimodal/file-viewing support. Apply GIMP only when:
- Image has excessive whitespace borders -> auto-crop
- Image appears washed out or low contrast -> autocontrast
- Image dimensions >3000px -> resize
- Image is not PNG -> convert
- Otherwise -> skip post-processing (preserve original quality)

### Batch Processing (for collections with many figures)

```bash
cli-anything-gimp batch 'Files/Images/{citationKey}-fig-*.png' --convert-to png -o 'Files/Images/'
```

## Post-Processing with Inkscape (SVG Figures)

Tool: `cli-anything-inkscape` (agent-native harness)

Use for vector figures extracted via Method C, or any SVG files. GIMP handles raster; Inkscape handles vector.

### Strip Editor Metadata (Clean SVG)

Remove Inkscape/Illustrator-specific namespaces for smaller, portable SVGs:

```bash
echo '
document open {figure_path}
export svg {figure_path} --plain
quit
' | cli-anything-inkscape
```

### Normalize Text Styling

Make extracted figure labels consistent across papers (uniform font, color):

```bash
echo '
document open {figure_path}
text list
style set LABEL_ID --fill black --font-family sans-serif --font-size 12
document save
quit
' | cli-anything-inkscape
```

### Font-Independent PNG Export (Text-to-Path)

For figures with custom fonts that may not be installed on all systems:

```bash
/opt/homebrew/bin/inkscape --export-type=png --export-dpi=200 \
  --export-text-to-path --export-area-drawing \
  --export-background='#ffffff' \
  --export-filename='{output_path}.png' '{figure_path}.svg'
```

### High-Quality PDF Export (for publication reuse)

```bash
echo '
document open {figure_path}
export pdf {vaultPath}/Files/Images/{citationKey}-fig-N.pdf --text-to-path
quit
' | cli-anything-inkscape
```

### Decision Logic (GIMP vs Inkscape Post-Processing)

```
Is the figure an SVG (vector)?
  ├── YES → Inkscape post-processing
  │     ├── Has messy metadata/namespaces → strip with --plain export
  │     ├── Inconsistent label fonts → normalize text styling
  │     ├── Needs PNG for Obsidian embed → export with --area drawing --dpi 200
  │     └── Will be reused in publication → export PDF with --text-to-path
  └── NO (PNG/JPG/raster) → GIMP post-processing
        ├── Excess whitespace → auto-crop
        ├── Low contrast → autocontrast
        ├── Oversized → resize
        └── Wrong format → convert
```
