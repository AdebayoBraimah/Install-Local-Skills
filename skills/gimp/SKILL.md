---
name: gimp
description: |
  Image manipulation via GIMP CLI: crop, resize, rotate, color adjustment, filters, format conversion,
  and batch processing. Use when: user wants to "edit image", "crop image", "resize image",
  "adjust contrast", "convert format", "batch process images", "post-process figures",
  "auto-crop", "enhance image", "desaturate", "sharpen image", or any image manipulation task.
  Invoke as /gimp <instruction> or /gimp with no args for interactive mode.
---

# GIMP CLI Image Manipulation

Manipulate images via the CLI-Anything GIMP harness. Supports single-image operations, chained session workflows, and batch processing.

## Configuration

| Setting | Value |
|---|---|
| CLI tool | `/Users/adebayobraimah/anaconda3/bin/cli-anything-gimp` |
| GIMP backend | `/Applications/GIMP.app/Contents/MacOS/gimp-console` |
| Supported input | PNG, JPEG, TIFF, BMP, WebP, XCF |
| Supported output | PNG, JPEG, TIFF, BMP, WebP, XCF |

---

## Quick Start

| User Says | Action |
|---|---|
| "crop this image" | `crop --auto` or `crop --box L T R B` |
| "resize to 800px wide" | `resize -w 800` |
| "make it grayscale" | `color --desaturate` |
| "enhance contrast" | `color --autocontrast` |
| "convert to PNG" | `convert src.jpg dest.png` |
| "batch resize all figures" | `batch "*.png" --resize-percent 50 -o out/` |
| "sharpen this image" | `filter --sharpen` |
| "rotate 90 degrees" | `rotate -d 90` |
| "flip horizontally" | `rotate --flip h` |
| "post-process extracted figures" | Auto-crop + autocontrast + resize pipeline |

---

## Workflows

### Direct Command (single operation)

```bash
cli-anything-gimp <command> [PATH] [options] -o <output>
```

Most commands accept an image path directly and write to `-o`. If `-o` is omitted, the result replaces the input (in-memory session, use `save` to persist).

### Session Mode (chained operations)

```bash
cli-anything-gimp open image.png
cli-anything-gimp crop --auto
cli-anything-gimp color --autocontrast
cli-anything-gimp resize --percent 50
cli-anything-gimp save output.png
```

Use session mode when applying multiple operations to the same image. `undo` and `redo` are available.

### Batch Processing

```bash
cli-anything-gimp batch "pattern/*.png" --resize-percent 50 --convert-to png -o output_dir/
```

Apply operations to all files matching a glob pattern. Available batch operations: `--resize-percent`, `--convert-to`, `--desaturate`, `--quality`.

---

## Command Reference

### Inspection

| Command | Usage | Description |
|---|---|---|
| `info` | `info [PATH]` | Show image dimensions, format, color mode, metadata |
| `backend` | `backend` | Check GIMP availability and binary location |

### Geometry

| Command | Key Flags | Description |
|---|---|---|
| `crop` | `--box L T R B`, `--auto`, `-o` | Crop to region or auto-crop uniform borders |
| `resize` | `-w WIDTH`, `-h HEIGHT`, `--percent N`, `--resample [nearest\|bilinear\|bicubic\|lanczos]`, `-o` | Resize by pixels or percentage |
| `rotate` | `-d DEGREES`, `--flip [h\|v]`, `--expand/--no-expand`, `-o` | Rotate by angle or flip |

### Color & Filters

| Command | Key Flags | Description |
|---|---|---|
| `color` | `--brightness F`, `--contrast F`, `--saturation F`, `--sharpness F`, `--desaturate`, `--invert`, `--autocontrast`, `-o` | Adjust color properties (1.0 = unchanged) |
| `filter` | `--blur RADIUS`, `--sharpen`, `--edge`, `--emboss`, `--smooth`, `-o` | Apply image filters |

### Format & I/O

| Command | Key Flags | Description |
|---|---|---|
| `convert` | `SRC DEST`, `-q QUALITY` | Convert between formats (PNG, JPEG, TIFF, BMP, WebP, XCF) |
| `open` | `PATH` | Load image into session |
| `save` | `PATH`, `-q QUALITY` | Save session image to file |
| `undo` | (none) | Undo last operation |
| `redo` | (none) | Redo last undone operation |

### Layers (XCF only)

| Command | Key Flags | Description |
|---|---|---|
| `layers` | `PATH`, `--flatten` | List or flatten layers in XCF file |

### Batch

| Command | Key Flags | Description |
|---|---|---|
| `batch` | `PATTERN`, `--resize-percent F`, `--convert-to [png\|jpg\|webp\|bmp\|tiff]`, `--desaturate`, `--quality N`, `-o DIR` | Batch-process files matching glob |

---

## Academic Figure Post-Processing

Common pipeline for cleaning up figures extracted from academic PDFs (via `pdfimages` or `magick`):

### Step 1: Inspect

```bash
cli-anything-gimp info 'Files/Images/{citationKey}-fig-1.png'
```

Check dimensions and format before processing.

### Step 2: Auto-Crop Whitespace

```bash
cli-anything-gimp crop --auto 'Files/Images/{citationKey}-fig-1.png' -o 'Files/Images/{citationKey}-fig-1.png'
```

Removes uniform borders (white margins from PDF extraction).

### Step 3: Contrast Enhancement

```bash
cli-anything-gimp color --autocontrast 'Files/Images/{citationKey}-fig-1.png' -o 'Files/Images/{citationKey}-fig-1.png'
```

Normalizes levels for scanned or washed-out figures.

### Step 4: Resize Oversized Images

If either dimension exceeds 3000px:

```bash
cli-anything-gimp resize --percent 50 'Files/Images/{citationKey}-fig-1.png' -o 'Files/Images/{citationKey}-fig-1.png'
```

### Step 5: Format Normalization

If the extracted image is not PNG:

```bash
cli-anything-gimp convert 'Files/Images/{citationKey}-fig-1.jpg' 'Files/Images/{citationKey}-fig-1.png'
```

### Batch Variant

Process all figures from a paper at once:

```bash
cli-anything-gimp batch 'Files/Images/{citationKey}-fig-*.png' --convert-to png -o 'Files/Images/'
```

### Decision Logic

Read each extracted figure via Read tool (multimodal). Apply GIMP only when:
- Image has excessive whitespace borders -> auto-crop
- Image appears washed out or low contrast -> autocontrast
- Image dimensions >3000px -> resize
- Image is not PNG -> convert
- Otherwise -> skip post-processing (preserve original quality)

---

## Error Handling

| Situation | Response |
|---|---|
| File not found | Check path, suggest glob to locate |
| Unsupported format | Convert first, or use `backend` to verify GIMP availability |
| GIMP backend missing | Report error, suggest installing GIMP |
| Batch pattern matches 0 files | Warn user, suggest checking glob pattern |
| Output overwrites input | This is allowed (in-place processing). Warn if destructive (e.g., lossy JPEG re-encoding) |
| Session image not loaded | Remind user to `open` an image first |

---

## Best Practices

1. Always `info` first to understand the image before applying operations
2. Use `--auto` crop before manual crop -- it handles uniform borders cleanly
3. For academic figures, prefer PNG output (lossless) over JPEG
4. Use `--resample lanczos` for highest-quality downscaling
5. Chain operations in session mode rather than writing intermediate files
6. Use `--json` flag on any command for machine-readable output when scripting
7. Back up originals before in-place batch processing on irreplaceable images
