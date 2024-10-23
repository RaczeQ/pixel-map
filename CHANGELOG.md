# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/RaczeQ/pixel-map/compare/0.2.0...HEAD

[0.2.0]: https://github.com/RaczeQ/pixel-map/compare/0.1.2...0.2.0

[0.1.2]: https://github.com/RaczeQ/pixel-map/compare/0.1.1...0.1.2

[0.1.1]: https://github.com/RaczeQ/pixel-map/releases/tag/0.1.1
