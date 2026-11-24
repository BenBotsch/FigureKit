"""Command line: ``figkit check <directory>``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from figkit.check import check, check_tokens
from figkit.export import WEB_WIDTH
from figkit.project import project
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
    args = parser.parse_args(argv)

    try:
        settings = project()
        style = settings.style() if args.style is None else load_style(args.style)
    except (StyleError, OSError) as error:
        print(error, file=sys.stderr)
        return 1
    css = args.css or settings.css
    if not args.directories and css is None:
        parser.error("check needs a directory, --css or css in [tool.figkit]")

    failed = False
    if css is not None:
        try:
            problems = check_tokens(css, style)
        except OSError as error:
            problems = [f"{css}: cannot be read, {error.strerror or error}"]
        for problem in problems:
            print(problem, file=sys.stderr)
        failed = bool(problems)
        if not problems:
            print(f"{css}: ok")
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
