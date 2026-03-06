"""Keyboard movement demonstration using ButtonPad.

Beginner overview:
    * We create an 8x8 grid of empty cells.
    * A single "cursor" (a highlighted cell) can be moved with arrow keys or
        WASD keys, or by clicking a destination cell with the mouse.
    * Movement wraps around the edges (going left from column 0 jumps to the
        last column, etc.).
    * The example shows how to bind keyboard events and cell click callbacks.
"""

from __future__ import annotations

import buttonpad

COLS = 8
ROWS = 8

# UI
WINDOW_BG = "#0e1220"   # dark backdrop
BTN_BG = "#1f2640"       # default button background
BTN_FG = "#e6e6e6"       # default text color
CURSOR_BG = "#2b78ff"    # blue highlight for current position


def build_layout(cols: int, rows: int) -> str:
    """Return the layout string for an unmerged grid of size cols x rows.

    Each cell uses the backtick token ` which creates an empty label/button
    in ButtonPad. We repeat the row text 'rows' times separated by newlines.
    """
    # Use no-merge empty buttons so each cell is independent (all individually clickable)
    row = ",".join(["`"] * cols)
    return "\n".join([row for _ in range(rows)])


def main() -> None:
    """Create the grid, set up movement handlers, and start the event loop.

    Steps:
      1. Build a textual layout for an 8x8 grid.
      2. Create the ButtonPad window with styling.
      3. Track a mutable dict pos holding current cursor coordinates.
      4. Define helper functions to highlight/unhighlight and move the cursor.
      5. Bind mouse clicks and keyboard keys to move the cursor.
      6. Start the GUI loop so events begin firing.
    """
    layout = build_layout(COLS, ROWS)
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=48,
        cell_height=48,
        padx=4,
        pady=4,
        border=8,
        title="Keyboard Movement Demo",
        default_bg_color=BTN_BG,
        default_text_color=BTN_FG,
        window_bg_color=WINDOW_BG,
        resizable=True,
    )

    # Current cursor position (start near the center). Using a dict lets inner
    # functions modify coordinates without needing 'nonlocal' or global vars.
    pos = {"x": 3, "y": 3}
    default_bg = BTN_BG

    def highlight(x: int, y: int) -> None:
        """Visually mark the cursor cell at (x,y)."""
        pad[x, y].bg_color = CURSOR_BG  # type: ignore[index]
        pad[x, y].text = ""  # keep it clean (no letter needed)

    def unhighlight(x: int, y: int) -> None:
        """Return a cell to the normal background color."""
        pad[x, y].bg_color = default_bg  # type: ignore[index]
        pad[x, y].text = ""

    def move_to(nx: int, ny: int) -> None:
        """Move the cursor to (nx, ny) with wrap-around and update visuals.

        Wrap-around means moving left from column 0 goes to the last column.
        If the new location is the same as current, we do nothing.
        """
        # Wrap indices using modulo so we stay inside 0..COLS-1 / 0..ROWS-1
        nx %= COLS
        ny %= ROWS
        if nx == pos["x"] and ny == pos["y"]:  # No change
            return
        # Update visuals: remove old highlight then apply new highlight
        unhighlight(pos["x"], pos["y"])  # previous location
        pos["x"], pos["y"] = nx, ny
        highlight(nx, ny)

    def on_cell_click(_el, x: int, y: int) -> None:
        """Mouse click handler that moves cursor directly to clicked cell."""
        move_to(x, y)

    # Assign the click handler to every cell so user can reposition cursor quickly.
    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y].on_click = on_cell_click  # type: ignore[index]

    # Keyboard movement functions. Each receives an (optional) Tk event object we ignore.
    def on_left(_evt=None):
        """Move cursor one cell left (wrap-around)."""
        move_to(pos["x"] - 1, pos["y"])  # wrap in move_to

    def on_right(_evt=None):
        """Move cursor one cell right (wrap-around)."""
        move_to(pos["x"] + 1, pos["y"])

    def on_up(_evt=None):
        """Move cursor one cell up (wrap-around)."""
        move_to(pos["x"], pos["y"] - 1)

    def on_down(_evt=None):
        """Move cursor one cell down (wrap-around)."""
        move_to(pos["x"], pos["y"] + 1)

    # Bind arrows and WASD (both lowercase/uppercase) for accessibility/variety.
    try:
        pad.root.bind_all("<Left>", on_left)
        pad.root.bind_all("<Right>", on_right)
        pad.root.bind_all("<Up>", on_up)
        pad.root.bind_all("<Down>", on_down)
        # WASD keys (lower & upper case)
        pad.root.bind_all("<KeyPress-a>", on_left)
        pad.root.bind_all("<KeyPress-A>", on_left)
        pad.root.bind_all("<KeyPress-d>", on_right)
        pad.root.bind_all("<KeyPress-D>", on_right)
        pad.root.bind_all("<KeyPress-w>", on_up)
        pad.root.bind_all("<KeyPress-W>", on_up)
        pad.root.bind_all("<KeyPress-s>", on_down)
        pad.root.bind_all("<KeyPress-S>", on_down)
    except Exception:
        # Some environments may not allow key binding (rare). We silently ignore.
        pass

    # Show the starting cursor location.
    highlight(pos["x"], pos["y"])

    pad.run()  # Enter Tkinter's event loop; the program now waits for events.


if __name__ == "__main__":
    main()
