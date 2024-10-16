import PIL
from shapely import box
import quackosm as qosm
from rich import get_console
import contextily as cx
from matplotlib import pyplot as plt
import numpy as np
import img2unicode


def expand_limit_to_ratio(ax, ratio) -> None:
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


def construct_full_string(chars, fgs, bgs):
    result = ""
    for y in range(chars.shape[0]):
        for x in range(chars.shape[1]):
            idx = y, x
            res = chars[idx]
            char = chr(res)
            fg_color = ",".join(map(str, fgs[idx]))
            bg_color = ",".join(map(str, bgs[idx]))
            result += (
                f"[rgb({fg_color}) ON rgb({bg_color})]{char}[/rgb({fg_color}) ON rgb({bg_color})]"
            )
        result += "\n"
    return result[:-1]


if __name__ == "__main__":
    # gdf = qosm.convert_pbf_to_geodataframe("monaco-latest.osm.pbf")
    gdf = qosm.convert_pbf_to_geodataframe(
        "monaco-latest.osm.pbf",
        geometry_filter=box(
            7.416486207767861, 43.7310867041912, 7.421931388477276, 43.73370705597216
        ),
        tags_filter={"building": True},
    )

    import shutil

    ts = shutil.get_terminal_size()
    # print(ts)

    from time import sleep

    from rich.console import Console
    from rich.align import Align
    from rich.text import Text
    from rich.panel import Panel

    console = get_console()

    w = console.width
    h = console.height * 2

    print(w, h)

    f, ax = plt.subplots(figsize=(w, h), dpi=10)
    f.patch.set_facecolor("black")
    canvas = f.canvas
    gdf.to_crs(3857).plot(ax=ax)
    ax.axis("off")
    ax.margins(0)
    expand_limit_to_ratio(ax, w / h)
    # print(ax.get_xlim(), ax.get_ylim())
    # cx.add_basemap(ax, source=cx.providers.CartoDB.PositronNoLabels, crs=3857, attribution=False)
    # cx.add_basemap(ax, source=cx.providers.CartoDB.DarkMatterNoLabels, crs=3857, attribution=False)
    f.tight_layout()
    canvas.draw()
    # plt.show()
    image_flat = np.frombuffer(canvas.tostring_rgb(), dtype="uint8")  # (H * W * 3,)
    image = image_flat.reshape(*reversed(canvas.get_width_height()), 3)

    # print(image.shape)

    braille_renderer = img2unicode.GammaRenderer(
        img2unicode.BestGammaOptimizer(True, "braille"), max_h=h, max_w=w, allow_upscale=True
    )
    fast_renderer = img2unicode.Renderer(
        img2unicode.FastGenericDualOptimizer("block"), max_h=h, max_w=w, allow_upscale=True
    )
    exact_renderer = img2unicode.Renderer(
        img2unicode.ExactGenericDualOptimizer("block"), max_h=h, max_w=w, allow_upscale=True
    )

    # text = Text.from_markup(construct_full_string(*fast_renderer.render_numpy(image)))
    # console.print(text)
    # console.print(Panel(text))

    # PIL.Image.fromarray(image).save("original.png")
    # fast_renderer.prerender(image).save("fast.png")
    # exact_renderer.prerender(image).save("exact.png")
    # braille_renderer.prerender(image).save("braille.png")

    # c, f, b = fast_renderer.render_numpy(image)

    # print(c.shape, f.shape, b.shape)

    # from rich.layout import Layout

    # layout = Layout()
    # print(layout)

    # with console.screen() as screen:
        
    #     screen.update(Panel(text))
        # for count in range(5, 0, -1):
        #     t
        #     text = Align.center(
        #         Text.from_markup(f"[blink]Don't Panic![/blink]\n{count}", justify="center"),
        #         vertical="middle",
        #     )
        #     screen.update(Panel(text))
        #     # sleep(1)

    console.print(construct_full_string(*fast_renderer.render_numpy(image)))
    # # console.print(construct_full_string(*exact_renderer.render_numpy(image)))
    console.print(construct_full_string(*braille_renderer.render_numpy(image)))
