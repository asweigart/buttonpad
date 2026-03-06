"""Peg Solitaire (English cross) implemented with ButtonPad.

This file aims to be beginner-friendly:
* The board is a 7x7 grid but only the central cross is playable.
* Each playable cell can contain a peg (1) or be empty (0); invalid cells use -1.
* A legal move (a "jump") lets a peg leap over an adjacent peg (orthogonally) into an empty hole two spaces away, removing the jumped peg.
* Goal: finish with a single peg (ideally in the center).

Code organization overview:
    - Global constants define colors, sizes, and board geometry.
    - The board data lives in a dictionary mapping (x, y) -> int (-1, 0, 1).
    - Helper functions handle board initialization, UI updates, move validation, and event handling.
    - `main()` builds the UI, wires events, and starts the Tkinter event loop via ButtonPad.

Feel free to skim the constants, then read the functions from top to bottom.
"""

from typing import List, Optional, Tuple, Dict
import buttonpad

COLS = 7
ROWS = 7

# Theme
WINDOW_BG = "#6d4c41"   # brown
PEG_BG = "#d7ccc8"      # light wood for cells with a peg
HOLE_BG = "#bcaaa4"     # slightly darker wood for empty holes
PEG_TEXT = "#4e342e"    # dark brown peg
SELECT_BG = "#ffe082"   # highlight selected peg (amber)

# Board values: -1 invalid, 0 empty, 1 peg

def is_valid_cell(x: int, y: int) -> bool:
    """Return True if (x,y) is a playable cell on the English cross board."""
    # English cross board: valid if in central cross (rows/cols 2..4)
    return (2 <= x <= 4) or (2 <= y <= 4)


def build_layout() -> str:
    """Build the ButtonPad layout string with buttons for valid cells and labels for invalid ones."""
    # Use backtick to disable merge; labels for invalid cells, buttons for valid
    rows: List[str] = []
    for y in range(ROWS):
        tokens: List[str] = []
        for x in range(COLS):
            if is_valid_cell(x, y):
                # Playable cells become buttons (we'll update their visuals later)
                tokens.append("`o")  # no-merge button; placeholder text (will be updated)
            else:
                # Non‑playable cells just show the window background
                tokens.append("`\"\"")  # no-merge blank label
        rows.append(",".join(tokens))
    return "\n".join(rows)


########################
# Global game state
bp = None  # type: ignore
BoardType = Dict[Tuple[int, int], int]
board: BoardType = {}
selected: Optional[Tuple[int, int]] = None


def init_board() -> None:
    """Initialize / reset the board dict with pegs (1), holes (0), and invalid cells (-1)."""
    global board, selected
    selected = None
    # Fill board dict with -1 for invalid, 1 for pegs, except center empty
    board.clear()
    for y in range(ROWS):
        for x in range(COLS):
            if is_valid_cell(x, y):
                # Start with a peg in every valid position...
                board[(x, y)] = 1
            else:
                # ...and mark unusable positions as -1
                board[(x, y)] = -1
    # The traditional starting position leaves the center empty.
    board[(3, 3)] = 0


def peg_count() -> int:
    """Return the current number of pegs on the board."""
    return sum(1 for v in board.values() if v == 1)


def update_status() -> None:
    """Update the status bar with the current peg count."""
    if bp is not None:
        try:
            bp.status_bar = f"Pegs: {peg_count()}"
        except Exception:
            pass


def apply_cell_style(x: int, y: int) -> None:
    """Refresh a single cell's visual based on its value and selection state."""
    if bp is None or not board:
        return
    el = bp[x, y]
    val = board[(x, y)]
    if val == -1:
        el.text = ""
        try:
            el.bg_color = WINDOW_BG
        except Exception:
            pass
        return
    if val == 1:
    # Draw a filled peg symbol (Unicode bullet) when occupied
        el.text = "●"
        el.text_color = PEG_TEXT
        base_bg = PEG_BG
    else:
    # Empty playable hole: show hole background, no text
        el.text = ""
        base_bg = HOLE_BG
    if selected == (x, y) and val == 1:
    # Highlight currently selected peg so user knows which piece will move
        el.bg_color = SELECT_BG
    else:
        el.bg_color = base_bg
    try:
        el.font_size = 20
    except Exception:
        pass


