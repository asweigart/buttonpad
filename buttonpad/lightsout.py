"""Lights Out puzzle implemented with ButtonPad.

Goal: Turn off (darken) all the lights. Clicking a cell toggles that cell and
its four orthogonal neighbors (up/down/left/right). When all lights are off,
the board briefly flashes colors and a new random puzzle appears.

Beginner notes:
    * The puzzle state is a 5x5 list of booleans (True = ON, False = OFF).
    * We redraw all cells after each move (simple and fine for small boards).
    * The flashing win animation uses a scheduled callback (pad.root.after).
    * A factory function builds the click handler so it can capture references
        to both the pad (UI) and the shared state list.
"""

from __future__ import annotations

import random
from typing import List
from buttonpad import ButtonPad

# 5x5 grid where each cell is a standalone button (no-merge using backtick `)
LAYOUT = """
`.,`.,`.,`.,`.
`.,`.,`.,`.,`.
`.,`.,`.,`.,`.
`.,`.,`.,`.,`.
`.,`.,`.,`.,`.
""".strip()

GRID_W = GRID_H = 5

# Colors / looks
ON_BG   = "#ffd54f"   # warm yellow
OFF_BG  = "#2b2b2b"   # dark gray
ON_FG   = "black"
OFF_FG  = "#bbbbbb"
FONT    = "TkDefaultFont"
FONT_SZ = 20

FLASH_ON  = "#00e676"  # green flash
FLASH_OFF = "#1e1e1e"
FLASH_COUNT = 6        # total on/off toggles
FLASH_MS    = 120      # ms between flashes


# --- game logic helpers (global) ---
def in_bounds(x: int, y: int) -> bool:
    """Return True if (x,y) is inside the puzzle grid."""
    return 0 <= x < GRID_W and 0 <= y < GRID_H


def toggle(state: List[List[bool]], x: int, y: int) -> None:
    """Invert (flip) the boolean at (x,y) if that coordinate exists."""
    if in_bounds(x, y):
        state[y][x] = not state[y][x]


def is_solved(state: List[List[bool]]) -> bool:
    """Return True if every light is OFF (False)."""
    return all(not v for row in state for v in row)


def new_random_puzzle(state: List[List[bool]], moves: int = 20) -> None:
    """Randomize a puzzle by applying a number of random legitimate moves.

    Strategy: Start from an all-OFF board and perform 'moves' random clicks.
    Each random click toggles the selected cell + its neighbors. This ensures
    the resulting board is always solvable (because we built it by valid moves).
    """
    for y in range(GRID_H):
        for x in range(GRID_W):
            state[y][x] = False
    for _ in range(moves):
        rx, ry = random.randrange(GRID_W), random.randrange(GRID_H)
        toggle(state, rx, ry)
        toggle(state, rx-1, ry)
        toggle(state, rx+1, ry)
        toggle(state, rx, ry-1)
        toggle(state, rx, ry+1)


def redraw(pad: ButtonPad, state: List[List[bool]]) -> None:
    """Update every cell's color to reflect the boolean 'state'."""
    for y in range(GRID_H):
        for x in range(GRID_W):
            el = pad[x, y]
            if state[y][x]:
                el.bg_color = ON_BG
                el.text_color = ON_FG
            else:
                el.bg_color = OFF_BG
                el.text_color = OFF_FG


def set_all(pad: ButtonPad, bg: str, fg: str) -> None:
    """Set the background & text color of all cells (used for win flash)."""
    for y in range(GRID_H):
        for x in range(GRID_W):
            el = pad[x, y]
            el.bg_color = bg
            el.text_color = fg


def win_flash_then_new(pad: ButtonPad, state: List[List[bool]], step: int = 0) -> None:
    """Flash colors to celebrate a win, then start a new randomized puzzle.

    We schedule repeated calls using pad.root.after until 'step' reaches
    FLASH_COUNT. Alternating steps choose different colors for a strobe effect.
    """
    if step >= FLASH_COUNT:
        new_random_puzzle(state)
        redraw(pad, state)
        return
    if step % 2 == 0:
        set_all(pad, FLASH_ON, "black")
    else:
        set_all(pad, FLASH_OFF, "white")
    try:
        pad.root.after(FLASH_MS, lambda: win_flash_then_new(pad, state, step + 1))
    except Exception:
        pass  # Window may be closed before animation ends


def handle_click_factory(pad: ButtonPad, state: List[List[bool]]):
    """Return a click handler bound to this pad & state (closure pattern).

    ButtonPad gives us the element + coordinates; we ignore the element
    itself and just use the (x,y) to apply the Lights Out toggle pattern.
    """
    def handler(_el, x: int, y: int):
        # Toggle clicked cell + its four neighbors
        toggle(state, x, y)
        toggle(state, x-1, y)
        toggle(state, x+1, y)
        toggle(state, x, y-1)
        toggle(state, x, y+1)
        redraw(pad, state)
        if is_solved(state):  # After every move, test for victory
            win_flash_then_new(pad, state)
    return handler


def main() -> None:
    """Create the window, configure cells, start a random puzzle, run loop."""
    pad = ButtonPad(
        layout=LAYOUT,
        cell_width=70,
        cell_height=70,
        padx=6,
        pady=6,
        window_bg_color="#121212",
        default_bg_color="#121212",
        default_text_color="white",
        title="Lights Out (5×5)",
        resizable=True,
        border=12,
    )
    state: List[List[bool]] = [[False]*GRID_W for _ in range(GRID_H)]
    handler = handle_click_factory(pad, state)
    for y in range(GRID_H):
        for x in range(GRID_W):
            el = pad[x, y]
            el.font_name = FONT
            el.font_size = FONT_SZ
            el.text = ''  # no text; background color represents state
            el.on_click = handler
    new_random_puzzle(state)
    redraw(pad, state)
    pad.run()


if __name__ == "__main__":
    main()
