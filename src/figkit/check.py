"""Checks of figures for CI.

A directory is checked for light/dark and language pairs, transparency, widths, file sizes and
its ``figures.json``; a stylesheet for the page colours that the figures share with it.
"""

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from pathlib import Path

from PIL import Image

from figkit import manifest
from figkit.export import RASTER_DPI, WEB_WIDTH
from figkit.theme import DEFAULT, Style

FORMATS = (".svg", ".png", ".webp")
# Bytes. Above these, a chart usually embeds a raster or far too many points.
BUDGET = {".svg": 150_000, ".png": 250_000, ".webp": 250_000}
# A PNG next to a WebP of the same name is the lossless copy of a photograph, which is larger.
PHOTO_PNG_BUDGET = 1_000_000
# The figure background is the first patch matplotlib writes into an SVG.
_BACKGROUND = re.compile(r'<g id="patch_1">\s*<path[^>]*style="([^"]*)"')
_SVG_WIDTH = re.compile(r'<svg[^>]* width="([\d.]+)pt"')
# ``failure-modes.de`` is the German file of ``failure-modes``.
_LANGUAGE = re.compile(r"^(?P<name>.+)\.(?P<language>[a-z]{2})$")
_CSS_COLOUR = re.compile(
    r"--color-([\w-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})"
)


def _figure_name(path: Path, style: Style) -> str:
    """Name of the figure without theme and language, ``card`` for ``card.de-dark.png``."""
    stem, _ = style.split(path.stem)
    match = _LANGUAGE.match(stem)
    return match["name"] if match else stem


def check(
    directory: Path,
    opaque: Iterable[str] = ("card",),
    width: float | None = WEB_WIDTH,
    style: Style | None = None,
) -> list[str]:
    """Problems of the figures in ``directory``; an empty list means it passes.

    Args:
        directory: Folder with a file per theme of ``style``, ``<name>.<format>`` and
            ``<name>-dark.<format>`` in the bundled one.
        opaque: Figure names that are deliberately opaque, such as a social card, in every
            language. Their width is not checked either.
        width: Canvas width in inches that every other figure must have, so that pages show
            all of them with the same text size; ``None`` skips the check.
        style: Style that named the files; each file of a theme with a pair needs the file of
            that pair. By default the bundled style.

    Returns:
        One message per problem, with the file it concerns.
    """
    style = style or DEFAULT
    keep_opaque = set(opaque)
    files = sorted(p for p in directory.iterdir() if p.suffix in FORMATS and p.is_file())
    problems = []
    names = {p.name for p in files}
    for path in files:
        stem, theme = style.split(path.stem)
        pair = style.pairs.get(theme)
        partner = f"{stem}{style.suffix(pair)}{path.suffix}" if pair else None
        if partner is not None and partner not in names:
            problems.append(f"{path.name}: missing its pair {partner}")
        size, budget = path.stat().st_size, BUDGET[path.suffix]
        if path.suffix == ".png" and f"{path.stem}.webp" in names:
            budget = PHOTO_PNG_BUDGET
        if size > budget:
            problems.append(f"{path.name}: {size:,} bytes, budget {budget:,}")
        if _figure_name(path, style) in keep_opaque:
            continue
        found = (
            _svg_problems(path, width) if path.suffix == ".svg" else _raster_problems(path, width)
        )
        problems += [f"{path.name}: {problem}" for problem in found]
    problems += _language_problems(files, style)
    problems += _manifest_problems(directory, names, [t.name for t in style.themes])
    return problems


def _language_problems(files: Iterable[Path], style: Style) -> list[str]:
    """Every figure that exists in one language exists in all of them."""
    languages: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in files:
        match = _LANGUAGE.match(style.split(path.stem)[0])
        if match:
            languages[match["name"], path.suffix].add(match["language"])
    every = set().union(*languages.values()) if languages else set()
    return [
        f"{name}{suffix}: missing the {code} file {name}.{code}{suffix}"
        for (name, suffix), found in sorted(languages.items())
        for code in sorted(every - found)
    ]


