---
name: inkscape
description: |
  Vector graphics manipulation via Inkscape CLI harness: create shapes, edit SVGs, manage text and layers,
  export to PNG/PDF/SVG/PS/EPS, path boolean operations, transform objects, and query geometry.
  Use when: user wants to "create SVG", "edit vector", "add shape", "export to PNG from SVG",
  "create diagram", "edit figure", "convert SVG to PDF", "extract vector figure", "recreate figure",
  "post-process SVG", "clean up figure", or any vector graphics task.
  Invoke as /inkscape <instruction> or /inkscape with no args for interactive mode.
---

# Inkscape CLI Vector Graphics

Manipulate vector graphics via the CLI-Anything Inkscape harness. Supports one-shot commands, REPL session workflows, and Inkscape CLI backend for exports and path operations.

## Configuration

> Harness paths assume the author's macOS Anaconda install layout. Adjust the listed paths to match your local install of `cli-anything-inkscape` if needed.

| Setting | Value |
|---|---|
| CLI tool | `~/anaconda3/bin/cli-anything-inkscape` |
| Inkscape backend | `/opt/homebrew/bin/inkscape` (v1.4.2) |
| Harness source | `~/bin/inkscape/agent-harness/` |
| Architecture | Hybrid: lxml for DOM ops + Inkscape CLI for export/path-ops/queries |
| Supported input | SVG |
| Supported output | SVG, PNG, PDF, PS, EPS |

---

## Quick Start

| User Says | Action |
|---|---|
| "create an SVG with shapes" | `document new` + `shape rect/circle/...` |
| "add text to this SVG" | `text add "Hello" --x 50 --y 100` |
| "export SVG to PNG" | `export png output.png --dpi 200` |
| "convert SVG to PDF" | `export pdf output.pdf` |
| "edit this figure" | `document open fig.svg` + modify + `document save` |
| "clean up extracted SVG" | `export svg clean.svg --plain` |
| "list objects in SVG" | `object list` |
| "change fill color" | `style set obj_id --fill "#ff0000"` |
| "create block diagram" | `document new` + shapes + text + lines |
| "query bounding boxes" | `query all` (uses Inkscape engine) |
| "boolean union of paths" | `path union obj1 obj2` |
| "post-process vector figure" | Open, strip metadata, normalize text, re-export |

---

## Workflows

### One-Shot Command

```bash
cli-anything-inkscape document new --width 800 --height 600 --json
cli-anything-inkscape shape rect --x 10 --y 10 --width 100 --height 80 --fill red --json
```

One-shot commands don't persist state between invocations. Use REPL for multi-step workflows.

### REPL Session (default mode — multi-step workflows)

Pipe commands via stdin. The REPL auto-injects `--json` for machine-readable output.

```bash
echo '
document new --width 600 --height 400
shape rect --x 20 --y 20 --width 200 --height 100 --fill "#e3f2fd" --stroke "#1565c0" --stroke-width 2 --id block1
text add "Encoder" --x 120 --y 75 --anchor middle --fill "#1565c0" --font-size 16 --id label1
shape circle --cx 400 --cy 200 --r 60 --fill "#e8f5e9" --stroke "#2e7d32" --id node1
document save --path output.svg
export png output.png --dpi 200 --area drawing --background "#ffffff"
quit
' | cli-anything-inkscape
```

### Open-Edit-Save (editing existing SVGs)

```bash
echo '
document open figure.svg
object list
style set some_label --fill black --font-family sans-serif
object delete unwanted_element
export svg figure-clean.svg --plain
export png figure.png --dpi 200 --area drawing --background "#ffffff"
quit
' | cli-anything-inkscape
```

---

## Command Reference

### Document Management

| Command | Usage | Description |
|---|---|---|
| `document new` | `--width W --height H --units px\|mm\|in\|pt` | Create blank SVG |
| `document open` | `PATH` | Open existing SVG |
| `document save` | `--path PATH` | Save to file (defaults to original path) |
| `document save-as` | `PATH` | Save to new path |
| `document info` | | Show width, height, viewBox, element count, dirty flag, undo depth |
| `document close` | | Close current document |

### Shape Creation

| Command | Key Flags | Description |
|---|---|---|
| `shape rect` | `--x --y --width --height [--rx --ry] [--fill --stroke --stroke-width] [--id] [--layer]` | Rectangle (optional rounded corners) |
| `shape circle` | `--cx --cy --r [--fill --stroke] [--id]` | Circle |
| `shape ellipse` | `--cx --cy --rx --ry [--fill --stroke] [--id]` | Ellipse |
| `shape line` | `--x1 --y1 --x2 --y2 [--stroke --stroke-width] [--id]` | Line segment |
| `shape path` | `--d "M 0 0 L 100 100" [--fill --stroke] [--id]` | SVG path from path data |
| `shape polygon` | `--points "100,10 40,198 190,78" [--fill --stroke] [--id]` | Closed polygon |
| `shape polyline` | `--points "0,0 50,50 100,0" [--fill --stroke] [--id]` | Open polyline |

