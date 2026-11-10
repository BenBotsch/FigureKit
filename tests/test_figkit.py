import re
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pytest
from matplotlib.figure import Figure
from PIL import Image

import figkit
from figkit.check import BUDGET, PHOTO_PNG_BUDGET, check
from figkit.cli import main
from figkit.export import PAD, palette
from figkit.theme import FONTS


def chart(theme: figkit.Theme, width: float = 6.4) -> Figure:
    figure, ax = plt.subplots(figsize=(width, 3.0))
    bars = ax.bar(["a", "b", "c"], [0.2, 0.5, 0.9], color=theme.series[0])
    figkit.bar_labels(ax, bars, theme)
    figkit.reference_line(ax, 0.5, "target", theme, axis="y")
    figkit.title(ax, "Example", theme, subtitle="three bars")
    return figure


def narrow(theme: figkit.Theme) -> Figure:
    return chart(theme, width=3.2)


def relative_luminance(colour: str) -> float:
    def channel(value: int) -> float:
        c = value / 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(int(colour[i : i + 2], 16)) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    high, low = sorted((relative_luminance(a), relative_luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def test_fonts_resolve_to_the_bundled_files() -> None:
    sans, mono = figkit.register_fonts()

    assert (sans, mono) == ("Bricolage Grotesque", "JetBrains Mono")
    assert {p.name for p in FONTS.glob("OFL-*.txt")} == {
        "OFL-BricolageGrotesque.txt",
        "OFL-JetBrainsMono.txt",
    }


def test_render_writes_a_transparent_svg_and_png_per_theme(tmp_path: Path) -> None:
    paths = figkit.render(tmp_path, "example", chart)

    assert [p.name for p in paths] == [
        "example.svg",
        "example.png",
        "example-dark.svg",
        "example-dark.png",
    ]
    for svg in tmp_path.glob("*.svg"):
        text = svg.read_text(encoding="utf-8")
        assert "<dc:date>" not in text
        assert "<text" not in text, "text must be stored as paths, so pages need no font"
    with Image.open(tmp_path / "example-dark.png") as image:
        rgba = image.convert("RGBA")
    assert rgba.getpixel((0, 0))[3] == 0  # type: ignore[index]
    assert check(tmp_path) == []


def test_the_dark_file_uses_the_dark_ink(tmp_path: Path) -> None:
    figkit.render(tmp_path, "example", chart, outputs=(figkit.SVG,))

    light = (tmp_path / "example.svg").read_text(encoding="utf-8")
    dark = (tmp_path / "example-dark.svg").read_text(encoding="utf-8")
    assert figkit.LIGHT.ink in light
    assert figkit.LIGHT.ink not in dark
    assert figkit.DARK.ink in dark


def test_svg_files_are_reproducible(tmp_path: Path) -> None:
    first = figkit.render(tmp_path / "a", "example", chart, outputs=(figkit.SVG,))
    second = figkit.render(tmp_path / "b", "example", chart, outputs=(figkit.SVG,))

    for a, b in zip(first, second, strict=True):
        assert a.read_bytes() == b.read_bytes()


def test_svg_files_end_lines_with_lf_on_every_platform(tmp_path: Path) -> None:
    paths = figkit.render(tmp_path, "example", chart, outputs=(figkit.SVG,))

    for path in paths:
        data = path.read_bytes()
        assert b"\n" in data
        assert b"\r\n" not in data


def test_png_width_follows_the_figure_width(tmp_path: Path) -> None:
    figkit.render(tmp_path, "wide", chart, outputs=(figkit.PNG,))
    figkit.render(tmp_path, "narrow", narrow, outputs=(figkit.PNG,))

    with Image.open(tmp_path / "wide.png") as wide, Image.open(tmp_path / "narrow.png") as small:
        # Cropped to the drawn content, so at most the full web width plus the margin.
        assert wide.width <= (figkit.WEB_WIDTH + 2 * PAD) * figkit.RASTER_DPI
        # Same text size in pixels, so a narrower figure gives a narrower image.
        assert small.width < wide.width * 0.6


def test_wider_figures_are_scaled_down_to_the_web_width(tmp_path: Path) -> None:
    def huge(theme: figkit.Theme) -> Figure:
        return chart(theme, width=12)

    figkit.render(tmp_path, "huge", huge, outputs=(figkit.SVG,))

    width = re.search(r'<svg[^>]* width="([\d.]+)pt"', (tmp_path / "huge.svg").read_text("utf-8"))
    assert width is not None
    assert float(width.group(1)) <= figkit.WEB_WIDTH * 72


def test_card_is_opaque_and_exactly_1200_by_630(tmp_path: Path) -> None:
    def card(theme: figkit.Theme) -> Figure:
        figure = plt.figure(figsize=figkit.CARD_INCHES)
        figure.text(0.1, 0.5, "card")
        return figure

    paths = figkit.render(tmp_path, "card", card, outputs=figkit.CARD)

    for path in paths:
        with Image.open(path) as image:
            assert image.size == (1200, 630)
            assert image.convert("RGBA").getpixel((0, 0))[3] == 255  # type: ignore[index]
    assert check(tmp_path) == []
    assert check(tmp_path, opaque=()) != []


def test_photo_output_writes_transparent_webp(tmp_path: Path) -> None:
    paths = figkit.render(tmp_path, "photo", chart, outputs=figkit.PHOTO)

    assert {p.suffix for p in paths} == {".webp", ".png"}
    assert check(tmp_path) == []


def test_png_palette_keeps_the_tones_of_a_photograph_and_its_soft_edges() -> None:
    # A grey ramp on an empty background with an anti-aliased border, like an image in a figure.
    ramp = np.tile(np.linspace(0, 255, 512).round().astype(np.uint8), (64, 1))
    rgba = np.zeros((80, 528, 4), dtype=np.uint8)
    rgba[8:72, 8:520, :3] = ramp[..., None]
    rgba[8:72, 8:520, 3] = 255
    rgba[7, 8:520] = (30, 30, 30, 96)

    result = np.asarray(palette(Image.fromarray(rgba, "RGBA")).convert("RGBA")).astype(int)

    inside = result[8:72, 8:520]
    assert np.abs(inside[..., :3] - rgba[8:72, 8:520, :3]).max() <= 4
    assert len(np.unique(inside[..., 0])) >= 200
    assert abs(result[7, 100, 3] - 96) <= 8
    assert result[0, 0, 3] == 0


def test_log_scale_labels_use_the_bundled_fonts(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    def log_chart(theme: figkit.Theme) -> Figure:
        figure, ax = plt.subplots(figsize=(4, 3))
        ax.plot([1, 2, 3], [1e-3, 1e-2, 1e-1], color=theme.series[0])
        ax.set_yscale("log")
        return figure

    # Hide the system fonts behind the generic families, as on a bare Linux runner.
    missing = ["No Such Font"]
    with plt.rc_context({"font.serif": missing, "font.cursive": missing, "font.fantasy": missing}):
        figkit.render(tmp_path, "log", log_chart, outputs=(figkit.SVG,), themes=(figkit.LIGHT,))

    assert not [r for r in caplog.records if "findfont" in r.getMessage()]


def test_check_allows_a_larger_png_next_to_a_photo(tmp_path: Path) -> None:
    for suffix in ("", "-dark"):
        noise = np.random.default_rng(0).integers(0, 255, (300, 400, 4), dtype=np.uint8)
        noise[..., 3] = 255
        noise[0, 0, 3] = noise[-1, -1, 3] = noise[0, -1, 3] = noise[-1, 0, 3] = 0
        Image.fromarray(noise, "RGBA").save(tmp_path / f"photo{suffix}.png")
    size = (tmp_path / "photo.png").stat().st_size
    assert BUDGET[".png"] < size < PHOTO_PNG_BUDGET

    assert any("budget" in p for p in check(tmp_path))
    for suffix in ("", "-dark"):
        with Image.open(tmp_path / f"photo{suffix}.png") as image:
            image.save(tmp_path / f"photo{suffix}.webp", quality=50)
    assert check(tmp_path) == []


def test_check_reports_missing_pairs_and_opaque_backgrounds(tmp_path: Path) -> None:
    figkit.render(tmp_path, "solid", chart, outputs=(figkit.Output("svg", transparent=False),))
    figkit.render(tmp_path, "single", chart, outputs=(figkit.SVG,), themes=(figkit.LIGHT,))

    problems = check(tmp_path)

    assert "single.svg: missing its pair single-dark.svg" in problems
    assert any(p.startswith("solid.svg: opaque background") for p in problems)


def test_cli_returns_non_zero_on_problems(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    figkit.render(tmp_path, "single", chart, outputs=(figkit.SVG,), themes=(figkit.LIGHT,))

    assert main(["check", str(tmp_path)]) == 1
    assert "missing its pair" in capsys.readouterr().err
    (tmp_path / "single.svg").unlink()
    assert main(["check", str(tmp_path)]) == 0
    assert main(["check", str(tmp_path / "absent")]) == 1


@pytest.mark.parametrize("theme", figkit.THEMES, ids=lambda t: t.name)
def test_text_colours_reach_wcag_contrast_on_every_page(theme: figkit.Theme) -> None:
    for page in theme.pages:
        assert contrast(theme.ink, page) >= 7
        assert contrast(theme.secondary, page) >= 4.5
        assert contrast(theme.muted, page) >= 3


def test_series_are_the_validated_palette() -> None:
    # Checked with the dataviz validator against both pages of each mode, see docs/style-guide.md.
    # Changing a colour means validating again and updating this snapshot.
    assert figkit.LIGHT.series == ("#2f5bd3", "#eb6834", "#1baf7a", "#eda100")
    assert figkit.DARK.series == ("#5b84ea", "#d95926", "#199e70", "#c98500")


def test_ink_on_picks_readable_text_for_a_fill() -> None:
    assert figkit.ink_on("#ffffff") == figkit.LIGHT.ink
    assert figkit.ink_on(figkit.LIGHT.ramp[-1]) == "#ffffff"
    assert figkit.hex_colour((1.0, 0.5, 0.0, 1.0)) == "#ff8000"


def test_reference_line_label_can_sit_left_of_a_vertical_line() -> None:
    figure, ax = plt.subplots()
    right = figkit.reference_line(ax, 0.5, "limit", figkit.LIGHT)
    left = figkit.reference_line(ax, 0.9, "limit", figkit.LIGHT, side="left")
    assert (right.get_horizontalalignment(), right.get_text()) == ("left", " limit")
    assert (left.get_horizontalalignment(), left.get_text()) == ("right", "limit ")
    plt.close(figure)
