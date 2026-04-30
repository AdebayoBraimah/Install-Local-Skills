# Implementation Patterns

Use this reference when writing or adapting visualization code. Python is the default; use other ecosystems only when they fit the user's environment or request.

## Python Setup

```python
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_theme(context="notebook", style="whitegrid", palette="colorblind")
```

## Reproducible Figure Helper

```python
def save_figure(fig, path, dpi=300):
    fig.savefig(path, dpi=dpi, bbox_inches="tight")
```

## Distribution by Group

```python
fig, ax = plt.subplots(figsize=(8, 4.5))
sns.violinplot(data=df, x="group", y="value", inner=None, cut=0, ax=ax)
sns.stripplot(data=df, x="group", y="value", color="black", alpha=0.25, size=2, ax=ax)
ax.set_title("Value distribution by group")
ax.set_xlabel("Group")
ax.set_ylabel("Value")
save_figure(fig, "distribution_by_group.png")
```

## Dense Relationship Plot

```python
fig, ax = plt.subplots(figsize=(6, 5))
hb = ax.hexbin(df["x"], df["y"], gridsize=80, mincnt=1, cmap="viridis", bins="log")
fig.colorbar(hb, ax=ax, label="log10(count)")
ax.set_title("Density of observations")
ax.set_xlabel("x")
ax.set_ylabel("y")
save_figure(fig, "hexbin_density.png")
```

## Time Series with Uncertainty

```python
fig, ax = plt.subplots(figsize=(9, 4.5))
ax.plot(summary["date"], summary["mean"], color="#1f77b4", label="Mean")
ax.fill_between(
    summary["date"],
    summary["lower"],
    summary["upper"],
    color="#1f77b4",
    alpha=0.2,
    label="Interval",
)
ax.set_title("Metric over time with uncertainty")
ax.set_xlabel("Date")
ax.set_ylabel("Metric")
ax.legend(frameon=False)
fig.autofmt_xdate()
save_figure(fig, "time_series_uncertainty.png")
```

## Confusion Matrix, ROC, and PR Curves

```python
from sklearn.metrics import ConfusionMatrixDisplay, RocCurveDisplay, PrecisionRecallDisplay

threshold = 0.5
y_pred = (y_score >= threshold).astype(int)

fig, axes = plt.subplots(1, 3, figsize=(15, 4.5))

ConfusionMatrixDisplay.from_predictions(
    y_true,
    y_pred,
    display_labels=["negative", "positive"],
    normalize=None,
    ax=axes[0],
    colorbar=False,
)
axes[0].set_title(f"Confusion matrix at threshold={threshold}")

RocCurveDisplay.from_predictions(y_true, y_score, ax=axes[1])
axes[1].set_title("ROC curve")

PrecisionRecallDisplay.from_predictions(y_true, y_score, ax=axes[2])
positive_rate = np.mean(y_true)
axes[2].axhline(positive_rate, color="gray", linestyle="--", label="Positive rate")
axes[2].legend(frameon=False)
axes[2].set_title("Precision-recall curve")

fig.tight_layout()
save_figure(fig, "classification_evaluation.png")
```

## PCA and t-SNE Skeleton

```python
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.preprocessing import StandardScaler

X_scaled = StandardScaler().fit_transform(X)

pca = PCA(n_components=2, random_state=0)
X_pca = pca.fit_transform(X_scaled)

tsne = TSNE(
    n_components=2,
    perplexity=30,
    learning_rate="auto",
    init="pca",
    random_state=0,
)
X_tsne = tsne.fit_transform(X_scaled)

projection = pd.DataFrame({
    "pca_1": X_pca[:, 0],
    "pca_2": X_pca[:, 1],
    "tsne_1": X_tsne[:, 0],
    "tsne_2": X_tsne[:, 1],
    "label": labels,
})
```

Always report t-SNE parameters and warn that visual clusters require validation.

## Plotly for Interactive Exploration

```python
import plotly.express as px

fig = px.scatter(
    df,
    x="x",
    y="y",
    color="category",
    hover_data=["id"],
    title="Interactive relationship view",
)
fig.update_layout(hovermode="closest")
fig.write_html("interactive_scatter.html")
```

Use Plotly when hover details, zooming, filtering, or HTML sharing matter.

## Altair for Declarative Charts

```python
import altair as alt

chart = (
    alt.Chart(df)
    .mark_circle(size=35, opacity=0.6)
    .encode(
        x=alt.X("x:Q", title="x"),
        y=alt.Y("y:Q", title="y"),
        color=alt.Color("category:N", title="Category"),
        tooltip=["id:N", "x:Q", "y:Q", "category:N"],
    )
    .properties(width=650, height=400, title="Relationship by category")
)
chart.save("altair_scatter.html")
```

Use Altair for concise grammar-of-graphics style charts, especially with interactive selection on moderate datasets.

## Optional Ecosystems

- **Bokeh**: useful for Python dashboards and linked interactions when the user already uses Bokeh.
- **R/ggplot2**: appropriate when the user's workflow is R-native or when statistical plotting conventions are already in ggplot2.
- **D3 or Observable Plot**: appropriate for custom web-native visualization, bespoke interactions, or production frontend integration.
- **PyTorch/TensorFlow**: use framework tensors only as data sources; convert to NumPy or pandas before plotting unless framework-specific tools are required.

