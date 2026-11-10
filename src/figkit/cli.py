"""Command line: ``figkit check <directory>``."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from figkit.check import check
from figkit.export import WEB_WIDTH


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command and return its exit code."""
    parser = argparse.ArgumentParser(prog="figkit", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    checker = commands.add_parser(
        "check", help="check light/dark pairs, transparency, widths and sizes"
    )
    checker.add_argument("directories", nargs="+", type=Path)
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
    args = parser.parse_args(argv)

    failed = False
    for directory in args.directories:
        if not directory.is_dir():
            print(f"{directory}: not a directory", file=sys.stderr)
            failed = True
            continue
        problems = check(
            directory,
            opaque=args.opaque or ("card",),
            width=None if args.any_width else WEB_WIDTH,
        )
        for problem in problems:
            print(f"{directory / problem}", file=sys.stderr)
        failed = failed or bool(problems)
        if not problems:
            print(f"{directory}: ok")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