def _manifest_problems(directory: Path, names: set[str], modes: Sequence[str]) -> list[str]:
    """``figures.json`` lists exactly the files of the directory, each with its texts.

    The file may be edited by hand, so every part of it is checked for its type and a broken
    part is reported instead of failing the check.
    """
    try:
        data = manifest.load(directory)
    except ValueError as error:
        return [f"{manifest.FILE}: not valid JSON, {error}"]
    if data is None:
        return []
    if not isinstance(data, dict):
        return [f"{manifest.FILE}: the top level is not an object"]
    codes = data.get("languages", [])
    figures = data.get("figures", [])
    if not isinstance(codes, list) or not all(isinstance(c, str) for c in codes):
        return [f"{manifest.FILE}: languages is not a list of codes"]
    if not isinstance(figures, list):
        return [f"{manifest.FILE}: figures is not a list"]
    problems = []
    listed: set[str] = set()
    for index, entry in enumerate(figures):
        problems += _entry_problems(entry, index, codes, names, listed, modes)
    page_files = {n for n in names if Path(n).suffix in (".svg", ".webp")}
    problems += [
        f"{file}: not in {manifest.FILE}, so the page has no alt text for it"
        for file in sorted(page_files - listed)
    ]
    return problems


def _entry_problems(
    entry: object,
    index: int,
    codes: list[str],
    names: set[str],
    listed: set[str],
    modes: Sequence[str],
) -> list[str]:
    """Problems of one figure in the manifest; adds the files it lists to ``listed``."""
    if not isinstance(entry, dict):
        return [f"{manifest.FILE}: figure {index + 1} is not an object"]
    name = entry.get("name") or f"figure {index + 1}"
    problems = []
    for code in codes:
        for key in ("title", "alt"):
            texts = entry.get(key)
            text = texts.get(code) if isinstance(texts, dict) else None
            if not isinstance(text, str) or not text.strip():
                problems.append(f"{manifest.FILE}: {name} has no {key} in {code}")
        every = entry.get("files")
        files = every.get(code) if isinstance(every, dict) else None
        if not isinstance(files, dict):
            problems.append(f"{manifest.FILE}: {name} has no files in {code}")
            continue
        for mode in modes:
            file = files.get(mode)
            if not isinstance(file, str):
                problems.append(f"{manifest.FILE}: {name} has no {mode} file in {code}")
                continue
            listed.add(file)
            if file not in names:
                problems.append(f"{manifest.FILE}: {name} lists {file}, which does not exist")
    return problems


def check_tokens(css: Path, style: Style | None = None) -> list[str]:
    """Colours of the figures that differ from the stylesheet of the website.

    Text and lines of the figures use the page colours of ``css``, a file with properties such
    as ``--color-text: light-dark(#1d1e22, #eceef3)``. A change on one side only shows as text in
    a figure that no longer matches the page around it. The first colour of ``light-dark`` is
    compared with the default theme of ``style``, the second with its pair; ``style.css`` names
    the properties.
    """
    style = style or DEFAULT
    if not style.css:
        return [f"{css.name}: the style names no custom properties, add css to its tokens"]
    pair = style.pairs.get(style.default)
    if pair is None:
        return [f"{css.name}: the default theme {style.default!r} has no pair for light-dark()"]
    themes = (style.theme(style.default), style.theme(pair))
    found = {
        m[1]: (m[2].lower(), m[3].lower()) for m in _CSS_COLOUR.finditer(css.read_text("utf-8"))
    }
    problems = []
    for prop, (key, index) in style.css.items():
        if prop not in found:
            problems.append(f"{css.name}: --color-{prop} is missing")
            continue
        for theme, colour in zip(themes, found[prop], strict=True):
            token = getattr(theme, key)
            value: str = token if index is None else token[index]
            mode = theme.name
            if value.lower() != colour:
                problems.append(
                    f"{css.name}: --color-{prop} is {colour} in {mode}, the figures use {value}"
                )
    return problems


def _svg_problems(path: Path, width: float | None) -> list[str]:
    text = path.read_text(encoding="utf-8")
    problems = []
    match = _BACKGROUND.search(text)
    if match and "fill: none" not in match.group(1):
        problems.append("opaque background, render with a transparent output")
    size = _SVG_WIDTH.search(text)
    if width is not None and size and abs(float(size.group(1)) - width * 72) > 0.1:
        problems.append(f"{float(size.group(1)):g} pt wide, the canvas is {width * 72:g} pt")
    return problems


def _raster_problems(path: Path, width: float | None) -> list[str]:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    problems = []
    corners = [(0, 0), (rgba.width - 1, 0), (0, rgba.height - 1), (rgba.width - 1, rgba.height - 1)]
    if any(rgba.getpixel(c)[3] != 0 for c in corners):  # type: ignore[index]
        problems.append("corners are not transparent")
    pixels = None if width is None else round(width * RASTER_DPI)
    if pixels is not None and abs(rgba.width - pixels) > 1:
        problems.append(f"{rgba.width} px wide, the canvas is {pixels} px")
    return problems
