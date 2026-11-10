"""Languages of figures: the language being drawn, German numbers and figures without a title.

:func:`figkit.render` sets the language and the headless mode while a figure is drawn, so the
helpers can follow them: :func:`number` writes ``0,95`` and ``1.500`` in German, tick labels are
converted the same way, and :func:`figkit.title` draws nothing in a headless figure, whose page
shows the title as text. Texts other than numbers come from the project, one table per language.
"""

import re
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any

from matplotlib.figure import Figure
from matplotlib.ticker import FixedFormatter, Formatter, NullFormatter

DEFAULT = "en"
# Languages whose numbers use a decimal comma, a thousands dot and a space before the percent sign.
_COMMA = frozenset({"de"})

_LANGUAGE: ContextVar[str] = ContextVar("figkit_language", default=DEFAULT)
_HEADLESS: ContextVar[bool] = ContextVar("figkit_headless", default=False)

# A number on its own: not a part of a name such as ResNet18 or AI4I, nor of a version like v0.1.
_NUMBER = re.compile(r"(?<![\w.,])(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?(?![\w.])")
_PERCENT = re.compile(r"(\d)%")


def language() -> str:
    """Language of the figure being drawn, ``en`` outside of :func:`figkit.render`."""
    return _LANGUAGE.get()


def headless() -> bool:
    """Whether the figure being drawn leaves out its title, because the page shows it."""
    return _HEADLESS.get()


@contextmanager
def speaking(code: str | None, *, without_title: bool = False) -> Iterator[None]:
    """Draw in ``code`` (``None`` keeps English) and, if asked, without the title."""
    tokens = (_LANGUAGE.set(code or DEFAULT), _HEADLESS.set(without_title))
    try:
        yield
    finally:
        _HEADLESS.reset(tokens[1])
        _LANGUAGE.reset(tokens[0])


def localize(text: str, code: str | None = None) -> str:
    """The numbers in ``text`` written as in ``code``, by default the current language.

    English ``1,447.5`` and ``95%`` become German ``1.447,5`` and ``95 %``. Text with mathtext
    (a ``$``) stays as it is, so are digits inside words.
    """
    if (code or language()) not in _COMMA or "$" in text:
        return text

    def swap(match: re.Match[str]) -> str:
        whole, fraction = match.group(1), match.group(2) or ""
        return whole.replace(",", ".") + fraction.replace(".", ",")

    return _PERCENT.sub(r"\1 %", _NUMBER.sub(swap, text))


def number(value: float, spec: str = "") -> str:
    """``value`` formatted with ``spec`` as in :func:`format` and written in the current language.

    ``number(0.781, ".3f")`` is ``0.781`` in English and ``0,781`` in German, ``number(1500, ",")``
    is ``1,500`` and ``1.500``.
    """
    return localize(format(value, spec))


class Localized(Formatter):
    """Tick labels of another formatter with their numbers in the given language."""

    def __init__(self, inner: Formatter, code: str) -> None:
        self.inner = inner
        self.code = code

    def set_axis(self, axis: Any) -> None:
        """Attach both formatters to the axis."""
        super().set_axis(axis)
        self.inner.set_axis(axis)

    def set_locs(self, locs: list[float]) -> None:
        """Pass the tick positions on."""
        self.inner.set_locs(locs)

    def __call__(self, x: float, pos: int | None = None) -> str:
        """Label of one tick."""
        return localize(self.inner(x, pos), self.code)

    def format_ticks(self, values: list[float]) -> list[str]:
        """Labels of all ticks."""
        return [localize(text, self.code) for text in self.inner.format_ticks(values)]

    def get_offset(self) -> str:
        """Offset text of the axis, such as 1e3."""
        return localize(self.inner.get_offset(), self.code)

    def __getattr__(self, name: str) -> Any:
        # Settings of the inner formatter, such as ScalarFormatter.set_powerlimits.
        return getattr(self.inner, name)


def localize_ticks(figure: Figure, code: str) -> None:
    """Write the numeric tick labels of every axes in ``code``; category names stay as set."""
    if code not in _COMMA:
        return
    for ax in figure.axes:
        for axis in (ax.xaxis, ax.yaxis):
            for get, put in (
                (axis.get_major_formatter, axis.set_major_formatter),
                (axis.get_minor_formatter, axis.set_minor_formatter),
            ):
                inner = get()
                if not isinstance(inner, FixedFormatter | NullFormatter | Localized):
                    put(Localized(inner, code))
