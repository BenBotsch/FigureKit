"""Small building blocks that keep figures of different projects alike."""

from collections.abc import Iterable, Sequence
from typing import Any, Literal

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.axes import Axes
from matplotlib.collections import PolyCollection
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.container import BarContainer, ErrorbarContainer
from matplotlib.figure import Figure
from matplotlib.legend import Legend
from matplotlib.text import Annotation, Text
from matplotlib.ticker import PercentFormatter

from figkit.export import WEB_WIDTH
from figkit.language import headless, localize
from figkit.theme import DEFAULT, TYPE, Style, Theme

Axis = Literal["x", "y"]


def mono(theme: Theme | None = None) -> str:
    """Family of numbers and identifiers: values, feature names, code.

    Without a theme it is the family of the bundled style.
    """
    return (theme.type if theme is not None else TYPE).mono


def hex_colour(rgba: Sequence[float]) -> str:
    """``#rrggbb`` of an RGB(A) tuple in 0..1, as a colormap returns it."""
    return "#" + "".join(f"{round(v * 255):02x}" for v in rgba[:3])


def _luminance(colour: str) -> float:
    r, g, b = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ink_on(colour: str, style: Style | None = None) -> str:
    """Dark or white text, whichever reads better on a fill of ``colour``.

    The dark text is the darkest ink of ``style``, by default of the bundled style.
    """
    if _luminance(colour) <= 0.5:
        return "#ffffff"
    return min(((style or DEFAULT).themes), key=lambda t: _luminance(t.ink)).ink


