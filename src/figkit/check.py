"""Checks of figures for CI.

A directory is checked for light/dark and language pairs, transparency, widths, file sizes and
its ``figures.json``; a stylesheet for the page colours that the figures share with it.
"""

import re
from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from PIL import Image

from figkit import manifest
from figkit.export import RASTER_DPI, WEB_WIDTH
from figkit.theme import tokens

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
# Portfolio custom property and the figure token it equals in both themes: (key, list index).
CSS_TOKENS: dict[str, tuple[str, int | None]] = {
    "bg": ("pages", 0),
    "surface": ("surface", None),
    "text": ("ink", None),
    "muted": ("secondary", None),
    "border": ("grid", None),
    "border-strong": ("muted", None),
}
_CSS_COLOUR = re.compile(
    r"--color-([\w-]+):\s*light-dark\(\s*(#[0-9a-fA-F]{6})\s*,\s*(#[0-9a-fA-F]{6})"
)


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
    problems += _language_problems(files)
    problems += _manifest_problems(directory, names)
    return problems


def _language_problems(files: Iterable[Path]) -> list[str]:
    """Every figure that exists in one language exists in all of them."""
    languages: dict[tuple[str, str], set[str]] = defaultdict(set)
    for path in files:
        match = _LANGUAGE.match(_light_name(path))
        if match:
            languages[match["name"], path.suffix].add(match["language"])
    every = set().union(*languages.values()) if languages else set()
    return [
        f"{name}{suffix}: missing the {code} file {name}.{code}{suffix}"
        for (name, suffix), found in sorted(languages.items())
        for code in sorted(every - found)
    ]


def _manifest_problems(directory: Path, names: set[str]) -> list[str]:
    """``figures.json`` lists exactly the files of the directory, each with its texts."""
    data = manifest.load(directory)
    if data is None:
        return []
    problems = []
    listed: set[str] = set()
    codes = data.get("languages", [])
    for entry in data.get("figures", []):
        name = entry.get("name", "?")
        for code in codes:
            for key in ("title", "alt"):
                if not str(entry.get(key, {}).get(code, "")).strip():
                    problems.append(f"{manifest.FILE}: {name} has no {key} in {code}")
            files = entry.get("files", {}).get(code)
            if files is None:
                problems.append(f"{manifest.FILE}: {name} has no files in {code}")
                continue
            for mode in ("light", "dark"):
                file = files.get(mode)
                listed.add(file)
                if file not in names:
                    problems.append(f"{manifest.FILE}: {name} lists {file}, which does not exist")
    page_files = {n for n in names if Path(n).suffix in (".svg", ".webp")}
    problems += [
        f"{file}: not in {manifest.FILE}, so the page has no alt text for it"
        for file in sorted(page_files - listed)
    ]
    return problems


def check_tokens(css: Path) -> list[str]:
    """Colours of the figures that differ from the stylesheet of the website.

    Text and lines of the figures use the page colours of ``css``, a file with properties such
    as ``--color-text: light-dark(#1d1e22, #eceef3)``. A change on one side only shows as text in
    a figure that no longer matches the page around it.
    """
    found = {
        m[1]: (m[2].lower(), m[3].lower()) for m in _CSS_COLOUR.finditer(css.read_text("utf-8"))
    }
    themes = tokens()["themes"]
    problems = []
    for prop, (key, index) in CSS_TOKENS.items():
        if prop not in found:
            problems.append(f"{css.name}: --color-{prop} is missing")
            continue
        for mode, colour in zip(("light", "dark"), found[prop], strict=True):
            value = themes[mode][key] if index is None else themes[mode][key][index]
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
