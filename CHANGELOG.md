# Changelog

Every release of figkit, newest first. Versions follow [Semantic Versioning](https://semver.org);
before 1.0 a minor version may break the API. The GitHub release of a tag takes its notes from the
section of that version.

## [Unreleased]

### Added

- Each release attaches the wheel and the source archive. CI builds both and checks that the
  installed wheel renders figures with the bundled fonts.

## [0.3.0] - 2026-11-19

### Breaking changes

- Importing figkit leaves the matplotlib backend alone. It no longer switches to `Agg`, so
  `plt.show()` and notebooks keep their backend. A batch job that only writes files can set
  `MPLBACKEND=Agg`.
- A theme other than `light` and `dark` writes `<name>[.<language>]-<theme>.<format>` instead of
  overwriting the light files.
- German figures can change on the next render: bar values, numbers at the end of a sentence and
  category names with numbers are written differently, see below.

### Fixed

- `localize` converts a number followed by a full stop: `F1 is 0.95.` becomes `F1 is 0,95.`.
  Versions such as `v0.1.2` stay as they are.
- `bar_labels` writes the values it formats in the language of the figure, `0,93` in German.
  Texts passed as `labels` stay as given.
- German tick labels leave category names unchanged when the categories are plotted as strings,
  such as `ax.bar(["1.5 mm", ...])`.
- SVGs with embedded images, such as heatmaps drawn with `imshow`, are byte-identical on Linux and
  Windows. Before, Pillow builds compressed the same pixels to different bytes.
- `Theme` is hashable and its `status` colours are read-only.
- `figkit check` reports a malformed `figures.json` (invalid JSON, wrong types, missing files)
  instead of failing with a traceback.
- `figkit check --opaque card` also covers the language files `card.de.png` and `card.en.png`.
- `page_entry` reads the size of raster files from the dpi or pixel width of their output instead
  of assuming 250 dpi.

### CI

- Tests run on Ubuntu and Windows. CI regenerates the example gallery and fails if an SVG changes.
- pre-commit runs ruff from `uv.lock`, so the hook and CI use the same version.

## [0.2.1] - 2026-11-10

### Added

- `page_entry` reads the manifest entry of a figure from files that a separate step wrote, such
  as a figure that needs a trained model. One step can still write the manifest of all figures.

## [0.2.0] - 2026-11-10

### Added

- `render` takes a `language` and a `headless` flag. German tick labels and `figkit.number` use a
  decimal comma, a thousands dot and a spaced percent sign.
- `page` writes a figure without its title in every language, and `write_manifest` lists the
  files with their titles and alt texts in `figures.json`.
- `figkit check` reports missing languages, gaps in the manifest and, with `--tokens`, page
  colours that differ from the website's stylesheet.

### Changed

- `render` rejects text below 8 pt, because pages scale the canvas down on phones.

## [0.1.2] - 2026-11-10

### Added

- Web figures are exactly 6.4 in wide, the PNG 1600 px, so text has the same size in every
  figure.
- `figkit check` fails on figures off the canvas width; `--any-width` skips the check.
- `line_labels` places direct labels at the ends of lines.

### Fixed

- `render` names the figure that does not fit the canvas.
- SVG files have LF line ends on every platform.
- Every mathtext face points to the bundled fonts, so Linux finds no missing family.
- The PNG budget of photographs is 1 MB, enough for full-width grids on the fixed canvas.

## [0.1.1] - 2026-11-10

### Fixed

- Palette PNGs keep the tones of photographs. Photo PNGs may be larger.
- Bold mathtext uses the bundled semibold.

## [0.1.0] - 2026-11-10

### Added

- Light and dark themes from the portfolio tokens, with bundled Bricolage Grotesque and
  JetBrains Mono.
- Transparent SVG and PNG export with byte-identical SVGs, plus WebP for photographs and an
  opaque Open Graph card.
- Helpers for titles, legends, grids, percent axes, values, bar labels and reference lines; the
  label of a vertical reference line goes on either side.
- `figkit check` for light/dark pairs, transparency and file sizes.

[Unreleased]: https://github.com/BenBotsch/FigureKit/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/BenBotsch/FigureKit/compare/v0.2.1...v0.3.0
[0.2.1]: https://github.com/BenBotsch/FigureKit/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/BenBotsch/FigureKit/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/BenBotsch/FigureKit/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/BenBotsch/FigureKit/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/BenBotsch/FigureKit/releases/tag/v0.1.0
