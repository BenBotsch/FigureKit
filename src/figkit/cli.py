"""Command line: ``figkit check``, ``figkit init`` and ``figkit style preview``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from figkit.access import check_style
from figkit.check import check, check_tokens
from figkit.export import WEB_WIDTH
from figkit.preview import preview
from figkit.project import init, project
from figkit.theme import StyleError, load_style


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command and return its exit code."""
    parser = argparse.ArgumentParser(prog="figkit", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    checker = commands.add_parser(
        "check",
        help="check light/dark and language pairs, transparency, widths, sizes and the manifest",
        description=(
            "Without --style and --css the settings come from [tool.figkit] in the nearest "
            "pyproject.toml, and without those from the bundled style."
        ),
    )
    checker.add_argument("directories", nargs="*", type=Path)
    checker.add_argument(
        "--opaque",
        action="append",
        default=None,
        metavar="NAME",
        help="figure that is opaque on purpose (repeatable, default: card)",
    )
    checker.add_argument(
        "--any-width",
        action="store_true",
        help="do not require the fixed canvas width of web figures",
    )
    checker.add_argument(
        "--a11y",
        action="store_true",
        help="check the contrast of text, the colour-blind separation of series and the ramp",
    )
    checker.add_argument(
        "--css",
        "--tokens",
        dest="css",
        type=Path,
        metavar="CSS",
        help="stylesheet whose page colours the figures must share, such as tokens.css",
    )
    checker.add_argument(
        "--style",
        type=Path,
        metavar="TOKENS",
        help="tokens file of the style that wrote the figures, such as figures/tokens.json",
    )
    starter = commands.add_parser(
        "init",
        help="copy the bundled style into the project and name it in [tool.figkit]",
        description=(
            "Writes the tokens and their schema, unless the tokens file exists, and appends "
            "[tool.figkit] to the pyproject.toml of the working directory."
        ),
    )
    starter.add_argument(
        "--tokens",
        type=Path,
        default=Path("figures/tokens.json"),
        metavar="TOKENS",
        help="tokens file of the project (default: figures/tokens.json)",
    )
    starter.add_argument(
        "--css", type=Path, metavar="CSS", help="stylesheet that figkit check compares"
    )
    styles = commands.add_parser("style", help="work with the style of the project")
    actions = styles.add_subparsers(dest="action", required=True)
    previewer = actions.add_parser(
        "preview",
        help="render a specimen of every token in every theme",
        description=(
            "Without --style the style comes from [tool.figkit] in the nearest pyproject.toml, "
            "and without that it is the bundled one."
        ),
    )
    previewer.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path("figkit-preview"),
        help="folder of the specimen files (default: figkit-preview)",
    )
    previewer.add_argument("--style", type=Path, metavar="TOKENS", help="tokens file to preview")
    args = parser.parse_args(argv)

    if args.command == "init":
        return _init(args.tokens, args.css)
    if args.command == "style":
        return _preview(args.directory, args.style)
    return _check(parser, args)


def _init(tokens: Path, css: Path | None) -> int:
    try:
        written = init(Path.cwd(), tokens, css)
    except (StyleError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    for path in written:
        print(f"{path}: written")
    return 0


def _preview(directory: Path, tokens: Path | None) -> int:
    try:
        style = project().style() if tokens is None else load_style(tokens)
        paths = preview(directory, style)
    except (StyleError, OSError, ValueError) as error:
        print(error, file=sys.stderr)
        for note in getattr(error, "__notes__", []):
            print(note, file=sys.stderr)
        return 1
    for path in paths:
        print(path)
    return 0


def _report(problems: list[str], passed: str) -> bool:
    """Print the problems, or ``passed`` without any; return whether there were problems."""
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(passed)
    return bool(problems)


def _check(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    try:
        settings = project()
        style = settings.style() if args.style is None else load_style(args.style)
    except (StyleError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    css = args.css or settings.css
    if not args.directories and css is None and not args.a11y:
        parser.error("check needs a directory, --a11y, --css or css in [tool.figkit]")

    failed = False
    if args.a11y:
        label = str(style.source) if style.source is not None else "bundled style"
        failed = _report([f"{label}: {p}" for p in check_style(style)], f"{label}: accessible")
    if css is not None:
        try:
            problems = check_tokens(css, style)
        except OSError as error:
            problems = [f"{css}: cannot be read, {error.strerror or error}"]
        failed = _report(problems, f"{css}: ok") or failed
    for directory in args.directories:
        if not directory.is_dir():
            print(f"{directory}: not a directory", file=sys.stderr)
            failed = True
            continue
        problems = check(
            directory,
            opaque=args.opaque or ("card",),
            width=None if args.any_width else WEB_WIDTH,
            style=style,
        )
        for problem in problems:
            print(f"{directory / problem}", file=sys.stderr)
        failed = failed or bool(problems)
        if not problems:
            print(f"{directory}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
