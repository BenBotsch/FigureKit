"""Settings of a project in the ``[tool.figkit]`` table of its ``pyproject.toml``.

A project with its own style names its tokens there once, and both its figure scripts and
``figkit check`` use them::

    [tool.figkit]
    tokens = "figures/tokens.json"        # style, relative to pyproject.toml
    css = "../Website/src/tokens.css"     # stylesheet that figkit check compares

Without the table, or without a ``pyproject.toml``, the bundled style applies.
"""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from figkit.theme import DEFAULT, Style, StyleError, load_style

FILE = "pyproject.toml"
_KEYS = ("tokens", "css")


@dataclass(frozen=True, slots=True)
class Project:
    """The figkit settings of a project.

    Attributes:
        tokens: Tokens file of the project's style, ``None`` for the bundled style.
        css: Stylesheet whose colours ``figkit check`` compares with the style, or ``None``.
        config: The ``pyproject.toml`` the settings came from, ``None`` without one.
    """

    tokens: Path | None = None
    css: Path | None = None
    config: Path | None = None

    def style(self) -> Style:
        """The style of ``tokens``, or the bundled style without them.

        Raises:
            StyleError: If the tokens are not a valid style.
            OSError: If the tokens file cannot be read.
        """
        return DEFAULT if self.tokens is None else load_style(self.tokens)


def find(start: Path | None = None) -> Path | None:
    """The nearest ``pyproject.toml`` in ``start`` or one of its parents, ``None`` without one."""
    folder = (start or Path.cwd()).resolve()
    for candidate in (folder, *folder.parents):
        if (candidate / FILE).is_file():
            return candidate / FILE
    return None


def project(start: Path | None = None) -> Project:
    """Settings of the project that contains ``start``, by default the working directory.

    Paths in the table are relative to the ``pyproject.toml`` that holds them. The style is read
    only by :meth:`Project.style`, so that a broken tokens file can be overridden.

    Raises:
        StyleError: If the file is not TOML or the table has unknown keys or values that are not
            paths.
        OSError: If the ``pyproject.toml`` cannot be read.
    """
    config = find(start)
    if config is None:
        return Project()
    try:
        data = tomllib.loads(config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as error:
        raise StyleError(str(config), [f"not TOML: {error}"]) from error
    table = data.get("tool", {}).get("figkit")
    if table is None:
        return Project(config=config)
    if not isinstance(table, dict):
        raise StyleError(str(config), ["tool.figkit: must be a table"])
    problems = [f"tool.figkit.{key}: unknown key" for key in table if key not in _KEYS]
    problems += [
        f"tool.figkit.{key}: must be a path"
        for key in _KEYS
        if key in table and (not isinstance(table[key], str) or not table[key])
    ]
    if problems:
        raise StyleError(str(config), problems)
    base = config.parent
    tokens = base / table["tokens"] if "tokens" in table else None
    css = base / table["css"] if "css" in table else None
    return Project(tokens, css, config)


def project_style(start: Path | None = None) -> Style:
    """Style of the project that contains ``start``, see :func:`project`.

    Raises:
        StyleError: If the settings or the tokens are not valid.
        OSError: If a file cannot be read.
    """
    return project(start).style()
