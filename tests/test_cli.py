"""Tests for CLI."""

import uuid

import pytest
from parametrization import Parametrization as P
from typer.testing import CliRunner

from pixel_map import __app_name__, __version__
from pixel_map.__main__ import app
from pixel_map.renderers import AVAILABLE_RENDERERS

runner = CliRunner()


def random_str() -> str:
    """Return random string."""
    return str(uuid.uuid4())


def test_version() -> None:
    """Test if version is properly returned."""
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert f"{__app_name__} {__version__}\n" in result.stdout


def test_pbf_file_or_geometry_filter_is_required() -> None:
    """Test if cannot run without pbf file and without geometry filter."""
    result = runner.invoke(
        app,
    )

    assert result.exit_code == 2
    assert "Missing argument 'FILES...'." in result.stdout


def test_basic_run() -> None:
    """Test if runs properly without options."""
    result = runner.invoke(app, ["--example", "monaco_buildings"])

    assert result.exit_code == 0
    assert "monaco_buildings.parquet" in result.stdout


@P.parameters("args")  # type: ignore
@P.case("Dark mode", ["--dark"])  # type: ignore
@P.case("Light mode", ["--light"])  # type: ignore
@P.case("Bounding box short", ["-b", "7.41855,43.73259,7.42227,43.73528"])  # type: ignore
@P.case("Bounding box long", ["--bbox", "7.41855, 43.73259, 7.42227, 43.73528"])  # type: ignore
@P.case("Renderer short", ["-r", "ascii"])  # type: ignore
@P.case("Renderer long", ["--renderer", "ascii"])  # type: ignore
@P.case("Color short", ["-c", "green"])  # type: ignore
@P.case("Color long", ["--color", "red"])  # type: ignore
@P.case("Color multiple", ["london_buildings", "-c", "C0"])  # type: ignore
@P.case("Color multiple 2", ["london_buildings", "-c", "C0,C1"])  # type: ignore
@P.case("Opacity short", ["-a", "0.8"])  # type: ignore
@P.case("Opacity long", ["--alpha", "0.6"])  # type: ignore
@P.case("Opacity long 2", ["--opacity", "0.3"])  # type: ignore
@P.case("Opacity multiple", ["london_buildings", "-a", "0"])  # type: ignore
@P.case("Opacity multiple 2", ["london_buildings", "-a", "0,1"])  # type: ignore
@P.case("Tileset short", ["-t", "CartoDB.DarkMatterNoLabels"])  # type: ignore
@P.case("Tileset long", ["--tileset", "CartoDB.DarkMatterNoLabels"])  # type: ignore
@P.case("Tileset long 2", ["--basemap", "CartoDB.DarkMatterNoLabels"])  # type: ignore
@P.case("No border short", ["-f"])  # type: ignore
@P.case("No border long", ["--fullscreen"])  # type: ignore
@P.case("No border long 2", ["--no-border"])  # type: ignore
@P.case("No background", ["--no-bg"])  # type: ignore
@P.case("No background 2", ["--no-background"])  # type: ignore
@P.case("Background color", ["--bg-color", "white"])  # type: ignore
@P.case("Background color 2", ["--background-color", "black"])  # type: ignore
@P.case("Console width", ["--width", "10"])  # type: ignore
@P.case("Console height", ["--height", "10"])  # type: ignore
@P.case("Console width and height", ["--width", "10", "--height", "10"])  # type: ignore
def test_proper_args(args: list[str]) -> None:
    """Test if runs properly with options."""
    result = runner.invoke(app, ["--example", "monaco_buildings", *args])

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "renderer",
    AVAILABLE_RENDERERS.keys(),
)  # type: ignore
def test_renderers(renderer: str) -> None:
    """Test if all renderers are working."""
    result = runner.invoke(app, ["--example", "monaco_buildings", "-r", renderer])

    assert result.exit_code == 0


@P.parameters("args")  # type: ignore
@P.case(
    "Random file",
    [random_str()],
)  # type: ignore
@P.case("Short bounding box", ["-b", "7.41855,43.73259,7.42227,"])  # type: ignore
@P.case("Long bounding box", ["-b", "7.41855,43.73259,7.42227,43.73528,7.42227"])  # type: ignore
@P.case("Wrong renderer", ["-r", random_str()])  # type: ignore
@P.case("Wrong tileset", ["-t", random_str()])  # type: ignore
@P.case("Wrong color", ["-c", random_str()])  # type: ignore
@P.case("Wrong opacity", ["-a", random_str()])  # type: ignore
@P.case("Wrong background color", ["--bg-color", random_str()])  # type: ignore
@P.case("Wrong number of colors", ["london_buildings", "-c", "C0,C1,C2"])  # type: ignore
def test_wrong_args(args: list[str], capsys: pytest.CaptureFixture) -> None:
    """Test if doesn't run properly with options."""
    # Fix for the I/O error from the Click repository
    # https://github.com/pallets/click/issues/824#issuecomment-1583293065
    with capsys.disabled():
        result = runner.invoke(app, ["--example", "monaco_buildings", *args])
        assert result.exit_code != 0
