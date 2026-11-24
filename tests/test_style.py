import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pytest
from fontTools.ttLib import TTFont
from matplotlib.figure import Figure

import figkit
from figkit.check import check, check_tokens
from figkit.theme import FONTS, TOKENS


def rename(font: TTFont, family: str, style: str) -> None:
    """``rename`` of ``scripts/build_fonts.py``, which gave the bundled fonts their names."""
    path = Path(__file__).resolve().parents[1] / "scripts" / "build_fonts.py"
    spec = importlib.util.spec_from_file_location("build_fonts", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.rename(font, family, style)


def bundled() -> dict[str, Any]:
    return copy.deepcopy(figkit.tokens())


def version_1() -> dict[str, Any]:
    """The bundled tokens in the format before 0.4: no version, pairs, default or css."""
    data = bundled()
    for key in ("$schema", "version", "default", "css"):
        data.pop(key)
    for theme in data["themes"].values():
        theme.pop("pair")
    return data


def write(path: Path, data: object) -> Path:
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def problems(data: object) -> tuple[str, ...]:
    with pytest.raises(figkit.StyleError) as error:
        figkit.parse_style(data)
    return error.value.problems


def test_the_default_style_is_the_bundled_tokens() -> None:
    style = figkit.DEFAULT

    assert style.source == TOKENS
    assert style.themes == figkit.THEMES == (figkit.LIGHT, figkit.DARK)
    assert style.default == "light"
    assert dict(style.pairs) == {"light": "dark", "dark": "light"}
    assert style.type == figkit.TYPE
    assert style.theme("dark") is figkit.DARK


def test_version_1_reads_as_the_same_style() -> None:
    old = figkit.parse_style(version_1())

    assert old.themes == figkit.DEFAULT.themes
    assert old.default == "light"
    assert dict(old.pairs) == dict(figkit.DEFAULT.pairs)
    assert dict(old.css) == dict(figkit.DEFAULT.css)


def test_a_style_with_three_themes(tmp_path: Path) -> None:
    data = bundled()
    data["themes"]["print"] = copy.deepcopy(data["themes"]["light"])
    del data["themes"]["print"]["pair"]
    data["themes"]["print"]["series"] = ["#000000", "#555555"]

    style = figkit.load_style(write(tmp_path / "tokens.json", data))

    assert [t.name for t in style.themes] == ["light", "dark", "print"]
    assert style.theme("print").series == ("#000000", "#555555")
    assert "print" not in style.pairs
    assert style.source == tmp_path / "tokens.json"
    with pytest.raises(KeyError, match="no theme 'sepia'"):
        style.theme("sepia")


def copy_font(source: Path, target: Path, family: str) -> None:
    """A copy of a bundled font under another family name, like a project's own font."""
    font = TTFont(source)
    rename(font, family, "SemiBold" if "SemiBold" in source.stem else "Regular")
    font.save(target)


def test_a_style_brings_its_own_font_files(tmp_path: Path) -> None:
    # matplotlib knows one file per family and process, so the fonts get names of their own.
    fonts = tmp_path / "fonts"
    fonts.mkdir()
    for path in FONTS.glob("*.ttf"):
        family = "Test Mono" if "Mono" in path.stem else "Test Sans"
        copy_font(path, fonts / path.name, family)
    data = bundled()
    data["font"].update(sans="Test Sans", mono="Test Mono", files=["fonts/*.ttf"])

    style = figkit.load_style(write(tmp_path / "tokens.json", data))

    assert [p.parent for p in style.type.files] == [fonts] * 4
    assert figkit.register_fonts(style.type) == ("Test Sans", "Test Mono")
    rc = figkit.rc(style.theme("light"))
    assert rc["font.sans-serif"] == ["Test Sans"]
    assert rc["font.monospace"] == ["Test Mono"]


def test_a_family_that_resolves_to_another_file_fails(tmp_path: Path) -> None:
    data = bundled()
    data["font"]["sans"] = "DejaVu Sans"
    style = figkit.parse_style(data)

    with pytest.raises(RuntimeError, match="'DejaVu Sans' resolved to"):
        figkit.register_fonts(style.type)


def test_a_theme_of_a_loaded_style_renders_with_its_type(tmp_path: Path) -> None:
    data = bundled()
    data["font"]["minimum"] = 8.5
    data["font"]["annotation"] = 8.5
    style = figkit.parse_style(data)

    def chart(theme: figkit.Theme) -> Figure:
        figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
        figkit.value(ax, 0.5, 0.5, "1", theme)
        ax.text(0.2, 0.2, "small", fontsize=8)
        return figure

    figkit.render(tmp_path, "ok", chart, (figkit.SVG,), (figkit.LIGHT,))
    with pytest.raises(ValueError, match=r"minimum is 8.5"):
        figkit.render(tmp_path, "strict", chart, (figkit.SVG,), style.themes)


def test_load_style_rejects_a_file_that_is_not_json(tmp_path: Path) -> None:
    path = tmp_path / "tokens.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(figkit.StyleError, match="not JSON"):
        figkit.load_style(path)


def test_font_files_that_match_nothing_fail(tmp_path: Path) -> None:
    data = bundled()
    data["font"]["files"] = ["missing/*.ttf"]

    with pytest.raises(figkit.StyleError, match=r"'missing/\*\.ttf' matches no file"):
        figkit.load_style(write(tmp_path / "tokens.json", data))


def test_every_problem_is_listed_with_its_path() -> None:
    data = bundled()
    data["font"]["tick"] = 0
    data["font"]["annotaton"] = 8
    data["themes"]["dark"]["series"][2] = "blue"
    data["themes"]["dark"]["status"].pop("good")
    data["themes"]["light"]["inc"] = "#000000"
    data["default"] = "sepia"
    data["css"]["text"] = ["pages"]

    found = problems(data)

    assert set(found) == {
        "font.annotaton: unknown key",
        "font.tick: must be a positive size in pt",
        "themes.light.inc: unknown key",
        "themes.dark.series[2]: 'blue' is not a #rrggbb colour",
        "themes.dark.status: must have exactly good, warning, serious, critical",
        "default: 'sepia' is not a theme",
        "css.text: must be [colour token] or [list token, index]",
    }


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        (lambda d: d.update(version=3), "version: 3 is not 1 or 2"),
        (lambda d: d.update(themes={}), "themes: must be an object with at least one theme"),
        (lambda d: d["font"].update(annotation=7), "font.annotation: 7 is below font.minimum 8"),
        (lambda d: d["font"].update(mono=""), "font.mono: must be a family name"),
        (lambda d: d["font"].update(files="*.ttf"), "font.files: must be a list of glob patterns"),
        (
            lambda d: d["themes"]["light"].update(ramp=["#ffffff"]),
            "themes.light.ramp: must be a list of at least 2 colours",
        ),
        (
            lambda d: d["themes"]["light"].update(pair="sepia"),
            "themes.light.pair: 'sepia' is not another theme",
        ),
        (
            lambda d: d["themes"]["light"].update(pair="light"),
            "themes.light.pair: 'light' is not another theme",
        ),
        (
            lambda d: d["themes"]["dark"].pop("pair"),
            "themes.light.pair: 'dark' does not pair back with 'light'",
        ),
        (
            lambda d: d["themes"]["dark"]["series"].pop(),
            "themes.light.series: must be as long as in its pair 'dark'",
        ),
    ],
)
def test_invalid_tokens_are_rejected(change: Any, problem: str) -> None:
    data = bundled()
    change(data)

    assert problem in problems(data)


