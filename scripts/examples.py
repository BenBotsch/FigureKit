"""Render the example gallery in ``docs/examples`` from invented data.

Run with ``uv run python scripts/examples.py``. The figures show the parts of the style: a line
chart with direct labels, bars with values and a reference line, a heatmap and a social card.
"""

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch

import figkit
from figkit import Theme

OUT = Path(__file__).resolve().parents[1] / "docs" / "examples"


def lines(theme: Theme) -> Figure:
    """Validation score of three models over the epochs."""
    epochs = np.arange(1, 21)
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.4))
    ends = []
    for slot, (name, end, speed) in enumerate(
        (("ResNet18", 0.97, 3.0), ("HOG + SVM", 0.86, 6.0), ("MobileNet", 0.93, 4.0))
    ):
        score = end - (end - 0.35) * np.exp(-(epochs - 1) / speed)
        ax.plot(epochs, score, color=theme.series[slot], label=name)
        ends.append((20.0, float(score[-1]), f"{name} {score[-1]:.2f}"))
    figkit.title(ax, "Validation macro F1", theme)
    figkit.legend_top(ax)
    figkit.grid(ax, "y")
    figkit.line_labels(ax, ends, theme)
    ax.set_xlabel("epoch")
    ax.set_xlim(1, 20)
    ax.set_xticks([1, 5, 10, 15, 20])
    ax.set_ylim(0.3, 1.0)
    return figure


def bars(theme: Theme) -> Figure:
    """Recall per class with a target line."""
    names = ["crazing", "inclusion", "patches", "pitted surface", "rolled-in scale", "scratches"]
    recall = [0.93, 0.81, 0.99, 0.88, 0.74, 0.96]
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.2))
    y = np.arange(len(names))
    container = ax.barh(y, recall, height=0.56, color=theme.series[0])
    figkit.bar_labels(ax, container, theme, fmt="{:.0%}")
    figkit.reference_line(ax, 0.8, "target 80 %", theme, where=1.02)
    ax.set_yticks(y, names)
    ax.invert_yaxis()
    figkit.category_axis(ax, "y")
    figkit.percent(ax, "x")
    figkit.grid(ax, "x")
    ax.set_xlim(0, 1.08)
    figkit.title(ax, "Recall per class", theme, subtitle="Test split, 300 images per class")
    return figure


def heatmap(theme: Theme) -> Figure:
    """A confusion matrix on the sequential ramp, counts in the cells."""
    rng = np.random.default_rng(0)
    counts = np.diag([46, 41, 50, 44, 37, 48]) + rng.integers(0, 4, (6, 6)) * (
        1 - np.eye(6, dtype=int)
    )
    rates = counts / counts.sum(axis=1, keepdims=True)
    cmap = LinearSegmentedColormap.from_list(f"ramp-{theme.name}", theme.ramp)
    names = ["Cr", "In", "Pa", "PS", "RS", "Sc"]
    figure, ax = plt.subplots(figsize=(3.8, 3.6))
    ax.imshow(rates, cmap=cmap, vmin=0, vmax=1)
    for (i, j), count in np.ndenumerate(counts):
        figkit.value(
            ax,
            j,
            i,
            str(count),
            theme,
            ha="center",
            va="center",
            color=figkit.ink_on(figkit.hex_colour(cmap(rates[i, j]))),
        )
    ax.set_xticks(range(6), names)
    ax.set_yticks(range(6), names)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_xlabel("predicted")
    ax.set_ylabel("true")
    figkit.title(ax, "Confusion matrix", theme)
    return figure


def card(theme: Theme) -> Figure:
    """A 1200 x 630 preview with headline numbers."""
    figure = plt.figure(figsize=figkit.CARD_INCHES)
    ax = figure.add_axes((0, 0, 1, 1))
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 63)
    ax.axis("off")
    ax.text(7, 52, "Project title", fontsize=26, fontweight="semibold", va="center")
    ax.text(
        7,
        45,
        "One line on what it does and why it matters",
        fontsize=13,
        color=theme.secondary,
        va="center",
    )
    tiles = (("Accuracy", "0.97"), ("Latency p95", "4.1 ms"), ("Model size", "11 MB"))
    for i, (label, number) in enumerate(tiles):
        x = 7 + i * 36
        ax.add_patch(
            FancyBboxPatch(
                (x, 13),
                33,
                22,
                boxstyle="round,pad=0,rounding_size=2",
                facecolor=theme.ramp[1],
                edgecolor="none",
            )
        )
        ax.text(x + 2.5, 29.5, label, fontsize=12, color=theme.secondary, va="center")
        ax.text(x + 2.5, 20, number, fontsize=26, fontfamily=figkit.mono(), va="center")
    return figure


def main() -> None:
    """Write every example in both themes."""
    for name, draw in (("lines", lines), ("bars", bars), ("heatmap", heatmap)):
        for path in figkit.render(OUT, name, draw):
            print(path.relative_to(OUT.parent.parent))
    for path in figkit.render(OUT, "card", card, outputs=figkit.CARD):
        print(path.relative_to(OUT.parent.parent))


if __name__ == "__main__":
    main()
