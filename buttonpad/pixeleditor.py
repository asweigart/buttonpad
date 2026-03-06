"""Simple pixel art editor using ButtonPad.

How it works:
    * 24 x 24 grid; each cell stores an index into a color palette.
    * Clicking a cell cycles its color to the next palette entry (wrap-around).
    * A tooltip (if supported) shows the cell's coordinates.

Beginner notes:
    * The board is a 2D list of ints; each int is an index in PALETTE.
    * set_cell() centralizes updating the data structure AND GUI element.
    * cycle_color() just computes next index and calls set_cell().
"""

from __future__ import annotations
from typing import List

try:
    import buttonpad  # local module name
except Exception:
    import ButtonPad as buttonpad  # type: ignore

COLS = 24
ROWS = 24
WINDOW_BG = "#f0f0f0"

# Basic color palette (cycle order)
PALETTE: List[str] = [
    "#ffffff",  # white
    "#000000",  # black
    "#ff0000",  # red
    "#00ff00",  # green
    "#0000ff",  # blue
    "#ffff00",  # yellow
    "#00ffff",  # cyan
    "#ff00ff",  # magenta
]


def build_layout() -> str:
    """Return a layout of independent buttons (each token is a backtick)."""
    row = ",".join(["`"] * COLS)
    return "\n".join([row for _ in range(ROWS)])


def main() -> None:
    """Create window, initialize board, wire handlers, and start event loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=22,
        cell_height=22,
        padx=0,
        pady=0,
        border=10,
        title="Pixel Editor",
        default_bg_color=PALETTE[0],
        default_text_color="black",
        window_bg_color=WINDOW_BG,
        resizable=True,
    )

    board: List[List[int]] = [[0 for _ in range(COLS)] for _ in range(ROWS)]  # palette indices

    def set_cell(x: int, y: int, idx: int) -> None:
        """Store palette index for (x,y) and repaint its background."""
        board[y][x] = idx % len(PALETTE)
        el = pad[x, y]  # type: ignore[index]
        el.bg_color = PALETTE[board[y][x]]
        el.text = ""

    def cycle_color(el, x: int, y: int) -> None:
        """Advance this cell's palette index by one (wrap)."""
        idx = (board[y][x] + 1) % len(PALETTE)
        set_cell(x, y, idx)

    for y in range(ROWS):
        for x in range(COLS):
            set_cell(x, y, 0)
            pad[x, y].on_click = cycle_color  # type: ignore[index]
            try:  # optional tooltip with coordinates
                pad[x, y].tooltip = f"{x}, {y}"  # type: ignore[index]
            except Exception:
                pass

    pad.run()


if __name__ == "__main__":
    main()
