"""Themes and the matplotlib defaults that turn them into a figure style."""

import json
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache
from importlib import resources
from pathlib import Path
from types import MappingProxyType
from typing import Any, cast

import matplotlib.pyplot as plt
from cycler import cycler
from matplotlib import font_manager

FONTS = Path(str(resources.files("figkit") / "fonts"))


TOKENS = Path(str(resources.files("figkit") / "tokens.json"))
_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
_COLOURS = ("surface", "ink", "secondary", "muted", "grid", "axis")
_LISTS = ("pages", "series", "ramp")
_STATUS = ("good", "warning", "serious", "critical")
_SIZES = ("size", "title", "label", "tick", "annotation", "minimum")
# Custom property of a stylesheet and the token it equals in both themes: (key, list index).
CSS_TOKENS: Mapping[str, tuple[str, int | None]] = MappingProxyType(
    {
        "bg": ("pages", 0),
        "surface": ("surface", None),
        "text": ("ink", None),
        "muted": ("secondary", None),
        "border": ("grid", None),
        "border-strong": ("muted", None),
    }
)


class StyleError(ValueError):
    """A tokens file that does not describe a valid style.

    Attributes:
        problems: Every problem found, each starting with the path of the value in the file,
            such as ``themes.dark.series[2]: 'blue' is not a #rrggbb colour``.
    """

    def __init__(self, source: str, problems: Sequence[str]) -> None:
        self.problems = tuple(problems)
        super().__init__(f"{source}: invalid style\n" + "\n".join(f"  {p}" for p in problems))


@dataclass(frozen=True, slots=True)
class Typography:
    """Font families and sizes in pt of one style.

    Attributes:
        sans: Family of text.
        mono: Family of numbers and identifiers.
        size: Default size of text.
        title: Size of titles.
        label: Size of axis labels, legends and subtitles.
        tick: Size of tick labels.
        annotation: Size of values and annotations on the plot.
        minimum: Smallest size allowed; :func:`figkit.render` fails below it.
        files: Font files of both families. Empty means the fonts bundled with figkit.
    """

    sans: str
    mono: str
    size: float
    title: float
    label: float
    tick: float
    annotation: float
    minimum: float
    files: tuple[Path, ...] = ()

    @classmethod
    def from_tokens(cls, raw: Mapping[str, Any], files: Sequence[Path] = ()) -> "Typography":
        """Typography of the ``font`` section of a tokens file that is already valid."""
        return cls(
            sans=raw["sans"],
            mono=raw["mono"],
            size=float(raw["size"]),
            title=float(raw["title"]),
            label=float(raw["label"]),
            tick=float(raw["tick"]),
            annotation=float(raw["annotation"]),
            minimum=float(raw["minimum"]),
            files=tuple(files),
        )