def title(ax: Axes, text: str, theme: Theme, subtitle: str | None = None) -> None:
    """Title at the top left of the axes, with an optional line of explanation below it.

    The subtitle takes the space where :func:`legend_top` would go; with a subtitle, put the
    legend inside the axes. In a headless figure (see :func:`figkit.render`) both are left out,
    because the page shows them.
    """
    if headless():
        return
    size = theme.type
    if subtitle is None:
        ax.set_title(text)
        return
    gap = 6
    ax.set_title(text, pad=gap + size.label * 1.25 + 4)
    ax.annotate(
        subtitle,
        xy=(0, 1),
        xycoords="axes fraction",
        xytext=(0, gap),
        textcoords="offset points",
        va="bottom",
        ha="left",
        fontsize=size.label,
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
    # PercentFormatter puts the sign right after the number; render adds the space of German.
    target.set_major_formatter(PercentFormatter(xmax=1, decimals=decimals))


def category_axis(ax: Axes, axis: Axis = "y") -> None:
    """Axis of category names: no spine and no tick marks, the names stand on their own."""
    ax.tick_params(axis=axis, length=0, pad=6)
    ax.spines["left" if axis == "y" else "bottom"].set_visible(False)


def mono_ticks(ax: Axes, axis: Axis = "y", theme: Theme | None = None) -> None:
    """Set the tick labels of an axis in the mono font, for identifiers such as column names."""
    labels = ax.get_yticklabels() if axis == "y" else ax.get_xticklabels()
    for label in labels:
        label.set_fontfamily(mono(theme))


def value(ax: Axes, x: float, y: float, text: str, theme: Theme, **kwargs: Any) -> Text:
    """A number on the plot, in mono and ink."""
    options: dict[str, Any] = {
        "fontfamily": mono(theme),
        "fontsize": theme.type.annotation,
        "color": theme.ink,
    }
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
    """Values at the ends of bars, in mono and in the secondary ink.

    Values formatted with ``fmt`` follow the language of the figure, ``0,93`` in German; texts
    passed as ``labels`` stay as given.
    """
    texts = (
        list(labels)
        if labels is not None
        else [localize(fmt.format(v)) for v in np.asarray(bars.datavalues)]
    )
    result: list[Annotation] = ax.bar_label(
        bars,
        labels=texts,
        padding=padding,
        fontfamily=mono(theme),
        fontsize=theme.type.annotation,
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
    small: dict[str, Any] = {"fontsize": theme.type.annotation, "color": theme.secondary}
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
    size = theme.type.annotation
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


def ramp_cmap(theme: Theme) -> LinearSegmentedColormap:
    """Colormap of the sequential ramp of ``theme``, from low to high, for heatmaps.

    Pair it with :func:`ink_on` and :func:`hex_colour` for values on the cells.
    """
    return LinearSegmentedColormap.from_list(f"ramp-{theme.name}", theme.ramp)


def band(
    ax: Axes,
    x: Sequence[float] | np.ndarray[Any, Any],
    low: Sequence[float] | np.ndarray[Any, Any],
    high: Sequence[float] | np.ndarray[Any, Any],
    theme: Theme,
    *,
    slot: int = 0,
    opacity: float = 0.2,
) -> PolyCollection:
    """Shaded interval around a line, such as a confidence band, in the colour of series ``slot``.

    The band has no edge and lies behind the lines, so the line of the same series stays on top.
    """
    return ax.fill_between(
        x, low, high, color=theme.series[slot], alpha=opacity, linewidth=0, zorder=1
    )


def error_bars(
    ax: Axes,
    x: Sequence[float] | np.ndarray[Any, Any],
    y: Sequence[float] | np.ndarray[Any, Any],
    error: Any,
    theme: Theme,
    *,
    axis: Axis = "y",
    colour: str | None = None,
) -> ErrorbarContainer:
    """Thin error bars without caps at the points ``(x, y)``, without markers or a line.

    ``error`` is what :meth:`~matplotlib.axes.Axes.errorbar` takes: one value, one per point or
    a ``(2, n)`` pair of lower and upper distances. ``axis`` is the direction of the bars. The
    colour is the secondary ink, so the bars read as a measure of the marks and not as marks.
    """
    spread = {"yerr" if axis == "y" else "xerr": error}
    return ax.errorbar(
        x,
        y,
        **spread,
        fmt="none",
        ecolor=colour or theme.secondary,
        elinewidth=1,
        capsize=0,
        zorder=3,
    )


def callout(
    ax: Axes,
    text: str,
    xy: tuple[float, float],
    offset: tuple[float, float],
    theme: Theme,
    **kwargs: Any,
) -> Annotation:
    """A note that points at ``xy`` with a thin arrow, for an outlier or an event.

    ``offset`` places the text relative to the point in points, such as ``(30, 20)`` for up and
    to the right, so the note keeps its distance whatever the axis limits are.
    """
    dx, dy = offset
    options: dict[str, Any] = {
        "xytext": offset,
        "textcoords": "offset points",
        "ha": "left" if dx >= 0 else "right",
        "va": "bottom" if dy >= 0 else "top",
        "fontsize": theme.type.annotation,
        "color": theme.secondary,
        "arrowprops": {
            "arrowstyle": "-|>",
            "color": theme.muted,
            "linewidth": 0.8,
            "shrinkA": 2,
            "shrinkB": 3,
            "mutation_scale": 7,
        },
        "annotation_clip": False,
    }
    return ax.annotate(text, xy, **(options | kwargs))


def small_multiples(
    count: int,
    *,
    columns: int = 3,
    height: float = 1.8,
    sharex: bool = True,
    sharey: bool = True,
) -> tuple[Figure, list[Axes]]:
    """A grid of ``count`` small charts on the full canvas width that share their axes.

    Shared axes make the panels comparable at a glance. Inner panels keep their ticks but not
    their tick labels, and cells beyond ``count`` are removed.

    Args:
        count: Number of panels.
        columns: Panels per row, fewer when ``count`` is smaller.
        height: Height of one row in inches.
        sharex: Share the x axis between all panels.
        sharey: Share the y axis between all panels.

    Returns:
        The figure and its ``count`` axes, row by row.

    Raises:
        ValueError: If ``count`` or ``columns`` is less than 1.
    """
    if count < 1 or columns < 1:
        msg = f"small_multiples needs at least one panel and column, got {count} and {columns}"
        raise ValueError(msg)
    columns = min(columns, count)
    rows = -(-count // columns)
    figure, grid_ = plt.subplots(
        rows,
        columns,
        figsize=(WEB_WIDTH, height * rows),
        sharex=sharex,
        sharey=sharey,
        squeeze=False,
    )
    cells = list(grid_.flat)
    for spare in cells[count:]:
        spare.remove()
    panels = cells[:count]
    for index, ax in enumerate(panels):
        # Set both sides explicitly: subplots hides the x labels of every row but the last,
        # yet the last panel of a column keeps them when the row below it is short.
        ax.tick_params(axis="x", labelbottom=not (sharex and index + columns < count))
        ax.tick_params(axis="y", labelleft=not (sharey and index % columns))
    return figure, panels
