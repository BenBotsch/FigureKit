"""Figures for a website: headless files per language and a ``figures.json`` that describes them.

A page shows the title and caption of a figure as text, in its own type and language, and needs
an alt text for each image. :func:`page` writes the figure without its title once per language,
and :func:`write` lists those files with their texts and sizes, so the website reads everything
from one file instead of copying texts out of a README::

    entries = [figkit.page(out, "f1", draw, {"en": Caption(...), "de": Caption(...)})]
    figkit.write_manifest(out, entries)
"""

import json
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Any

from matplotlib.figure import Figure
from PIL import Image

from figkit.export import RASTER_DPI, SVG, Output, path_for, render
from figkit.theme import DARK, LIGHT, Theme

FILE = "figures.json"
VERSION = 1

PageDraw = Callable[[str, Theme], Figure]

_SVG_SIZE = re.compile(r'<svg[^>]* width="([\d.]+)pt" height="([\d.]+)pt"')


@dataclass(frozen=True, slots=True)
class Caption:
    """Texts of a figure in one language.

    Attributes:
        title: Headline the page shows above the figure.
        alt: Alt text, what a reader who cannot see the image needs to know: the finding and the
            key numbers.
        subtitle: Line below the title, such as the data and the method.
    """

    title: str
    alt: str
    subtitle: str | None = None


def size(path: Path) -> tuple[float, float]:
    """Width and height of a figure file in points, read from the file."""
    if path.suffix == ".svg":
        match = _SVG_SIZE.search(path.read_text(encoding="utf-8"))
        if match is None:
            msg = f"{path.name}: no width and height in pt"
            raise ValueError(msg)
        return float(match.group(1)), float(match.group(2))
    with Image.open(path) as image:
        return image.width * 72 / RASTER_DPI, image.height * 72 / RASTER_DPI


def page(
    directory: Path,
    name: str,
    draw: PageDraw,
    captions: Mapping[str, Caption],
    outputs: Sequence[Output] = (SVG,),
) -> dict[str, Any]:
    """Write ``name`` without its title in each language of ``captions`` and describe it.

    ``draw`` receives the language and the theme. The first output is the one the page shows;
    for photographs pass :data:`figkit.PHOTO` and the page gets the WebP.

    Returns:
        The entry of the figure for :func:`write`.
    """
    for language in captions:
        render(directory, name, partial(draw, language), outputs, language=language, headless=True)
    return entry(directory, name, captions, outputs[0])


def entry(
    directory: Path, name: str, captions: Mapping[str, Caption], output: Output = SVG
) -> dict[str, Any]:
    """The entry of ``name`` for :func:`write`, from files that :func:`page` wrote earlier.

    For a figure whose drawing needs more than the others, such as a trained model, so that a
    separate step writes it: the manifest of all figures can still be written in one place.

    Raises:
        FileNotFoundError: If a file of a language in ``captions`` is missing.
    """
    files: dict[str, dict[str, Any]] = {}
    for language in captions:
        light = path_for(directory, name, LIGHT, output, language)
        dark = path_for(directory, name, DARK, output, language)
        for path in (light, dark):
            if not path.is_file():
                msg = f"{path.name} is missing; write the figure with page() first"
                raise FileNotFoundError(msg)
        width, height = size(light)
        files[language] = {
            "light": light.name,
            "dark": dark.name,
            "width": round(width, 1),
            "height": round(height, 1),
        }
    return {
        "name": name,
        "title": {code: c.title for code, c in captions.items()},
        "subtitle": {code: c.subtitle for code, c in captions.items() if c.subtitle},
        "alt": {code: c.alt for code, c in captions.items()},
        "files": files,
    }


def write(directory: Path, entries: Sequence[Mapping[str, Any]]) -> Path:
    """Write ``figures.json`` with the entries of :func:`page`, in their order.

    Raises:
        ValueError: If the entries differ in their languages or a name occurs twice.
    """
    names = [entry["name"] for entry in entries]
    if len(set(names)) != len(names):
        msg = f"figure names occur twice: {sorted({n for n in names if names.count(n) > 1})}"
        raise ValueError(msg)
    languages = sorted({code for entry in entries for code in entry["files"]})
    for entry in entries:
        if sorted(entry["files"]) != languages:
            msg = f"figure {entry['name']!r} is not in every language of {languages}"
            raise ValueError(msg)
    manifest = {"version": VERSION, "languages": languages, "figures": list(entries)}
    path = directory / FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    # Bytes, so the file ends lines with LF on every platform.
    text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))
    return path


def load(directory: Path) -> dict[str, Any] | None:
    """The manifest of ``directory``, or ``None`` if it has none."""
    path = directory / FILE
    if not path.is_file():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return data
