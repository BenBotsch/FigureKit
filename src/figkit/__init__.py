"""One figure style for every project.

Draw a figure as a function of the :class:`Theme` and let :func:`render` write it::

    import matplotlib.pyplot as plt
    import figkit

    def draw(theme: figkit.Theme) -> plt.Figure:
        figure, ax = plt.subplots(figsize=(6.4, 3.4))
        ax.plot([1, 2, 3], [0.4, 0.7, 0.8], color=theme.series[0], label="model")
        figkit.title(ax, "Validation F1", theme)
        return figure

    figkit.render(Path("docs/figures"), "f1", draw)

This writes ``f1.svg``, ``f1-dark.svg``, ``f1.png`` and ``f1-dark.png``, all transparent.
"""

from figkit.export import (
    CARD,
    CARD_INCHES,
    PHOTO,
    PNG,
    RASTER_DPI,
    SVG,
    WEB,
    WEB_WIDTH,
    Draw,
    Output,
    canvas,
    path_for,
    render,
    save,
)
from figkit.helpers import (
    bar_labels,
    category_axis,
    grid,
    hex_colour,
    ink_on,
    legend_top,
    line_labels,
    mono,
    mono_ticks,
    percent,
    reference_line,
    title,
    value,
)
from figkit.theme import DARK, LIGHT, THEMES, Theme, rc, register_fonts, styled, tokens

__all__ = [
    "CARD",
    "CARD_INCHES",
    "DARK",
    "LIGHT",
    "PHOTO",
    "PNG",
    "RASTER_DPI",
    "SVG",
    "THEMES",
    "WEB",
    "WEB_WIDTH",
    "Draw",
    "Output",
    "Theme",
    "bar_labels",
    "canvas",
    "category_axis",
    "grid",
    "hex_colour",
    "ink_on",
    "legend_top",
    "line_labels",
    "mono",
    "mono_ticks",
    "path_for",
    "percent",
    "rc",
    "reference_line",
    "register_fonts",
    "render",
    "save",
    "styled",
    "title",
    "tokens",
    "value",
]