### Text

| Command | Usage | Description |
|---|---|---|
| `text add` | `"content" --x X --y Y [--font-size --font-family --fill --anchor start\|middle\|end] [--id]` | Create text element |
| `text edit` | `OBJ_ID "new content"` | Replace text content |
| `text list` | | List all text elements |

### Object Manipulation

| Command | Usage | Description |
|---|---|---|
| `object list` | `[--type rect\|circle\|text\|...]` | List all objects (optionally filter by type) |
| `object get` | `OBJ_ID` | Detailed info: all attributes, children |
| `object delete` | `OBJ_ID` | Remove an object |
| `object duplicate` | `OBJ_ID [--new-id ID]` | Clone an object |
| `object set-attr` | `OBJ_ID ATTR VALUE` | Set any SVG attribute |
| `object get-attr` | `OBJ_ID ATTR` | Read an attribute value |
| `object group` | `ID1 ID2 ... [--id GROUP_ID]` | Group objects |
| `object ungroup` | `GROUP_ID` | Dissolve group, promote children |

### Style

| Command | Usage | Description |
|---|---|---|
| `style get` | `OBJ_ID` | Read computed style as key-value dict |
| `style set` | `OBJ_ID [--fill --stroke --stroke-width --opacity --fill-opacity --stroke-opacity]` | Set style properties (preserves existing) |

### Transform

| Command | Usage | Description |
|---|---|---|
| `transform move` | `OBJ_ID --dx DX --dy DY` | Translate |
| `transform scale` | `OBJ_ID --sx SX [--sy SY]` | Scale (uniform if sy omitted) |
| `transform rotate` | `OBJ_ID --angle DEG [--cx --cy]` | Rotate (optional center point) |
| `transform set` | `OBJ_ID "matrix(1,0,0,1,10,20)"` | Set raw SVG transform |
| `transform flip` | `OBJ_ID --axis horizontal\|vertical` | Flip (via Inkscape backend) |
| `transform align` | `ID1 ID2 ... --position left\|hcenter\|right\|top\|vcenter\|bottom [--relative-to selection\|page\|drawing]` | Align (via Inkscape backend) |

### Layer Management

| Command | Usage | Description |
|---|---|---|
| `layer list` | | List all Inkscape layers (id, label, style) |
| `layer add` | `LABEL [--id ID]` | Create new layer |
| `layer rename` | `LAYER_ID NEW_LABEL` | Rename layer |
| `layer delete` | `LAYER_ID` | Delete layer and contents |

### Export (via Inkscape engine)

| Command | Key Flags | Description |
|---|---|---|
| `export png` | `OUTPUT [--dpi 96] [--width PX] [--height PX] [--area page\|drawing] [--background COLOR] [--background-opacity F] [--object-id ID] [--id-only]` | Export to PNG |
| `export pdf` | `OUTPUT [--area page\|drawing] [--text-to-path] [--pdf-version 1.4\|1.5]` | Export to PDF |
| `export svg` | `OUTPUT [--plain]` | Export SVG (--plain strips Inkscape extensions) |
| `export ps` | `OUTPUT [--level 2\|3] [--area page\|drawing] [--text-to-path]` | Export to PostScript |
| `export eps` | `OUTPUT [--area page\|drawing] [--text-to-path]` | Export to EPS |

### Path Boolean Operations (via Inkscape engine)

| Command | Usage | Description |
|---|---|---|
| `path union` | `ID1 ID2 ...` | Merge paths |
| `path difference` | `ID1 ID2 ...` | Subtract top from bottom |
| `path intersection` | `ID1 ID2 ...` | Keep overlapping region |
| `path exclusion` | `ID1 ID2 ...` | XOR — non-overlapping parts |
| `path combine` | `ID1 ID2 ...` | Combine into compound path |
| `path break-apart` | `OBJ_ID` | Split compound path |
| `path simplify` | `OBJ_ID` | Remove extra nodes |
| `path to-path` | `OBJ_ID` | Convert shape/text to path |

### Geometry Queries (via Inkscape engine)

| Command | Usage | Description |
|---|---|---|
| `query bbox` | `OBJ_ID` | Accurate bounding box (x, y, width, height) |
| `query all` | | Bounding boxes for all objects |

### Utilities

| Command | Description |
|---|---|
| `undo` | Undo last operation (50-deep stack) |
| `redo` | Redo last undone operation |
| `status` | Session state: file, dirty flag, undo/redo depth |
| `inkscape-version` | Print Inkscape backend version |

