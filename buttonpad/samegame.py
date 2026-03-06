"""SameGame clone using ButtonPad.

Rules summary:
    * Remove groups of 2 or more adjacent (4-direction) same-colored blocks.
    * Blocks above fall down (gravity) after removal, and empty columns shift left.
    * Score = percentage of blocks removed when no more moves exist. Perfect game
        (100%) if you remove all blocks.

Implementation notes:
    * Board stored as dict[(x,y)] -> color index or None (empty).
    * cluster_at() performs an iterative flood fill to find a same-colored group.
    * apply_gravity() compacts each column; shift_columns_left() compacts columns.
    * A simple in-memory HIGH_SCORE tracks best percentage this run.
"""

from __future__ import annotations

from typing import List, Optional, Tuple, Dict
import random
import buttonpad

COLS = 15
ROWS = 10

# UI
WINDOW_BG = "#f5f5f5"
EMPTY_BG = "#e8e8e8"

# Palette
GREEN = "#2ecc71"
RED = "#e74c3c"
BLUE = "#3498db"
YELLOW = "#f1c40f"
PURPLE = "#9b59b6"
PALETTE: List[str] = [GREEN, RED, BLUE, YELLOW, PURPLE]

Coord = Tuple[int, int]
BoardType = Dict[Coord, Optional[int]]

# In-memory high score (percentage) for current program run
HIGH_SCORE = 0  # starts at 0%


def build_layout() -> str:
    """Return layout string for a COLS x ROWS grid of independent cells."""
    row = ",".join(["`"] * COLS)
    return "\n".join([row for _ in range(ROWS)])


def in_bounds(x: int, y: int) -> bool:
    """Return True if (x,y) is on the board."""
    return 0 <= x < COLS and 0 <= y < ROWS


def new_game(pad, board: BoardType) -> None:
    """Populate board with random colors and refresh UI & status."""
    for y in range(ROWS):
        for x in range(COLS):
            board[(x, y)] = random.randrange(len(PALETTE))
    update_ui(pad, board)
    update_status(pad)


def update_ui(pad, board: BoardType) -> None:
    """Redraw every cell based on its color index or emptiness."""
    for y in range(ROWS):
        for x in range(COLS):
            el = pad[x, y]  # type: ignore[index]
            idx = board[(x, y)]
            el.text = ""
            el.bg_color = EMPTY_BG if idx is None else PALETTE[idx]


def cluster_at(board: BoardType, x0: int, y0: int) -> List[Coord]:
    """Return list of connected (4-dir) same-colored cells starting at (x0,y0)."""
    if not in_bounds(x0, y0):
        return []
    color = board[(x0, y0)]
    if color is None:
        return []
    visited = set()
    stack = [(x0, y0)]
    out: List[Coord] = []
    while stack:
        x, y = stack.pop()
        if (x, y) in visited or not in_bounds(x, y):
            continue
        if board[(x, y)] != color:
            continue
        visited.add((x, y))
        out.append((x, y))
        stack.extend([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)])
    return out


def remove_cells(board: BoardType, cells: List[Coord]) -> None:
    """Set each coordinate in cells to None (mark empty)."""
    for x, y in cells:
        board[(x, y)] = None


def apply_gravity(board: BoardType) -> None:
    """Let blocks fall down in each column (empties become leading None values)."""
    for x in range(COLS):
        col_vals = [board[(x, y)] for y in range(ROWS) if board[(x, y)] is not None]
        new_col: List[Optional[int]] = [None] * (ROWS - len(col_vals)) + col_vals  # empties at top
        for y in range(ROWS):
            board[(x, y)] = new_col[y]


def shift_columns_left(board: BoardType) -> None:
    """Remove empty columns by sliding remaining columns to the left."""
    nonempty_xs = [x for x in range(COLS) if any(board[(x, y)] is not None for y in range(ROWS))]
    snapshot: Dict[int, List[Optional[int]]] = {x: [board[(x, y)] for y in range(ROWS)] for x in nonempty_xs}
    for y in range(ROWS):
        for x in range(COLS):
            board[(x, y)] = None
    for newx, oldx in enumerate(nonempty_xs):
        col = snapshot[oldx]
        for y in range(ROWS):
            board[(newx, y)] = col[y]


def update_status(pad) -> None:
    """Display current session high score in the status bar."""
    try:
        pad.status_bar = f"High Score: {HIGH_SCORE}%"
    except Exception:
        pass


def has_moves(board: BoardType) -> bool:
    """Return True if there's at least one removable cluster (size >= 2)."""
    seen = set()
    for y in range(ROWS):
        for x in range(COLS):
            if (x, y) in seen or board[(x, y)] is None:
                continue
            cells = cluster_at(board, x, y)
            for cx, cy in cells:
                seen.add((cx, cy))
            if len(cells) >= 2:
                return True
    return False


def on_click(pad, board: BoardType, _el, x: int, y: int) -> None:
    """Handle user clicking a cell: remove cluster & update score if needed."""
    cells = cluster_at(board, x, y)
    if len(cells) < 2:
        return
    remove_cells(board, cells)
    apply_gravity(board)
    shift_columns_left(board)
    update_ui(pad, board)
    if not has_moves(board):  # Game ends -> compute & report score
        remaining = sum(1 for yy in range(ROWS) for xx in range(COLS) if board[(xx, yy)] is not None)
        total = COLS * ROWS
        removed = total - remaining
        score = round((removed / total) * 100)
        msg = f"{remaining} out of {total} blocks remaining. Score: {score}%"
        if remaining == 0:
            msg += " PERFECT GAME!"
        global HIGH_SCORE
        if score > HIGH_SCORE:
            HIGH_SCORE = score
            update_status(pad)
        try:
            buttonpad.alert(msg)
        except Exception:
            print(msg)
        new_game(pad, board)


def main() -> None:
    """Create window, initialize board, start new game and run loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=40,
        cell_height=40,
        padx=2,
        pady=2,
        border=10,
        title="SameGame",
        default_bg_color=EMPTY_BG,
        default_text_color="black",
        window_bg_color=WINDOW_BG,
        resizable=False,
        status_bar="High Score: 0%",
    )
    board: BoardType = {(x, y): None for y in range(ROWS) for x in range(COLS)}
    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y].on_click = (lambda el, xx=x, yy=y: on_click(pad, board, el, xx, yy))  # type: ignore[index]
    new_game(pad, board)
    pad.run()


if __name__ == "__main__":
    main()
