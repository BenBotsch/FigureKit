"""A specimen figure that shows every token of a style, for ``figkit style preview``.

The specimen draws all series colours as lines with direct labels and a reference line, the
sequential ramp as a strip of cells and the status colours as bars, with a title, a subtitle,
axis labels and tick labels in the fonts and sizes of the style. :func:`preview` renders it in
every theme, so a new tokens file can be judged before the first real figure uses it.
"""

from collections.abc import Sequence
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import ListedColormap
from matplotlib.figure import Figure

from figkit.export import WEB, WEB_WIDTH, Output, render
from figkit.helpers import (
    category_axis,
    grid,
    ink_on,
    line_labels,
    reference_line,
    title,
    value,
)
from figkit.theme import DEFAULT, Style, Theme

NAME = "style"


def specimen(theme: Theme, style: Style | None = None) -> Figure:
    """The specimen in ``theme``; ``style`` picks the dark ink of text on ramp cells."""
    figure = plt.figure(figsize=(WEB_WIDTH, 5.4))
    rows = figure.add_gridspec(2, 2, height_ratios=(2.3, 1), hspace=0.75, wspace=0.45)
    lines = figure.add_subplot(rows[0, :])
    ramp = figure.add_subplot(rows[1, 0])
    status = figure.add_subplot(rows[1, 1])

    steps = np.arange(0, 11)
    ends = []
    for slot, colour in enumerate(theme.series):
        level = 0.9 - 0.7 * slot / max(len(theme.series), 2)
        curve = level - (level - 0.05) * np.exp(-steps / (2.0 + slot))
        lines.plot(steps, curve, color=colour)
        ends.append((10.0, float(curve[-1]), f"series {slot + 1}  {colour}"))
    reference_line(lines, 0.5, "reference", theme, axis="y", where=0.02)
    title(lines, f"Style preview, {theme.name}", theme, subtitle="Series in their fixed order")
    grid(lines, "y")
    lines.set_xlim(0, 10)
    lines.set_ylim(0, 1)
    lines.set_xlabel("step")
    line_labels(lines, ends, theme)

    cells = np.linspace(0, 1, len(theme.ramp))[np.newaxis, :]
    ramp.imshow(
        cells,
        cmap=ListedColormap(list(theme.ramp), name=f"ramp-{theme.name}"),
        vmin=0,
        vmax=1,
        aspect="auto",
    )
    for index, colour in enumerate(theme.ramp):
        value(
            ramp,
            index,
            0,
            str(index + 1),
            theme,
            ha="center",
            va="center",
            color=ink_on(colour, style),
        )
    ramp.set_xticks([])
    ramp.set_yticks([])
    for spine in ramp.spines.values():
        spine.set_visible(False)
    ramp.set_title("Ramp")

    names = list(theme.status)
    positions = np.arange(len(names))
    status.barh(positions, [1] * len(names), height=0.6, color=[theme.status[n] for n in names])
    status.set_yticks(positions, names)
    status.invert_yaxis()
    status.set_xticks([])
    status.spines["bottom"].set_visible(False)
    category_axis(status, "y")
    status.set_title("Status")
    return figure


def preview(
    directory: Path, style: Style | None = None, outputs: Sequence[Output] = WEB
) -> list[Path]:
    """Render the specimen in every theme of ``style`` to ``directory`` as ``style*.svg|png``.

    Raises:
        ValueError: If the specimen does not fit the canvas or has text below the minimum size
            of the style, such as tick labels smaller than ``font.minimum``.
    """
    style = style or DEFAULT
    directory.mkdir(parents=True, exist_ok=True)
    return render(directory, NAME, lambda theme: specimen(theme, style), outputs, style=style)
