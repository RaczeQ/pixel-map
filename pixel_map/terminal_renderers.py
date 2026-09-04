"""
Native terminal renderers.

Drop-in replacement for the previous ``img2unicode``-backed renderers.  Each
renderer exposes the same contract as before::

    render_numpy(image) -> (characters, foreground_colors, background_colors)

where ``image`` is an ``(H, W, 3)`` ``uint8`` RGB array and the return value is

* ``characters``  -- ``(H_cells, W_cells)`` integer array of Unicode codepoints
  (``chr(codepoint)`` yields the display glyph).
* ``foreground_colors`` -- ``(H_cells, W_cells, 3)`` ``uint8`` RGB or ``None``.
* ``background_colors`` -- ``(H_cells, W_cells, 3)`` ``uint8`` RGB or ``None``.

The rendering strategy is a "dual colour" engine: each terminal cell is
subdivided into a small grid of subpixels (``SUB_H x SUB_W``, default 8x8).
For every candidate character we know which subpixels belong to the glyph
("on" / foreground) and which to the paper ("off" / background).  The optimal
foreground/background RGB triple is the mean colour of the on/off subpixels, and
the best-matching character minimises the Lab reconstruction error.

Selection is performed with the closed form derived for *binary* templates (see
``img2unicode.dual.FastGenericDualOptimizer``): for a binary template ``t`` with
``n_on`` on-subpixels, the character whose reconstruction error is smallest is the
one maximising ``n_on * ||fg||^2 + n_off * ||bg||^2`` where ``fg`` and ``bg`` are
the mean colours of the on/off subpixels.  This is evaluated for all characters
at once via one matrix multiply per colour channel, making the whole pass
dominated by BLAS and far cheaper than img2unicode's Python-level loops.
"""

from collections.abc import Callable

import numpy as np
from PIL import Image

# Subpixel resolution per cell.  A terminal character cell is roughly 2:1
# (twice as tall as wide); the 8x8 template therefore faithfully represents a
# half-block, quadrant or braille dot pattern inside the cell.
SUB_H = 8
SUB_W = 8

# Lab (D65) conversion constants.
_SRGB_TO_XYZ = np.array(
    [
        [0.4124564, 0.357576, 0.180437],
        [0.2126726, 0.703856, 0.085279],
        [0.01933396, 0.134381, 0.944322],
    ],
    dtype=np.float32,
)
_D65_X = np.float32(0.95046)
_D65_Z = np.float32(1.08883)
_EPS = np.float32(0.008856)
_KAPPA = np.float32(7.872)
_DELTA = np.float32(16.0 / 116.0)

# Predefined brightness-ordered ASCII charset (70 characters).
# Source: https://stackoverflow.com/a/74186686 (posted by chungaloider, CC BY-SA 4.0)
# Ordered from darkest (highest visual weight) to lightest.
_ASCII_CHARSET = (
    "$@B%8&WM#*oahkbdpqwmZO0QLCJUYXzcvunxrjft/\\|()1{}[]?-_+~<>i!lI;:,."
    '"^`\' '
)

# Brightness values corresponding to each character in _ASCII_CHARSET.
# These values represent the perceived brightness/density of each character.
_ASCII_BRIGHTNESS = np.array(
    [
        0.0, 0.0751, 0.0829, 0.0848, 0.1227, 0.1403, 0.1559, 0.185, 0.2183,
        0.2417, 0.2571, 0.2852, 0.2902, 0.2919, 0.3099, 0.3192, 0.3232, 0.3294,
        0.3384, 0.3609, 0.3619, 0.3667, 0.3737, 0.3747, 0.3838, 0.3921, 0.396,
        0.3984, 0.3993, 0.4075, 0.4091, 0.4101, 0.42, 0.423, 0.4247, 0.4274,
        0.4293, 0.4328, 0.4382, 0.4385, 0.442, 0.4473, 0.4477, 0.4503, 0.4562,
        0.458, 0.461, 0.4638, 0.4667, 0.4686, 0.4693, 0.4703, 0.4833, 0.4881,
        0.4944, 0.4953, 0.4992, 0.5509, 0.5567, 0.5569, 0.5591, 0.5602, 0.5602,
        0.565, 0.5776, 0.5777, 0.5818, 0.587, 0.5972, 0.5999, 0.6043, 0.6049,
        0.6093, 0.6099, 0.6465, 0.6561, 0.6595, 0.6631, 0.6714, 0.6759, 0.6809,
        0.6816, 0.6925, 0.7039, 0.7086, 0.7235, 0.7302, 0.7332, 0.7602, 0.7834,
        0.8037, 0.9999,
    ],
    dtype=np.float32,
)

