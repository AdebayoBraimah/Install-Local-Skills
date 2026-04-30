# Scalability and Publication-Quality Figures

Use this reference for large datasets, overplotting, uncertainty, dense point clouds, multi-panel layouts, and research or publication output.

## Large Dataset Strategy

For large point clouds, choose the visual representation by task:

| Problem | Better approach |
|---|---|
| Millions of x/y points | Hexbin, 2D histogram, rasterized scatter, Datashader-style rendering |
| Dense overlap hides distribution | Alpha blending, contour, KDE, density heatmap |
| Need group comparison | Facets, sampled overlays plus aggregate density |
| Need rare-event visibility | Stratified sampling, separate rare-event layer, small multiples |
| Need exact aggregates | Binning or grouped summaries with counts |

Never default to a raw opaque scatter plot for millions of points.

## Overplotting Controls

- Reduce mark size and opacity.
- Rasterize dense layers while keeping labels and axes vectorized.
- Use hexbin or 2D histograms to show density.
- Use contours for smooth density structure.
- Use faceting to reduce visual collision.
- Sample only when the sampling design is disclosed.

## Aggregation and Binning

Aggregation improves readability but changes the claim.

State:

- Bin widths or bin counts.
- Aggregation function.
- Whether bins are linear, log, quantile, spatial, or time-based.
- How missing values and outliers were handled.

Use log color scales for highly skewed bin counts, but label the scale clearly.

## Uncertainty Visualization

Choose uncertainty encodings by audience and task:

- Error bars for compact point estimates.
- Confidence or credible bands for trends.
- Violin/box/interval plots for group distributions.
- Fan charts for forecasts.
- Posterior densities or ridgelines for full distribution comparison.
- Bootstrap intervals when analytic intervals are unavailable.

Avoid hiding uncertainty when data are sampled, modeled, forecasted, or noisy.

## Publication Standards

For paper-ready figures:

- Use a clear title or caption-level claim.
- Include units, sample size, data source, filters, and date range where relevant.
- Use consistent scales across panels when direct comparison is intended.
- Use direct labels or compact legends.
- Keep typography readable at final print size.
- Avoid dense gridlines and decorative backgrounds.
- Use colorblind-safe palettes and verify grayscale readability.

## Export Guidance

- Use SVG or PDF for line art, diagrams, and vector-friendly plots.
- Use PNG or TIFF at 300+ DPI for dense raster images.
- Save with `bbox_inches="tight"` for Matplotlib exports.
- Keep the figure size close to final intended dimensions.
- For dense scatter, rasterize only the point layer when possible.

Matplotlib example:

```python
fig, ax = plt.subplots(figsize=(6.5, 4.0), constrained_layout=True)
# draw plot here
fig.savefig("figure.pdf", bbox_inches="tight")
fig.savefig("figure.png", dpi=300, bbox_inches="tight")
```

## Multi-Panel Figures

- Use panels to separate tasks, not to display every available variable.
- Share axes when comparisons depend on scale.
- Use panel labels only when needed by captions or papers.
- Keep annotations short and close to the relevant mark.
- Put common legends outside the plotting area if repeated legends waste space.

## Geospatial Cautions

- Normalize counts by population, area, exposure, or opportunity when comparing regions.
- State projection when geometry or distance matters.
- Avoid choropleths for raw counts across differently sized regions.
- Use proportional symbols or hex maps when area size dominates perception.
- Include missing-data styling distinct from zero.

