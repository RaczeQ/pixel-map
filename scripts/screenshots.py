"""
Run the commands of Markdown pages and draw what the terminal shows.

A block of commands followed by an image gets that image: `python scripts/screenshots.py README.md`.
"""

import contextlib
import io
import re
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

import matplotlib
import rich
from PIL import Image, ImageDraw, ImageFont
from rich.segment import Segment
from typer.testing import CliRunner

from pixel_map.__main__ import app

COLUMNS, ROWS = 240, 68
BACKGROUND, FOREGROUND = "#282c34", "#dcdfe4"
FONT = ImageFont.truetype(
    Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSansMono.ttf", size=14
)
WIDTH = round(FONT.getlength("M"))
HEIGHT = 2 * WIDTH
BASELINE = round(0.78 * HEIGHT)

SCREENSHOT = re.compile(
    r"```sh\n(?P<commands>(?:(?!```).)*)```\s*"
    r'(?:<p[^>]*>\s*<img src="|!\[[^]]*\]\()'
    r"(?:https://raw\.githubusercontent\.com/RaczeQ/pixel-map/main/)?"
    r'(?P<image>[^")]+)',
    re.DOTALL,
)


def run(arguments: list[str]) -> list[list[Segment]]:
    """Run pixel-map and return the lines that it prints."""
    rich.reconfigure(
        record=True,
        file=io.StringIO(),
        width=COLUMNS,
        height=ROWS,
        color_system="truecolor",
        legacy_windows=False,
    )
    result = CliRunner().invoke(app, arguments)
    if result.exit_code:
        raise SystemExit(f"pixel-map {shlex.join(arguments)}\n{result.output}{result.exception!r}")
    lines = Segment.split_lines(rich.get_console()._record_buffer)
    # The spinners leave blank lines.
    return [line for line in lines if any(s.style or s.text.strip() for s in line if not s.control)]


def draw_character(
    canvas: ImageDraw.ImageDraw, x: int, y: int, character: str, color: str
) -> None:
    """Draw a character, Braille patterns as dots: the font has none."""
    dots = ord(character) - 0x2800
    if not 0 <= dots < 256:
        canvas.text((x, y + BASELINE), character, color, FONT, anchor="ls")
        return
    # https://en.wikipedia.org/wiki/Braille_Patterns#Identifying,_naming_and_ordering
    for bit, (row, column) in enumerate(
        [(0, 0), (1, 0), (2, 0), (0, 1), (1, 1), (2, 1), (3, 0), (3, 1)]
    ):
        if dots >> bit & 1:
            center_x, center_y = x + WIDTH * (column + 0.5) / 2, y + HEIGHT * (row + 0.5) / 4
            radius = WIDTH / 7
            canvas.ellipse(
                (center_x - radius, center_y - radius, center_x + radius, center_y + radius),
                fill=color,
            )


def draw(lines: list[list[Segment]]) -> Image.Image:
    """Draw the lines as a terminal does."""
    columns = max(Segment.get_line_length(line) for line in lines)
    image = Image.new("RGB", (columns * WIDTH, len(lines) * HEIGHT), BACKGROUND)
    canvas = ImageDraw.Draw(image)
    for row, line in enumerate(lines):
        column = 0
        for text, style, control in line:
            if control:
                continue
            color, background = FOREGROUND, None
            if style and style.color:
                color = style.color.get_truecolor().hex
            if style and style.bgcolor:
                background = style.bgcolor.get_truecolor(foreground=False).hex
            for character in text:
                x, y = column * WIDTH, row * HEIGHT
                if background:
                    canvas.rectangle((x, y, x + WIDTH - 1, y + HEIGHT - 1), fill=background)
                draw_character(canvas, x, y, character, color)
                column += 1
    return image


def main(page: Path) -> None:
    """Draw the images of a page."""
    with tempfile.TemporaryDirectory() as directory, contextlib.chdir(directory):
        for screenshot in SCREENSHOT.finditer(page.read_text()):
            for command in screenshot["commands"].replace("\\\n", "").strip().splitlines():
                name, *arguments = shlex.split(command.removeprefix("$ "))
                if name == "pixel-map":
                    lines = run(arguments)
                else:
                    subprocess.run([name, *arguments], check=True)
            image = page.parent / screenshot["image"]
            image.parent.mkdir(exist_ok=True)
            draw(lines).save(image, quality=90, lossless=True)
            print(image)


if __name__ == "__main__":
    for path in sys.argv[1:]:
        main(Path(path).resolve())
