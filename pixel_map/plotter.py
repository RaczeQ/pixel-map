"""
Plotting functionality.

Generates a Matplotlib canvas that is rendered to an image and later transformed into a list of
unicode characters.
"""

import os
from pathlib import Path
from typing import Any, Optional, Union

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
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.style import Style
from rich.text import Text

from pixel_map.renderers import AVAILABLE_RENDERERS

TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:3857", always_xy=True)

EPSG_3857_BOUNDS = (-20037508.34, -20048966.1, 20037508.34, 20048966.1)


def plot_geo_data(
    files: list[str],
    renderer: str,
    bbox: Optional[tuple[float, float, float, float]] = None,
    color: Union[str, list[str]] = "C0",
    alpha: Union[float, list[float]] = 1.0,
    basemap_provider: Optional[str] = None,
    background_color: Optional[str] = None,
    no_border: bool = False,
    console_width: Optional[int] = None,
    console_height: Optional[int] = None,
    plotting_dpi: int = 10,
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
        color (Union[str, list[str]], optional): Color or list of colors used to plot geo data.
            If a list, must be the same length as a number of files. Defaults to "C0".
        alpha (Union[str, list[float]], optional): Opacity or list of opacities used to plot
            geo data.  If a list, must be the same length as a number of files. Defaults to 1.
        basemap_provider (str, optional): A basemap used to plot under the geo data.
            Defaults to None.
        background_color (str, optional): Background color. Used then basemap_provider is None.
            Defaults to None.
        no_border (bool, optional): Removes the border around the map. Defaults to False.
        console_width (int, optional): Console width. Can be used to set arbitrary value.
            Defaults to None.
        console_height (int, optional): Console height. Can be used to set arbitrary value.
            Defaults to None.
        plotting_dpi (int, optional): Quality of matplotlib figure. It's used to multiply terminal
            size by some value to get better quality plot. Defaults to 10.
    """
    force_terminal = os.getenv("FORCE_TERMINAL_MODE", "false").lower() == "true"
    if force_terminal:
        console = Console(force_interactive=False, force_jupyter=False, force_terminal=True)
    else:
        console = get_console()

    if console_width:
        console.width = console_width

    if console_height:
        console.height = console_height

    if no_border:
        terminal_width = console.width
        terminal_height = console.height - 1
    else:
        terminal_width = console.width - 2
        terminal_height = console.height - 3  # 2 for panel and 1 for new line

    map_width = terminal_width
    map_height = terminal_height * 2

    map_ratio = map_width / map_height

    with _get_progress_object(console) as progress:
        progress.add_task("Calculating bounding box", total=None)
        bbox_axes_bounds = None
        if bbox:
            bbox, bbox_axes_bounds = _expand_bbox_to_match_ratio(bbox, ratio=map_ratio)

    with _get_progress_object(console) as progress:
        progress.add_task("Loading Geo data", total=None)
        gdfs = _load_geo_data(files, bbox=bbox)
        if bbox:
            gdfs = [gdf.clip_by_rect(*bbox) for gdf in gdfs]

    with _get_progress_object(console) as progress:
        progress.add_task("Plotting geo data", total=None)
        f, ax = plt.subplots(figsize=(map_width, map_height), dpi=plotting_dpi)

        ax.set_axis_off()
        ax.set_xticks([])
        ax.set_yticks([])

        f.patch.set_facecolor(background_color)
        canvas = f.canvas
        # gdf.to_crs(3857).plot(ax=ax, alpha=0.4)
        if isinstance(color, str):
            color = [color]
        if isinstance(alpha, (int, float)):
            alpha = [alpha]
        for idx, gdf in enumerate(gdfs):
            plot_color = color[idx % len(color)]
            plot_alpha = alpha[idx % len(alpha)]
            gdf.to_crs(3857).plot(ax=ax, color=plot_color, alpha=plot_alpha)

        if bbox_axes_bounds:
            left, bottom, right, top = bbox_axes_bounds
            ax.set_xlim([left, right])
            ax.set_ylim([bottom, top])

        left, bottom, right, top = _expand_axes_limit_to_match_ratio(ax, ratio=map_ratio)

        if basemap_provider:
            try:
                cx.add_basemap(
                    ax,
                    source=basemap_provider,
                    crs=3857,
                    attribution=False,
                )
            except ValueError:
                cx.add_basemap(
                    ax,
                    source=basemap_provider,
                    crs=3857,
                    attribution=False,
                    zoom=0,
                )

        ax.set_position((0, 0, 1, 1))
        canvas.draw()

        image_flat = np.frombuffer(canvas.tostring_rgb(), dtype="uint8")  # (H * W * 3,)
        image = image_flat.reshape(*reversed(canvas.get_width_height()), 3)

    with _get_progress_object(console) as progress:
        progress.add_task("Rendering geo data", total=None)
        renderer_object = AVAILABLE_RENDERERS[renderer](
            terminal_width=terminal_width, terminal_height=terminal_height
        )
        characters, foreground_colors, background_colors = renderer_object.render_numpy(image)
        full_rich_string = _construct_full_rich_string(
            characters, foreground_colors, background_colors
        )

    if no_border:
        console.print(full_rich_string)
    else:
        title = _generate_panel_title(files, terminal_width)

        map_minx, map_miny = TRANSFORMER.transform(
            left, bottom, direction=TransformDirection.INVERSE
        )
        map_maxx, map_maxy = TRANSFORMER.transform(right, top, direction=TransformDirection.INVERSE)
        subtitle = _generate_panel_subtitle(
            map_minx, map_miny, map_maxx, map_maxy, terminal_width, terminal_height
        )

        console.print(
            Panel.fit(
                full_rich_string,
                padding=0,
                title=title,
                subtitle=subtitle,
                box=HEAVY,
            )
        )


def get_predefined_dark_style() -> tuple[str, str]:
    """Get default background and color for dark style."""
    return "CartoDB.DarkMatterNoLabels", "C1"


def get_predefined_light_style() -> tuple[str, str]:
    """Get default background and color for light style."""
    return "CartoDB.PositronNoLabels", "C0"


def _load_geo_data(
    files: list[str], bbox: Optional[tuple[float, float, float, float]] = None
) -> list[gpd.GeoSeries]:
    paths = [Path(file_path) for file_path in files]
    return [
        (
            _read_geoparquet_file(path, bbox=bbox).geometry
            if path.suffix == ".parquet"
            else gpd.read_file(path, bbox=bbox).geometry
        )
        for path in paths
    ]


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

    left = max(left, EPSG_3857_BOUNDS[0])
    bottom = max(bottom, EPSG_3857_BOUNDS[1])
    right = min(right, EPSG_3857_BOUNDS[2])
    top = min(top, EPSG_3857_BOUNDS[3])

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
    else:
        new_height = (current_ratio / ratio) * height
        height_padding = (new_height - height) / 2
        bottom = bottom - height_padding
        top = top + height_padding

    left = max(left, EPSG_3857_BOUNDS[0])
    bottom = max(bottom, EPSG_3857_BOUNDS[1])
    right = min(right, EPSG_3857_BOUNDS[2])
    top = min(top, EPSG_3857_BOUNDS[3])

    ax.set_xlim([left, right])
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


def _generate_panel_subtitle(
    minx: float, miny: float, maxx: float, maxy: float, terminal_width: int, terminal_height: int
) -> str:
    bbox_str = f"BBOX: {minx:.5f},{miny:.5f},{maxx:.5f},{maxy:.5f}"
    terminal_wh_str = f"MAP W:{terminal_width} H:{terminal_height}"

    subtitle = f"{bbox_str} | {terminal_wh_str}"

    if len(subtitle) <= (terminal_width - 4):
        return subtitle
    elif len(bbox_str) <= (terminal_width - 4):
        return bbox_str

    return ""


def _get_progress_object(console: Console) -> Progress:
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    )
