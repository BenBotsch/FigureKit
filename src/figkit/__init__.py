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

This writes ``f1.svg``, ``f1-dark.svg``, ``f1.png`` and ``f1-dark.png``, all transparent. For a
website, :func:`page` writes the figure without its title per language, ``f1.de.svg`` and
``f1.en.svg``, and :func:`write_manifest` lists them with their titles and alt texts.
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
    check_text,
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
from figkit.language import headless, language, localize, number
from figkit.manifest import Caption, page
from figkit.manifest import write as write_manifest
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
    "Caption",
    "Draw",
    "Output",
    "Theme",
    "bar_labels",
    "canvas",
    "category_axis",
    "check_text",
    "grid",
    "headless",
    "hex_colour",
    "ink_on",
    "language",
    "legend_top",
    "line_labels",
    "localize",
    "mono",
    "mono_ticks",
    "number",
    "page",
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
    "write_manifest",
]