def test_version_1_keeps_its_two_themes_and_has_no_pairs() -> None:
    data = version_1()
    data["themes"]["light"]["pair"] = "dark"
    data["themes"]["print"] = data["themes"]["light"]

    found = problems(data)

    assert "themes.light.pair: needs version 2" in found
    assert "themes: version 1 has exactly light and dark; use version 2 for others" in found
    assert problems([]) == ("the file must hold a JSON object",)


def test_the_schema_knows_the_keys_the_loader_knows() -> None:
    schema = json.loads((TOKENS.parent / "tokens.schema.json").read_text(encoding="utf-8"))
    theme = schema["$defs"]["theme"]
    font = schema["properties"]["font"]

    assert set(theme["properties"]) - {"$comment"} == set(bundled()["themes"]["light"])
    assert set(theme["required"]) == set(theme["properties"]) - {"$comment", "pair"}
    assert set(font["properties"]) - {"$comment", "files"} == set(bundled()["font"])
    assert set(schema["properties"]) - {"$comment"} == set(bundled()) - {"$comment"}


def three_themes(default: str = "light") -> figkit.Style:
    """Light and dark as a pair, and a print theme on its own."""
    data = bundled()
    data["themes"]["print"] = copy.deepcopy(data["themes"]["light"])
    del data["themes"]["print"]["pair"]
    data["default"] = default
    return figkit.parse_style(data)


