# pixel-map

Python CLI tool for plotting geo data in the terminal

<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/pixel-map-monaco.jpg"><br/>
</p>

<p align="center">
    <img alt="GitHub" src="https://img.shields.io/github/license/raczeq/pixel-map?logo=mit&logoColor=%23fff">
    <img src="https://img.shields.io/github/checks-status/raczeq/pixel-map/main?logo=GitHubActions&logoColor=%23fff" alt="Checks">
    <a href="https://github.com/raczeq/pixel-map/actions/workflows/ci-prod.yml" target="_blank">
        <img alt="GitHub Workflow Status - PROD" src="https://img.shields.io/github/actions/workflow/status/raczeq/pixel-map/ci-prod.yml?label=build-prod&logo=GitHubActions&logoColor=%23fff">
    </a>
    <a href="https://results.pre-commit.ci/latest/github/raczeq/pixel-map/main" target="_blank">
        <img src="https://results.pre-commit.ci/badge/github/raczeq/pixel-map/main.svg" alt="pre-commit.ci status">
    </a>
    <a href="https://www.codefactor.io/repository/github/raczeq/pixel-map"><img alt="CodeFactor Grade" src="https://img.shields.io/codefactor/grade/github/raczeq/pixel-map?logo=codefactor&logoColor=%23fff"></a>
    <a href="https://app.codecov.io/gh/raczeq/pixel-map/tree/main"><img alt="Codecov" src="https://img.shields.io/codecov/c/github/raczeq/pixel-map?logo=codecov&token=PRS4E02ZX0&logoColor=%23fff"></a>
    <a href="https://pypi.org/project/pixel-map" target="_blank">
        <img src="https://img.shields.io/pypi/v/pixel-map?color=%2334D058&label=pypi%20package&logo=pypi&logoColor=%23fff" alt="Package version">
    </a>
    <a href="https://pypi.org/project/pixel-map" target="_blank">
        <img src="https://img.shields.io/pypi/pyversions/pixel-map.svg?color=%2334D058&logo=python&logoColor=%23fff" alt="Supported Python versions">
    </a>
    <a href="https://pypi.org/project/pixel-map" target="_blank">
        <img alt="PyPI - Downloads" src="https://img.shields.io/pypi/dm/pixel-map">
    </a>
</p>

## Installation

PyPI:

```sh
$ pip install img2unicode
```

uv:

```sh
$ uv pip install img2unicode
```

## Usage

To display your data in the terminal, you can just pass a filename as an argument:
```sh
$ pixel-map <file_name>
```

Tool can also display data for multiple files at once:
```sh
$ pixel-map <file_name_1> <file_name_2>
```

See more examples below ⬇️

<details>
  <summary>CLI Help output (<code>pixel-map -h</code>)</summary>

```console
 Usage: pixel-map [OPTIONS] FILES...

 Plot the geo data into a terminal.
 Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
 unicode characters.

╭─ Arguments ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    files      FILES...  List of files to display. Those could be any that can be opened by GeoPandas. [required]                                                                │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --bbox                         -b             BBOX   Clip the map to a given bounding box. Expects 4 floating point numbers separated by commas.                                  │
│ --renderer                     -r             TEXT   Renderer used for generating terminal output. Possible values: all, ascii, ascii-bw, block, braille, braille-bw, half, quad, │
│                                                      space.                                                                                                                       │
│                                                      [default: (block)]                                                                                                           │
│ --dark                             --light           Uses the predefined dark or light style. Can be overriden with user defined style. [default: dark]                           │
│ --color                        -c             COLOR  Pass color or list of colours per each geo file.                                                                             │
│ --alpha,--opacity              -a             FLOAT  Pass opacity or list of opacities per each geo file.                                                                         │
│ --basemap,--tileset            -t             TILES  Set the basemap provider. Can be any value parsed by xyzservices library. Defaults to CartoDB.DarkMatterNoLabels if --dark   │
│                                                      or CartoDB.PositronNoLabels if --light.                                                                                      │
│ --no-border,--fullscreen       -f                    Removes the border around the map.                                                                                           │
│ --no-background,--no-bg                              Removes the background of the map and plots only geo data.                                                                   │
│ --background-color,--bg-color                 COLOR  Set the background color. Can be used together with --no-background.                                                         │
│ --width                                       INT    Override the current console width.                                                                                          │
│ --height                                      INT    Override the current console height.                                                                                         │
│ --dpi                                         INT    DPI used to get better quality matplotlib plot before rendering to terminal. [default: 10]                                   │
│ --example,--example-files                            Can be used to load one of example files based on name. Possible values: london_buildings, london_park, london_water,        │
│                                                      monaco_buildings.                                                                                                            │
│ --version                      -v                    Show the application's version and exit.                                                                                     │
│ --install-completion                                 Install completion for the current shell.                                                                                    │
│ --show-completion                                    Show completion for the current shell, to copy it or customize the installation.                                             │
│ --help                         -h                    Show this message and exit.                                                                                                  │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```
</details>

