"""The changelog and the release notes made from it."""

import importlib.util
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "release_notes.py"


def _release_notes() -> ModuleType:
    spec = importlib.util.spec_from_file_location("release_notes", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def test_changelog_has_the_version_of_the_package() -> None:
    version = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "version"
    ]
    result = _run(f"v{version}")
    assert result.returncode == 0, result.stderr
    assert f"FigureKit@v{version}" in result.stdout


def test_notes_hold_install_section_and_changes() -> None:
    changelog = "\n".join(
        [
            "# Changelog",
            "## [Unreleased]",
            "- next",
            "## [1.1.0] - 2026-01-02",
            "### Fixed",
            "- this",
            "## [1.0.0] - 2026-01-01",
            "- that",
            "[1.1.0]: https://example.org/compare/v1.0.0...v1.1.0",
        ]
    )
    notes = _release_notes().notes(changelog, "1.1.0")
    assert '@v1.1.0"' in notes
    assert "### Fixed\n- this" in notes
    assert "that" not in notes and "next" not in notes
    assert notes.endswith("**Changes:** https://example.org/compare/v1.0.0...v1.1.0\n")


def test_last_section_ends_at_the_links() -> None:
    changelog = "## [1.0.0] - 2026-01-01\n- first\n\n[1.0.0]: https://example.org/v1.0.0\n"
    assert _release_notes().section(changelog, "1.0.0") == "- first"


@pytest.mark.parametrize(
    ("changelog", "message"),
    [
        ("## [1.0.0] - 2026-01-01\n- first\n", "no section for 1.0.10"),
        ("## [1.0.10] - 2026-01-01\n\n## [1.0.0]\n- first\n", "section for 1.0.10 in"),
    ],
)
def test_missing_or_empty_section_is_an_error(changelog: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        _release_notes().section(changelog, "1.0.10")


def test_unknown_version_fails_without_notes() -> None:
    result = _run("9.9.9")
    assert result.returncode == 1
    assert result.stdout == ""
    assert "no section for 9.9.9" in result.stderr
