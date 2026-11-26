"""Accessibility of the colours of a style."""

import json
from pathlib import Path
from typing import Any

import pytest

import figkit
from figkit.access import check_style, contrast, distance
from figkit.cli import main

ROOT = Path(__file__).resolve().parents[1]


def style_with(change: dict[str, Any]) -> figkit.Style:
    """The bundled style with the keys of ``change`` replaced in its light theme."""
    data = json.loads(json.dumps(figkit.tokens()))
    data["themes"]["light"].update(change)
    return figkit.parse_style(data)


def test_the_bundled_and_the_example_style_pass() -> None:
    assert check_style() == []
    assert check_style(figkit.load_style(ROOT / "docs/examples/style/tokens.json")) == []


def test_contrast_and_distance_match_known_values() -> None:
    assert contrast("#000000", "#ffffff") == pytest.approx(21)
    assert contrast("#777777", "#ffffff") == pytest.approx(4.48, abs=0.01)
    assert distance("#000000", "#ffffff") == pytest.approx(100, abs=0.01)
    # Red and green, far apart in normal vision, nearly merge without red cones.
    assert distance("#d03b3b", "#3b8f3b") > 15
    assert distance("#d03b3b", "#3b8f3b", "protanopia") < distance("#d03b3b", "#3b8f3b") / 2


@pytest.mark.parametrize(
    ("change", "problem"),
    [
        ({"ink": "#999999"}, "light: ink #999999 has 2.69:1 on #faf8f4, needs 4.5:1"),
        ({"secondary": "#8a8a8a"}, "light: secondary #8a8a8a has"),
        ({"muted": "#c0c0c0"}, "light: muted #c0c0c0 has"),
        (
            {"series": ["#0f766e", "#b4387a", "#1baf7a", "#eda100"]},
            "light: series 1 #0f766e and 2 #b4387a are 4.0 apart with deuteranopia, need 6",
        ),
        (
            {"series": ["#2f5bd3", "#3060d8", "#1baf7a", "#eda100"]},
            "light: series 1 #2f5bd3 and 2 #3060d8 are",
        ),
        ({"ramp": ["#f4f8fd", "#9ec5f4", "#cde2fb"]}, "light: ramp lightness does not change"),
        ({"ramp": ["#f4f8fd", "#eef4fc"]}, "light: ramp #f4f8fd and #eef4fc differ by"),
    ],
)
def test_each_rule_reports_its_problem(change: dict[str, Any], problem: str) -> None:
    problems = check_style(style_with(change))

    assert any(p.startswith(problem) for p in problems), problems
    assert all(p.startswith("light:") for p in problems)


def test_close_series_fail_in_normal_vision_too() -> None:
    problems = check_style(style_with({"series": ["#2f5bd3", "#3060d8", "#1baf7a", "#eda100"]}))

    assert any(p.endswith("need 15") for p in problems)


def test_cli_checks_the_style_only_with_a11y(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    data = json.loads(json.dumps(figkit.tokens()))
    data["themes"]["dark"]["secondary"] = "#3d4250"
    (tmp_path / "tokens.json").write_text(json.dumps(data), encoding="utf-8")
    (tmp_path / "pyproject.toml").write_text(
        '[tool.figkit]\ntokens = "tokens.json"\n', encoding="utf-8"
    )
    (tmp_path / "figures").mkdir()
    monkeypatch.chdir(tmp_path)

    assert main(["check", "figures"]) == 0
    assert main(["check", "--a11y"]) == 1
    assert "tokens.json: dark: secondary #3d4250 has" in capsys.readouterr().err
    assert main(["check", "--a11y", "--style", str(ROOT / "src/figkit/tokens.json")]) == 0
    assert "tokens.json: accessible" in capsys.readouterr().out
