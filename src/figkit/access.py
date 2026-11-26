"""Accessibility of the colours of a style, for ``figkit check --a11y``.

Three rules, checked in every theme against every page colour the theme is meant for:

* Text contrast (WCAG 2.2): ``ink`` and ``secondary`` reach 4.5:1, the level of small text;
  ``muted`` marks such as reference lines reach 3:1, the level of graphical objects.
* Series: neighbouring slots stay apart for readers with protanopia and deuteranopia, simulated
  after Machado, Oliveira and Fernandes (2009) at full severity, and for everyone else. The
  distance is Euclidean in OKLab times 100, with the floors of the dataviz palette validator
  that the bundled series were checked with: 6 under simulation and 15 in normal vision.
* Ramp: lightness changes in one direction with a visible step between neighbours.

Series below 3:1 against the page are allowed, because figures label such marks directly; see
``docs/style-guide.md``. Alt texts are checked with the manifest by :func:`figkit.check.check`.
"""

import itertools
import math
from collections.abc import Sequence

from figkit.theme import DEFAULT, Style, Theme

TEXT_CONTRAST = 4.5
MARK_CONTRAST = 3.0
CVD_FLOOR = 6.0
NORMAL_FLOOR = 15.0
RAMP_STEP = 0.06  # OKLCH lightness between neighbouring ramp colours

Matrix = tuple[tuple[float, float, float], ...]

# Machado, Oliveira and Fernandes (2009), severity 1.0, applied to linear RGB.
_SIMULATION: dict[str, Matrix] = {
    "protanopia": (
        (0.152286, 1.052583, -0.204868),
        (0.114503, 0.786281, 0.099216),
        (-0.003882, -0.048116, 1.051998),
    ),
    "deuteranopia": (
        (0.367322, 0.860646, -0.227968),
        (0.280085, 0.672501, 0.047413),
        (-0.011820, 0.042940, 0.968881),
    ),
}


def _linear(colour: str) -> tuple[float, float, float]:
    """Linear RGB of ``#rrggbb``."""
    channels = (int(colour[i : i + 2], 16) / 255 for i in (1, 3, 5))
    r, g, b = (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return r, g, b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio of two colours, from 1 to 21."""

    def luminance(colour: str) -> float:
        r, g, b = _linear(colour)
        return 0.2126 * r + 0.7152 * g + 0.0722 * b

    high, low = sorted((luminance(a), luminance(b)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _oklab(rgb: Sequence[float]) -> tuple[float, float, float]:
    r, g, b = rgb
    l_ = math.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m_ = math.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s_ = math.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return (
        0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
        1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
        0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_,
    )


def _simulate(colour: str, vision: str | None) -> tuple[float, float, float]:
    rgb = _linear(colour)
    if vision is None:
        return rgb
    r, g, b = (
        min(1.0, max(0.0, row[0] * rgb[0] + row[1] * rgb[1] + row[2] * rgb[2]))
        for row in _SIMULATION[vision]
    )
    return r, g, b


def distance(a: str, b: str, vision: str | None = None) -> float:
    """OKLab distance times 100 of two colours, seen with ``vision`` or with normal vision."""
    return 100 * math.dist(_oklab(_simulate(a, vision)), _oklab(_simulate(b, vision)))


def lightness(colour: str) -> float:
    """OKLCH lightness from 0 to 1."""
    return _oklab(_linear(colour))[0]


def check_style(style: Style | None = None) -> list[str]:
    """Accessibility problems of the colours of ``style``; an empty list means it passes.

    Returns:
        One message per problem, starting with the theme it concerns.
    """
    style = style or DEFAULT
    return [problem for theme in style.themes for problem in _theme_problems(theme)]


def _theme_problems(theme: Theme) -> list[str]:
    problems = []
    for role, minimum in (
        ("ink", TEXT_CONTRAST),
        ("secondary", TEXT_CONTRAST),
        ("muted", MARK_CONTRAST),
    ):
        colour: str = getattr(theme, role)
        for page in theme.pages:
            ratio = contrast(colour, page)
            if ratio < minimum:
                problems.append(
                    f"{theme.name}: {role} {colour} has {ratio:.2f}:1 on {page}, "
                    f"needs {minimum:g}:1"
                )
    for i, (a, b) in enumerate(itertools.pairwise(theme.series)):
        pair = f"series {i + 1} {a} and {i + 2} {b}"
        for vision in _SIMULATION:
            gap = distance(a, b, vision)
            if gap < CVD_FLOOR:
                problems.append(
                    f"{theme.name}: {pair} are {gap:.1f} apart with {vision}, need {CVD_FLOOR:g}"
                )
        gap = distance(a, b)
        if gap < NORMAL_FLOOR:
            problems.append(f"{theme.name}: {pair} are {gap:.1f} apart, need {NORMAL_FLOOR:g}")
    levels = [lightness(c) for c in theme.ramp]
    steps = [b - a for a, b in itertools.pairwise(levels)]
    if steps and not (all(s > 0 for s in steps) or all(s < 0 for s in steps)):
        problems.append(f"{theme.name}: ramp lightness does not change in one direction")
    else:
        problems += [
            f"{theme.name}: ramp {theme.ramp[i]} and {theme.ramp[i + 1]} differ by "
            f"{abs(step):.3f} in lightness, need {RAMP_STEP:g}"
            for i, step in enumerate(steps)
            if abs(step) < RAMP_STEP
        ]
    return problems
