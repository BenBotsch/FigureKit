import json
import warnings
from dataclasses import replace
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure
from matplotlib.mathtext import MathTextParser

import figkit
from figkit.theme import TOKENS, rc, register_fonts, styled


def bundled() -> dict[str, Any]:
    data: dict[str, Any] = json.loads(TOKENS.read_text(encoding="utf-8"))
    return data


def problems(data: object) -> tuple[str, ...]:
    with pytest.raises(figkit.StyleError) as error:
        figkit.parse_style(data)
    return error.value.problems


def fonts_of(formula: str, theme: figkit.Theme = figkit.LIGHT) -> dict[str, str]:
    """File name of the font of each character that mathtext sets for ``formula``."""
    with styled(theme):
        glyphs = MathTextParser("path").parse(formula, 72).glyphs
    return {chr(glyph[2]): Path(str(glyph[0].fname)).name for glyph in glyphs}


def test_variables_are_italic_and_not_the_upright_text_font() -> None:
    fonts = fonts_of(r"$x_i$")

    assert fonts == {"x": "DejaVuSans-Oblique.ttf", "i": "DejaVuSans-Oblique.ttf"}


def test_greek_letters_and_operators_are_sans_serif() -> None:
    fonts = fonts_of(r"$\alpha \leq \beta$")

    alpha, beta = "\N{GREEK SMALL LETTER ALPHA}", "\N{GREEK SMALL LETTER BETA}"
    assert fonts[alpha] == fonts[beta] == "DejaVuSans-Oblique.ttf"
    assert not any(name.startswith(("cm", "STIXGeneral")) for name in fonts.values())


def test_numbers_in_formulas_keep_the_text_font() -> None:
    fonts = fonts_of(r"$10^{2}$")

    assert set(fonts.values()) == {"BricolageGrotesque-Regular.ttf"}


def test_the_bundled_style_names_its_math_fonts() -> None:
    assert figkit.TYPE.math_italic == "DejaVu Sans"
    assert figkit.TYPE.math_fallback == "stixsans"


def test_a_style_without_math_uses_the_defaults() -> None:
    data = bundled()
    del data["font"]["math"]

    style = figkit.parse_style(data)

    assert style.type.math_italic == "DejaVu Sans"
    assert style.type.math_fallback == "stixsans"


def test_a_style_chooses_its_math_fonts() -> None:
    data = bundled()
    data["font"]["math"] = {"fallback": "cm"}

    style = figkit.parse_style(data)

    assert style.type.math_fallback == "cm"
    assert style.type.math_italic == "DejaVu Sans"
    assert rc(style.themes[0])["mathtext.fallback"] == "cm"


@pytest.mark.parametrize(
    ("math", "problem"),
    [
        ("DejaVu Sans", "font.math: must be an object"),
        ({"italic": ""}, "font.math.italic: must be a family name"),
        ({"fallback": "dejavusans"}, "font.math.fallback: must be one of cm, stix, stixsans"),
        ({"bold": "X"}, "font.math.bold: unknown key"),
    ],
)
def test_invalid_math_fonts_are_style_errors(math: object, problem: str) -> None:
    data = bundled()
    data["font"]["math"] = math

    assert problem in problems(data)


def test_a_math_italic_without_an_italic_face_fails() -> None:
    upright = replace(figkit.TYPE, math_italic="Bricolage Grotesque")

    with pytest.raises(RuntimeError, match="has no italic face"):
        register_fonts(upright)


def test_a_formula_with_a_missing_glyph_fails_before_any_file(tmp_path: Path) -> None:
    def chart(theme: figkit.Theme) -> Figure:
        figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
        ax.set_xlabel("$丐$")
        return figure

    with pytest.raises(ValueError, match=r"missing glyphs: .*U\+4e10") as error:
        figkit.render(tmp_path, "cjk", chart, (figkit.SVG,), (figkit.LIGHT,))

    assert "while writing figure 'cjk' in the light theme" in error.value.__notes__
    assert not list(tmp_path.iterdir())


def test_plain_text_with_a_missing_glyph_fails(tmp_path: Path) -> None:
    def chart(theme: figkit.Theme) -> Figure:
        figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
        ax.set_title("丑")
        return figure

    with pytest.raises(ValueError, match="missing from font"):
        figkit.render(tmp_path, "cjk", chart, (figkit.SVG,), (figkit.LIGHT,))


def test_a_complete_formula_renders(tmp_path: Path) -> None:
    def chart(theme: figkit.Theme) -> Figure:
        figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
        ax.plot([0, 1], [0, 1], color=theme.series[0])
        ax.set_xlabel(r"step $t$, rate $\alpha = 10^{-3}$")
        ax.set_ylabel(r"$\hat{p}_i$")
        return figure

    paths = figkit.render(tmp_path, "formula", chart, (figkit.SVG,))

    assert [path.name for path in paths] == ["formula.svg", "formula-dark.svg"]


def test_complete_glyphs_passes_other_warnings_through() -> None:
    with pytest.warns(UserWarning, match="unrelated"), figkit.complete_glyphs():
        warnings.warn("unrelated", UserWarning, stacklevel=1)
