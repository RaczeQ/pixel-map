"""
Benchmarks for terminal renderers.

Measures the ``render_numpy`` step (the image-to-unicode conversion) for every
renderer, both on a synthetic RGB canvas and on real matplotlib output.

Usage::

    pdm run python benchmarks/bench_render.py
     pdm run python benchmarks/bench_render.py --repeats 5 --renderers block

Baseline (img2unicode on ``main``, 78x21 cells @ dpi=10, synthetic gradient):

| renderer  | img2unicode | native  | speedup |
|-----------|-------------|---------|---------|
| block     |   40.5 ms   |  8.9 ms |   ~4.5x |
| half      |   11.3 ms   |  9.3 ms |   ~1.2x |
| quad      |   11.5 ms   |  9.7 ms |   ~1.2x |
| space     |   11.1 ms   |  9.2 ms |   ~1.2x |
| ascii     |   46.9 ms   |  9.0 ms |   ~5.2x |
| all       |  496.5 ms   | 10.5 ms |  ~47x   |
| braille   |  450.9 ms   | 10.4 ms |  ~43x   |
| braille-bw|  445.7 ms   |  8.2 ms |  ~54x   |
| ascii-bw  |  379.3 ms   |  6.1 ms |  ~62x   |
"""

from __future__ import annotations

import argparse
import statistics
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from pixel_map.renderers import AVAILABLE_RENDERERS  # noqa: E402

RENDERER_NAMES = list(AVAILABLE_RENDERERS.keys())

# Representative terminal canvas sizes.
# console_width=80, console_height=24 with a border => 78 x 21 cells;
# matplotlib canvas at dpi=10 is figsize=(78, 42) => ~780 x 420 px.
DEFAULT_WIDTH = 78
DEFAULT_HEIGHT = 21
DEFAULT_DPI = 10


def make_synthetic_image(
    width: int, height: int, dpi: int = DEFAULT_DPI
) -> np.ndarray:
    """Build a deterministic synthetic RGB image for benchmarking."""
    w_px = width * dpi
    h_px = height * dpi * 2
    xs = np.linspace(0, 1, w_px)
    ys = np.linspace(0, 1, h_px)
    xv, yv = np.meshgrid(xs, ys)
    r = (xv * 255).astype(np.uint8)
    g = (yv * 255).astype(np.uint8)
    b = ((xv + yv) / 2 * 255).astype(np.uint8)
    return np.stack([r, g, b], axis=-1)


def time_render(
    renderer_name: str,
    image: np.ndarray,
    width: int,
    height: int,
    repeats: int,
    warmup: int,
) -> list[float]:
    """Time ``render_numpy`` for a single renderer and return per-repeat samples."""
    factory = AVAILABLE_RENDERERS[renderer_name]
    renderer = factory(terminal_width=width, terminal_height=height)

    for _ in range(warmup):
        renderer.render_numpy(image)

    samples: list[float] = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        renderer.render_numpy(image)
        samples.append(time.perf_counter() - t0)
    return samples


def print_report(name: str, samples: list[float]) -> None:
    """Print mean/min/median/max timing for one renderer."""
    mean_ms = statistics.mean(samples) * 1000
    min_ms = min(samples) * 1000
    median_ms = statistics.median(samples) * 1000
    max_ms = max(samples) * 1000
    print(
        f"  {name:14s} mean={mean_ms:7.1f}ms  "
        f"min={min_ms:7.1f}ms  median={median_ms:7.1f}ms  "
        f"max={max_ms:7.1f}ms"
    )


def run_bench(
    renderers: list[str],
    width: int,
    height: int,
    dpi: int,
    repeats: int,
    warmup: int,
) -> None:
    """Benchmark the ``render_numpy`` step for every renderer on a synthetic image."""
    image = make_synthetic_image(width, height, dpi=dpi)
    print(
        f"Synthetic image: {image.shape[1]}x{image.shape[0]} "
        f"({width}x{height} cells @ dpi={dpi})"
    )
    print(f"Warm-up: {warmup}  Repeats: {repeats}\n")

    results = {}
    for name in renderers:
        factory = AVAILABLE_RENDERERS[name]
        renderer = factory(terminal_width=width, terminal_height=height)
        # Sanity: confirm the contract.
        chars, fg, bg = renderer.render_numpy(image)
        assert chars.ndim == 2
        assert np.issubdtype(chars.dtype, np.integer) or chars.dtype.kind == "i"
        fg_ok = fg is None or fg.shape == chars.shape + (3,)
        bg_ok = bg is None or bg.shape == chars.shape + (3,)
        assert fg_ok and bg_ok, f"contract mismatch for {name}"
        samples = time_render(name, image, width, height, repeats, warmup)
        print_report(name, samples)
        results[name] = statistics.mean(samples) * 1000

    print()
    fastest = min(results, key=lambda k: results[k])
    slowest = max(results, key=lambda k: results[k])
    print(f"Fastest: {fastest} ({results[fastest]:.1f}ms)")
    print(f"Slowest: {slowest} ({results[slowest]:.1f}ms)")


def run_full_pipeline(
    renderers: list[str],
    example: str,
    repeats: int,
    warmup: int,
) -> None:
    """
    Benchmark the full ``plot_geo_data`` pipeline end-to-end.

    Requires network access for the contextily basemap.
    """
    from pixel_map.plotter import plot_geo_data

    example_path = str(
        Path(__file__).parent.parent / "pixel_map" / "example_files" / f"{example}.parquet"
    )
    print(f"Full pipeline on '{example}' ({example_path}) (needs network for basemap)\n")

    for name in renderers:
        # warmup
        for _ in range(warmup):
            plot_geo_data(
                [example_path],
                renderer=name,
                basemap_provider="CartoDB.DarkMatterNoLabels",
                console_width=100,
                console_height=30,
            )
        samples: list[float] = []
        for _ in range(repeats):
            t0 = time.perf_counter()
            plot_geo_data(
                [example_path],
                renderer=name,
                basemap_provider="CartoDB.DarkMatterNoLabels",
                console_width=100,
                console_height=30,
            )
            samples.append(time.perf_counter() - t0)
        print_report(name, samples)


def main() -> None:
    """Parse CLI arguments and run the benchmark."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--renderers",
        nargs="+",
        default=RENDERER_NAMES,
        help="Renderers to benchmark (default: all)",
    )
    parser.add_argument("--width", type=int, default=DEFAULT_WIDTH)
    parser.add_argument("--height", type=int, default=DEFAULT_HEIGHT)
    parser.add_argument("--dpi", type=int, default=DEFAULT_DPI)
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument(
        "--example", default=None, help="Run full-pipeline benchmark on an example file"
    )
    args = parser.parse_args()

    if args.repeats < 1:
        parser.error("--repeats must be at least 1")
    if args.warmup < 0:
        parser.error("--warmup must be non-negative")
    for r in args.renderers:
        if r not in AVAILABLE_RENDERERS:
            parser.error(f"Unknown renderer '{r}'. Available: {', '.join(RENDERER_NAMES)}")

    run_bench(args.renderers, args.width, args.height, args.dpi, args.repeats, args.warmup)

    if args.example is not None:
        run_full_pipeline(args.renderers, args.example, args.repeats, args.warmup)


if __name__ == "__main__":
    main()
