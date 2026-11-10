"""Writing figures: file names, formats, sizes and reproducible metadata.

Every figure exists for a light and a dark page. The light file is ``<name>.<format>`` and the dark
one ``<name>-dark.<format>``, the convention of the portfolio's ``Figure`` component and of
``<picture>`` in a README. The default output :data:`WEB` writes a transparent SVG and a
transparent 250 dpi PNG of each, so the same file sits on any page colour of its mode.

Web outputs have a fixed canvas: every file is exactly 6.4 in wide, 1600 px as PNG. Pages scale
images to their column, so equal widths give the same text size in every figure, and titles start
at the same left edge. A narrower drawing leaves empty space on the right.
"""

import io
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from itertools import groupby
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.transforms import Bbox
from PIL import Image

from figkit.theme import THEMES, Theme, styled

Draw = Callable[[Theme], Figure]


@dataclass(frozen=True, slots=True)
class Output:
    """How a figure is written.

    Attributes:
        format: ``svg``, ``png`` or ``webp``.
        transparent: Leave the background empty instead of filling it with the theme surface.
        width: Width of the canvas in inches. With ``tight``, the file is exactly this wide: a
            drawing that sticks out is narrowed until it fits, a smaller one is padded on the
            right. Without ``tight``, a wider figure is scaled down to it.
        pixels: Width of a raster image in pixels; without it, ``dpi`` decides.
        dpi: Resolution of raster formats when ``pixels`` is not set.
        tight: Crop to the drawn content plus a small margin. Off for fixed sizes such as a
            social card, whose pixel size must not change.
    """

    format: str
    transparent: bool = True
    width: float | None = None
    pixels: int | None = None
    dpi: float = 150
    tight: bool = True


# 6.4 inches shown in a column of 800 CSS pixels enlarge 9 pt text to about 15 px. Every web file
# has this width, so the text has this size in every figure; at 250 dpi a PNG is 1600 pixels wide,
# sharp at twice that column.
WEB_WIDTH = 6.4
RASTER_DPI = 250
SVG = Output("svg", width=WEB_WIDTH)
PNG = Output("png", width=WEB_WIDTH, dpi=RASTER_DPI)
WEB = (SVG, PNG)
# Photographs and heatmaps over images: SVG would embed them as a large raster anyway.
PHOTO = (Output("webp", width=WEB_WIDTH, dpi=RASTER_DPI), PNG)
# Open Graph and LinkedIn previews are opaque and exactly 1200 x 630 pixels.
CARD_INCHES = (8.0, 4.2)
CARD = (Output("png", transparent=False, dpi=150, tight=False),)
PAD = 0.15

# Metadata without dates or versions, so that the files change only with their content.
_SAVE_OPTIONS: dict[str, dict[str, Any]] = {
    "svg": {"metadata": {"Date": None, "Creator": None}},
}


def path_for(directory: Path, name: str, theme: Theme, output: Output) -> Path:
    """File of one figure in one theme and format."""
    suffix = "-dark" if theme.name == "dark" else ""
    return directory / f"{name}{suffix}.{output.format}"


def save(figure: Figure, path: Path, output: Output) -> Path:
    """Write the figure to ``path`` in the given output; the figure stays open."""
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = figure.get_size_inches()
    bbox: Bbox | str | None = None
    if output.tight and output.width is not None:
        bbox = canvas(figure, output.width)
    elif output.width is not None and width > output.width:
        figure.set_size_inches(output.width, height * output.width / width)
    if output.tight and bbox is None:
        bbox = "tight"
    dpi = output.dpi
    if output.pixels is not None:
        if isinstance(bbox, Bbox):
            drawn = bbox.width
        elif bbox == "tight":
            figure.draw_without_rendering()
            drawn = figure.get_tightbbox().width + 2 * PAD
        else:
            drawn = figure.get_figwidth()
        dpi = output.pixels / drawn
    options: dict[str, Any] = {"bbox_inches": bbox, "pad_inches": PAD} if bbox is not None else {}
    if output.format == "svg":
        # Saving to a path opens the file in text mode, which writes CRLF on Windows. A binary
        # buffer keeps LF, so the files are byte-identical on every platform.
        svg = io.BytesIO()
        figure.savefig(
            svg, format="svg", transparent=output.transparent, **options, **_SAVE_OPTIONS["svg"]
        )
        path.write_bytes(svg.getvalue())
        return path
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi, transparent=output.transparent, **options)
    buffer.seek(0)
    with Image.open(buffer) as image:
        _write_raster(image, path, output)
    return path


