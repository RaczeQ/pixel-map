"""Main CLI module."""

from typing import Annotated, Optional, cast

import click
import typer

from pixel_map import __app_name__, __version__

VALID_EXAMPLE_FILES = ["london_buildings", "london_park", "london_water", "monaco_buildings"]
example_files_help_string = ", ".join(
    f"[bold dark_orange]{example}[/bold dark_orange]" for example in VALID_EXAMPLE_FILES
)

app = typer.Typer(context_settings={"help_option_names": ["-h", "--help"]}, rich_markup_mode="rich")

# TODO:
# - add option to select colours (pass list - must match number of files)
# - add option to select colours per type (polygon, linestring, point)
#   (pass list(s) - must match number of files)
# - define default colour schemes with option to select
#       --light (positron + blue)
#       or --dark (darkmatter + orange?) [default]
#       or --street (voyager + ???)
# - add option to select tileset (or no tileset) by name
# - add option to pass map height and width
# - add option to remove the panel (border)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} {__version__}")
        raise typer.Exit()


class BboxGeometryParser(click.ParamType):  # type: ignore
    """Parser for bounding boxes."""

    name = "BBOX"

    def convert(self, value, param=None, ctx=None):  # type: ignore
        """Convert parameter value."""
        try:
            bbox_values = tuple(float(x.strip()) for x in value.split(","))
            if len(bbox_values) == 4:
                return bbox_values
        except ValueError:  # ValueError raised when passing non-numbers to float()
            pass

        raise typer.BadParameter(
            "Cannot parse provided bounding box."
            " Valid value must contain 4 floating point numbers"
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
            help=(
                "Clip the map to a given [bold dark_orange]bounding box[/bold dark_orange]."
                " Expects 4 floating point numbers separated by commas."
            ),
            click_type=BboxGeometryParser(),
            show_default=False,
        ),
    ] = None,
    no_border: Annotated[
        bool,
        typer.Option(
            "--no-border/",
            "--fullscreen/",
            help=("Removes the border around the map."),
            show_default=False,
        ),
    ] = False,
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

    from pixel_map.plotter import plot_geo_data

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

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        plot_geo_data(
            files, bbox=cast(Optional[tuple[float, float, float, float]], bbox), no_border=no_border
        )


def main() -> None:
    """Run the CLI."""
    app(prog_name=__app_name__)  # pragma: no cover


if __name__ == "__main__":
    app(prog_name=__app_name__)  # pragma: no cover