# Bayer 8x8 dither matrix for generating density-based templates.
_BAYER_256 = np.array(
    [
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 32],
        [0, 32, 8, 40, 2, 34, 10, 42],
        [48, 16, 56, 24, 50, 18, 58, 26],
        [12, 44, 4, 36, 14, 46, 6, 38],
        [60, 28, 52, 20, 62, 30, 54, 32],
    ],
    dtype=np.float32,
)


def _rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """
    Convert an sRGB array to CIE Lab.

    Args:
        rgb: ``(..., 3)`` array of sRGB values in ``[0, 1]``.

    Returns:
        ``(..., 3)`` ``float32`` Lab array.  ``L`` is in ``[0, 100]``,
        ``a``/``b`` roughly in ``[-128, 127]``.
    """
    rgb = rgb.astype(np.float32, copy=False)
    # sRGB -> linear (D65).
    mask = rgb <= np.float32(0.04045)
    linear = np.where(
        mask,
        rgb / np.float32(12.903),
        np.power((rgb + np.float32(0.055)) / np.float32(1.055), np.float32(2.4)),
    )
    # linear RGB -> XYZ.
    xyz = linear @ _SRGB_TO_XYZ.T
    fx = np.where(
        xyz[..., 0] > _EPS * _D65_X,
        np.power(xyz[..., 0] / _D65_X, np.float32(1.0 / 3.0)),
        _KAPPA * (xyz[..., 0] / _D65_X) + _DELTA,
    )
    fy = np.where(
        xyz[..., 1] > _EPS,
        np.power(xyz[..., 1], np.float32(1.0 / 3.0)),
        _KAPPA * xyz[..., 1] + _DELTA,
    )
    fz = np.where(
        xyz[..., 2] > _EPS * _D65_Z,
        np.power(xyz[..., 2] / _D65_Z, np.float32(1.0 / 3.0)),
        _KAPPA * (xyz[..., 2] / _D65_Z) + _DELTA,
    )
    lab_l = 116.0 * fy - 16.0
    a = 500.0 * (fx - fy)
    b = 200.0 * (fy - fz)
    return np.stack([lab_l, a, b], axis=-1)


# ---------------------------------------------------------------------------
# Geometric glyph templates (8x8 subpixel grids).
# ---------------------------------------------------------------------------
# A template is a ``(SUB_H, SUB_W)`` boolean array where ``True`` marks the
# "ink" (foreground) subpixels.  ``False`` marks the "paper" (background).