---

## Academic Figure Workflows

### Vector Figure Extraction from PDF

Extract vector figures as SVG instead of rasterizing:

```bash
# Extract page as clean SVG
/opt/homebrew/bin/inkscape --export-type=svg --export-plain-svg \
  --export-page=PAGE \
  --export-filename='Files/Images/{citationKey}-fig-N.svg' \
  '{pdfPath}'

# Then clean up and export via harness
echo '
document open Files/Images/{citationKey}-fig-N.svg
object list
export png Files/Images/{citationKey}-fig-N.png --dpi 200 --area drawing --background "#ffffff"
document save
quit
' | cli-anything-inkscape
```

### SVG Post-Processing (complement to GIMP for raster)

| Task | Command |
|---|---|
| Strip editor metadata | `export svg out.svg --plain` |
| Normalize label fonts | `style set LABEL_ID --fill black --font-family sans-serif` |
| Font-independent PNG | Inkscape CLI: `--export-text-to-path --export-dpi=200` |
| Remove unwanted elements | `object delete ELEMENT_ID` |
| High-quality PDF | `export pdf out.pdf --text-to-path` |

Decision logic: **Raster figures → GIMP** (`/gimp`), **Vector figures → Inkscape** (`/inkscape`).

### Figure Recreation (extraction fallback)

When extraction from PDF fails entirely, recreate simple diagrams programmatically:

```bash
echo '
document new --width 600 --height 300
shape rect --x 30 --y 100 --width 120 --height 60 --fill "#e3f2fd" --stroke "#1565c0" --stroke-width 2 --id input
text add "Input" --x 90 --y 135 --anchor middle --fill "#1565c0" --font-size 14
shape rect --x 230 --y 100 --width 120 --height 60 --fill "#fff3e0" --stroke "#e65100" --stroke-width 2 --id process
text add "Process" --x 290 --y 135 --anchor middle --fill "#e65100" --font-size 14
shape rect --x 430 --y 100 --width 120 --height 60 --fill "#e8f5e9" --stroke "#2e7d32" --stroke-width 2 --id output
text add "Output" --x 490 --y 135 --anchor middle --fill "#2e7d32" --font-size 14
shape line --x1 150 --y1 130 --x2 230 --y2 130 --stroke "#333" --stroke-width 2
shape line --x1 350 --y1 130 --x2 430 --y2 130 --stroke "#333" --stroke-width 2
export png Files/Images/{citationKey}-fig-N.png --dpi 150 --area drawing --background "#ffffff"
document save --path Files/Images/{citationKey}-fig-N.svg
quit
' | cli-anything-inkscape
```

Mark recreated figures: `*Figure N (reconstructed): description*`

### Diagram Creation (programmatic SVG)

Use when precise geometry control is needed and Mermaid/Drawio/Excalidraw aren't ideal:
- Labeled block pipelines with exact positioning
- Annotated shapes with specific colors and styling
- Figures requiring both SVG (editable) and PNG (embed) output
- Compositions built step-by-step with full JSON feedback

---

## Integration with Other Skills

| Raster task | Use `/gimp` |
|---|---|
| Vector task | Use `/inkscape` |
| Simple flowchart | Use Mermaid (inline code block) |
| Spatial conceptual diagram | Use `/excalidraw` |
| Complex architecture with formulas | Use `/drawio` |
| Edit/clean extracted SVG figure | Use `/inkscape` |
| Recreate failed figure extraction | Use `/inkscape` |

---

## Error Handling

| Situation | Response |
|---|---|
| File not found | Check path, ensure `.svg` extension |
| No document open | Run `document new` or `document open` first |
| Object not found | Run `object list` to see available IDs |
| Inkscape binary missing | Report error: `brew install inkscape` |
| Export fails | Check Inkscape backend via `inkscape-version` |
| Path op needs ≥2 objects | Select at least two object IDs |
| Unsaved changes on close | Warning emitted; use `document save` first |

---

## Best Practices

1. Always `object list` to inspect the document before modifying
2. Use `--id` when creating shapes — auto-generated IDs are opaque
3. Use `--area drawing` for exports to auto-crop to content bounds
4. Use `--plain` SVG export to strip editor namespaces for portability
5. Use `--text-to-path` for font-independent PDF/PNG output
6. Pair SVG + PNG output: SVG for editing, PNG for Obsidian embedding
7. Use `query all` for accurate geometry — `object list` shows DOM attributes, not rendered bounds
8. Chain operations in REPL mode rather than separate CLI invocations
9. All commands support `--json` for machine-readable output
10. Undo stack holds 50 operations — use freely for experimentation
