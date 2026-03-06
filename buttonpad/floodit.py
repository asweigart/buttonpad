"""Flood-It clone using ButtonPad.

Game rules (simplified): Starting from the top-left corner, change the color
of the connected region to eventually make the entire board one color in as
few moves as possible.

UI layout (total rows = 18 board + 2 info rows = 20 visual rows):
    * Rows 0..17: 18x18 grid of color cells (the puzzle board).
    * Row 18: Info/controls row (seed entry, new puzzle button, best/current scores).
    * Row 19: Palette row (6 big color buttons; each spans 3 columns).

Beginner notes:
    * The board is stored in a dict mapping (x, y) -> color index (0..5).
    * flood_fill() changes the connected component starting at (0,0) to a new color.
    * Moves are tracked, and per-seed best scores are stored in a dictionary.
    * The seed determines the randomized board; generating with the same seed
        produces the same puzzle, making comparisons of move counts meaningful.
"""

from __future__ import annotations
from typing import List, Tuple, Dict
import random

import buttonpad  # local module name

COLS = 18
ROWS = 18  # board only; layout adds 2 more rows (info + palette)

# After random fill, perform extra smoothing iterations by copying
# a random neighbor's color into random cells to increase contiguity.
# Adjustable constant; default ties to board size.
SMOOTHING_STEPS = COLS * ROWS // 4

# Six distinct pleasant colors
PALETTE = [
    "green",
    "red",
    "blue",
    "yellow",
    "purple",
    "orange",
]

Coord = Tuple[int, int]
BoardType = Dict[Coord, int]

# Global state references (initialized in main)
pad = None  # type: ignore[assignment]
board: BoardType
moves: Dict[str, int]
best_scores: Dict[int, int]
current_seed: Dict[str, int]
seed_entry = None  # type: ignore[assignment]
best_val_label = None  # type: ignore[assignment]
cur_val_label = None  # type: ignore[assignment]
palette_buttons: List
new_btn = None  # type: ignore[assignment]


def build_layout(initial_seed: int) -> str:
        """Return the ButtonPad layout string.

        We create:
            * An 18x18 board of unmerged cells (each token `'' = empty label cell).
            * An info row with merged cells for labels, seed entry, new game, scores.
            * A final row of 6 palette buttons (each spanning 3 columns). Tokens with
                identical consecutive names merge automatically in ButtonPad.
        """
        # Board rows
        top_row = ",".join(["`''"] * COLS)
        top = "\n".join([top_row for _ in range(ROWS)])

        # Info row content tokens
        info: List[str] = []
        info += ["'Puzzle Seed:'"] * 3  # label spans 3 columns
        info += [f"[{initial_seed}]"] * 4  # seed entry spans 4 columns
        info += ["New Puzzle"] * 3        # new puzzle button
        info += ["'Best Score:'"] * 3     # best label
        info += ["''"] * 2                # best value display
        info += ["'Current Score:'"] * 2  # current label
        info += ["''"] * 1                # current value
        info_row = ",".join(info)

        # Palette row: 6 colors * 3 columns each
        pal_tokens: List[str] = []
        for i in range(6):
                token = f"C{i+1}"
                pal_tokens += [token] * 3
        palette_row = ",".join(pal_tokens)
        return "\n".join([top, info_row, palette_row])


def all_same_color(board: BoardType) -> bool:
    """Return True if every cell on the board has the same color index."""
    first = board[(0, 0)]
    for y in range(ROWS):
        for x in range(COLS):
            if board[(x, y)] != first:
                return False
    return True


def flood_fill(board: BoardType, x: int, y: int, new_color: int) -> int:
    """Flood-fill starting at (x,y); return count of modified cells.

    We use an iterative stack-based approach (q list) to avoid recursion depth
    issues. Only cells matching the original color are changed; neighbors
    (4-direction) are explored.
    """
    orig = board[(x, y)]
    if orig == new_color:
        return 0
    q: List[Coord] = [(x, y)]
    changed = 0
    while q:
        cx, cy = q.pop()
        if board[(cx, cy)] != orig:
            continue
        board[(cx, cy)] = new_color
        changed += 1
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = cx + dx, cy + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS and board[(nx, ny)] == orig:
                q.append((nx, ny))
    return changed


def update_board_ui() -> None:
    """Apply board colors to the GUI elements."""
    for y in range(ROWS):
        for x in range(COLS):
            el = pad[x, y]  # type: ignore[index]
            el.text = ""
            el.bg_color = PALETTE[board[(x, y)]]


