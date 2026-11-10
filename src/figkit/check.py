"""Checks of a directory of figures, for CI: pairs, transparency, widths and file sizes."""

import re
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from figkit.export import RASTER_DPI, WEB_WIDTH

FORMATS = (".svg", ".png", ".webp")
# Bytes. Above these, a chart usually embeds a raster or far too many points.
BUDGET = {".svg": 150_000, ".png": 250_000, ".webp": 250_000}
# A PNG next to a WebP of the same name is the lossless copy of a photograph, which is larger.
PHOTO_PNG_BUDGET = 1_000_000
# The figure background is the first patch matplotlib writes into an SVG.
_BACKGROUND = re.compile(r'<g id="patch_1">\s*<path[^>]*style="([^"]*)"')
_SVG_WIDTH = re.compile(r'<svg[^>]* width="([\d.]+)pt"')


def _light_name(path: Path) -> str:
    return path.stem.removesuffix("-dark")


def check(
    directory: Path, opaque: Iterable[str] = ("card",), width: float | None = WEB_WIDTH
) -> list[str]:
    """Problems of the figures in ``directory``; an empty list means it passes.

    Args:
        directory: Folder with ``<name>.<format>`` and ``<name>-dark.<format>`` files.
        opaque: Figure names that are deliberately opaque, such as a social card. Their width
            is not checked either.
        width: Canvas width in inches that every other figure must have, so that pages show
            all of them with the same text size; ``None`` skips the check.

    Returns:
        One message per problem, with the file it concerns.
    """
    keep_opaque = set(opaque)
    files = sorted(p for p in directory.iterdir() if p.suffix in FORMATS and p.is_file())
    problems = []
    names = {p.name for p in files}
    for path in files:
        light = _light_name(path)
        partner = (
            f"{light}{path.suffix}" if path.stem.endswith("-dark") else f"{light}-dark{path.suffix}"
        )
        if partner not in names:
            problems.append(f"{path.name}: missing its pair {partner}")
        size, budget = path.stat().st_size, BUDGET[path.suffix]
        if path.suffix == ".png" and f"{path.stem}.webp" in names:
            budget = PHOTO_PNG_BUDGET
        if size > budget:
            problems.append(f"{path.name}: {size:,} bytes, budget {budget:,}")
        if light in keep_opaque:
            continue
        found = (
            _svg_problems(path, width) if path.suffix == ".svg" else _raster_problems(path, width)
        )
        problems += [f"{path.name}: {problem}" for problem in found]
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
