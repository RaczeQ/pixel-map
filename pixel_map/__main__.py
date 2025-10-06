"""Main CLI module."""

from contextlib import suppress
from typing import Annotated, Optional, cast

import click
import typer

from pixel_map import __app_name__, __version__
from pixel_map.renderers import AVAILABLE_RENDERERS

renderer_help_string = ", ".join(
    f"[bold dark_orange]{renderer}[/bold dark_orange]"
    for renderer in sorted(AVAILABLE_RENDERERS.keys())
)
VALID_EXAMPLE_FILES = ["london_buildings", "london_park", "london_water", "monaco_buildings"]
example_files_help_string = ", ".join(
    f"[bold dark_orange]{example}[/bold dark_orange]" for example in sorted(VALID_EXAMPLE_FILES)
)

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, rich_markup_mode="rich")

# TODO:
# - add option to select colours per type (polygon, linestring, point)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} {__version__}")
        raise typer.Exit()


class BboxParser(click.ParamType):  # type: ignore
    """Parser for bounding boxes."""

    name = "BBOX"

    def convert(self, value, param=None, ctx=None):  # type: ignore
        """Convert parameter value."""
        with suppress(ValueError):  # ValueError raised when passing non-numbers to float()
            bbox_values = tuple(float(x.strip()) for x in value.split(","))
            if len(bbox_values) == 4:
                return bbox_values

        raise typer.BadParameter(
            "Cannot parse provided bounding box."
            " Valid value must contain 4 floating point numbers"
            " separated by commas."
        ) from None


class ColorParser(click.ParamType):  # type: ignore
    """Parser for colours."""

    name = "COLOR"

    def convert(self, value, param=None, ctx=None):  # type: ignore
        """Convert parameter value."""
        with suppress(ValueError):  # ValueError raised when passing non-numbers to float()
            colors = [x.strip() for x in value.split(",")]
            return colors


class AlphaParser(click.ParamType):  # type: ignore
    """Parser for bounding boxes."""

    name = "FLOAT"

    def convert(self, value, param=None, ctx=None):  # type: ignore
        """Convert parameter value."""
        with suppress(ValueError):  # ValueError raised when passing non-numbers to float()
            alpha_values = [float(x.strip()) for x in value.split(",")]
            return alpha_values

        raise typer.BadParameter(
            "Cannot parse provided alpha values."
            " Valid value must contain floating point numbers"
            " separated by commas."
        ) from None


