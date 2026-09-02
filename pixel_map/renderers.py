"""
Terminal renderers.

Re-exports the native renderers implemented in :mod:`pixel_map.terminal_renderers`
which replace the previous ``img2unicode`` back-end.  The public names and
constructor signature ``(terminal_width, terminal_height)`` are unchanged so
that :mod:`pixel_map.plotter` and :mod:`pixel_map.__main__` keep working
without modification.
"""

from pixel_map.terminal_renderers import (  # noqa: F401
    AVAILABLE_RENDERERS as AVAILABLE_RENDERERS,
)
from pixel_map.terminal_renderers import (
    TerminalRenderer as TerminalRenderer,
)
