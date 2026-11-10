# Figure style guide

Rules for every figure of every project. `figkit` enforces the parts that can be checked: colours,
type, file names, transparency, file sizes. The rest is a short checklist for the author.

## 1. Form before colour

Decide what the figure has to show before drawing it.

| Job | Form |
| --- | --- |
| One headline number | Text or a card, not a chart |
| Compare a few values | Horizontal bars, sorted, with the value at the end of each bar |
| A value with its uncertainty | Dot with an interval line |
| Change over time or training | Line with the final value labelled at its end |
| Two categories against each other | Heatmap on the sequential ramp, counts in the cells |
| A process or architecture | Boxes and arrows in `ink` and `muted`; colour only for groups |

Two measures with different units go into two charts. Never use a second y-axis.

## 2. Colour

- **Series** (`theme.series`) take their slots in a fixed order. A model or category keeps its slot
  in every figure of a project, even when another figure leaves it out. Four slots exist. A fifth
  series goes into "other" or a second panel.
- **Magnitude** uses `theme.ramp` (one hue, light to dark), for example a confusion matrix.
- **Status** (`theme.status`: good, warning, serious, critical) is reserved for limits and states,
  such as a drift alert line. It never serves as a series colour, and it always comes with a
  text label.
- **Text** is never coloured by series. Titles and values use `ink`; axis labels, ticks, legends and
  notes use `secondary`. A coloured mark next to the text carries the identity.

The series were checked with the dataviz palette validator against both page colours of each mode:
light #faf8f4 and #ffffff, dark #111318 and #1a1d24. All checks pass, covering the lightness band,
chroma, colour-vision-deficiency separation of neighbouring slots and the normal-vision floor. In
light mode, green and yellow reach less than 3:1 against the page. A figure that uses them labels
the marks directly or has a legend. Changing a colour means validating again:

```sh
node validate_palette.js "#2f5bd3,#eb6834,#1baf7a,#eda100" --mode light --surface "#faf8f4"
node validate_palette.js "#5b84ea,#d95926,#199e70,#c98500" --mode dark --surface "#111318"
```

Text colours are tested in `tests/test_figkit.py`. Against every page, ink reaches at least 7:1,
secondary at least 4.5:1 and muted at least 3:1.

## 3. Type and layout

- Bricolage Grotesque for text, JetBrains Mono for numbers and identifiers (`figkit.value`,
  `figkit.bar_labels`, `figkit.mono_ticks`). Both fonts ship with the package under the SIL Open
  Font License. Text is stored as paths in the SVG, so a page needs neither font.
- The title sits at the top left (`figkit.title`), with an optional subtitle underneath. The legend
  sits at the top right on the line of the title (`figkit.legend_top`). A figure with a subtitle
  puts its legend inside the axes instead.
- Draw a full-width figure 6.4 in wide. Shown in a column of 800 CSS px, 9 pt text then comes out at
  about 15 px. Wider figures are scaled down to 6.4 in, narrower ones keep their size.
- Use a grid on one axis only, as hairlines. Category axes have no spine and no tick marks.
- Lines are 2 px wide. Markers are at least 6 pt, and only where points matter.

## 4. Files

```text
<name>.svg        light page, transparent, for the web
<name>-dark.svg   dark page, transparent
<name>.png        light page, transparent, 250 dpi (about 1600 px at full width)
<name>-dark.png   dark page, transparent
card.png          1200 x 630 social preview, opaque (CARD output)
```

Photographs and images with overlays use `PHOTO` (WebP and PNG) instead of SVG. The WebP is the
file for web pages; the PNG is a lossless copy for slides and documents. Every PNG is stored with a
palette of 256 colours and alpha: the opaque pixels get a median-cut palette, which keeps the tones
of a photograph without contour lines, and only the anti-aliased edges share the remaining entries.
Generated figures are never edited by hand. Each project has one command that writes all of them.

`figkit check <directory>` fails CI when a file has no pair, when a figure that should be
transparent is opaque, or when a file exceeds its budget: SVG 150 KB, PNG and WebP 250 KB, and
750 KB for a PNG next to a WebP of the same name, the copy of a photograph.

## 5. Embedding

A README on GitHub:

```html
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/figures/recall-dark.svg">
  <img src="docs/figures/recall.svg" alt="Recall per class: all classes above 80 % except rolled-in scale at 74 %.">
</picture>
```

The portfolio (`src/components/base/Figure.astro`) reads the size from the SVG:

```astro
<Figure src="/images/projects/<project>/recall.svg"
        darkSrc="/images/projects/<project>/recall-dark.svg"
        alt="..." />
```

Slides, LinkedIn and tools without SVG take the PNG.

## 6. Alt text

Write what the figure shows, not what it looks like. Give the finding and the numbers that carry
it, in one or two sentences. "Bar chart of recall" is not an alt text; "Recall per class: all
classes above 80 % except rolled-in scale at 74 %" is.
