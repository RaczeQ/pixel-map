"""Main CLI module."""

from typing import Annotated, Optional

import click
import typer

from pixel_map import __app_name__, __version__

app = typer.Typer(
    context_settings={"help_option_names": ["-h", "--help"]}, rich_markup_mode="rich"
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"{__app_name__} {__version__}")
        raise typer.Exit()


class BboxGeometryParser(click.ParamType):  # type: ignore
    """Parser for geometry in WKT form."""

    name = "BBOX"

    def convert(self, value, param=None, ctx=None):  # type: ignore
        """Convert parameter value."""
        try:
            bbox_values = tuple(float(x.strip()) for x in value.split(","))
            return bbox_values
        except ValueError:  # ValueError raised when passing non-numbers to float()
            raise typer.BadParameter(
                "Cannot parse provided bounding box."
                " Valid value must contain 4 floating point numbers"
                " separated by commas."
            ) from None


@app.command()
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
    from pixel_map.plotter import plot_geo_data
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore")
        plot_geo_data(files, bbox=bbox)


def main() -> None:
    app(prog_name=__app_name__)  # pragma: no cover


if __name__ == "__main__":
    app(prog_name=__app_name__)  # pragma: no cover
