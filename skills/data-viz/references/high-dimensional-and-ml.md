# High-Dimensional and Machine Learning Visualization

Use this reference for PCA, t-SNE, UMAP, embeddings, model evaluation plots, calibration, loss curves, attention, saliency, and ML-specific visualization caveats.

## Dimensionality Reduction Choices

| Method | Use when | Strengths | Main caveats |
|---|---|---|---|
| PCA | Need a fast, linear, stable baseline | Deterministic, interpretable variance, good preprocessing check | Misses nonlinear structure |
| t-SNE | Exploring local neighborhoods in embeddings | Often separates nearby local groups visually | Can create false clusters; global distances and cluster sizes are unreliable |
| UMAP | Exploring nonlinear structure at larger scale | Often faster than t-SNE, can preserve more neighborhood structure | Sensitive to `n_neighbors`, `min_dist`, metric, and seed |
| Pair plot | Few numeric variables | Transparent, easy diagnostics | Does not scale to many features |
| Parallel coordinates | Many variables, labeled groups | Shows multivariate profiles | Can become unreadable without filtering |

Always compare embeddings against labels, nearest neighbors, quantitative metrics, or domain knowledge before making semantic claims.

## PCA Guidance

- Standardize features when units or scales differ.
- Report explained variance for plotted components.
- Inspect loadings when interpretability matters.
- Use PCA before t-SNE/UMAP when denoising or reducing very high dimensions.
- Do not claim PCA clusters are nonlinear manifolds; PCA is linear.

## t-SNE Guidance

t-SNE is useful for local-neighborhood exploration, not proof of class structure.

Critical caveats:

- Apparent clusters can be artifacts of perplexity, learning rate, initialization, early exaggeration, or random seed.
- Distances between far-apart clusters are not meaningful.
- Cluster area and density are not reliable population estimates.
- Multiple runs can look different; set and report the random seed.
- Compare with PCA and UMAP before claiming robust structure.

Recommended reporting:

- Number of samples and source of embeddings.
- Preprocessing and normalization.
- Perplexity, learning rate, iterations, initialization, metric, and random seed.
- Whether labels were used only for coloring or influenced the embedding.

## UMAP Guidance

UMAP is useful for nonlinear embedding exploration and larger datasets, but it is not neutral.

Report:

- `n_neighbors`, `min_dist`, distance metric, random seed, preprocessing, and sample size.
- Whether supervised UMAP was used.
- Whether the visual pattern persists across parameter settings.

Interpret carefully:

- Small `n_neighbors` emphasizes local detail; large values emphasize broader structure.
- Small `min_dist` makes tighter clumps; larger values spreads points.
- Different metrics can change the geometry substantially.

## Embedding Plot Best Practices

- Use small points, alpha blending, or rasterization for dense plots.
- Prefer direct labels or representative annotations over huge legends.
- Use colorblind-safe palettes for classes.
- Show unlabeled points in neutral gray when highlighting a subset.
- Facet by known metadata when one plot becomes overloaded.
- Include a warning when the projection is exploratory.

## Classification Evaluation

### Confusion Matrix

- Specify class order and decision threshold.
- Normalize by true label for recall-focused reading or predicted label for precision-focused reading.
- Show raw counts when class support matters.
- For imbalanced data, include per-class precision, recall, and F1 alongside the matrix.

### ROC Curve

- Useful for ranking quality across thresholds.
- Can look overly optimistic under severe class imbalance.
- Include AUC only when the positive/negative class definition is clear.

### Precision-Recall Curve

- Prefer PR curves for rare-positive problems.
- Include baseline prevalence so users can interpret lift.
- Explain the operating threshold if a decision will be made.

### Calibration

- Use reliability diagrams and calibration error when predicted probabilities are consumed as probabilities.
- Include sample counts per bin; sparse bins are unstable.

## Training and Optimization Plots

- Plot training and validation loss together.
- Use log scale when loss spans orders of magnitude.
- Smooth only for readability and keep raw traces available.
- Mark learning-rate changes, early stopping, or major training events.
- Avoid overinterpreting noisy single-run curves; compare seeds when possible.

## Attention and Saliency

- Attention maps and saliency heatmaps are explanations, not proof of causal importance.
- Report the method used and preprocessing.
- Compare against simple baselines when possible.
- Avoid color maps that exaggerate small differences.
- For images, overlay heatmaps with transparency and include the original image.
- For text, ensure highlighted tokens are readable and not hidden by color contrast.

