"""
Plotting functionality.

Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
unicode characters.
"""

from pathlib import Path
from typing import Any, Optional

import contextily as cx
import geopandas as gpd
import img2unicode
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from pyproj import Transformer
from pyproj.enums import TransformDirection
from rich import get_console
from rich.progress import Progress, SpinnerColumn, TextColumn


def plot_geo_data(
    files: list[str], bbox: Optional[tuple[float, float, float, float]] = None
) -> None:
    """
    Plot a geo data into a terminal.

    Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
    unicode characters.

    Args:
        files (list[str]): List of files to plot.
        bbox (Optional[tuple[float, float, float, float]], optional): Bounding box used to clip the
            geo data. Defaults to None.
    """
    console = get_console()

    terminal_width = console.width
    terminal_height = console.height - 1

    map_width = terminal_width
    map_height = terminal_height * 2

    map_ratio = map_width / map_height

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Calculating bounding box", total=None)
        bbox_axes_bounds = None
        if bbox:
            bbox, bbox_axes_bounds = _expand_bbox_to_match_ratio(bbox, ratio=map_ratio)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Loading Geo data", total=None)
        gdf = _load_geo_data(files, bbox=bbox)
        if bbox:
            gdf = gdf.clip_by_rect(*bbox)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Plotting geo data", total=None)
        f, ax = plt.subplots(figsize=(map_width, map_height), dpi=10)
        f.patch.set_facecolor("black")
        canvas = f.canvas
        gdf.to_crs(3857).plot(ax=ax, alpha=0.4)
        ax.axis("off")
        ax.margins(0)

        if bbox_axes_bounds:
            left, bottom, right, top = bbox_axes_bounds
            ax.set_xlim([left, right])
            ax.set_ylim([bottom, top])

        _expand_axes_limit_to_match_ratio(ax, ratio=map_ratio)
        # cx.add_basemap(
        #     ax,
        #     source=cx.providers.CartoDB.PositronNoLabels,
        #     crs=3857,
        #     attribution=False,
        # )
        cx.add_basemap(
            ax,
            source=cx.providers.CartoDB.DarkMatterNoLabels,
            crs=3857,
            attribution=False,
        )
        # cx.add_basemap(
        #     ax,
        #     source=cx.providers.CartoDB.VoyagerNoLabels,
        #     crs=3857,
        #     attribution=False,
        # )
        f.tight_layout()
        canvas.draw()
        image_flat = np.frombuffer(canvas.tostring_rgb(), dtype="uint8")  # (H * W * 3,)
        image = image_flat.reshape(*reversed(canvas.get_width_height()), 3)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        progress.add_task("Rendering geo data", total=None)
        fast_renderer = img2unicode.Renderer(
            # img2unicode.FastGenericDualOptimizer(),
            # img2unicode.ExactGenericDualOptimizer("block"),
            # img2unicode.FastQuadDualOptimizer(),
            img2unicode.FastGenericDualOptimizer("block"),
            # img2unicode.FastGammaOptimizer("no_block"),
            max_h=terminal_height,
            max_w=terminal_width,
            allow_upscale=True,
        )
        characters, foreground_colors, background_colors = fast_renderer.render_numpy(image)
        # braille_renderer = img2unicode.GammaRenderer(
        #     img2unicode.BestGammaOptimizer(True, "braille"),
        #     max_h=terminal_height,
        #     max_w=terminal_width,
        #     allow_upscale=True,
        # )
        # characters, foreground_colors, background_colors  = braille_renderer.render_numpy(image)
        full_rich_string = _construct_full_rich_string(
            characters, foreground_colors, background_colors
        )
    console.print(full_rich_string)


def _load_geo_data(
    files: list[str], bbox: Optional[tuple[float, float, float, float]] = None
) -> gpd.GeoSeries:
    paths = [Path(file_path) for file_path in files]
    return gpd.pd.concat(
        [
            (
                _read_geoparquet_file(path, bbox=bbox).geometry
                if path.suffix == ".parquet"
                else gpd.read_file(path, bbox=bbox).geometry
            )
            for path in paths
        ]
    )


def _read_geoparquet_file(
    path: Path, bbox: Optional[tuple[float, float, float, float]] = None
) -> gpd.GeoDataFrame:
    try:
        return gpd.read_parquet(path, bbox=bbox)
    except Exception:
        return gpd.read_parquet(path)


def _expand_bbox_to_match_ratio(
    bbox: tuple[float, float, float, float], ratio: float
) -> tuple[tuple[float, float, float, float], tuple[float, float, float, float]]:
    minx, miny, maxx, maxy = bbox

    transformer = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)
    left, bottom = transformer.transform(minx, miny)
    right, top = transformer.transform(maxx, maxy)

    width = right - left
    height = top - bottom
    current_ratio = width / height
    if current_ratio < ratio:
        new_width = (ratio / current_ratio) * width
        width_padding = (new_width - width) / 2
        left = left - width_padding
        right = right + width_padding
    else:
        new_height = (current_ratio / ratio) * height
        height_padding = (new_height - height) / 2
        bottom = bottom - height_padding
        top = top + height_padding

    new_minx, new_miny = transformer.transform(left, bottom, direction=TransformDirection.INVERSE)
    new_maxx, new_maxy = transformer.transform(right, top, direction=TransformDirection.INVERSE)

    return (new_minx, new_miny, new_maxx, new_maxy), (left, bottom, right, top)


def _expand_axes_limit_to_match_ratio(ax: Axes, ratio: float) -> None:
    left, right = ax.get_xlim()
    bottom, top = ax.get_ylim()
    width = right - left
    height = top - bottom
    current_ratio = width / height
    if current_ratio < ratio:
        new_width = (ratio / current_ratio) * width
        width_padding = (new_width - width) / 2
        left = left - width_padding
        right = right + width_padding
        ax.set_xlim([left, right])
    else:
        new_height = (current_ratio / ratio) * height
        height_padding = (new_height - height) / 2
        bottom = bottom - height_padding
        top = top + height_padding
        ax.set_ylim([bottom, top])


def _construct_full_rich_string(
    characters: Any, foreground_colors: Any, background_colors: Any
) -> str:
    result = ""
    for y in range(characters.shape[0]):
        for x in range(characters.shape[1]):
            idx = y, x
            res = characters[idx]
            char = chr(res)
            fg_color = ",".join(map(str, foreground_colors[idx]))
            bg_color = ",".join(map(str, background_colors[idx]))
            result += (
                f"[rgb({fg_color}) ON rgb({bg_color})]{char}[/rgb({fg_color}) ON rgb({bg_color})]"
            )
        result += "\n"
    return result[:-1]
