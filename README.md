# FigureKit

Publication-ready matplotlib figures for READMEs, websites and slides, in one consistent style.
A figure is a function of the theme. FigureKit draws it once per theme, such as light and dark,
and once per language, writes transparent SVG and PNG files, and checks them in CI.

<table>
  <tr>
    <td width="33%"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/examples/bars-dark.svg">
      <img src="docs/examples/bars.svg" alt="Bar chart: recall per class with a target line at 80 %; rolled-in scale is the only class below it.">
    </picture></td>
    <td width="33%"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/examples/lines-dark.svg">
      <img src="docs/examples/lines.svg" alt="Line chart: validation macro F1 per epoch for several models, labelled at the line ends.">
    </picture></td>
    <td width="33%"><picture>
      <source media="(prefers-color-scheme: dark)" srcset="docs/examples/heatmap-dark.svg">
      <img src="docs/examples/heatmap.svg" alt="Confusion matrix of true against predicted class on the sequential ramp.">
    </picture></td>
  </tr>
</table>

The images follow the colour mode of this page. [docs/examples](docs/examples) holds the whole
gallery, drawn by [`scripts/examples.py`](scripts/examples.py).

## Features

- **One style, many projects.** The bundled style matches the portfolio: Bricolage Grotesque
  with JetBrains Mono for numbers, both bundled. Any project can bring its own style with any
  number of themes in a single JSON file.
- **Readable in every mode.** Series colours are validated for colour-vision deficiencies against
  the page colours; text colours reach WCAG contrast, checked in the tests.
- **Transparent files.** One file per theme fits every page colour of that theme.
- **Reproducible.** The same figure gives byte-identical SVGs, without date or version.
- **Two languages.** Website figures come without title in every language, German numbers
  included, with a `figures.json` of titles and alt texts.
- **Checked in CI.** `figkit check` fails on missing theme or language pairs, opaque backgrounds,
  figures off the canvas, text below 8 pt, oversized files, missing alt texts and page colours
  that differ from the website's stylesheet.

## Quickstart

**1. Install** with a pinned tag, so a style change reaches a project only when it updates the tag:

```sh
uv add "figkit @ git+https://github.com/BenBotsch/FigureKit@v0.3.1"
```