def update_scores_ui(seed_val: int) -> None:
    """Refresh the best/current score labels for the given seed."""
    if seed_val in best_scores:
        best_val_label.text = str(best_scores[seed_val])  # type: ignore[union-attr]
    else:
        best_val_label.text = "-"  # type: ignore[union-attr]
    cur_val_label.text = str(moves["count"])  # type: ignore[union-attr]


def parse_seed() -> int:
    """Return the integer seed from the entry (or randomize if invalid)."""
    try:
        return int(seed_entry.text.strip())  # type: ignore[union-attr]
    except Exception:
        s = random.randint(1000, 9999)
        seed_entry.text = str(s)  # type: ignore[union-attr]
        return s


def new_puzzle() -> None:
    """Generate a new randomized board using the current/entered seed.

    Steps:
      1. Read/validate seed.
      2. Fill board with random colors.
      3. Ensure not trivially solved (force a change if uniform).
      4. Perform smoothing passes copying neighbor colors to create blobs.
      5. Reset move count & update UI.
    """
    s = parse_seed()
    random.seed(s)
    current_seed["value"] = s
    for y in range(ROWS):
        for x in range(COLS):
            board[(x, y)] = random.randrange(0, 6)
    if all_same_color(board):  # Avoid instantly-solved puzzle
        board[(0, 0)] = (board[(0, 0)] + 1) % 6
    for _ in range(SMOOTHING_STEPS):  # Add contiguity by local copying
        x = random.randrange(0, COLS)
        y = random.randrange(0, ROWS)
        neighbors = []
        if x > 0:
            neighbors.append((x - 1, y))
        if x < COLS - 1:
            neighbors.append((x + 1, y))
        if y > 0:
            neighbors.append((x, y - 1))
        if y < ROWS - 1:
            neighbors.append((x, y + 1))
        if neighbors:
            nx, ny = random.choice(neighbors)
            board[(x, y)] = board[(nx, ny)]
    moves["count"] = 0
    update_board_ui()
    update_scores_ui(s)


def maybe_finish_and_update_best(seed_val: int) -> None:
    """If puzzle solved, record best score for this seed if it's an improvement."""
    if all_same_color(board):
        cur = moves["count"]
        prev = best_scores.get(seed_val)
        if prev is None or cur < prev:
            best_scores[seed_val] = cur
            best_val_label.text = str(cur)  # type: ignore[union-attr]


def pick_color(color_index: int, _el=None, _x=None, _y=None) -> None:
    """Handle palette click: flood-fill starting region to selected color."""
    s = current_seed["value"]
    if board[(0, 0)] != color_index:
        flood_fill(board, 0, 0, color_index)
        moves["count"] += 1
        cur_val_label.text = str(moves["count"])  # type: ignore[union-attr]
        update_board_ui()
        maybe_finish_and_update_best(s)


def main() -> None:
    """Construct the UI, initialize state, and start the game."""
    global pad, board, moves, best_scores, current_seed, seed_entry, best_val_label, cur_val_label, palette_buttons, new_btn
    initial_seed = random.randint(1000, 9999)
    layout = build_layout(initial_seed)
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=26,
        cell_height=26,
        padx=2,
        pady=2,
        border=10,
        title="Flood-It",
        default_bg_color="lightgray",
        default_text_color="#222222",
        window_bg_color="#f5f5f5",
        resizable=True,
    )
    board = {(x, y): 0 for y in range(ROWS) for x in range(COLS)}
    moves = {"count": 0}
    best_scores = {}

    # Element references (merged top-left tokens for multi-column elements)
    seed_label = pad[0, ROWS]
    seed_entry = pad[3, ROWS]
    new_btn = pad[7, ROWS]
    best_label = pad[10, ROWS]
    best_val_label = pad[13, ROWS]
    cur_label = pad[15, ROWS]
    cur_val_label = pad[17, ROWS]

    # Palette buttons (row ROWS+1 at x positions 0,3,6,9,12,15)
    palette_buttons = [pad[i * 3, ROWS + 1] for i in range(6)]

    # Style palette buttons (color blocks with no text)
    for i, el in enumerate(palette_buttons):
        el.text = ""
        el.bg_color = PALETTE[i]

    # Multi-line labels (newlines inserted programmatically)
    seed_label.text = "Puzzle\nSeed:"
    new_btn.text = "New\nPuzzle"
    best_label.text = "Best\nScore:"
    cur_label.text = "Current\nScore:"

    current_seed = {"value": initial_seed}

    # Palette click handlers (capture index via default arg in lambda)
    for idx, el in enumerate(palette_buttons):
        el.on_click = (lambda _e, _x, _y, i=idx: pick_color(i))

    new_btn.on_click = lambda _e, _x, _y: new_puzzle()  # New puzzle button

    new_puzzle()  # Initialize first board
    pad.run()


if __name__ == "__main__":
    main()