@app.command()  # type: ignore
def plot(
    files: Annotated[
        list[str],
        typer.Argument(
            help="List of files to display. Those could be any that can be opened by GeoPandas.",
            show_default=False,
        ),
    ],
    bbox: Annotated[
        Optional[str],
        typer.Option(
            "--bbox",
            "-b",
            help=(
                "Clip the map to a given [bold dark_orange]bounding box[/bold dark_orange]."
                " Expects 4 floating point numbers separated by commas."
            ),
            click_type=BboxParser(),
            show_default=False,
        ),
    ] = None,
    renderer: Annotated[
        str,
        typer.Option(
            "--renderer",
            "-r",
            help=(
                "Renderer used for generating terminal output."
                f" Possible values: {renderer_help_string}."
            ),
            case_sensitive=False,
            show_default="block",
            is_eager=True,
        ),
    ] = "block",
    is_dark_style: Annotated[
        bool,
        typer.Option(
            "--dark/--light",
            help=(
                "Uses the predefined dark or light style. Can be overriden with user defined style."
            ),
            show_default=True,
        ),
    ] = True,
    colors: Annotated[
        Optional[str],
        typer.Option(
            "--color",
            "-c",
            help=("Pass color or list of colours per each geo file."),
            click_type=ColorParser(),
            show_default=False,
        ),
    ] = None,
    alphas: Annotated[
        Optional[str],
        typer.Option(
            "--alpha",
            "--opacity",
            "-a",
            help=("Pass opacity or list of opacities per each geo file."),
            click_type=AlphaParser(),
            show_default=False,
        ),
    ] = None,
    basemap_provider: Annotated[
        Optional[str],
        typer.Option(
            "--basemap",
            "--tileset",
            "-t",
            metavar="TILES",
            help=(
                "Set the basemap provider. Can be any value parsed by xyzservices library."
                " Defaults to [bold dark_orange]CartoDB.DarkMatterNoLabels[/bold dark_orange]"
                " if --dark or [bold dark_orange]CartoDB.PositronNoLabels[/bold dark_orange]"
                " if --light."
            ),
            show_default=False,
        ),
    ] = None,
    no_border: Annotated[
        bool,
        typer.Option(
            "--no-border/",
            "--fullscreen/",
            "-f/",
            help=("Removes the border around the map."),
            show_default=False,
        ),
    ] = False,
    no_background: Annotated[
        bool,
        typer.Option(
            "--no-background/",
            "--no-bg/",
            help=("Removes the background of the map and plots only geo data."),
            show_default=False,
        ),
    ] = False,
    background_color: Annotated[
        Optional[str],
        typer.Option(
            "--background-color",
            "--bg-color",
            metavar="COLOR",
            help=("Set the background color. Can be used together with --no-background."),
            show_default=False,
        ),
    ] = None,
    console_width: Annotated[
        Optional[int],
        typer.Option(
            "--width",
            metavar="INT",
            help=("Override the current console width."),
            show_default=False,
        ),
    ] = None,
    console_height: Annotated[
        Optional[int],
        typer.Option(
            "--height",
            metavar="INT",
            help=("Override the current console height."),
            show_default=False,
        ),
    ] = None,
    plotting_dpi: Annotated[
        int,
        typer.Option(
            "--dpi",
            metavar="INT",
            help=("DPI used to get better quality matplotlib plot before rendering to terminal."),
            show_default=True,
        ),
    ] = 10,
    example_files: Annotated[
        bool,
        typer.Option(
            "--example/",
            "--example-files/",
            help=(
                "Can be used to load one of example files based on name."
                f" Possible values: {example_files_help_string}."
            ),
            show_default=False,
        ),
    ] = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            help="Show the application's version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """
    Plot the geo data into a terminal.

    Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
    unicode characters.
    """
    import warnings

    from pixel_map.plotter import (
        get_predefined_dark_style,
        get_predefined_light_style,
        plot_geo_data,
    )

    if renderer not in AVAILABLE_RENDERERS:
        raise typer.BadParameter(f"Provided renderer {renderer} doesn't exist.") from None

    if example_files:
        from pathlib import Path

        loaded_example_files = []
        for file_name in files:
            if file_name not in VALID_EXAMPLE_FILES:
                raise typer.BadParameter(
                    f"Provided file {file_name} doesn't exist in examples."
                ) from None
            loaded_example_files.append(
                (Path(__file__).parent / "example_files" / f"{file_name}.parquet").as_posix()
            )
        files = loaded_example_files

    if is_dark_style:
        provider, color = get_predefined_dark_style()
    else:
        provider, color = get_predefined_light_style()

    if not basemap_provider:
        basemap_provider = provider

    background_color = background_color or ("black" if is_dark_style else "white")

    if no_background:
        basemap_provider = None

    parsed_colors: Optional[list[str]] = colors  # type: ignore[assignment]
    if not parsed_colors:
        parsed_colors = [color]

    parsed_alphas: Optional[list[float]] = alphas  # type: ignore[assignment]
    if not parsed_alphas:
        parsed_alphas = [1]

    if len(parsed_colors) > 1 and len(parsed_colors) != len(files):
        raise typer.BadParameter(
            f"Number of colors ({len(parsed_colors)}) and geo files ({len(files)}) doesn't match."
        ) from None

    if len(parsed_alphas) > 1 and len(parsed_alphas) != len(files):
        raise typer.BadParameter(
            f"Number of alphas ({len(parsed_alphas)}) and geo files ({len(files)}) doesn't match."
        ) from None

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        plot_geo_data(
            files,
            renderer=renderer,
            bbox=cast("Optional[tuple[float, float, float, float]]", bbox),
            color=parsed_colors,
            alpha=parsed_alphas,
            basemap_provider=basemap_provider,
            background_color=background_color or "black",
            no_border=no_border,
            console_width=console_width,
            console_height=console_height,
            plotting_dpi=plotting_dpi,
        )


def main() -> None:
    """Run the CLI."""
    app(prog_name=__app_name__)  # pragma: no cover


if __name__ == "__main__":
    app(prog_name=__app_name__)  # pragma: no cover