@dataclass(frozen=True, slots=True)
class Theme:
    """Colours of one page mode.

    Attributes:
        name: Name of the mode, such as ``light`` or ``dark``. The files of the default theme of
            the style have no suffix, every other theme adds ``-<name>``.
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
            Read-only and left out of the hash, so themes can be keys of a dict or a cache.
        type: Fonts and sizes; every helper takes them from the theme it receives.
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
    status: Mapping[str, str] = field(hash=False)
    type: Typography = field(default_factory=lambda: TYPE)


@dataclass(frozen=True, slots=True)
class Style:
    """A complete figure style: the themes of one website or project and their type.

    Attributes:
        themes: Themes in the order :func:`figkit.render` draws them, all with the same type.
        default: Name of the theme for a single file, such as the light one.
        pairs: Each theme and the theme a page swaps it with, such as light and dark.
            Read-only and left out of the hash.
        css: Custom properties of the website's stylesheet and the token each equals, as
            ``(key, index)``; ``index`` picks an entry of a list token such as ``pages``.
            Empty when the tokens name none. Read-only and left out of the hash.
        source: File the style was read from, ``None`` for one built in code.
    """

    themes: tuple[Theme, ...]
    default: str
    pairs: Mapping[str, str] = field(hash=False)
    css: Mapping[str, tuple[str, int | None]] = field(hash=False)
    source: Path | None = None

    @property
    def type(self) -> Typography:
        """Typography of the style, shared by all themes."""
        return self.themes[0].type

    def theme(self, name: str) -> Theme:
        """The theme called ``name``.

        Raises:
            KeyError: If the style has no such theme.
        """
        for theme in self.themes:
            if theme.name == name:
                return theme
        msg = f"no theme {name!r}; the style has {', '.join(t.name for t in self.themes)}"
        raise KeyError(msg)

    def suffix(self, name: str) -> str:
        """Suffix of the files of theme ``name``: none for the default theme, else ``-<name>``."""
        return "" if name == self.default else f"-{name}"

    def split(self, stem: str) -> tuple[str, str]:
        """Split a file stem into the figure and the name of its theme.

        ``bars.de-dark`` gives ``("bars.de", "dark")``, ``bars.de`` gives the default theme. A
        stem may only end in the suffix of a theme of this style.
        """
        others = sorted((t.name for t in self.themes if t.name != self.default), key=len)
        for name in reversed(others):
            if stem.endswith(f"-{name}"):
                return stem.removesuffix(f"-{name}"), name
        return stem, self.default


def load_style(path: Path) -> Style:
    """Read a style from a tokens file in the format of the bundled ``tokens.json``.

    Patterns in ``font.files`` are relative to the tokens file. Without them the style uses the
    bundled fonts.

    Raises:
        StyleError: If the file is not JSON or not a valid style; the error lists every problem.
        OSError: If the file cannot be read.
    """
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise StyleError(str(path), [f"not JSON: {error}"]) from error
    return parse_style(data, base=path.parent, source=path)


def parse_style(data: object, *, base: Path | None = None, source: Path | None = None) -> Style:
    """Build a style from the parsed contents of a tokens file.

    Args:
        data: Parsed JSON in version 1 (one light and one dark theme, the format before 0.4) or 2.
        base: Folder that the patterns of ``font.files`` are relative to, by default the working
            directory.
        source: File the data came from, kept on the style and named in errors.

    Raises:
        StyleError: If the data is not a valid style; the error lists every problem.
    """
    label = str(source) if source is not None else "style"
    problems = _problems(data)
    if problems:
        raise StyleError(label, problems)
    raw = cast("dict[str, Any]", data)
    files: list[Path] = []
    for pattern in raw["font"].get("files", []):
        found = sorted((base or Path.cwd()).glob(pattern))
        if not found:
            problems.append(f"font.files: {pattern!r} matches no file")
        files.extend(found)
    if problems:
        raise StyleError(label, problems)
    typography = Typography.from_tokens(raw["font"], files)
    themes = tuple(_theme(name, value, typography) for name, value in raw["themes"].items())
    if raw.get("version", 1) == 1:
        pairs = {"light": "dark", "dark": "light"}
    else:
        pairs = {name: value["pair"] for name, value in raw["themes"].items() if "pair" in value}
    # Version 1 is the portfolio's format; a project of version 2 names its own properties.
    css = dict(CSS_TOKENS) if raw.get("version", 1) == 1 else {}
    if "css" in raw:
        css = {
            key: (target[0], target[1] if len(target) > 1 else None)
            for key, target in raw["css"].items()
        }
    return Style(
        themes=themes,
        # Version 1 always meant light as the default, whatever the order of its themes.
        default=raw.get("default", "light" if raw.get("version", 1) == 1 else themes[0].name),
        pairs=MappingProxyType(pairs),
        css=MappingProxyType(css),
        source=source,
    )


def _theme(name: str, raw: Mapping[str, Any], typography: Typography) -> Theme:
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
        status=MappingProxyType(dict(raw["status"])),
        type=typography,
    )


def _problems(data: object) -> list[str]:
    """Every problem of a tokens file, each starting with the path of the value."""
    if not isinstance(data, dict):
        return ["the file must hold a JSON object"]
    problems = _unknown("", data, ("$schema", "version", "default", "font", "themes", "css"))
    version = data.get("version", 1)
    if version not in (1, 2) or isinstance(version, bool):
        problems.append(f"version: {version!r} is not 1 or 2")
    problems += _font_problems(data.get("font"))
    themes = data.get("themes")
    if not isinstance(themes, dict) or not themes:
        return [*problems, "themes: must be an object with at least one theme"]
    if version == 1 and sorted(themes) != ["dark", "light"]:
        problems.append("themes: version 1 has exactly light and dark; use version 2 for others")
    for name, raw in themes.items():
        problems += _theme_problems(name, raw, themes, version == 2)
    default = data.get("default")
    if default is not None and default not in themes:
        problems.append(f"default: {default!r} is not a theme")
    if "css" in data:
        problems += _css_problems(data["css"], themes)
    return problems


def _font_problems(font: object) -> list[str]:
    if not isinstance(font, dict):
        return ["font: must be an object"]
    problems = _unknown("font.", font, ("sans", "mono", *_SIZES, "files"))
    problems += [
        f"font.{key}: must be a family name"
        for key in ("sans", "mono")
        if not isinstance(font.get(key), str) or not font[key]
    ]
    bad = [
        key
        for key in _SIZES
        if isinstance(font.get(key), bool)
        or not isinstance(font.get(key), int | float)
        or font[key] <= 0
    ]
    problems += [f"font.{key}: must be a positive size in pt" for key in bad]
    if not bad:
        problems += [
            f"font.{key}: {font[key]} is below font.minimum {font['minimum']}"
            for key in ("size", "title", "label", "tick", "annotation")
            if font[key] < font["minimum"]
        ]
    files = font.get("files", [])
    if not isinstance(files, list) or not all(isinstance(f, str) and f for f in files):
        problems.append("font.files: must be a list of glob patterns")
    else:
        # Path.glob accepts only relative patterns; an anchored one would raise instead.
        problems += [
            f"font.files: {f!r} must be relative to the tokens file"
            for f in files
            if Path(f).anchor or Path(f).is_absolute()
        ]
    return problems


def _theme_problems(
    name: str, raw: object, themes: Mapping[str, Any], pairs_allowed: bool
) -> list[str]:
    where = f"themes.{name}"
    if not isinstance(raw, dict):
        return [f"{where}: must be an object"]
    problems = _unknown(f"{where}.", raw, (*_COLOURS, *_LISTS, "status", "pair"))
    problems += [_colour(f"{where}.{key}", raw.get(key)) for key in _COLOURS]
    for key, least in zip(_LISTS, (1, 1, 2), strict=True):
        values = raw.get(key)
        if not isinstance(values, list) or len(values) < least:
            problems.append(f"{where}.{key}: must be a list of at least {least} colours")
            continue
        problems += [_colour(f"{where}.{key}[{i}]", v) for i, v in enumerate(values)]
    status = raw.get("status")
    if not isinstance(status, dict) or sorted(status) != sorted(_STATUS):
        problems.append(f"{where}.status: must have exactly {', '.join(_STATUS)}")
    else:
        problems += [_colour(f"{where}.status.{key}", status[key]) for key in _STATUS]
    if "pair" in raw:
        problems += _pair_problems(name, raw, themes, pairs_allowed)
    return [p for p in problems if p]


def _pair_problems(
    name: str, raw: Mapping[str, Any], themes: Mapping[str, Any], allowed: bool
) -> list[str]:
    where = f"themes.{name}.pair"
    pair = raw["pair"]
    partner = themes.get(pair) if isinstance(pair, str) else None
    if not allowed:
        return [f"{where}: needs version 2"]
    if pair == name or not isinstance(partner, dict):
        return [f"{where}: {pair!r} is not another theme"]
    if partner.get("pair") != name:
        return [f"{where}: {pair!r} does not pair back with {name!r}"]
    series = raw.get("series")
    if isinstance(series, list) and len(partner.get("series") or []) != len(series):
        return [f"themes.{name}.series: must be as long as in its pair {pair!r}"]
    return []


def _css_problems(css: object, themes: Mapping[str, Any]) -> list[str]:
    if not isinstance(css, dict):
        return ["css: must be an object"]
    problems = []
    for prop, target in css.items():
        single = isinstance(target, list) and len(target) == 1 and target[0] in _COLOURS
        indexed = (
            isinstance(target, list)
            and len(target) == 2
            and target[0] in _LISTS
            and isinstance(target[1], int)
            and not isinstance(target[1], bool)
            and target[1] >= 0
        )
        if not (single or indexed):
            problems.append(f"css.{prop}: must be [colour token] or [list token, index]")
            continue
        if indexed:
            key, index = target
            # Every theme must hold the entry, or check_tokens would fail on the missing one.
            problems += [
                f"css.{prop}: themes.{name}.{key} has no entry {index}"
                for name, raw in themes.items()
                if isinstance(raw, dict)
                and isinstance(raw.get(key), list)
                and index >= len(raw[key])
            ]
    return problems


def _unknown(where: str, raw: Mapping[str, Any], known: Sequence[str]) -> list[str]:
    """A problem per key that is neither known nor a ``$comment``, which catches typos."""
    return [f"{where}{key}: unknown key" for key in raw if key not in known and key != "$comment"]


def _colour(where: str, value: object) -> str:
    if isinstance(value, str) and _HEX.match(value):
        return ""
    return f"{where}: {value!r} is not a #rrggbb colour"


DEFAULT = load_style(TOKENS)
TYPE: Typography = DEFAULT.type
LIGHT = DEFAULT.theme("light")
DARK = DEFAULT.theme("dark")
THEMES = DEFAULT.themes


@cache
def tokens() -> dict[str, Any]:
    """The contents of the bundled ``tokens.json``, the source of :data:`DEFAULT`."""
    data: dict[str, Any] = json.loads(TOKENS.read_text(encoding="utf-8"))
    return data


@cache
def register_fonts(typography: Typography | None = None) -> tuple[str, str]:
    """Add the fonts of a typography to matplotlib and return the sans and mono family names.

    Args:
        typography: Fonts to add; by default those of the bundled style.

    Raises:
        RuntimeError: If matplotlib does not resolve a family to one of the files. A silent
            fallback to another font would change every figure without an error.
    """
    typography = typography or TYPE
    files = typography.files or tuple(sorted(FONTS.glob("*.ttf")))
    for path in files:
        font_manager.fontManager.addfont(str(path))
    for family in (typography.sans, typography.mono):
        found = Path(
            font_manager.findfont(
                font_manager.FontProperties(family=family), fallback_to_default=False
            )
        )
        # The same file, however it is spelled: Windows may give the package a short 8.3
        # path such as RUNNER~1 while matplotlib reports the long one.
        if not any(found.samefile(path) for path in files):
            msg = (
                f"font {family!r} resolved to {found}, not to a file of the style; matplotlib "
                "keeps one file per family, so two styles need fonts of different names"
            )
            raise RuntimeError(msg)
    return typography.sans, typography.mono


def rc(theme: Theme) -> dict[str, Any]:
    """Matplotlib settings for the theme: recessive axes, hairline grid, text in ink."""
    register_fonts(theme.type)
    size = theme.type
    sans, mono = size.sans, size.mono
    return {
        "figure.facecolor": theme.surface,
        "axes.facecolor": theme.surface,
        "savefig.facecolor": theme.surface,
        "axes.edgecolor": theme.axis,
        "axes.linewidth": 0.8,
        "axes.labelcolor": theme.secondary,
        "axes.titlecolor": theme.ink,
        "axes.titlesize": size.title,
        "axes.titleweight": "semibold",
        "axes.titlelocation": "left",
        "axes.titlepad": 10,
        "axes.labelsize": size.label,
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
        "xtick.labelsize": size.tick,
        "ytick.labelsize": size.tick,
        "xtick.major.size": 3,
        "ytick.major.size": 3,
        "text.color": theme.ink,
        "legend.frameon": False,
        "legend.fontsize": size.label,
        "legend.labelcolor": theme.secondary,
        "legend.handlelength": 1.4,
        "font.family": "sans-serif",
        "font.sans-serif": [sans],
        "font.monospace": [mono],
        "font.size": size.size,
        "mathtext.fontset": "custom",
        # Mathtext loads every face of the custom set for each label, log ticks too. Faces left
        # at their defaults fall back to generic families such as cursive, which a bare Linux
        # system lacks, so all of them point to the bundled fonts. The bundle has semibold.
        "mathtext.rm": sans,
        "mathtext.it": f"{sans}:italic",
        "mathtext.bf": f"{sans}:semibold",
        "mathtext.bfit": f"{sans}:italic:semibold",
        "mathtext.sf": sans,
        "mathtext.tt": mono,
        "mathtext.cal": sans,
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
