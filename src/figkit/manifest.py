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

from figkit.export import SVG, Output, path_for, render
from figkit.theme import DEFAULT, Style, Theme

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


def size(path: Path, output: Output = SVG) -> tuple[float, float]:
    """Width and height of a figure file in points, read from the file.

    An SVG states its size. A raster image has only pixels, so ``output``, the output that wrote
    it, gives the resolution: its ``dpi``, or with ``pixels`` the fixed canvas ``width``.

    Raises:
        ValueError: If the SVG has no size in pt, or a raster output sets ``pixels`` without a
            fixed canvas, which leaves the resolution unknown.
    """
    if path.suffix == ".svg":
        match = _SVG_SIZE.search(path.read_text(encoding="utf-8"))
        if match is None:
            msg = f"{path.name}: no width and height in pt"
            raise ValueError(msg)
        return float(match.group(1)), float(match.group(2))
    with Image.open(path) as image:
        width, height = image.size
    if output.pixels is None:
        dpi = output.dpi
    elif output.width is not None and output.tight:
        dpi = width / output.width
    else:
        msg = f"{path.name}: pixels without a fixed canvas width leave the size unknown"
        raise ValueError(msg)
    return width * 72 / dpi, height * 72 / dpi


def page(
    directory: Path,
    name: str,
    draw: PageDraw,
    captions: Mapping[str, Caption],
    outputs: Sequence[Output] = (SVG,),
    style: Style | None = None,
) -> dict[str, Any]:
    """Write ``name`` without its title in each language of ``captions`` and describe it.

    ``draw`` receives the language and the theme, once per theme of ``style``. The first output
    is the one the page shows; for photographs pass :data:`figkit.PHOTO` and the page gets the
    WebP.

    Returns:
        The entry of the figure for :func:`write`.
    """
    for language in captions:
        render(
            directory,
            name,
            partial(draw, language),
            outputs,
            language=language,
            headless=True,
            style=style,
        )
    return entry(directory, name, captions, outputs[0], style)


def entry(
    directory: Path,
    name: str,
    captions: Mapping[str, Caption],
    output: Output = SVG,
    style: Style | None = None,
) -> dict[str, Any]:
    """The entry of ``name`` for :func:`write`, from files that :func:`page` wrote earlier.

    For a figure whose drawing needs more than the others, such as a trained model, so that a
    separate step writes it: the manifest of all figures can still be written in one place. The
    files of each language are listed under the names of the themes of ``style``, ``light`` and
    ``dark`` in the bundled one; the size is that of the default theme.

    Raises:
        FileNotFoundError: If a file of a language in ``captions`` is missing.
    """
    style = style or DEFAULT
    files: dict[str, dict[str, Any]] = {}
    for language in captions:
        paths = {
            theme.name: path_for(directory, name, theme, output, language, style)
            for theme in style.themes
        }
        for path in paths.values():
            if not path.is_file():
                msg = f"{path.name} is missing; write the figure with page() first"
                raise FileNotFoundError(msg)
        width, height = size(paths[style.default], output)
        files[language] = {
            **{theme: path.name for theme, path in paths.items()},
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


def load(directory: Path) -> object:
    """The parsed manifest of ``directory``, or ``None`` if it has none.

    The file may be edited by hand, so the result is any JSON value; :mod:`figkit.check` checks
    its structure.

    Raises:
        ValueError: If the file is not valid JSON.
    """
    path = directory / FILE
    if not path.is_file():
        return None
    data: object = json.loads(path.read_text(encoding="utf-8"))
    return data