## Examples

`pixel-map` is published with few example files for testing.

#### Basic usage

```sh
$ pixel-map --example london_buildings
```
<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/london_dark.jpg"><br/>
</p>

#### Light mode

```sh
$ pixel-map --example london_buildings --light
```
<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/london_light.jpg"><br/>
</p>

#### Multiple files with different colors

```sh
$ pixel-map --example london_buildings london_water london_park -c C1,C0,C2
```
<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/london_multiple.jpg"><br/>
</p>

#### Different basemap and changed opacity (alpha)

```sh
$ pixel-map --example london_water -c C0 -a 0.6 -t Esri.WorldImagery
```
<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/london_satellite.jpg"><br/>
</p>

#### No background and different renderer

You can explore multiple available renderers. Full list available in the `pixel-map` CLI help.

```sh
$ pixel-map --example london_buildings --no-bg -r ascii-bw
```
<p align="center">
  <img src="https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/london_ascii.jpg"><br/>
</p>

## Dependencies

- `typer[all] (>=0.9.0)` (click, colorama, rich, shellingham): Required for CLI

- `rich (>=12.0.0)`: For showing progress and generating terminal output

- `geopandas (>=0.6)`: For reading Geo files and plotting

- `pyarrow (>=16.0.0)`: For geoparquet files support

- `matplotlib (>=3.2.0)`: For generating the plot with styling and cropping

- `contextily (>=1)`: For adding basemap to the plot

- `numpy (>=1.26.0)`: For transforming matplotlib array into an image

- `img2unicode[n2] (>=0.1a11)`: For transforming generated plot image into a list of unicode characters for the terminal

## How does it work?

1. Files are read by `GeoPandas` to GeoSerieses.
2. `Matplotlib` figure is created with the size of the terminal (`pixel-map` expects a default monospace font with the ratio of 8 to 16 pixels. Figure canvas takes terminal height and multiplies it by two).
3. GeoSerieses are plotted to the canvas.
4. Plot bounding box is expanded to the canvas ratio (based on terminal size).
5. Basemap is loaded with `contextily`.
6. Canvas is copied to the image as an `NumPy` array.
7. `img2unicode` is used to render image using unicode characters with color.
8. `Rich` string output is generated using the list of unicode characters with background and foreground colors.
9. Output is printed to the console.

## FAQ

- **Why does my terminal render visible characters in the output?**

  Check if your terminal doesn't have automatic contrast changer for WCAG compatibility.

  For example in VS Code there is an option `terminal.integrated.minimumContrastRatio` that is set to `4.5` by default.

  | Contrast: 4.5 | Contrast: 1 |
  | --- | --- |
  | ![](https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/monaco_contrast.jpg) | ![](https://raw.githubusercontent.com/RaczeQ/pixel-map/main/images/monaco_contrast_low.jpg) |

- **Why are there black bars on the left/right, top/bottom of the output?**

  This can happen when output is bigger than Earth bounding box and basemap doesn't cover that far, but image is stretched to the full terminal size.

## Contributing

If you want to contribute, please fork the repository, use `pdm` tool to install the project.

To run the tests you can use command `tox -e python3.12` (or other python version, `-e` is for the environment) or with simple `pytest tests`.

Please remember to update `CHANGELOG.md` with description your changes.
