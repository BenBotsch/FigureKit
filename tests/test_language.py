import json
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import figkit
from figkit.check import check, check_tokens
from figkit.cli import main
from figkit.language import localize_ticks

CAPTIONS = {
    "en": figkit.Caption("Three bars", "Three bars from 20 % to 90 %.", "Example data"),
    "de": figkit.Caption("Drei Balken", "Drei Balken von 20 % bis 90 %.", "Beispieldaten"),
}


def chart(language: str, theme: figkit.Theme) -> Figure:
    figure, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.bar(["a", "b", "c"], [0.2, 0.5, 0.9], color=theme.series[0])
    figkit.percent(ax)
    figkit.title(ax, CAPTIONS[language].title, theme, subtitle=CAPTIONS[language].subtitle)
    return figure


@pytest.mark.parametrize(
    ("english", "german"),
    [
        ("0.781", "0,781"),
        ("1,447 correct", "1.447 correct"),
        ("1,447.5", "1.447,5"),
        ("95%", "95 %"),
        ("[0.72, 0.84]", "[0,72, 0,84]"),
        ("ResNet18 INT8 on AI4I 2020", "ResNet18 INT8 on AI4I 2020"),
        ("figkit v0.1.2", "figkit v0.1.2"),
        ("$10^{-2}$", "$10^{-2}$"),
    ],
)
def test_localize_writes_german_numbers_and_leaves_names(english: str, german: str) -> None:
    assert figkit.localize(english, "de") == german
    assert figkit.localize(english, "en") == english


def test_number_follows_the_language_of_render(tmp_path: Path) -> None:
    seen: dict[str, str] = {}

    def draw(theme: figkit.Theme) -> Figure:
        seen[figkit.language()] = figkit.number(1500.25, ",.1f")
        return chart("en", theme)

    figkit.render(tmp_path, "n", draw, (figkit.SVG,), (figkit.LIGHT,), language="de")
    figkit.render(tmp_path, "n", draw, (figkit.SVG,), (figkit.LIGHT,))

    assert seen == {"de": "1.500,2", "en": "1,500.2"}
    assert figkit.language() == "en"


def test_german_tick_labels_use_a_comma_and_a_spaced_percent_sign() -> None:
    figure, ax = plt.subplots()
    ax.plot([0, 1], [0, 1])
    figkit.percent(ax, "y")
    localize_ticks(figure, "de")

    assert ax.yaxis.get_major_formatter().format_ticks([0.5]) == ["50 %"]
    assert ax.xaxis.get_major_formatter().format_ticks([0.25, 0.5]) == ["0,25", "0,50"]
    plt.close(figure)


def test_render_names_files_by_language_and_drops_the_title_when_headless(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    titles: list[str] = []
    close = plt.close

    def keep_title(figure: Figure) -> None:
        titles.append(figure.axes[0].get_title(loc="left"))
        close(figure)

    monkeypatch.setattr(plt, "close", keep_title)
    paths = figkit.render(tmp_path, "bars", lambda t: chart("de", t), language="de", headless=True)
    figkit.render(tmp_path, "bars", lambda t: chart("en", t), themes=(figkit.LIGHT,))

    assert [p.name for p in paths] == [
        "bars.de.svg",
        "bars.de.png",
        "bars.de-dark.svg",
        "bars.de-dark.png",
    ]
    assert titles == ["", "", "Three bars"]
    assert figkit.headless() is False


def test_render_rejects_text_below_the_minimum_size(tmp_path: Path) -> None:
    def tiny(theme: figkit.Theme) -> Figure:
        figure = chart("en", theme)
        figure.axes[0].text(0, 0.5, "footnote", fontsize=6)
        return figure

    with pytest.raises(ValueError, match="'footnote' is 6 pt") as error:
        figkit.render(tmp_path, "tiny", tiny)
    assert "while writing figure 'tiny'" in str(error.value.__notes__)


def test_page_and_manifest_describe_every_file(tmp_path: Path) -> None:
    entry = figkit.page(tmp_path, "bars", chart, CAPTIONS)
    path = figkit.write_manifest(tmp_path, [entry])

    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["languages"] == ["de", "en"]
    figure = data["figures"][0]
    assert figure["files"]["de"]["light"] == "bars.de.svg"
    assert figure["files"]["en"]["dark"] == "bars.en-dark.svg"
    assert figure["files"]["de"]["width"] == pytest.approx(460.8)
    assert figure["alt"]["de"] == "Drei Balken von 20 % bis 90 %."
    assert b"\r\n" not in path.read_bytes()
    assert check(tmp_path) == []


def test_page_entry_describes_files_written_earlier(tmp_path: Path) -> None:
    written = figkit.page(tmp_path, "bars", chart, CAPTIONS)

    assert figkit.page_entry(tmp_path, "bars", CAPTIONS) == written
    with pytest.raises(FileNotFoundError, match=r"lines\.en\.svg is missing"):
        figkit.page_entry(tmp_path, "lines", CAPTIONS)


def test_check_reports_a_missing_language_and_alt_text(tmp_path: Path) -> None:
    figkit.write_manifest(tmp_path, [figkit.page(tmp_path, "bars", chart, CAPTIONS)])
    path = tmp_path / "figures.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["figures"][0]["alt"]["de"] = " "
    path.write_text(json.dumps(data), encoding="utf-8")
    figkit.render(tmp_path, "extra", lambda t: chart("en", t), (figkit.SVG,), language="en")

    problems = check(tmp_path)

    assert "figures.json: bars has no alt in de" in problems
    assert "extra.svg: missing the de file extra.de.svg" in problems
    assert "extra.en.svg: not in figures.json, so the page has no alt text for it" in problems


def test_write_manifest_rejects_figures_in_different_languages(tmp_path: Path) -> None:
    both = figkit.page(tmp_path, "a", chart, CAPTIONS)
    english = figkit.page(tmp_path, "b", chart, {"en": CAPTIONS["en"]})

    with pytest.raises(ValueError, match="'b' is not in every language"):
        figkit.write_manifest(tmp_path, [both, english])


def test_check_tokens_compares_the_page_colours(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    css = tmp_path / "tokens.css"
    css.write_text(
        ":root {\n"
        "  --color-bg: light-dark(#faf8f4, #111318);\n"
        "  --color-surface: light-dark(#ffffff, #1a1d24);\n"
        "  --color-text: light-dark(#1d1e22, #eceef3);\n"
        "  --color-muted: light-dark(#5e6270, #A6ABBA);\n"
        "  --color-border: light-dark(#ebe6dc, #2a2e38);\n"
        "  --color-border-strong: light-dark(#76859a, #76859a);\n"
        "}\n",
        encoding="utf-8",
    )
    assert check_tokens(css) == []
    assert main(["check", "--tokens", str(css)]) == 0

    css.write_text(css.read_text(encoding="utf-8").replace("#1d1e22", "#000000"), encoding="utf-8")

    assert check_tokens(css) == [
        "tokens.css: --color-text is #000000 in light, the figures use #1d1e22"
    ]
    assert main(["check", "--tokens", str(css)]) == 1
    assert "--color-text" in capsys.readouterr().err
