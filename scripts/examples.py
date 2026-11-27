"""Render the example gallery in ``docs/examples`` from invented data.

Run with ``uv run python scripts/examples.py``. The figures show the parts of the style: a line
chart with direct labels, bars with values and a reference line, a heatmap, small multiples
with confidence bands and a social card.

``docs/examples/style`` shows the line chart in the example style of its ``tokens.json``, with a
print theme. ``docs/readme`` holds the images that only the README shows: the bar chart in plain
matplotlib and both themes of it side by side on their page colours.
"""

import io
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # The script only writes files.

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.patches import FancyBboxPatch
from PIL import Image

import figkit
from figkit import Theme

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "examples"
STYLE = OUT / "style"
README = ROOT / "docs" / "readme"
CLASSES = ["crazing", "inclusion", "patches", "pitted surface", "rolled-in scale", "scratches"]
RECALL = [0.93, 0.81, 0.99, 0.88, 0.74, 0.96]


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
    names = CLASSES
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.2))
    y = np.arange(len(names))
    container = ax.barh(y, RECALL, height=0.56, color=theme.series[0])
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
    cmap = figkit.ramp_cmap(theme)
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


def multiples(theme: Theme) -> Figure:
    """Learning curves of three models, the mean of five seeds with a band of their spread."""
    rng = np.random.default_rng(1)
    sizes = np.array([100, 200, 400, 800, 1600, 3200])
    figure, panels = figkit.small_multiples(3, height=2.2)
    for slot, (ax, (name, end)) in enumerate(
        zip(panels, (("ResNet18", 0.96), ("HOG + SVM", 0.84), ("MobileNet", 0.92)), strict=True)
    ):
        mean = end - (end - 0.4) * np.exp(-np.log2(sizes / 100) / 1.6)
        spread = 0.08 * np.exp(-np.log2(sizes / 100) / 2.5) + rng.uniform(0, 0.01, sizes.size)
        ax.plot(sizes, mean, color=theme.series[slot], marker="o", markersize=3)
        figkit.band(ax, sizes, mean - spread, mean + spread, theme, slot=slot)
        ax.set_xscale("log", base=2)
        ax.set_xticks([100, 400, 1600], ["100", "400", "1600"])
        ax.minorticks_off()
        ax.set_title(name, fontsize=theme.type.label, loc="left")
        figkit.grid(ax, "y")
    panels[0].set_ylim(0.3, 1.0)
    panels[0].set_ylabel("macro $F_1$")
    panels[1].set_xlabel("training images")
    plateau = float(np.asarray(panels[1].lines[0].get_ydata())[-1])
    figkit.callout(panels[1], "plateau", (3200, plateau), (-22, -22), theme)
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


def before(path: Path) -> Path:
    """The bar chart as plain matplotlib draws it, without figkit."""
    with plt.rc_context({"svg.hashsalt": "figkit"}):
        figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.2))
        ax.barh(CLASSES, RECALL)
        ax.axvline(0.8)
        ax.invert_yaxis()
        ax.set_title("Recall per class")
        figure.tight_layout()
        buffer = io.BytesIO()  # A path would get CRLF line ends on Windows.
        figure.savefig(buffer, format="svg", metadata={"Date": None})
        path.write_bytes(buffer.getvalue())
    plt.close(figure)
    return path


def modes(path: Path) -> Path:
    """The light and the dark PNG of the bar chart side by side on their page colours."""
    tiles = [
        (Image.open(OUT / f"bars{suffix}.png").convert("RGBA"), theme.pages[0])
        for suffix, theme in (("", figkit.LIGHT), ("-dark", figkit.DARK))
    ]
    width, height = tiles[0][0].size
    pad = width // 20
    sheet = Image.new("RGBA", (2 * (width + 2 * pad), height + 2 * pad))
    for i, (tile, page) in enumerate(tiles):
        panel = Image.new("RGBA", (width + 2 * pad, height + 2 * pad), page)
        panel.alpha_composite(tile, (pad, pad))
        sheet.paste(panel, (i * (width + 2 * pad), 0))
    sheet = sheet.resize((sheet.width // 2, sheet.height // 2), Image.Resampling.LANCZOS)
    sheet.convert("RGB").save(path, optimize=True)
    return path


def main() -> None:
    """Write every example in both themes, the example style and the README images."""
    for name, draw in (
        ("lines", lines),
        ("bars", bars),
        ("heatmap", heatmap),
        ("multiples", multiples),
    ):
        for path in figkit.render(OUT, name, draw):
            print(path.relative_to(ROOT))
    for path in figkit.render(OUT, "card", card, outputs=figkit.CARD):
        print(path.relative_to(ROOT))
    style = figkit.load_style(STYLE / "tokens.json")
    for path in figkit.render(STYLE, "lines", lines, style=style):
        print(path.relative_to(ROOT))
    README.mkdir(parents=True, exist_ok=True)
    print(before(README / "before.svg").relative_to(ROOT))
    print(modes(README / "modes.png").relative_to(ROOT))


if __name__ == "__main__":
    main()
