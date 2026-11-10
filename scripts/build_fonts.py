"""Build the static font files in ``src/figkit/fonts`` from the variable fonts of Google Fonts.

Matplotlib reads only the default instance of a variable font, so the weights the figures use are
cut out as static files. The sources are pinned to one commit of github.com/google/fonts, so a
rebuild gives the same files. Run with ``uv run python scripts/build_fonts.py``.
"""

import io
import urllib.request
from pathlib import Path

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont

COMMIT = "5bb28733cec313b63fbd415b574b5ae35c8aa8b8"
BASE = f"https://raw.githubusercontent.com/google/fonts/{COMMIT}/ofl"
TARGET = Path(__file__).resolve().parents[1] / "src" / "figkit" / "fonts"

# Source file, then (output name, family, style, axis location) per instance. Bricolage
# Grotesque is cut at its 12 pt optical size, the size of chart text.
FONTS = {
    "bricolagegrotesque/BricolageGrotesque[opsz,wdth,wght].ttf": [
        (
            "BricolageGrotesque-Regular.ttf",
            "Bricolage Grotesque",
            "Regular",
            {"opsz": 12, "wdth": 100, "wght": 400},
        ),
        (
            "BricolageGrotesque-SemiBold.ttf",
            "Bricolage Grotesque",
            "SemiBold",
            {"opsz": 12, "wdth": 100, "wght": 600},
        ),
    ],
    "jetbrainsmono/JetBrainsMono[wght].ttf": [
        ("JetBrainsMono-Regular.ttf", "JetBrains Mono", "Regular", {"wght": 400}),
        ("JetBrainsMono-SemiBold.ttf", "JetBrains Mono", "SemiBold", {"wght": 600}),
    ],
}
LICENSES = {
    "bricolagegrotesque/OFL.txt": "OFL-BricolageGrotesque.txt",
    "jetbrainsmono/OFL.txt": "OFL-JetBrainsMono.txt",
}


def fetch(path: str) -> bytes:
    """Download one file of the pinned commit."""
    with urllib.request.urlopen(f"{BASE}/{path}", timeout=60) as response:
        data: bytes = response.read()
    return data


def rename(font: TTFont, family: str, style: str) -> None:
    """Give the instance its own family and style names, so matplotlib lists it as a weight."""
    names = font["name"]
    full = f"{family} {style}"
    postscript = f"{family.replace(' ', '')}-{style}"
    for record in list(names.names):
        if record.nameID in (16, 17, 21, 22, 25) or record.nameID >= 256:
            names.removeNames(nameID=record.nameID)
    for name_id, value in ((1, family), (2, style), (4, full), (6, postscript)):
        names.setName(value, name_id, 3, 1, 0x409)
        names.setName(value, name_id, 1, 0, 0)
    weight = 600 if style == "SemiBold" else 400
    font["OS/2"].usWeightClass = weight


def main() -> None:
    """Write every instance and the licences into the package."""
    TARGET.mkdir(parents=True, exist_ok=True)
    for source, instances in FONTS.items():
        data = fetch(source)
        for output, family, style, location in instances:
            font = TTFont(io.BytesIO(data))
            static = instantiateVariableFont(font, location, updateFontNames=False)
            rename(static, family, style)
            if "STAT" in static:
                del static["STAT"]
            static.save(TARGET / output)
            print(f"wrote {output}")
    for source, output in LICENSES.items():
        (TARGET / output).write_bytes(fetch(source).replace(b"\r\n", b"\n"))
        print(f"wrote {output}")


if __name__ == "__main__":
    main()
