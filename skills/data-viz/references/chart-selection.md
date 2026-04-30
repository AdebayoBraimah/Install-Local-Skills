# Chart Selection and Critique

Use this reference when choosing charts, mapping data and task types to visual encodings, or critiquing misleading plot designs.

## Data Types

- **Categorical**: unordered labels such as product, class, region.
- **Ordinal**: ordered labels such as severity, Likert score, rank.
- **Continuous**: numeric measures with meaningful distance.
- **Temporal**: dates, timestamps, durations, intervals.
- **Spatial**: points, polygons, rasters, routes, regions.
- **Graph**: nodes and edges, often with weights or directions.

## Task Types

- **Comparison**: compare values across groups or conditions.
- **Distribution**: show spread, skew, tails, outliers, multimodality.
- **Relationship**: show association between variables.
- **Composition**: show part-to-whole structure.
- **Flow**: show movement, transitions, or pipelines.
- **Change**: show temporal trends or before/after differences.
- **Uncertainty**: show intervals, variance, posterior distributions, or confidence.

## Encoding Hierarchy

Prefer encodings in this order when accuracy matters:

1. Position on a common scale.
2. Position on non-aligned scales.
3. Length.
4. Angle or slope.
5. Area.
6. Volume.
7. Color hue or intensity.
8. Shape.

Use color sparingly: categorical hue for groups, sequential color for ordered magnitude, and diverging color when there is a meaningful midpoint.

## Selection Matrix

| Goal | Recommended | Alternatives | Avoid |
|---|---|---|---|
| One metric across categories | Sorted bar, dot plot | Lollipop | Pie for precise comparison |
| Many categories | Horizontal bar, dot plot | Faceted bars | Rotated labels in crowded vertical bars |
| Time trend | Line | Area, small multiples | Connecting unordered categories |
| Distribution | Histogram, ECDF | Box, violin, KDE | Mean-only summaries |
| Distribution by group | Box/violin + jitter | Ridgeline, faceted histograms | Overlapped opaque histograms |
| Two-variable relationship | Scatter | Hexbin, contour, regression | Overplotted raw scatter for dense data |
| Correlation matrix | Heatmap | Clustered heatmap | Inferring causality |
| Composition at one time | Stacked bar | Treemap, waffle | 3D pie |
| Composition over time | Stacked area | 100% stacked area, facets | Too many stacked series |
| Ranking change | Slope chart | Dumbbell plot | Dual-axis overlays |
| Flow volume | Sankey/alluvial | Funnel for stage conversion | Decorative flow without labels |
| Network structure | Node-link, adjacency matrix | Matrix with clustering | Treating layout as proof |
| Geographic rate | Choropleth normalized by population | Hex map | Raw counts by area |

## Design Principles

- Start with the analytical question, not the chart type.
- Preserve natural ordering for time, rank, and ordinal categories.
- Sort categorical comparisons by value when no natural order exists.
- Make titles state the insight, not just the variable names.
- Put units in axis labels or subtitles.
- Use direct labels when legends make reading harder.
- Remove decoration that does not encode data or guide interpretation.

## Misleading Patterns

- **Truncated bars** exaggerate differences. Bar charts should usually start at zero.
- **Dual axes** can imply correlation by arbitrary scaling. Prefer small multiples, indexed series, or normalized values.
- **Area encodings** make exact comparison hard. Use them for approximate magnitude only.
- **Pie/donut charts** are weak for comparing similar values. Use bars unless the task is rough part-to-whole reading with few parts.
- **3D charts** distort perception and add no data.
- **Rainbow maps** create artificial boundaries and uneven emphasis.
- **Missing uncertainty** can make noisy estimates look definitive.
- **Unlabeled filters or transformations** make the visual claim unverifiable.

## Accessibility Checklist

- Use colorblind-safe palettes, such as blue/orange pairs or Seaborn's `colorblind`.
- Do not rely on color alone; add labels, line styles, symbols, or facets.
- Keep text readable at intended display size.
- Ensure sufficient contrast between marks, text, and background.
- Provide alt text or a short textual summary when sharing static charts.
- Confirm the chart remains understandable in grayscale when print is likely.

