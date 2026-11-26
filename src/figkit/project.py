"""Settings of a project in the ``[tool.figkit]`` table of its ``pyproject.toml``.

A project with its own style names its tokens there once, and both its figure scripts and
``figkit check`` use them::

    [tool.figkit]
    tokens = "figures/tokens.json"        # style, relative to pyproject.toml
    css = "../Website/src/tokens.css"     # stylesheet that figkit check compares

Without the table, or without a ``pyproject.toml``, the bundled style applies.
"""

import json
import shutil
import tomllib
from dataclasses import dataclass
from pathlib import Path

from figkit.theme import DEFAULT, SCHEMA, Style, StyleError, load_style, tokens

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


def init(root: Path, tokens_file: Path, css: Path | None = None) -> list[Path]:
    """Give the project in ``root`` a style of its own and name it in ``[tool.figkit]``.

    Writes a copy of the bundled tokens to ``tokens_file`` with the schema next to it, unless
    the file exists; an existing file is kept and only checked. Then appends the table to the
    ``pyproject.toml`` of ``root``. Relative paths are relative to ``root``.

    Returns:
        The files written or changed, the ``pyproject.toml`` last.

    Raises:
        FileNotFoundError: If ``root`` has no ``pyproject.toml``.
        FileExistsError: If the project already has a ``[tool.figkit]`` table.
        StyleError: If the ``pyproject.toml`` is not TOML or an existing tokens file is not a
            valid style.
        OSError: If a file cannot be read or written.
    """
    config = root / FILE
    if not config.is_file():
        msg = f"{config}: not found; init needs the pyproject.toml of a project"
        raise FileNotFoundError(msg)
    text = config.read_text(encoding="utf-8")
    try:
        data = tomllib.loads(text)
    except tomllib.TOMLDecodeError as error:
        raise StyleError(str(config), [f"not TOML: {error}"]) from error
    if "figkit" in data.get("tool", {}):
        msg = f"{config}: [tool.figkit] exists already; init leaves it as it is"
        raise FileExistsError(msg)

    target = tokens_file if tokens_file.is_absolute() else root / tokens_file
    written: list[Path] = []
    if target.exists():
        load_style(target)
    else:
        template = tokens()
        template["$schema"] = f"./{SCHEMA.name}"
        template["$comment"] = (
            "Colours and type of the figures of this project, a copy of the figkit style. "
            "Preview them with `figkit style preview`."
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(template, indent=2) + "\n", encoding="utf-8", newline="\n")
        written.append(target)
        schema = target.parent / SCHEMA.name
        if not schema.exists():
            shutil.copyfile(SCHEMA, schema)
            written.append(schema)

    table = ["[tool.figkit]", f"tokens = {_toml_path(target, root)}"]
    if css is not None:
        table.append(f"css = {_toml_path(css if css.is_absolute() else root / css, root)}")
    # The table keeps the line ends of the file, so that Git shows only the added lines.
    raw = config.read_bytes()
    end = "\r\n" if b"\r\n" in raw else "\n"
    lead = "" if not raw else (end if raw.endswith(b"\n") else end * 2)
    with config.open("a", encoding="utf-8", newline="") as file:
        file.write(lead + end.join(table) + end)
    written.append(config)
    return written


def _toml_path(path: Path, root: Path) -> str:
    """``path`` relative to ``root`` where it can be, with forward slashes, as a TOML string."""
    try:
        relative = path.relative_to(root).as_posix()
    except ValueError:
        relative = path.as_posix()
    return json.dumps(relative)  # A JSON string of a path is a valid TOML basic string.