Each [release](https://github.com/BenBotsch/FigureKit/releases) also attaches the wheel;
[CHANGELOG.md](CHANGELOG.md) lists what changed, breaking changes first.

**2. Draw** a figure as a function of the theme and let `render` write it:

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
```

Result:

```text
docs/figures/
├── recall.svg        light, transparent, 6.4 in canvas
├── recall-dark.svg
├── recall.png        1600 px wide
└── recall-dark.png
```

**3. Embed** both files; the browser picks the one of its mode:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/recall-dark.svg">
  <img src="docs/figures/recall.svg" alt="Recall per class: all classes above the 80 % target.">
</picture>
```

**4. Check** in CI:

```sh
uv run figkit check docs/figures
```

## Outputs

| Output | Files |
| --- | --- |
| `WEB` (default) | transparent SVG and PNG on a 6.4 in canvas, the PNG 1600 px wide |
| `PHOTO` | transparent WebP and PNG, for images and overlays |
| `CARD` | opaque 1200 x 630 PNG for Open Graph; draw on `CARD_INCHES` |

## Figures for a website

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
```

Result:

```text
docs/figures/page/
├── recall.de.svg   recall.de-dark.svg
├── recall.en.svg   recall.en-dark.svg
└── figures.json    titles, alt texts and files per language and theme
```

A figure that a separate step draws, because it needs a trained model for example, is written
there with `page`. `figkit.page_entry(out, name, TEXT, figkit.PHOTO[0])` then reads its entry from
the files, so one step can still write the manifest of all figures.

In German, tick labels, the values of `bar_labels` and `figkit.number` write `0,74`, `1.500` and
`74 %`; category names and other text come from the project. Text below 8 pt is an error,
because pages scale the canvas down on phones.

## A style of your own

The bundled style is the portfolio's. Another project describes its own in a tokens file. Start
from a copy of [`src/figkit/tokens.json`](src/figkit/tokens.json); its schema,
[`tokens.schema.json`](src/figkit/tokens.schema.json), lists every key and gives editors
completion and validation when the copy's `$schema` points to it.

```json
{
  "version": 2,
  "default": "light",
  "font": {
    "sans": "Inter", "mono": "IBM Plex Mono", "files": ["fonts/*.ttf"],
    "size": 9, "title": 11, "label": 9, "tick": 8.5, "annotation": 8, "minimum": 8
  },
  "themes": {
    "light": {"pair": "dark", "pages": ["#ffffff"], "surface": "#ffffff", "ink": "#111111", "…": "…"},
    "dark":  {"pair": "light", "…": "…"},
    "print": {"…": "…"}
  },
  "css": {"text": ["ink"], "bg": ["pages", 0]}
}
```

Each theme needs `pages`, `surface`, `ink`, `secondary`, `muted`, `grid`, `axis`, `series`,
`ramp` and `status` (`good`, `warning`, `serious`, `critical`).

| Key | Meaning |
| --- | --- |
| `default` | Theme whose files carry no suffix; every other theme writes `-<name>`. |
| `pair` | Theme a page swaps with, such as light and dark. `figkit check` requires the file of the pair; a theme without one, such as `print`, stands alone. |
| `font.files` | Glob patterns relative to the tokens file; without them the bundled fonts apply. matplotlib keeps one file per family in a process, so own font files need family names of their own. |
| `css` | Maps custom properties of the website, `--color-text: light-dark(#111111, #eeeeee)`, to tokens. `figkit check --css` compares the first colour with the default theme and the second with its pair. |

`figkit.load_style(path)` rejects unknown keys and lists every problem with its place, such as
`themes.dark.series[2]: 'blue' is not a #rrggbb colour`. The style then goes to `render`, `page`,
`page_entry` and `check`:

```python
style = figkit.load_style(Path("figures/tokens.json"))
figkit.render(Path("docs/figures"), "recall", recall, style=style)
# recall.svg, recall-dark.svg, recall-print.svg and the PNGs
```

A project names its style once in its `pyproject.toml`. Scripts read it with
`figkit.project_style()`, and `figkit check` uses it unless `--style` or `--css` say otherwise:

```toml
[tool.figkit]
tokens = "figures/tokens.json"              # relative to pyproject.toml
css = "../Website/src/styles/tokens.css"
```

## Command line

```sh
figkit check [DIRECTORY ...] [--css CSS] [--style TOKENS] [--opaque NAME] [--any-width]
```

| Option | Effect |
| --- | --- |
| `DIRECTORY` | Folders of figures to check: theme and language pairs, transparency, canvas width, text size, file size and `figures.json`. |
| `--css CSS` | Compares the page, text and line colours with a stylesheet (alias `--tokens`). |
| `--style TOKENS` | Style that wrote the figures; overrides `[tool.figkit]`. |
| `--opaque NAME` | Figure that is opaque on purpose; repeatable, default `card`. |
| `--any-width` | Does not require the fixed canvas width of web figures. |

The exit code is 1 on any problem. In CI:

```sh
uv run figkit check docs/figures docs/figures/page
uv run figkit check --css ../Portfolio/src/styles/tokens.css
```

## API

| Area | Names |
| --- | --- |
| Render | `render`, `page`, `page_entry`, `write_manifest`, `save`, `path_for`, `canvas`, `styled`, `headless` |
| Outputs | `WEB`, `PHOTO`, `CARD`, `SVG`, `PNG`, `WEB_WIDTH`, `CARD_INCHES`, `RASTER_DPI` |
| Helpers | `title`, `legend_top`, `grid`, `percent`, `category_axis`, `mono`, `mono_ticks`, `value`, `bar_labels`, `reference_line`, `line_labels`, `ink_on`, `hex_colour` |
| Languages | `Caption`, `language`, `localize`, `number` |
| Style | `Theme`, `Typography`, `Style`, `StyleError`, `load_style`, `parse_style`, `DEFAULT`, `LIGHT`, `DARK`, `THEMES`, `TYPE`, `tokens`, `rc`, `register_fonts` |
| Project | `Project`, `project`, `project_style` |
| Checks | `check_text` and the `figkit check` command |

`figkit.styled(theme)` applies the style without writing files, for example in a notebook.
Importing figkit leaves the matplotlib backend alone; a batch job that only writes files can set
`MPLBACKEND=Agg`.

## Rules

[docs/style-guide.md](docs/style-guide.md) covers which form fits which data, how colours are
assigned, layout, file names, embedding and alt text.

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
uv run python scripts/examples.py      # regenerate the gallery
uv run --no-project --with fonttools python scripts/build_fonts.py   # rebuild the static fonts
uv build && bash scripts/check_package.sh   # render and check figures with the built wheel
```

A release: move the entries under `Unreleased` in [CHANGELOG.md](CHANGELOG.md) to a new version
section, set that version in `pyproject.toml` and `uv.lock` (`uv version 0.4.0`), and push the tag
`v0.4.0`. The release workflow checks that tag and version match, tests the wheel on Ubuntu and
Windows and publishes the GitHub release with the notes of that section.

The colours and type sizes of the bundled style live only in
[src/figkit/tokens.json](src/figkit/tokens.json).

## License

Code: MIT. Fonts in `src/figkit/fonts`: SIL Open Font License 1.1, see the `OFL-*.txt` files.
They are static cuts of the variable fonts, made with fontTools from pinned Google Fonts sources.
Neither font declares a Reserved Font Name.
