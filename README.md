# FigureKit

One figure style for all my projects. It renders matplotlib figures in a light and a dark theme
and writes them as transparent SVG and PNG, ready for a README, the portfolio and slides.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/examples/bars-dark.svg">
  <img src="docs/examples/bars.svg" alt="Example bar chart: recall per class with a target line at 80 %; rolled-in scale is the only class below it.">
</picture>

- **Looks like the portfolio.** Text and line colours come from the portfolio tokens, the type is
  Bricolage Grotesque with JetBrains Mono for numbers, and both fonts are bundled.
- **Readable in both modes.** The series colours are validated for colour-vision deficiencies
  against the light and dark page colours. Text colours reach WCAG contrast, checked in the tests.
- **Transparent.** One file per mode fits every page colour of that mode.
- **Reproducible.** The same figure gives byte-identical SVGs. The files carry no date or version.
- **Two languages.** A website gets each figure without its title in every language, German
  numbers included, and a `figures.json` with titles and alt texts.
- **Checked.** `figkit check` fails CI on missing light/dark or language pairs, opaque
  backgrounds, figures off the canvas, oversized files, missing alt texts and page colours that
  differ from the website's stylesheet.

## Install

```sh
uv add "figkit @ git+https://github.com/BenBotsch/FigureKit@v0.2.1"
```

Pin a tag, so a style change reaches a project only when it updates the tag.

## Use

A figure is a function of the theme. `render` calls it once per theme and writes every output:

```python
from pathlib import Path

import matplotlib.pyplot as plt
import figkit


def recall(theme: figkit.Theme) -> plt.Figure:
    figure, ax = plt.subplots(figsize=(figkit.WEB_WIDTH, 3.2))
    bars = ax.barh(["crazing", "inclusion", "patches"], [0.93, 0.81, 0.99], color=theme.series[0])
    figkit.bar_labels(ax, bars, theme, fmt="{:.0%}")
    figkit.reference_line(ax, 0.8, "target 80 %", theme)
    figkit.category_axis(ax, "y")
    figkit.percent(ax, "x")
    figkit.title(ax, "Recall per class", theme, subtitle="Test split")
    return figure


figkit.render(Path("docs/figures"), "recall", recall)
# docs/figures/recall.svg, recall-dark.svg, recall.png, recall-dark.png
```

| Output | Files |
| --- | --- |
| `WEB` (default) | transparent SVG and PNG on a 6.4 in canvas, the PNG 1600 px wide |
| `PHOTO` | transparent WebP and PNG, for images and overlays |
| `CARD` | opaque 1200 x 630 PNG for Open Graph; draw on `CARD_INCHES` |

Helpers: `title`, `legend_top`, `grid`, `percent`, `category_axis`, `mono_ticks`, `value`,
`bar_labels`, `reference_line`, `line_labels`, `ink_on`, `hex_colour`, `number`, `localize`,
`language`. `canvas` returns the
fixed box that `render` crops to. `figkit.styled(theme)` applies the
style without writing files, for example in a notebook.

### Figures for a website

The website shows the title as text, so its files leave it out. `page` draws the figure once per
language, the draw function receives the language as its first argument, and `write_manifest`
lists the files with their texts:

```python
TEXT = {
    "en": figkit.Caption("Recall per class", "All classes above 80 % but scale."),
    "de": figkit.Caption("Recall je Klasse", "Alle Klassen über 80 % außer Zunder."),
}


def recall_page(language: str, theme: figkit.Theme) -> plt.Figure:
    # Labels from a table per language, numbers with figkit.number(0.74, ".0%").
    return draw_recall(LABELS[language], theme)


out = Path("docs/figures/page")
figkit.write_manifest(out, [figkit.page(out, "recall", recall_page, TEXT)])
# recall.de.svg, recall.de-dark.svg, recall.en.svg, recall.en-dark.svg, figures.json
```

A figure that a separate step draws, because it needs a trained model for example, is written
there with `page`. `figkit.page_entry(out, name, TEXT, figkit.PHOTO[0])` then reads its entry from
the files, so one step can still write the manifest of all figures.

In German, tick labels and `figkit.number` write `0,74`, `1.500` and `74 %`; other text comes from
the project. Text below 8 pt is an error, because pages scale the canvas down on phones.

In CI:

```sh
uv run figkit check docs/figures docs/figures/page
uv run figkit check --tokens ../Portfolio/src/styles/tokens.css
```

## Rules

[docs/style-guide.md](docs/style-guide.md) covers which form fits which data, how colours are
assigned, layout, file names, embedding and alt text. [docs/examples](docs/examples) shows the
gallery from `scripts/examples.py`.

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
uv run python scripts/examples.py      # regenerate the gallery
uv run --no-project --with fonttools python scripts/build_fonts.py   # rebuild the static fonts
```

Colours and type sizes live only in [src/figkit/tokens.json](src/figkit/tokens.json).

## License

Code: MIT. Fonts in `src/figkit/fonts`: SIL Open Font License 1.1, see the `OFL-*.txt` files.
They are static cuts of the variable fonts, made with fontTools from pinned Google Fonts sources.
Neither font declares a Reserved Font Name.
