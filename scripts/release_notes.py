"""Print the release notes of one version from ``CHANGELOG.md``.

Run with ``uv run python scripts/release_notes.py 0.3.0``. The release workflow writes the output
into the GitHub release of the tag, so the changelog is the only place the notes are written.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parents[1] / "CHANGELOG.md"


def section(changelog: str, version: str) -> str:
    """Body of the section ``## [<version>]``, without its heading and link line.

    Raises:
        ValueError: If the changelog has no section for ``version`` or the section is empty.
    """
    heading = re.compile(rf"^## \[{re.escape(version)}\][^\n]*\n", re.MULTILINE)
    start = heading.search(changelog)
    if start is None:
        msg = f"CHANGELOG.md has no section for {version}"
        raise ValueError(msg)
    end = re.compile(r"^(## |\[[^\]]+\]: )", re.MULTILINE).search(changelog, start.end())
    body = changelog[start.end() : end.start() if end else None].strip()
    if not body:
        msg = f"the section for {version} in CHANGELOG.md is empty"
        raise ValueError(msg)
    return body


def notes(changelog: str, version: str) -> str:
    """Install command, the changelog section and a link to the changes since the last tag."""
    install = f'```sh\nuv add "figurekit=={version}"\n```'
    link = re.search(rf"^\[{re.escape(version)}\]: (\S+)$", changelog, re.MULTILINE)
    changes = f"\n\n**Changes:** {link.group(1)}" if link else ""
    return f"{install}\n\n{section(changelog, version)}{changes}\n"


def main(argv: list[str]) -> int:
    """Print the notes of the version in ``argv``; a leading ``v`` is allowed."""
    if len(argv) != 1:
        print("usage: release_notes.py VERSION", file=sys.stderr)
        return 2
    try:
        text = notes(CHANGELOG.read_text(encoding="utf-8"), argv[0].removeprefix("v"))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
