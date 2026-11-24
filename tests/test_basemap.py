"""Tests for basemaps."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from matplotlib import pyplot as plt
from ml2drender import Renderer
from pytest_mock import MockerFixture
from typer.testing import CliRunner

from pixel_map.__main__ import app
from pixel_map.plotter import _add_basemap

runner = CliRunner()

LABEL = {"type": "Feature", "properties": {}, "geometry": {"type": "Point", "coordinates": [0, 0]}}


@pytest.fixture  # type: ignore
def style(tmp_path: Path) -> str:
    """Red style with a label, whose glyphs cannot be loaded."""
    path = tmp_path / "style.json"
    layers = [
        {"id": "red", "type": "background", "paint": {"background-color": "#ff0000"}},
        {"id": "label", "type": "symbol", "source": "label", "layout": {"text-field": "label"}},
    ]
    document = {
        "version": 8,
        "glyphs": (tmp_path / "{fontstack}" / "{range}.pbf").as_uri(),
        "sources": {"label": {"type": "geojson", "data": LABEL}},
        "layers": layers,
    }
    path.write_text(json.dumps(document))
    return path.as_posix()


@pytest.mark.parametrize("dpi", [1, 8, 100])  # type: ignore
def test_resolution(style: str, dpi: int) -> None:
    """Test if basemap has the resolution of the renderers, without labels, whatever the dpi."""
    figure, ax = plt.subplots(figsize=(20, 10), dpi=dpi)
    ax.set_position((0, 0, 1, 1))
    ax.axis((-2000, 2000, -1000, 1000))

    _add_basemap(ax, style)

    image = ax.images[0].get_array()
    assert image.shape[:2] == (80, 160)
    assert (image[..., :3] == [255, 0, 0]).all()
    plt.close(figure)


def test_rendered_once(style: str, mocker: MockerFixture) -> None:
    """Test if basemap isn't rendered again when the canvas is drawn."""
    render = mocker.spy(Renderer, "projected")

    result = runner.invoke(app, ["--example", "monaco_buildings", "-t", style])

    assert result.exit_code == 0
    assert render.call_count == 1


@pytest.mark.parametrize(
    "bbox", ["-180,-85,180,85", "7.41855,43.73259,7.42227,43.73528"]
)  # type: ignore
def test_bbox(style: str, bbox: str) -> None:
    """Test if basemap is drawn for the world and for a few streets."""
    result = runner.invoke(app, ["--example", "monaco_buildings", "-t", style, "--bbox", bbox])

    assert result.exit_code == 0


@pytest.mark.parametrize(
    "args,source", [(["--dark"], "OpenFreeMap.Dark"), (["--light"], "OpenFreeMap.Positron")]
)  # type: ignore
def test_default_basemaps(args: list[str], source: str, mocker: MockerFixture) -> None:
    """Test if default basemaps are OpenFreeMap styles without labels."""
    add_basemap = mocker.patch("pixel_map.plotter.bml.add_basemap")

    result = runner.invoke(app, ["--example", "monaco_buildings", *args])

    assert result.exit_code == 0
    (call,) = add_basemap.call_args_list
    assert call.kwargs["source"] == source
    assert call.kwargs["labels"] is False


def test_no_background(mocker: MockerFixture) -> None:
    """Test if basemap isn't drawn without background."""
    add_basemap = mocker.patch("pixel_map.plotter.bml.add_basemap")

    result = runner.invoke(app, ["--example", "monaco_buildings", "--no-bg"])

    assert result.exit_code == 0
    assert not add_basemap.called


def test_raster_tiles_with_contextily(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test if raster tiles are left to contextily."""
    calls: list[dict[str, Any]] = []
    contextily = SimpleNamespace(add_basemap=lambda ax, **kwargs: calls.append(kwargs))
    monkeypatch.setitem(sys.modules, "contextily", contextily)

    result = runner.invoke(app, ["--example", "monaco_buildings", "-t", "Esri.WorldImagery"])

    assert result.exit_code == 0
    assert [call["source"] for call in calls] == ["Esri.WorldImagery"]


def test_raster_tiles_without_contextily(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test if missing contextily is reported."""
    monkeypatch.setitem(sys.modules, "contextily", None)

    result = runner.invoke(app, ["--example", "monaco_buildings", "-t", "Esri.WorldImagery"])

    assert result.exit_code == 2
    # The lines are wrapped in a box.
    assert "pip install contextily" in " ".join(result.output.replace("│", " ").split())


def test_misspelled_style() -> None:
    """Test if a similar name of a style is suggested."""
    result = runner.invoke(app, ["--example", "monaco_buildings", "-t", "OpenFreeMap.Positro"])

    assert result.exit_code == 2
    assert "OpenFreeMap.Positron" in result.output
