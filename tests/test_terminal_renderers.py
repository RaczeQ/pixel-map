"""Tests for the native ``terminal_renderers`` module."""

import numpy as np
import pytest

from pixel_map.terminal_renderers import (
    _ASCII_CHARSET,
    AVAILABLE_RENDERERS,
    TerminalRenderer,
    _get_charset,
)

COLOR_RENDERERS = ["block", "all", "ascii", "space", "half", "quad", "braille"]
BW_RENDERERS = ["ascii-bw", "braille-bw"]
TERMINAL_W = 10
TERMINAL_H = 8

_ASCII_SET = set(_ASCII_CHARSET)


def _make_renderer(name: str) -> TerminalRenderer:
    """Create a renderer with the default terminal dimensions."""
    return AVAILABLE_RENDERERS[name](terminal_width=TERMINAL_W, terminal_height=TERMINAL_H)


# Expected character sets per renderer (as sets of decoded codepoints).
_CHARSETS = {
    "block": "█▀▄▌▐░▒▓",
    "half": "▀▄",
    "quad": "▘▝▖▗▀▄▌▐▚▞",
    "braille": {chr(0x2800 + n) for n in range(256)},
    "ascii": _ASCII_SET,
    "all": (_ASCII_SET | set("█▀▄▌▐░▒▓")
             | {chr(0x2800 + n) for n in range(256)}),
    "space": " ",
    "ascii-bw": _ASCII_SET,
    "braille-bw": {chr(0x2800 + n) for n in range(256)},
}


def _solid_image(color: tuple[int, int, int], w: int = 80, h: int = 80) -> np.ndarray:
    img = np.zeros((h, w, 3), dtype=np.uint8)
    img[..., 0] = color[0]
    img[..., 1] = color[1]
    img[..., 2] = color[2]
    return img


@pytest.mark.parametrize("name", COLOR_RENDERERS + BW_RENDERERS)  # type: ignore
def test_render_numpy_shapes_and_dtype(name: str) -> None:
    """Output shapes are (H, W) cells and characters are integer codepoints."""
    renderer = _make_renderer(name)
    image = _solid_image((123, 45, 67))
    chars, fg, bg = renderer.render_numpy(image)

    assert chars.shape == (TERMINAL_H, TERMINAL_W)
    assert np.issubdtype(chars.dtype, np.integer)
    for c in chars.flat:
        assert 0 <= c <= 0x10FFFF
        assert chr(c) in _CHARSETS[name]


@pytest.mark.parametrize("name", COLOR_RENDERERS)  # type: ignore
def test_render_numpy_returns_colors(name: str) -> None:
    """Colour renderers return ``(H, W, 3)`` uint8 colour arrays."""
    renderer = _make_renderer(name)
    image = _solid_image((200, 50, 10))
    chars, fg, bg = renderer.render_numpy(image)

    assert fg is not None and bg is not None
    assert fg.shape == (TERMINAL_H, TERMINAL_W, 3)
    assert bg.shape == (TERMINAL_H, TERMINAL_W, 3)
    assert fg.dtype == np.uint8
    assert bg.dtype == np.uint8


@pytest.mark.parametrize("name", BW_RENDERERS)  # type: ignore
def test_render_numpy_monochrome_returns_none(name: str) -> None:
    """Monochrome renderers return ``None`` for both colours."""
    renderer = _make_renderer(name)
    image = _solid_image((200, 50, 10))
    chars, fg, bg = renderer.render_numpy(image)

    assert fg is None
    assert bg is None
    assert chars.shape == (TERMINAL_H, TERMINAL_W)


@pytest.mark.parametrize("name", COLOR_RENDERERS)  # type: ignore
def test_solid_color_background_matches(name: str) -> None:
    """A uniformly coloured image yields a background equal to that colour."""
    color = (255, 0, 0)
    renderer = _make_renderer(name)
    image = _solid_image(color)
    _, fg, bg = renderer.render_numpy(image)

    assert bg is not None
    bg_mean = bg.reshape(-1, 3).mean(axis=0)
    np.testing.assert_allclose(bg_mean, np.array(color, dtype=np.float64), atol=2)