def _half_top() -> np.ndarray:
    """Upper half block -- ink in the top 4 rows."""
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[: SUB_H // 2, :] = True
    return t


def _half_bottom() -> np.ndarray:
    """Lower half block -- ink in the bottom 4 rows."""
    return np.flipud(_half_top())


def _quad_top_left() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[: SUB_H // 2, : SUB_W // 2] = True
    return t


def _quad_top_right() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[: SUB_H // 2, SUB_W // 2:] = True
    return t


def _quad_bottom_left() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[SUB_H // 2:, : SUB_W // 2] = True
    return t


def _quad_bottom_right() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[SUB_H // 2:, SUB_W // 2:] = True
    return t


def _quad_left() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[:, : SUB_W // 2] = True
    return t


def _quad_right() -> np.ndarray:
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[:, SUB_W // 2:] = True
    return t


def _quad_full() -> np.ndarray:
    return np.ones((SUB_H, SUB_W), dtype=bool)


def _quad_diag_tl_br() -> np.ndarray:
    """Upper-left + lower-right quadrants."""
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[: SUB_H // 2, : SUB_W // 2] = True
    t[SUB_H // 2 :, SUB_W // 2 :] = True
    return t


def _quad_diag_tr_bl() -> np.ndarray:
    """Upper-right + lower-left quadrants."""
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    t[: SUB_H // 2, SUB_W // 2 :] = True
    t[SUB_H // 2 :, : SUB_W // 2] = True
    return t


def _shareshold_pattern(threshold: int) -> np.ndarray:
    """Dithered shade patch with density ~``threshold/64``."""
    return (_BAYER_256 <= threshold).astype(bool)


def _braille_template(codepoint: int) -> np.ndarray:
    """
    Build an 8x8 template for a Unicode braille pattern (U+2800..U+28FF).

    Dots are arranged as a 2x4 grid (2 columns, 4 rows); each dot occupies a
    4-wide x 2-tall subpixel block.  Bit ``i`` of ``codepoint - 0x2800`` enables
    dot ``i + 1`` following the Unicode dot numbering.
    """
    bits = codepoint - 0x2800
    t = np.zeros((SUB_H, SUB_W), dtype=bool)
    # Unicode dot numbering: dots 1-4 are the left column (top->bottom),
    # dots 5-8 are the right column.
    positions = [
        (0, 0),  # dot 1
        (1, 0),  # dot 2
        (2, 0),  # dot 3
        (3, 0),  # dot 4
        (0, 1),  # dot 5
        (1, 1),  # dot 6
        (2, 1),  # dot 7
        (3, 1),  # dot 8
    ]
    for bit, (rg, cg) in enumerate(positions):
        if bits & (1 << bit):
            r0 = rg * 2
            c0 = cg * 4
            t[r0 : r0 + 2, c0 : c0 + 4] = True
    return t


def _brightness_template(brightness: float) -> np.ndarray:
    """
    Generate a binary template for a given brightness level using Bayer ordering.

    Higher brightness => denser pattern (more "on" subpixels).

    Args:
        brightness: Float in [0, 1]. 0 = empty, 1 = full.

    Returns:
        ``(SUB_H, SUB_W)`` boolean template.
    """
    threshold = brightness * 64.0  # Bayer matrix values are 0-63
    return (_BAYER_256 <= threshold).astype(bool)


def _generate_ascii_charset() -> list[tuple[int, np.ndarray]]:
    """
    Generate ASCII character templates ordered by predefined brightness values.

    Uses the brightness values from https://stackoverflow.com/a/74186686 to
    create density-based templates via Bayer ordering. Each character gets a
    template whose density matches its perceived brightness.

    Brightness values represent how much ink/ink-coverage a character has.
    Characters with low brightness values (like ``$``) are visually dense and
    get dense templates; characters with high brightness values (like `` ` ``)
    are visually light and get sparse templates.

    Returns:
        List of ``(codepoint, template)`` pairs.
    """
    chars = list(_ASCII_CHARSET)
    brightness_values = _ASCII_BRIGHTNESS[: len(chars)]

    # Sort brightness values to get distinct density levels (65 levels as specified)
    sorted_brightness = np.sort(np.unique(brightness_values))
    n_levels = len(sorted_brightness)

    # Create a mapping from brightness value to density level index
    # This allows us to assign brightness to each character
    brightness_to_level = {b: i for i, b in enumerate(sorted_brightness)}

    result: list[tuple[int, np.ndarray]] = []
    for char, brightness in zip(chars, brightness_values, strict=True):
        level_idx = brightness_to_level[float(brightness)]
        # Map level to density in [0, 1] range.
        # Brightness values go from 0 (darkest char like $) to ~1 (lightest char like space).
        # We want darkest chars to have the densest templates (density=1) and lightest chars
        # to have the sparest templates (density=0). So we invert: density = 1 - level_idx/max
        density = 1.0 - (level_idx / max(n_levels - 1, 1))
        template = _brightness_template(density)
        # Space character gets a truly empty template so it renders as "nothing"
        # (invisible on any background), matching the behavior of braille's U+2800.
        if char == " ":
            template = np.zeros((SUB_H, SUB_W), dtype=bool)
        result.append((ord(char), template))

    return result


# ---------------------------------------------------------------------------
# Character sets.  Each entry is a list of ``(codepoint, template)`` pairs.
# ---------------------------------------------------------------------------

_BLOCK_GEOMETRIC: list[tuple[int, np.ndarray]] = [
    (ord("█"), _quad_full()),
    (ord("▀"), _half_top()),
    (ord("▄"), _half_bottom()),
    (ord("▌"), _quad_left()),
    (ord("▐"), _quad_right()),
    (ord("░"), _shareshold_pattern(16)),  # ~25 % density
    (ord("▒"), _shareshold_pattern(32)),    # ~50 % density
    (ord("▓"), _shareshold_pattern(48)),    # ~75 % density
]

_HALF_GEOMETRIC: list[tuple[int, np.ndarray]] = [
    (ord("▀"), _half_top()),
    (ord("▄"), _half_bottom()),
]

_QUAD_GEOMETRIC: list[tuple[int, np.ndarray]] = [
    (ord("▘"), _quad_top_left()),
    (ord("▝"), _quad_top_right()),
    (ord("▖"), _quad_bottom_left()),
    (ord("▗"), _quad_bottom_right()),
    (ord("▀"), _half_top()),
    (ord("▄"), _half_bottom()),
    (ord("▌"), _quad_left()),
    (ord("▐"), _quad_right()),
    (ord("▚"), _quad_diag_tl_br()),
    (ord("▞"), _quad_diag_tr_bl()),
]

_BRAILLE_GEOMETRIC: list[tuple[int, np.ndarray]] = [
    (i, _braille_template(i)) for i in range(0x2800, 0x28FF + 1)
]

_ASCII_FONT = _generate_ascii_charset()

_ALL_SET: list[tuple[int, np.ndarray]] = _ASCII_FONT + _BLOCK_GEOMETRIC + _BRAILLE_GEOMETRIC

_SPACE_GEOMETRIC: list[tuple[int, np.ndarray]] = [
    (ord(" "), np.zeros((SUB_H, SUB_W), dtype=bool))
]

CHARSET_BUILDERS: dict[str, Callable[[], list[tuple[int, np.ndarray]]]] = {
    "half": lambda: _HALF_GEOMETRIC,
    "quad": lambda: _QUAD_GEOMETRIC,
    "braille": lambda: _BRAILLE_GEOMETRIC,
    "block": lambda: _BLOCK_GEOMETRIC,
    "ascii": lambda: _ASCII_FONT,
    "all": lambda: _ALL_SET,
    "space": lambda: _SPACE_GEOMETRIC,
}


# ---------------------------------------------------------------------------
# Charset pre-computation.
# ---------------------------------------------------------------------------


class _Charset:
    """
    Pre-computed character templates for a renderer.

    Attributes:
        codes: ``(C,)`` int32 codepoints.
        templates: ``(C, S)`` float32 binary template (1 = ink).
        on_count: ``(C,)`` float32 number of ink subpixels.
        off_count: ``(C,)`` float32 number of paper subpixels.
        cs1: ``(C, S)`` normalised ink template ``t / sqrt(n_on)``.
        cs2: ``(C, S)`` normalised paper template ``(1-t) / sqrt(n_off)``.
        densities: ``(C,)`` float32 ink density ``n_on / S``.
    """

    def __init__(self, entries: list[tuple[int, np.ndarray]]) -> None:
        codes = np.array([e[0] for e in entries], dtype=np.int32)
        flat = np.array([e[1].reshape(-1).astype(np.float32) for e in entries])
        on_count = flat.sum(axis=1)
        off_count = flat.shape[1] - on_count
        self.codes = codes
        self.templates = flat
        self.on_count = on_count
        self.off_count = off_count
        self.S = flat.shape[1]
        with np.errstate(divide="ignore", invalid="ignore"):
            self.cs1 = np.nan_to_num(flat / np.sqrt(on_count)[:, None])
            self.cs2 = np.nan_to_num((1.0 - flat) / np.sqrt(off_count)[:, None])
        self.densities = on_count / self.S


_CHARSET_CACHE: dict[str, _Charset] = {}


def _get_charset(name: str) -> _Charset:
    """Return the (cached) pre-computed charset for ``name``."""
    cs = _CHARSET_CACHE.get(name)
    if cs is None:
        builder = CHARSET_BUILDERS.get(name, CHARSET_BUILDERS["all"])
        cs = _Charset(builder())
        _CHARSET_CACHE[name] = cs
    return cs


# ---------------------------------------------------------------------------
# Dual-color rendering engine.
# ---------------------------------------------------------------------------


def _select_monochrome(
    charset: _Charset, patches_lab: np.ndarray, H: int, W: int
) -> np.ndarray:
    """
    Pick the best character codepoint per cell (monochrome mode).

    Matches the L* channel only.  Ties (e.g. uniform cells) are broken by ink density so that bright
    cells get denser glyphs and dark cells sparser ones.
    """
    lum = patches_lab[:, :, 0]  # (cells, S)
    fg_corr = charset.cs1 @ lum.T  # (C, cells)
    bg_corr = charset.cs2 @ lum.T  # (C, cells)
    score = fg_corr * fg_corr + bg_corr * bg_corr  # (C, cells)
    cell_mean = lum.mean(axis=1) / 100.0  # L* is 0-100; normalise to [0, 1] to
    max_score = score.max(axis=0, keepdims=True)  # (1, cells)
    near_best = score >= max_score * np.float32(0.9999)
    density_diff = np.abs(charset.densities[:, None] - cell_mean[None, :])  # (C, cells)
    density_diff = np.where(near_best, density_diff, np.inf)
    best = np.argmin(density_diff, axis=0)  # (cells,)
    return np.asarray(charset.codes[best].reshape(H, W).astype(np.int32))


def _colors_for_best(
    charset: _Charset,
    patches_rgb: np.ndarray,
    best_idx: np.ndarray,
    H: int,
    W: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Compute per-cell mean foreground/background RGB for the chosen chars."""
    templates_best = charset.templates[best_idx]  # (cells, S) float32
    on_count = templates_best.sum(axis=1)
    off_count = charset.S - on_count
    weight = templates_best[:, :, None]  # (cells, S, 1)
    fg_sum = (patches_rgb * weight).sum(axis=1)
    bg_sum = (patches_rgb * (1.0 - weight)).sum(axis=1)
    fg = np.divide(fg_sum, np.maximum(on_count[:, None], 1.0))
    bg = np.divide(bg_sum, np.maximum(off_count[:, None], 1.0))
    # Templates that are fully on (no paper) or fully off (no ink) mirror the
    # other colour so the cell is still uniformly filled.
    fg = np.where((on_count == 0)[:, None], bg, fg)
    bg = np.where((off_count == 0)[:, None], fg, bg)
    fg = fg.reshape(H, W, 3)
    bg = bg.reshape(H, W, 3)
    return fg, bg


def _render_dual(
    image: np.ndarray,
    charset: _Charset,
    terminal_height: int,
    terminal_width: int,
    *,
    sub_h: int = SUB_H,
    sub_w: int = SUB_W,
    monochrome: bool = False,
) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
    """
    Render ``image`` into terminal cells using ``charset``.

    Args:
        image: ``(H_px, W_px, 3)`` uint8 RGB array (the full matplotlib canvas).
        charset: pre-computed character templates.
        terminal_height: number of terminal cells vertically.
        terminal_width: number of terminal cells horizontally.
        sub_h: vertical subpixel count per cell.
        sub_w: horizontal subpixel count per cell.
        monochrome: if ``True`` return ``(chars, None, None)`` selecting
            characters by luminance density (no colour styling).

    Returns:
        ``(characters, fg, bg)`` following the contract documented at the top
        of this module.
    """
    H = terminal_height
    W = terminal_width
    # Downsample the whole canvas to (W*sub_w, H*sub_h).  The matplotlib figure
    # is 2:1 (cell aspect), so each cell maps to ``sub_h x sub_w`` subpixels
    # after the downscale.
    target_w = W * sub_w
    target_h = H * sub_h
    img_h, img_w = image.shape[:2]
    if img_w == target_w and img_h == target_h:
        # Fast path: canvas already at target resolution.
        small = image
    elif img_w == target_w and img_h == target_h * 2:
        # Width matches and height is exactly 2x (2:1 terminal cell aspect).
        # Average pairs of rows — a fast integer-ratio downscale that avoids
        # the overhead of a full PIL bilinear resize.
        small = np.ascontiguousarray(image).reshape(target_h, 2, target_w, 3).mean(axis=1)
        small = np.ascontiguousarray(small).astype(np.uint8)
    else:
        # General case: full bilinear resize via Pillow.
        small = np.asarray(
            Image.fromarray(image).resize((target_w, target_h), Image.Resampling.BILINEAR)
        )
    small = np.ascontiguousarray(small)
    S = sub_h * sub_w
    # Reshape to (cells, S, 3) with cells ordered row-major (y, x).
    patches = small.reshape(H, sub_h, W, sub_w, 3).transpose(0, 2, 1, 3, 4).reshape(
        H * W, S, 3
    )
    cells = H * W
    patches_rgb = patches.astype(np.float32, copy=False)
    patches_lab = _rgb_to_lab(patches_rgb / 255.0)

    if monochrome:
        characters = _select_monochrome(charset, patches_lab, H, W)
        return characters, None, None

    # --- Colour selection ------------------------------------------------
    score = np.zeros((len(charset.templates), cells), dtype=np.float32)
    for e in range(3):
        patch_e = patches_lab[:, :, e]  # (cells, S)
        fg_corr = charset.cs1 @ patch_e.T  # (C, cells)
        bg_corr = charset.cs2 @ patch_e.T  # (C, cells)
        score += fg_corr * fg_corr + bg_corr * bg_corr
    best_idx = np.argmax(score, axis=0)  # (cells,)
    codes = charset.codes[best_idx]  # (cells,)
    characters = codes.reshape(H, W).astype(np.int32)
    fg, bg = _colors_for_best(charset, patches_rgb, best_idx, H, W)

    return (
        characters,
        fg.astype(np.uint8) if fg is not None else None,
        bg.astype(np.uint8) if bg is not None else None,
    )


# ---------------------------------------------------------------------------
# Renderer classes + factory functions (constructor signature unchanged).
# ---------------------------------------------------------------------------


class TerminalRenderer:
    """Base class kept for introspection; all logic lives in ``_render_dual``."""

    def __init__(self, terminal_width: int, terminal_height: int) -> None:
        """Initialise the renderer with the target terminal dimensions."""
        self.terminal_width = terminal_width
        self.terminal_height = terminal_height

    def render_numpy(
        self, image: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
        """Render ``image`` into terminal cells."""
        raise NotImplementedError


class _DualRenderer(TerminalRenderer):
    def __init__(
        self,
        terminal_width: int,
        terminal_height: int,
        charset_name: str,
        *,
        monochrome: bool = False,
    ) -> None:
        super().__init__(terminal_width, terminal_height)
        self._charset_name = charset_name
        self._monochrome = monochrome

    def render_numpy(
        self, image: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray | None, np.ndarray | None]:
        characters, fg, bg = _render_dual(
            image,
            _get_charset(self._charset_name),
            self.terminal_height,
            self.terminal_width,
            sub_h=SUB_H,
            sub_w=SUB_W,
            monochrome=self._monochrome,
        )
        # For ASCII renderer: replace characters where fg ≈ bg (uniform cells)
        # with space.  For uniform cells the character is invisible regardless of
        # which glyph is chosen, but showing a dense character like '$' in the
        # raw text is confusing.  Space (codepoint 32) is the neutral "nothing".
        if not self._monochrome and fg is not None and bg is not None:
            if self._charset_name in ("ascii", "all"):
                fg_bg_diff = np.abs(fg.astype(np.int16) - bg.astype(np.int16))
                uniform_mask = (fg_bg_diff < 12).all(axis=-1)  # (H, W)
                space_code = np.int32(ord(" "))
                characters = np.where(uniform_mask, space_code, characters)
        return characters, fg, bg


# Factory functions (identical names + signature as the old img2unicode ones).


def get_fast_block_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Block renderer."""
    return _DualRenderer(terminal_width, terminal_height, "block")


def get_fast_all_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """All renderer."""
    return _DualRenderer(terminal_width, terminal_height, "all")


def get_fast_ascii_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """ASCII renderer."""
    return _DualRenderer(terminal_width, terminal_height, "ascii")


def get_space_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Space renderer."""
    return _DualRenderer(terminal_width, terminal_height, "space")


def get_half_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Half renderer."""
    return _DualRenderer(terminal_width, terminal_height, "half")


def get_quad_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Quad renderer."""
    return _DualRenderer(terminal_width, terminal_height, "quad")


def get_braille_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Braille renderer."""
    return _DualRenderer(terminal_width, terminal_height, "braille")


def get_ascii_bw_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """ASCII black-white renderer."""
    return _DualRenderer(terminal_width, terminal_height, "ascii", monochrome=True)


def get_braille_bw_renderer(terminal_width: int, terminal_height: int) -> "_DualRenderer":
    """Braille black-white renderer."""
    return _DualRenderer(terminal_width, terminal_height, "braille", monochrome=True)


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