def canvas(figure: Figure, width: float, pad: float = PAD) -> Bbox:
    """Box of exactly ``width`` inches around the drawn content, starting at its left edge.

    Text keeps its size when the figure gets narrower, so a drawing that sticks out is narrowed
    by the excess and measured again, a few times until it fits. The height follows the content.

    Raises:
        ValueError: If the content cannot be fitted, for example a fixed text wider than the canvas.
    """
    for _ in range(8):
        figure.draw_without_rendering()
        box = figure.get_tightbbox().padded(pad)
        excess = box.width - width
        # Up to a fortieth of an inch of the margin may be cut, the padding absorbs it.
        if excess <= pad / 6:
            return Bbox.from_extents(box.x0, box.y0, box.x0 + width, box.y1)
        w, h = figure.get_size_inches()
        if w - excess <= 1:
            break
        # Only the axes shrink with the figure, so step a little further than the excess.
        figure.set_size_inches(w - 1.25 * excess, h)
    msg = f"the drawing is {box.width:.2f} in wide and does not fit a canvas of {width} in"
    raise ValueError(msg)


def _write_raster(image: Image.Image, path: Path, output: Output) -> None:
    rgba = image.convert("RGBA")
    if output.pixels is not None and rgba.width != output.pixels:
        # The tight box is measured before the final draw, so the width can be off by a pixel.
        height = round(rgba.height * output.pixels / rgba.width)
        rgba = rgba.resize((output.pixels, height), Image.Resampling.LANCZOS)
    if output.format == "webp":
        rgba.save(path, format="webp", quality=88, method=6)
        return
    # A 256-colour palette with alpha makes the PNG several times smaller; Pillow writes no date
    # or version into it.
    palette(rgba).save(path, format="png", optimize=True)


# Palette entries of fully opaque pixels; the rest hold the semi-transparent edges of text and lines
# and, in the last entry, the empty background.
_SOLID = 224
_CLEAR = 255


def palette(rgba: Image.Image) -> Image.Image:
    """The image in at most 256 colours with alpha, without visible banding in photographs.

    Pillow's only RGBA quantiser, the fast octree, keeps a few dozen greys of a photograph, which
    shows as contour lines. So the opaque pixels get a median-cut palette of their own, and only
    the semi-transparent pixels, the anti-aliased edges on the empty background, use the octree.
    """
    data = np.asarray(rgba.convert("RGBA"))
    alpha = data[..., 3]
    solid = alpha == 255
    edges = (alpha > 0) & ~solid
    index = np.full(alpha.shape, _CLEAR, dtype=np.uint8)
    colours: list[int] = []
    alphas: list[int] = []
    if solid.any():
        # The other pixels take the colour of an opaque one, so they use no palette entries.
        # Quantising the image itself keeps full precision; mapping it onto a given palette
        # would round to 6 bits per channel.
        rgb = data[..., :3].copy()
        rgb[~solid] = data[..., :3][solid][0]
        solid_palette = Image.fromarray(rgb).quantize(
            _SOLID, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        )
        index[solid] = np.asarray(solid_palette)[solid]
        colours = _entries(solid_palette.getpalette() or [], 3, _SOLID)
        alphas = [255] * _SOLID
    offset = len(alphas)
    free = _CLEAR - offset
    if edges.any():
        sample = Image.fromarray(np.ascontiguousarray(data[edges].reshape(-1, 1, 4)), "RGBA")
        edge_palette = sample.quantize(
            free, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE
        )
        index[edges] = offset + np.asarray(edge_palette).reshape(-1)
        rgba_entries = _entries(edge_palette.getpalette(rawmode="RGBA") or [], 4, free)
        for i in range(free):
            colours += rgba_entries[4 * i : 4 * i + 3]
            alphas.append(rgba_entries[4 * i + 3])
    colours += [0] * (3 * _CLEAR - len(colours)) + [0, 0, 0]
    alphas += [0] * (_CLEAR - len(alphas)) + [0]
    result = Image.fromarray(index, "P")
    result.putpalette(colours)
    result.info["transparency"] = bytes(alphas)
    return result


def _entries(values: list[int], channels: int, count: int) -> list[int]:
    """The first ``count`` palette entries, padded with zeros."""
    values = values[: channels * count]
    return values + [0] * (channels * count - len(values))


def render(
    directory: Path,
    name: str,
    draw: Draw,
    outputs: Sequence[Output] = WEB,
    themes: Sequence[Theme] = THEMES,
) -> list[Path]:
    """Draw one figure in every theme and write it in every output.

    ``draw`` receives the theme and returns a new figure. For transparent outputs its surface is
    ``none``, so fills that use ``theme.surface`` as a gap colour become empty as well. The figure
    is drawn once per theme and transparency and closed after writing.

    Returns:
        The written files, in the order of ``themes`` and then ``outputs``.
    """
    paths: list[Path] = []
    for theme in themes:
        for transparent, group in groupby(outputs, key=lambda o: o.transparent):
            used = replace(theme, surface="none") if transparent else theme
            with styled(used), plt.rc_context({"svg.hashsalt": name}):
                figure = draw(used)
                try:
                    paths.extend(
                        save(figure, path_for(directory, name, theme, output), output)
                        for output in group
                    )
                except ValueError as error:
                    error.add_note(f"while writing figure {name!r} in the {theme.name} theme")
                    raise
                finally:
                    plt.close(figure)
    return paths