def small(theme: figkit.Theme) -> Figure:
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
    ax.plot([0, 1], [0, 1], color=theme.series[0])
    return figure


def test_files_are_named_after_the_default_theme_of_the_style(tmp_path: Path) -> None:
    style = three_themes(default="dark")

    paths = figkit.render(tmp_path, "f", small, (figkit.SVG,), style=style)

    assert [p.name for p in paths] == ["f-light.svg", "f.svg", "f-print.svg"]
    assert style.split("f.de-print") == ("f.de", "print")
    assert style.split("f.de") == ("f.de", "dark")
    assert style.split("f-sepia") == ("f-sepia", "dark")


def test_check_pairs_only_the_themes_with_a_pair(tmp_path: Path) -> None:
    style = three_themes()
    figkit.render(tmp_path, "f", small, (figkit.SVG,), style=style)
    assert check(tmp_path, style=style) == []

    (tmp_path / "f-dark.svg").unlink()
    assert check(tmp_path, style=style) == ["f.svg: missing its pair f-dark.svg"]
    (tmp_path / "f.svg").unlink()
    assert check(tmp_path, style=style) == []


def test_the_manifest_lists_every_theme_of_the_style(tmp_path: Path) -> None:
    style = three_themes()
    captions = {"en": figkit.Caption("Title", "Alt text.")}

    entry = figkit.page(tmp_path, "f", lambda _, theme: small(theme), captions, style=style)
    figkit.write_manifest(tmp_path, [entry])

    files = entry["files"]["en"]
    assert (files["light"], files["dark"], files["print"]) == (
        "f.en.svg",
        "f.en-dark.svg",
        "f.en-print.svg",
    )
    assert check(tmp_path, style=style) == []
    (tmp_path / "f.en-print.svg").unlink()
    assert "figures.json: f lists f.en-print.svg, which does not exist" in check(
        tmp_path, style=style
    )


def test_check_tokens_follows_the_css_of_the_style(tmp_path: Path) -> None:
    css = tmp_path / "tokens.css"
    css.write_text("--color-ink: light-dark(#1d1e22, #ffffff);", encoding="utf-8")
    data = bundled()
    data["css"] = {"ink": ["ink"]}

    assert check_tokens(css, figkit.parse_style(data)) == [
        "tokens.css: --color-ink is #ffffff in dark, the figures use #eceef3"
    ]
    del data["css"]
    assert check_tokens(css, figkit.parse_style(data)) == [
        "tokens.css: the style names no custom properties, add css to its tokens"
    ]
    assert check_tokens(css, three_themes(default="print")) == [
        "tokens.css: the default theme 'print' has no pair for light-dark()"
    ]


def test_ink_on_takes_the_darkest_ink_of_the_style() -> None:
    data = bundled()
    data["themes"]["light"]["ink"] = "#000000"
    style = figkit.parse_style(data)

    assert figkit.ink_on("#ffffff") == figkit.LIGHT.ink
    assert figkit.ink_on("#ffffff", style) == "#000000"
    assert figkit.ink_on("#000000", style) == "#ffffff"


def test_version_1_defaults_to_light_whatever_the_order() -> None:
    data = version_1()
    data["themes"] = {"dark": data["themes"]["dark"], "light": data["themes"]["light"]}

    style = figkit.parse_style(data)

    assert style.default == "light"
    assert style.suffix("dark") == "-dark"
    assert style.suffix("light") == ""


def test_a_css_index_beyond_a_list_is_rejected() -> None:
    data = bundled()
    data["css"]["bg"] = ["pages", 9]

    assert "css.bg: themes.light.pages has no entry 9" in problems(data)
    assert "css.bg: themes.dark.pages has no entry 9" in problems(data)


def test_an_absolute_font_pattern_is_a_style_error(tmp_path: Path) -> None:
    data = bundled()
    pattern = str(tmp_path / "*.ttf")
    data["font"]["files"] = [pattern]

    assert f"font.files: {pattern!r} must be relative to the tokens file" in problems(data)
