"""Checks of a directory of figures, for CI: pairs, transparency and file sizes."""

import re
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

FORMATS = (".svg", ".png", ".webp")
# Bytes. Above these, a chart usually embeds a raster or far too many points.
BUDGET = {".svg": 150_000, ".png": 250_000, ".webp": 250_000}
# A PNG next to a WebP of the same name is the lossless copy of a photograph, which is larger.
PHOTO_PNG_BUDGET = 750_000
# The figure background is the first patch matplotlib writes into an SVG.
_BACKGROUND = re.compile(r'<g id="patch_1">\s*<path[^>]*style="([^"]*)"')


def _light_name(path: Path) -> str:
    return path.stem.removesuffix("-dark")


def check(directory: Path, opaque: Iterable[str] = ("card",)) -> list[str]:
    """Problems of the figures in ``directory``; an empty list means it passes.

    Args:
        directory: Folder with ``<name>.<format>`` and ``<name>-dark.<format>`` files.
        opaque: Figure names that are deliberately opaque, such as a social card.

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
        problem = _svg_problem(path) if path.suffix == ".svg" else _raster_problem(path)
        if problem:
            problems.append(f"{path.name}: {problem}")
    return problems


def _svg_problem(path: Path) -> str | None:
    match = _BACKGROUND.search(path.read_text(encoding="utf-8"))
    if match and "fill: none" not in match.group(1):
        return "opaque background, render with a transparent output"
    return None


def _raster_problem(path: Path) -> str | None:
    with Image.open(path) as image:
        rgba = image.convert("RGBA")
    corners = [(0, 0), (rgba.width - 1, 0), (0, rgba.height - 1), (rgba.width - 1, rgba.height - 1)]
    if any(rgba.getpixel(c)[3] != 0 for c in corners):  # type: ignore[index]
        return "corners are not transparent"
    return None