def update_all_cells() -> None:
    """Redraw every cell to reflect the current board and selection state."""
    if not board or bp is None:
        return
    for y in range(ROWS):
        for x in range(COLS):
            apply_cell_style(x, y)


def in_bounds(x: int, y: int) -> bool:
    """Return True if (x,y) lies within the rectangular board dimensions."""
    return 0 <= x < COLS and 0 <= y < ROWS


def can_jump(sx: int, sy: int, dx: int, dy: int) -> bool:
    """Return True if a legal jump exists from (sx,sy) to (dx,dy)."""
    # Destination must be inside board AND a valid playable cell
    if not (in_bounds(dx, dy) and is_valid_cell(dx, dy)):
        return False
    # Must start on a peg and land in an empty hole
    if board[(sx, sy)] != 1 or board[(dx, dy)] != 0:
        return False
    vx, vy = dx - sx, dy - sy
    # Only orthogonal jumps exactly two cells away are legal
    if (abs(vx), abs(vy)) not in ((2, 0), (0, 2)):
        return False
    mx, my = sx + vx // 2, sy + vy // 2
    # The midpoint cell must contain the jumped-over peg
    if not in_bounds(mx, my) or board[(mx, my)] != 1:
        return False
    return True


def perform_jump(sx: int, sy: int, dx: int, dy: int) -> None:
    """Execute a jump move, removing the jumped peg and updating UI."""
    vx, vy = dx - sx, dy - sy
    mx, my = sx + vx // 2, sy + vy // 2
    # Vacate start, remove middle peg, occupy destination
    board[(sx, sy)] = 0
    board[(mx, my)] = 0
    board[(dx, dy)] = 1
    apply_cell_style(sx, sy)
    apply_cell_style(mx, my)
    apply_cell_style(dx, dy)
    update_status()


def on_cell_click(_el, x: int, y: int) -> None:
    """Handle clicks: select pegs, deselect, or perform jumps onto empty holes."""
    global selected
    if not is_valid_cell(x, y):
        return
    val = board[(x, y)]
    if val == 1:
        # Clicking a peg: either select it, or deselect if it's already selected
        if selected == (x, y):
            selected = None
            apply_cell_style(x, y)
            return
        if selected is not None:
            # Deselect previous peg visually
            px, py = selected
            apply_cell_style(px, py)
        selected = (x, y)
        apply_cell_style(x, y)
        return
    if val == 0 and selected is not None:
        # Attempt a jump from the currently selected peg into this empty hole
        sx, sy = selected
        if can_jump(sx, sy, x, y):
            perform_jump(sx, sy, x, y)
            selected = None
            return


def new_game() -> None:
    """Start a new game by reinitializing board and updating UI."""
    init_board()
    update_all_cells()
    update_status()


def rebind_menu() -> None:
    """Configure the application menu (currently New Game + Quit)."""
    if bp is not None:
        bp.menu = {
            "File": {
                "New Game": (new_game, "Cmd+N"),
                "Quit": (bp.quit, "Cmd+Q"),
            }
        }


def main() -> None:
    """Program entry: create UI, initialize game state, wire handlers, and start event loop."""
    global bp, board, selected
    layout = build_layout()
    peg_count_initial = sum(1 for y in range(ROWS) for x in range(COLS) if is_valid_cell(x, y)) - 1
    bp = buttonpad.ButtonPad(
        layout=layout,
        cell_width=48,
        cell_height=48,
        padx=2,
        pady=2,
        window_bg_color=WINDOW_BG,
        default_bg_color=PEG_BG,
        default_text_color=PEG_TEXT,
        title="Peg Solitaire",
        resizable=False,
        border=8,
        status_bar=f"Pegs remaining: {peg_count_initial}",
        menu=None,
    )

    bp.status_bar_text_color = "black"
    board = {(x, y): -1 for y in range(ROWS) for x in range(COLS)}
    selected = None
    init_board()
    update_all_cells()
    update_status()
    for y in range(ROWS):
        for x in range(COLS):
            if is_valid_cell(x, y):
                el = bp[x, y]
                # Use a lambda with default args to capture current coordinates
                el.on_click = lambda _el, xx=x, yy=y: on_cell_click(_el, xx, yy)
    rebind_menu()
    bp.run()


if __name__ == "__main__":
    main()
