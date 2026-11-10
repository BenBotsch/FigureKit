"""Themes and the matplotlib defaults that turn them into a figure style."""

import json
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import cache
from importlib import resources
from pathlib import Path
from typing import Any, cast

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.pyplot as plt
from cycler import cycler
from matplotlib import font_manager

FONTS = Path(str(resources.files("figkit") / "fonts"))


@dataclass(frozen=True, slots=True)
class Theme:
    """Colours of one page mode.

    Attributes:
        name: ``light`` or ``dark``; the dark files get the suffix ``-dark``.
        surface: Background of opaque output. Transparent output replaces it with ``none``.
        pages: Page colours the transparent output is meant for; the colours were checked on them.
        ink: Titles and values.
        secondary: Axis labels, tick labels, legends and annotations.
        muted: Reference lines and other marks that are not text.
        grid: Hairline grid.
        axis: Spines and baselines.
        series: Categorical colours, used in this fixed order.
        ramp: Sequential ramp from low to high, for heatmaps and confusion matrices.
        status: ``good``, ``warning``, ``serious`` and ``critical``. Never used for a series.
    """

    name: str
    surface: str
    pages: tuple[str, ...]
    ink: str
    secondary: str
    muted: str
    grid: str
    axis: str
    series: tuple[str, ...]
    ramp: tuple[str, ...]
    status: Mapping[str, str]


@cache
def tokens() -> dict[str, Any]:
    """The contents of ``tokens.json``, the single source of colours and type sizes."""
    text = (resources.files("figkit") / "tokens.json").read_text(encoding="utf-8")
    data: dict[str, Any] = json.loads(text)
    return data


def _theme(name: str) -> Theme:
    raw = tokens()["themes"][name]
    return Theme(
        name=name,
        surface=raw["surface"],
        pages=tuple(raw["pages"]),
        ink=raw["ink"],
        secondary=raw["secondary"],
        muted=raw["muted"],
        grid=raw["grid"],
        axis=raw["axis"],
        series=tuple(raw["series"]),
        ramp=tuple(raw["ramp"]),
        status=dict(raw["status"]),
    )


LIGHT = _theme("light")
DARK = _theme("dark")
THEMES = (LIGHT, DARK)


@cache
def register_fonts() -> tuple[str, str]:
    """Add the bundled fonts to matplotlib and return the sans and mono family names.

    Raises:
        RuntimeError: If matplotlib does not resolve a family to the bundled file. A silent
            fallback to another font would change every figure without an error.
    """
    for path in sorted(FONTS.glob("*.ttf")):
        font_manager.fontManager.addfont(str(path))
    families = tokens()["font"]
    for key in ("sans", "mono"):
        family = families[key]
        found = font_manager.findfont(
            font_manager.FontProperties(family=family), fallback_to_default=False
        )
        if Path(found).parent != FONTS:
            msg = f"font {family!r} resolved to {found}, not to the bundled file"
            raise RuntimeError(msg)
    return families["sans"], families["mono"]


def rc(theme: Theme) -> dict[str, Any]:
    """Matplotlib settings for the theme: recessive axes, hairline grid, text in ink."""
    sans, mono = register_fonts()
    size = tokens()["font"]
    return {
        "figure.facecolor": theme.surface,
        "axes.facecolor": theme.surface,
        "savefig.facecolor": theme.surface,
        "axes.edgecolor": theme.axis,
        "axes.linewidth": 0.8,
        "axes.labelcolor": theme.secondary,
        "axes.titlecolor": theme.ink,
        "axes.titlesize": size["title"],
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.labelsize": size["label"],
        "axes.labelpad": 6,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": False,
        "axes.axisbelow": True,
        "axes.prop_cycle": cycler(color=list(theme.series)),
        "grid.color": theme.grid,
        "grid.linewidth": 0.8,
        "xtick.color": theme.axis,
        "ytick.color": theme.axis,
        "xtick.labelcolor": theme.secondary,
        "ytick.labelcolor": theme.secondary,
        "xtick.labelsize": size["tick"],
        "ytick.labelsize": size["tick"],
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "text.color": theme.ink,
        "legend.frameon": False,
        "legend.fontsize": size["label"],
        "legend.labelcolor": theme.secondary,
        "legend.handlelength": 1.4,
        "font.family": "sans-serif",
        "font.sans-serif": [sans],
        "font.monospace": [mono],
        "font.size": size["size"],
        "mathtext.fontset": "custom",
        "mathtext.rm": sans,
        # Mathtext loads its bold faces for every label, log ticks too; the bundle has semibold.
        "mathtext.bf": f"{sans}:semibold",
        "mathtext.bfit": f"{sans}:italic:semibold",
        "lines.linewidth": 2,
        "lines.markersize": 6,
        "lines.solid_capstyle": "round",
        "patch.linewidth": 0,
        "svg.fonttype": "path",
    }


@contextmanager
def styled(theme: Theme) -> Iterator[None]:
    """Apply the theme's matplotlib settings inside the block."""
    # The settings are checked by matplotlib at run time; its stubs list every key as a literal.
    with plt.rc_context(cast("Any", rc(theme))):
        yield
