"""Writing figures: file names, formats, sizes and reproducible metadata.

Every figure exists for a light and a dark page. The light file is ``<name>.<format>`` and the dark
one ``<name>-dark.<format>``, the convention of the portfolio's ``Figure`` component and of
``<picture>`` in a README. The default output :data:`WEB` writes a transparent SVG and a
transparent 250 dpi PNG of each, so the same file sits on any page colour of its mode.

Web outputs have a fixed canvas: every file is exactly 6.4 in wide, 1600 px as PNG. Pages scale
images to their column, so equal widths give the same text size in every figure, and titles start
at the same left edge. A narrower drawing leaves empty space on the right.
"""

import base64
import hashlib
import io
import re
import struct
import zlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace
from itertools import groupby
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.figure import Figure
from matplotlib.text import Text
from matplotlib.transforms import Bbox
from PIL import Image

from figkit.language import localize_ticks, speaking
from figkit.theme import DEFAULT, TYPE, Style, Theme, styled

Draw = Callable[[Theme], Figure]


@dataclass(frozen=True, slots=True)
class Output:
    """How a figure is written.

    Attributes:
        format: ``svg``, ``png`` or ``webp``.
        transparent: Leave the background empty instead of filling it with the theme surface.
        width: Width of the canvas in inches. With ``tight``, the file is exactly this wide: a
            drawing that sticks out is narrowed until it fits, a smaller one is padded on the
            right. Without ``tight``, a wider figure is resized to this width; text keeps its size.
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


def path_for(
    directory: Path,
    name: str,
    theme: Theme,
    output: Output,
    language: str | None = None,
    style: Style | None = None,
) -> Path:
    """File of one figure in one theme and format, ``<name>[.<language>][-<theme>].<format>``.

    The default theme of ``style``, light in the bundled one, has no suffix. Every other theme
    gets its name as the suffix, ``-dark``, so that two themes never write the same file.
    """
    stem = f"{name}.{language}" if language else name
    suffix = (style or DEFAULT).suffix(theme.name)
    return directory / f"{stem}{suffix}.{output.format}"


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
        path.write_bytes(_portable_images(svg.getvalue()))
        return path
    buffer = io.BytesIO()
    figure.savefig(buffer, format="png", dpi=dpi, transparent=output.transparent, **options)
    buffer.seek(0)
    with Image.open(buffer) as image:
        _write_raster(image, path, output)
    return path


# An image that matplotlib embeds in an SVG, with the id it derives from the PNG bytes.
_EMBEDDED = re.compile(rb'data:image/png;base64,\n([A-Za-z0-9+/=]+)"(?: id="(image[0-9a-f]{10})")?')
_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _portable_images(svg: bytes) -> bytes:
    """The SVG with every embedded PNG written again by :func:`_png`.

    matplotlib embeds images, such as a heatmap drawn with ``imshow``, as PNGs that Pillow
    compresses with the zlib of its build. Linux and Windows builds compress the same pixels to
    different bytes, and matplotlib derives the image id from them. Writing the PNG again with
    Python's zlib and deriving the id from that PNG keeps the file the same on every platform.
    """

    def rewrite(match: re.Match[bytes]) -> bytes:
        with Image.open(io.BytesIO(base64.b64decode(match[1]))) as image:
            png = _png(np.asarray(image.convert("RGBA")))
        text = b"data:image/png;base64,\n" + base64.b64encode(png) + b'"'
        if match[2] is None:
            return text
        salt = str(plt.rcParams["svg.hashsalt"] or "").encode()
        return text + b' id="image' + hashlib.sha256(salt + png).hexdigest()[:10].encode() + b'"'

    return _EMBEDDED.sub(rewrite, svg)


def _png(rgba: np.ndarray[Any, np.dtype[np.uint8]]) -> bytes:
    """An 8-bit RGBA PNG of ``rgba`` without metadata, every row with the filter ``Up``."""
    height, width = rgba.shape[:2]
    rows = rgba.reshape(height, width * 4).astype(np.int16)
    # Up stores each row as its difference to the row above, which turns the flat cells of a
    # heatmap into runs of zeros; the first row is compared with zeros.
    up = (rows - np.vstack([np.zeros_like(rows[:1]), rows[:-1]])) % 256
    raw = np.hstack([np.full((height, 1), 2), up]).astype(np.uint8).tobytes()

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data))
        )

    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        _PNG_SIGNATURE
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


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


def check_text(figure: Figure, minimum: float | None = None) -> None:
    """Fail on visible text below the smallest size of the style, which pages make unreadable.

    Raises:
        ValueError: If a text is smaller than ``minimum``, by default the minimum of the bundled
            style.
    """
    if minimum is None:
        minimum = TYPE.minimum
    for text in figure.findobj(Text):
        size = float(text.get_fontsize())
        if text.get_visible() and text.get_text().strip() and size < minimum:
            msg = f"text {text.get_text()!r} is {size:g} pt, the minimum is {minimum:g}"
            raise ValueError(msg)


def render(
    directory: Path,
    name: str,
    draw: Draw,
    outputs: Sequence[Output] = WEB,
    themes: Sequence[Theme] | None = None,
    *,
    language: str | None = None,
    headless: bool = False,
    style: Style | None = None,
) -> list[Path]:
    """Draw one figure in every theme and write it in every output.

    ``draw`` receives the theme and returns a new figure. For transparent outputs its surface is
    ``none``, so fills that use ``theme.surface`` as a gap colour become empty as well. The figure
    is drawn once per theme and transparency and closed after writing.

    Args:
        directory: Folder of the files.
        name: Name of the figure, the start of every file name.
        draw: Function of the theme that returns a new figure.
        outputs: Formats to write.
        themes: Themes to draw, by default all themes of ``style``.
        language: Code such as ``de``. It goes into the file names, ``<name>.de.svg``, and
            :func:`figkit.language` returns it while ``draw`` runs; numeric tick labels and
            :func:`figkit.number` follow it. Without it the figure is English and unmarked.
        headless: Leave out the title and subtitle of :func:`figkit.title`, for a page that
            shows them as text.
        style: Style that names the files, see :func:`path_for`; by default the bundled one.

    Returns:
        The written files, in the order of ``themes`` and then ``outputs``.

    Raises:
        ValueError: If the drawing does not fit the canvas or has text below the minimum size;
            the message names the figure.
    """
    style = style or DEFAULT
    paths: list[Path] = []
    for theme in style.themes if themes is None else themes:
        for transparent, group in groupby(outputs, key=lambda o: o.transparent):
            used = replace(theme, surface="none") if transparent else theme
            with (
                styled(used),
                plt.rc_context({"svg.hashsalt": name}),
                speaking(language, without_title=headless),
            ):
                figure = draw(used)
                try:
                    localize_ticks(figure, language or "en")
                    check_text(figure, theme.type.minimum)
                    paths.extend(
                        save(
                            figure,
                            path_for(directory, name, theme, output, language, style),
                            output,
                        )
                        for output in group
                    )
                except ValueError as error:
                    error.add_note(f"while writing figure {name!r} in the {theme.name} theme")
                    raise
                finally:
                    plt.close(figure)
    return paths
