"""
Plotting functionality.

Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
unicode characters.
"""

from pathlib import Path
from typing import Any, Optional

import contextily as cx
import geopandas as gpd
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from pyproj import Transformer
from pyproj.enums import TransformDirection
from rich import get_console
from rich.box import HEAVY
from rich.color import Color
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.text import Text

from pixel_map.renderers import AVAILABLE_RENDERERS

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)


def plot_geo_data(
    files: list[str],
    renderer: str,
    bbox: Optional[tuple[float, float, float, float]] = None,
    no_border: bool = False,
) -> None:
    """
    Plot the geo data into a terminal.

    Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
    unicode characters.

    Args:
        files (list[str]): List of files to plot.
        renderer (str): A name for the renderer used to generate terminal output.
            Defaults to "block".
        bbox (Optional[tuple[float, float, float, float]], optional): Bounding box used to clip the
            geo data. Defaults to None.
        no_border (Optional[bool], optional): Removes the border around the map. Defaults to False.
    """
    console = get_console()

    if no_border:
        terminal_width = console.width
        terminal_height = console.height - 1
    else:
        terminal_width = console.width - 2
        terminal_height = console.height - 3  # 2 for panel and 1 for new line

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
        # gdf.to_crs(3857).plot(ax=ax, alpha=0.4)
        gdf.to_crs(3857).plot(ax=ax)
        ax.axis("off")
        ax.margins(0)

        if bbox_axes_bounds:
            left, bottom, right, top = bbox_axes_bounds
            ax.set_xlim([left, right])
            ax.set_ylim([bottom, top])

        left, bottom, right, top = _expand_axes_limit_to_match_ratio(ax, ratio=map_ratio)
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
        renderer_object = AVAILABLE_RENDERERS[renderer](
            terminal_width=terminal_width, terminal_height=terminal_height
        )
        characters, foreground_colors, background_colors = renderer_object.render_numpy(image)
        full_rich_string = _construct_full_rich_string(
            characters, foreground_colors, background_colors
        )

    map_minx, map_miny = TRANSFORMER.transform(left, bottom, direction=TransformDirection.INVERSE)
    map_maxx, map_maxy = TRANSFORMER.transform(right, top, direction=TransformDirection.INVERSE)

    if no_border:
        console.print(full_rich_string)
    else:
        title = _generate_panel_title(files, terminal_width)

        console.print(
            Panel.fit(
                full_rich_string,
                padding=0,
                title=title,
                subtitle=f"BBOX: {map_minx:.5f},{map_miny:.5f},{map_maxx:.5f},{map_maxy:.5f}",
                box=HEAVY,
            )
        )


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

    left, bottom = TRANSFORMER.transform(minx, miny)
    right, top = TRANSFORMER.transform(maxx, maxy)

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

    new_minx, new_miny = TRANSFORMER.transform(left, bottom, direction=TransformDirection.INVERSE)
    new_maxx, new_maxy = TRANSFORMER.transform(right, top, direction=TransformDirection.INVERSE)

    return (new_minx, new_miny, new_maxx, new_maxy), (left, bottom, right, top)


def _expand_axes_limit_to_match_ratio(ax: Axes, ratio: float) -> tuple[float, float, float, float]:
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

    return left, bottom, right, top


def _construct_full_rich_string(
    characters: Any, foreground_colors: Any, background_colors: Any
) -> Text:
    has_fg_color = foreground_colors is not None
    has_bg_color = background_colors is not None
    result = Text()
    for y in range(characters.shape[0]):
        for x in range(characters.shape[1]):
            idx = y, x
            res = characters[idx]
            result.append(
                chr(res),
                style=Style(
                    color=(Color.from_rgb(*foreground_colors[idx]) if has_fg_color else None),
                    bgcolor=(Color.from_rgb(*background_colors[idx]) if has_bg_color else None),
                ),
            )
        result.append("\n")
    return result[:-1]


def _generate_panel_title(files: list[str], terminal_width: int) -> str:
    file_paths = [Path(f).name for f in files]

    if len(file_paths) == 1:
        title = "1 file"
    else:
        title = f"{len(file_paths)} files"

    file_names_in_title = []
    file_names_left = file_paths
    while file_names_left:
        current_file_name = file_names_left.pop(0)
        file_names_in_title.append(current_file_name)
        titles_joined = ", ".join(file_names_in_title)
        titles_left = len(file_names_left)
        if titles_left == 0:
            new_title = titles_joined
        elif titles_left == 1:
            new_title = f"{titles_joined} + 1 other file"
        else:
            new_title = f"{titles_joined} + {titles_left} other files"

        if len(new_title) > (terminal_width - 4):
            break

        title = new_title

    return title
