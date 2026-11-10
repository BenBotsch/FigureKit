"""Small building blocks that keep figures of different projects alike."""

from collections.abc import Iterable, Sequence
from typing import Any, Literal

import numpy as np
from matplotlib.axes import Axes
from matplotlib.container import BarContainer
from matplotlib.legend import Legend
from matplotlib.text import Annotation, Text
from matplotlib.ticker import PercentFormatter

from figkit.theme import Theme, tokens

Axis = Literal["x", "y"]


def mono() -> str:
    """Family of numbers and identifiers: values, feature names, code."""
    family: str = tokens()["font"]["mono"]
    return family


def hex_colour(rgba: Sequence[float]) -> str:
    """``#rrggbb`` of an RGB(A) tuple in 0..1, as a colormap returns it."""
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgba[:3])


def ink_on(colour: str) -> str:
    """Dark or white text, whichever reads better on a fill of ``colour``."""
    r, g, b = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    light = 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.5
    return tokens()["themes"]["light"]["ink"] if light else "#ffffff"


def title(ax: Axes, text: str, theme: Theme, subtitle: str | None = None) -> None:
    """Title at the top left of the axes, with an optional line of explanation below it.

    The subtitle takes the space where :func:`legend_top` would go; with a subtitle, put the
    legend inside the axes.
    """
    size = tokens()["font"]
    if subtitle is None:
        ax.set_title(text)
        return
    gap = 6
    ax.set_title(text, pad=gap + size["label"] * 1.25 + 4)
    ax.annotate(
        subtitle,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(0, gap),
        textcoords="offset points",
        va="bottom",
        ha="left",
        fontsize=size["label"],
        color=theme.secondary,
    )


def legend_top(ax: Axes, ncols: int | None = None, **kwargs: Any) -> Legend:
    """Legend in one row at the top right, on the line of the title."""
    handles, _ = ax.get_legend_handles_labels()
    return ax.legend(
        loc="lower right",
        bbox_to_anchor=(1.0, 1.0),
        ncols=ncols or len(handles),
        borderaxespad=0.3,
        columnspacing=1.2,
        **kwargs,
    )


def grid(ax: Axes, axis: Axis | Literal["both"] = "y") -> None:
    """Hairline grid along one axis, behind the data."""
    ax.grid(True, axis=axis)
    ax.set_axisbelow(True)


def percent(ax: Axes, axis: Axis = "y", decimals: int = 0) -> None:
    """Show the axis from 0 to 1 as 0 % to 100 %."""
    target = ax.yaxis if axis == "y" else ax.xaxis
    target.set_major_formatter(PercentFormatter(xmax=1, decimals=decimals))


def category_axis(ax: Axes, axis: Axis = "y") -> None:
    """Axis of category names: no spine and no tick marks, the names stand on their own."""
    ax.tick_params(axis=axis, length=0, pad=6)
    ax.spines["left" if axis == "y" else "bottom"].set_visible(False)


def mono_ticks(ax: Axes, axis: Axis = "y") -> None:
    """Set the tick labels of an axis in the mono font, for identifiers such as column names."""
    labels = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    for label in labels:
        label.set_fontfamily(mono())


def value(ax: Axes, x: float, y: float, text: str, theme: Theme, **kwargs: Any) -> Text:
    """A number on the plot, in mono and ink."""
    options = {"fontfamily": mono(), "fontsize": tokens()["font"]["annotation"], "color": theme.ink}
    return ax.text(x, y, text, **(options | kwargs))


def bar_labels(
    ax: Axes,
    bars: BarContainer,
    theme: Theme,
    *,
    labels: Iterable[str] | None = None,
    fmt: str = "{:.2f}",
    padding: float = 3,
) -> list[Annotation]:
    """Values at the ends of bars, in mono and in the secondary ink."""
    texts = (
        list(labels) if labels is not None else [fmt.format(v) for v in np.asarray(bars.datavalues)]
    )
    result: list[Annotation] = ax.bar_label(
        bars,
        labels=texts,
        padding=padding,
        fontfamily=mono(),
        fontsize=tokens()["font"]["annotation"],
        color=theme.secondary,
    )
    return result


def reference_line(
    ax: Axes,
    position: float,
    label: str,
    theme: Theme,
    *,
    axis: Axis = "x",
    colour: str | None = None,
    where: float = 1.0,
    side: Literal["left", "right"] = "right",
) -> Text:
    """A thin line at a fixed value (threshold, chance level, alert limit) with its label.

    ``where`` is the position of the label along the line in axes coordinates. The label sits
    above a horizontal line, and on ``side`` of a vertical one; use ``left`` near the right edge.
    """
    line_colour = colour or theme.muted
    small = {"fontsize": tokens()["font"]["annotation"], "color": theme.secondary}
    if axis == "x":
        ax.axvline(position, color=line_colour, linewidth=1, zorder=1)
        return ax.text(
            position,
            where,
            f" {label}" if side == "right" else f"{label} ",
            transform=ax.get_xaxis_transform(),
            ha="left" if side == "right" else "right",
            va="top",
            **small,
        )
    ax.axhline(position, color=line_colour, linewidth=1, zorder=1)
    return ax.text(
        where,
        position,
        label,
        transform=ax.get_yaxis_transform(),
        ha="right" if where >= 0.5 else "left",
        va="bottom",
        **small,
    )


def line_labels(
    ax: Axes,
    items: Sequence[tuple[float, float, str]],
    theme: Theme,
    *,
    offset: float = 5,
) -> list[Annotation]:
    """Names at the ends of lines, pushed apart vertically so that they do not overlap.

    Direct labels make a legend unnecessary and carry the identity of series whose colour has
    little contrast against the page. The text is in the secondary ink; the line next to it
    carries the colour. Call this after the limits and the figure size are final.

    Args:
        ax: Axes of the lines.
        items: ``(x, y, text)`` of each line end, in data coordinates.
        theme: Theme of the figure.
        offset: Distance from the line end to the text, in points.
    """
    size = tokens()["font"]["annotation"]
    spacing = size * 1.35
    figure = ax.get_figure()
    dpi = figure.dpi if figure is not None else 72
    wanted = [float(ax.transData.transform((x, y))[1]) * 72 / dpi for x, y, _ in items]
    placed = _spread(wanted, spacing)
    return [
        ax.annotate(
            text,
            xy=(x, y),
            xytext=(offset, placed[i] - wanted[i]),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=size,
            color=theme.secondary,
            annotation_clip=False,
        )
        for i, (x, y, text) in enumerate(items)
    ]


def _spread(wanted: Sequence[float], spacing: float) -> list[float]:
    """Positions at least ``spacing`` apart, each group of crowded labels centred on its targets."""
    order = sorted(range(len(wanted)), key=lambda i: wanted[i])
    groups: list[list[int]] = []
    for i in order:
        groups.append([i])
        # Merge with the group below while the two overlap, and centre the merged group again.
        while len(groups) > 1:
            low, high = groups[-2], groups[-1]
            if _start(low, wanted, spacing) + len(low) * spacing <= _start(high, wanted, spacing):
                break
            groups[-2:] = [low + high]
    placed = [0.0] * len(wanted)
    for group in groups:
        start = _start(group, wanted, spacing)
        for k, i in enumerate(group):
            placed[i] = start + k * spacing
    return placed


def _start(group: Sequence[int], wanted: Sequence[float], spacing: float) -> float:
    centre = sum(wanted[i] for i in group) / len(group)
    return centre - (len(group) - 1) * spacing / 2