def test_solid_color_fg_matches_when_uniform() -> None:
    """For a uniform field foreground and background converge to the colour."""
    renderer = _make_renderer("half")
    image = _solid_image((0, 128, 255))
    _, fg, bg = renderer.render_numpy(image)

    assert fg is not None and bg is not None
    np.testing.assert_allclose(
        fg.reshape(-1, 3).mean(axis=0), [0, 128, 255], atol=2
    )
    np.testing.assert_allclose(
        bg.reshape(-1, 3).mean(axis=0), [0, 128, 255], atol=2
    )


def test_two_tone_foreground_background_differ() -> None:
    """A left/right tone split produces different colours per cell group."""
    renderer = _make_renderer("half")
    w, h = TERMINAL_W * 8, TERMINAL_H * 16
    image = np.zeros((h, w, 3), dtype=np.uint8)
    image[:, : w // 2, 0] = 255  # red left
    image[:, w // 2 :, 1] = 255  # green right
    chars, fg, bg = renderer.render_numpy(image)

    assert fg is not None and bg is not None
    left_fg = fg[:, : TERMINAL_W // 2].reshape(-1, 3).mean(axis=0)
    right_fg = fg[:, TERMINAL_W // 2 :].reshape(-1, 3).mean(axis=0)
    assert np.linalg.norm(left_fg - right_fg) > 100  # red vs green
    assert left_fg[0] > 100 and left_fg[1] < 50  # left is red-dominant
    assert right_fg[1] > 100 and right_fg[0] < 50  # right is green-dominant


def test_space_renderer_is_uniform_space() -> None:
    """Space renderer outputs ``' '`` codepoints with matching colours."""
    renderer = _make_renderer("space")
    image = _solid_image((10, 20, 30))
    chars, fg, bg = renderer.render_numpy(image)

    assert set(chars.flatten().tolist()) == {ord(" ")}
    assert fg is not None and bg is not None
    np.testing.assert_allclose(
        fg.reshape(-1, 3).mean(axis=0), [10, 20, 30], atol=2
    )
    np.testing.assert_allclose(
        bg.reshape(-1, 3).mean(axis=0), [10, 20, 30], atol=2
    )


def test_braille_codepoints_round_trip() -> None:
    """Braille renderer only emits U+2800--U+28FF codepoints."""
    renderer = _make_renderer("braille")
    image = _solid_image((128, 128, 128))
    chars, _, _ = renderer.render_numpy(image)
    for c in chars.flat:
        assert 0x2800 <= c <= 0x28FF


def test_monochrome_density_gradient() -> None:
    """Brighter cells should use denser braille glyphs than darker ones."""
    renderer = _make_renderer("braille-bw")
    w, h = TERMINAL_W * 8, TERMINAL_H * 16
    image = np.zeros((h, w, 3), dtype=np.uint8)
    # Top half dark, bottom half bright.
    image[: h // 2] = 10
    image[h // 2 :] = 245
    chars, fg, bg = renderer.render_numpy(image)

    assert fg is bg is None
    top_densities = [
        bin(int(chars[y, x]) - 0x2800).count("1")
        for y in range(TERMINAL_H // 2)
        for x in range(TERMINAL_W)
    ]
    bot_densities = [
        bin(int(chars[y, x]) - 0x2800).count("1")
        for y in range(TERMINAL_H // 2, TERMINAL_H)
        for x in range(TERMINAL_W)
    ]
    assert sum(top_densities) < sum(bot_densities)


def test_charset_caching() -> None:
    """Repeated lookups return the cached _Charset instance."""
    a = _get_charset("block")
    b = _get_charset("block")
    assert a is b
    assert len(a.codes) > 0
