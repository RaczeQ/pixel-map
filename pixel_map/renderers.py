"""
Wrappers around img2unicode.Renderers.

Look https://github.com/matrach/img2unicode/tree/master/examples for more information
about renderers.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from img2unicode import Renderer


def get_fast_block_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Fast block renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.FastGenericDualOptimizer("block"),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_fast_all_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Fast all renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.FastGenericDualOptimizer(),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_fast_ascii_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Fast all renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.FastGenericDualOptimizer("ascii"),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_space_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Space renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.SpaceDualOptimizer(),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_half_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Half renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.HalfBlockDualOptimizer(),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_quad_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Quad renderer."""
    import img2unicode

    return img2unicode.Renderer(
        img2unicode.FastQuadDualOptimizer(),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )


def get_braille_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Braille renderer."""
    import img2unicode

    return img2unicode.GammaRenderer(
        img2unicode.BestGammaOptimizer(use_color=True, charmask="braille"),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )

def get_ascii_bw_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """ASCII black-white renderer."""
    import img2unicode

    return img2unicode.GammaRenderer(
        img2unicode.BestGammaOptimizer(use_color=False, charmask="ascii"),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )

def get_braille_bw_renderer(terminal_width: int, terminal_height: int) -> "Renderer":
    """Braille renderer."""
    import img2unicode

    return img2unicode.GammaRenderer(
        img2unicode.BestGammaOptimizer(use_color=False, charmask="braille"),
        max_h=terminal_height,
        max_w=terminal_width,
        allow_upscale=True,
    )

AVAILABLE_RENDERERS = {
    "block": get_fast_block_renderer,
    "all": get_fast_all_renderer,
    "ascii": get_fast_ascii_renderer,
    "space": get_space_renderer,
    "half": get_half_renderer,
    "quad": get_quad_renderer,
    "braille": get_braille_renderer,
    "braille-bw": get_braille_bw_renderer,
    "ascii-bw": get_ascii_bw_renderer,
}
