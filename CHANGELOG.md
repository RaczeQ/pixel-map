# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Replaced the `img2unicode` dependency with a native dual-colour terminal
  renderer (`pixel_map/terminal_renderers.py`).  The new engine rasterises
  glyph templates (geometric for half/quad/braille/block, Pillow for ASCII) and
  selects the best character per cell via a fully vectorised Lab-distance
  optimisation, yielding a 4x-60x speed-up over `img2unicode` while keeping the
  exact `render_numpy(image) -> (characters, fg_colors, bg_colors)` contract.
  All nine renderer names are preserved: `block`, `all`, `ascii`, `space`,
  `half`, `quad`, `braille`, `braille-bw`, `ascii-bw`.
- Dropped Python 3.9 support (EOL since October 2025; no numpy wheel exists for
  both 3.9 and 3.13).  Minimum is now Python 3.10.
- The native renderer now has a fast path that skips the Pillow resize when the
  matplotlib canvas dimensions already match the subpixel grid (achievable with
  `--dpi 8`), and a row-averaged binreduce for the common 2:1 cell-aspect case.

### Fixed

- Fixed a `ValueError: cannot reshape array` on high-DPI (Retina) displays
  where the matplotlib canvas buffer is physically larger than
  `get_width_height()` reports.  The reshape now uses
  `get_width_height(physical=True)` and derives correct dimensions from the
  buffer pixel count.
- Replaced the removed `canvas.tostring_rgb()` with `canvas.buffer_rgba()` for
  matplotlib 3.10+ compatibility.

### Removed

- `img2unicode` (and its transitive heavy dependencies `scikit-image`,
  `scikit-learn` and the Linux-only `n2` ANN library) are no longer required.
  `pillow` is now a direct dependency.

## [0.2.4] - 2024-11-14

### Fixed

- Added automatic bounds checking when providing custom bounding box

## [0.2.3] - 2024-11-01

### Changed

- Bumped minimal geopandas version

## [0.2.2] - 2024-10-23

## [0.2.1] - 2024-10-23

### Added

- Option to pass console width and height
- Option to pass plotting DPI

### Fixed

- Automatic bounds clipping to the EPSG:3857 limits
- Capped minimal contextily zoom at 0

## [0.2.0] - 2024-10-21

### Added

- Option to change colors
- Option to change opacity
- Option to change basemap
- Default light and dark style
- Single letter flags to the CLI

### Changed

- Subtitle rendering

### Fixed

- Canvas not filling the space fully

## [0.1.2] - 2024-10-21

### Added

- Multiple renderers
- Option to disable border around the map
- Title scaling based on terminal width
- Example geo files

### Changed

- Cleaned dependencies list

## [0.1.1] - 2024-10-18

### Added

- Plotting basic functionality with CLI

[Unreleased]: https://github.com/RaczeQ/pixel-map/compare/0.2.4...HEAD

[0.2.4]: https://github.com/RaczeQ/pixel-map/compare/0.2.3...0.2.4

[0.2.3]: https://github.com/RaczeQ/pixel-map/compare/0.2.2...0.2.3

[0.2.2]: https://github.com/RaczeQ/pixel-map/compare/0.2.1...0.2.2

[0.2.1]: https://github.com/RaczeQ/pixel-map/compare/0.2.0...0.2.1

[0.2.0]: https://github.com/RaczeQ/pixel-map/compare/0.1.2...0.2.0

[0.1.2]: https://github.com/RaczeQ/pixel-map/compare/0.1.1...0.1.2

[0.1.1]: https://github.com/RaczeQ/pixel-map/releases/tag/0.1.1
