"""Render figures with an installed figkit and check the files that the wheel must contain.

``scripts/check_package.sh`` runs it in a fresh environment with the built wheel. A file missing
from the wheel, such as a font, ``tokens.json`` or a licence, then fails before a release instead
of in a project that installs the tag. Usage: ``python -I scripts/smoke.py OUT``.
"""

import sys
from importlib import metadata
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # The script only writes files.

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

import figkit
from figkit.check import check

TEXT = {
    "en": figkit.Caption("Recall per class", "All three classes reach the 80 % target."),
    "de": figkit.Caption("Recall je Klasse", "Alle drei Klassen erreichen das Ziel von 80 %."),
}
NAMES = {"en": ["crazing", "inclusion", "patches"], "de": ["Risse", "Einschluss", "Flecken"]}


def recall(names: list[str], theme: figkit.Theme) -> Figure:
    """Bars with values and a reference line, the parts that use both fonts."""
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.0))
    bars = ax.barh(names, [0.93, 0.81, 0.99], color=theme.series[0])
    figkit.bar_labels(ax, bars, theme, fmt="{:.0%}")
    figkit.reference_line(ax, 0.8, "target 80 %", theme)
    figkit.category_axis(ax, "y")
    figkit.percent(ax, "x")
    figkit.title(ax, "Recall per class", theme)
    return figure


def problems_of_install() -> list[str]:
    """Reasons why the imported figkit is not a complete installed wheel."""
    package = Path(figkit.__file__).resolve().parent
    if "site-packages" not in package.parts:
        return [f"figkit was imported from {package}, not from an installed wheel"]
    found = []
    for name in ("py.typed", "tokens.json", "tokens.schema.json"):
        if not (package / name).is_file():
            found.append(f"the wheel lacks figkit/{name}")
    if not list((package / "fonts").glob("*.ttf")):
        found.append("the wheel lacks the fonts")
    # The metadata carries the licences, apart from the copies next to the fonts.
    files = (Path(str(file)) for file in metadata.files("figkit") or ())
    licences = {file.name for file in files if "licenses" in file.parts}
    for licence in ("LICENSE", "OFL-BricolageGrotesque.txt", "OFL-JetBrainsMono.txt"):
        if licence not in licences:
            found.append(f"the wheel lacks the licence {licence}")
    return found


def main(argv: list[str]) -> int:
    """Check the install, write a figure into ``argv[0]`` and a page into its ``page`` folder."""
    if len(argv) != 1:
        print("usage: smoke.py OUT", file=sys.stderr)
        return 2
    out = Path(argv[0])
    problems = problems_of_install()
    if not problems:
        figkit.register_fonts()  # Raises if matplotlib falls back to another font.
        figkit.render(out, "recall", lambda theme: recall(NAMES["en"], theme))
        site = out / "page"
        page = figkit.page(site, "recall", lambda code, theme: recall(NAMES[code], theme), TEXT)
        figkit.write_manifest(site, [page])
        problems = check(out) + check(site)
    for problem in problems:
        print(problem, file=sys.stderr)
    if not problems:
        print(f"figkit {metadata.version('figkit')} from the wheel: ok")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
