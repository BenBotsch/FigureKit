import json
from pathlib import Path

import matplotlib.pyplot as plt
import pytest
from matplotlib.figure import Figure

import figkit
from figkit.cli import main


def tokens_with_print(path: Path) -> Path:
    """The bundled tokens with a print theme that has no pair."""
    data = json.loads(json.dumps(figkit.tokens()))
    data["themes"]["print"] = {k: v for k, v in data["themes"]["light"].items() if k != "pair"}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def configure(root: Path, table: str) -> None:
    (root / "pyproject.toml").write_text(f"[project]\nname = 'x'\n\n{table}", encoding="utf-8")


def chart(theme: figkit.Theme) -> Figure:
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 2))
    ax.plot([0, 1], [0, 1], color=theme.series[0])
    return figure


def test_without_a_table_the_bundled_style_applies(tmp_path: Path) -> None:
    configure(tmp_path, "")

    settings = figkit.project(tmp_path)

    assert settings == figkit.Project(None, None, tmp_path / "pyproject.toml")
    assert settings.style() is figkit.DEFAULT
    assert figkit.project_style(tmp_path) is figkit.DEFAULT


def test_the_table_is_found_from_a_subfolder(tmp_path: Path) -> None:
    tokens_with_print(tmp_path / "figures" / "tokens.json")
    configure(tmp_path, '[tool.figkit]\ntokens = "figures/tokens.json"\ncss = "site/tokens.css"\n')
    (tmp_path / "scripts").mkdir()

    settings = figkit.project(tmp_path / "scripts")

    assert settings.tokens == tmp_path / "figures" / "tokens.json"
    assert [t.name for t in settings.style().themes] == ["light", "dark", "print"]
    assert [t.name for t in figkit.project_style(tmp_path).themes] == ["light", "dark", "print"]
    assert settings.css == tmp_path / "site" / "tokens.css"


@pytest.mark.parametrize(
    ("table", "problem"),
    [
        ('[tool.figkit]\ntoken = "a.json"\n', "tool.figkit.token: unknown key"),
        ("[tool.figkit]\ncss = 3\n", "tool.figkit.css: must be a path"),
        ("[tool.figkit\n", "not TOML"),
        ("[tool]\nfigkit = 1\n", "tool.figkit: must be a table"),
    ],
)
def test_a_broken_table_fails(tmp_path: Path, table: str, problem: str) -> None:
    configure(tmp_path, table)

    with pytest.raises(figkit.StyleError, match=problem):
        figkit.project(tmp_path)


def test_check_uses_the_style_of_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    style = figkit.load_style(tokens_with_print(tmp_path / "tokens.json"))
    out = tmp_path / "figures"
    figkit.render(out, "f", chart, (figkit.SVG,), style=style)
    (out / "f-dark.svg").unlink()
    monkeypatch.chdir(tmp_path)

    # The bundled style reads f-print.svg as a light file and wants f-print-dark.svg.
    configure(tmp_path, "")
    assert main(["check", "figures"]) == 1
    assert "f-print.svg: missing its pair f-print-dark.svg" in capsys.readouterr().err

    configure(tmp_path, '[tool.figkit]\ntokens = "tokens.json"\n')
    assert main(["check", "figures"]) == 1
    assert capsys.readouterr().err.strip().endswith("f.svg: missing its pair f-dark.svg")

    figkit.render(out, "f", chart, (figkit.SVG,), style=style)
    assert main(["check", "figures"]) == 0
    configure(tmp_path, '[tool.figkit]\ntokens = "missing.json"\n')
    assert main(["check", "figures"]) == 1
    assert main(["check", "figures", "--style", "tokens.json"]) == 0


def test_check_compares_the_css_of_the_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "tokens.css").write_text(
        "--color-text: light-dark(#1d1e22, #ffffff);", encoding="utf-8"
    )
    configure(tmp_path, '[tool.figkit]\ncss = "tokens.css"\n')
    monkeypatch.chdir(tmp_path)

    assert main(["check"]) == 1
    assert "--color-text is #ffffff in dark" in capsys.readouterr().err

    (tmp_path / "other.css").write_text("", encoding="utf-8")
    assert main(["check", "--css", "other.css"]) == 1
    assert "--color-bg is missing" in capsys.readouterr().err

    configure(tmp_path, "")
    with pytest.raises(SystemExit):
        main(["check"])
    assert "css in [tool.figkit]" in capsys.readouterr().err
