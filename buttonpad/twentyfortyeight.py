"""2048 number merging puzzle.

Rules summary:
    * Press arrow keys (or WASD) to slide all tiles in that direction.
    * Adjacent equal tiles merge once per move (2+2 -> 4, etc.).
    * After each successful move a new tile (2 or 4) appears in a random empty cell.
    * Goal: create a tile with value 2048 (game auto-restarts on win or loss here).

Implementation notes:
    * Board stored as dictionary mapping (x,y) -> value.
    * Movement reuses a helper (move_line) to compress & merge a one-dimensional list.
    * apply_move handles directional orientation by reversing lines for right/down.
    * After a move we check for win (2048) or if no moves remain (loss).
"""
from __future__ import annotations

import random
from typing import List, Tuple, Dict
import buttonpad

COLS = 4
ROWS = 4

# Appearance
WINDOW_BG = "#0e1220"    # dark backdrop
EMPTY_BG = "#1f2640"     # empty cell
TEXT_COLOR = "#ffffff"    # always white text
FONT_SIZE = 24

# Background colors per tile value (fallback used if missing)
TILE_BG = {
    0: EMPTY_BG,
    2: "#3c3f58",
    4: "#4455aa",
    8: "#2b78ff",
    16: "#26a69a",
    32: "#43a047",
    64: "#f57c00",
    128: "#e64a19",
    256: "#d32f2f",
    512: "#8e24aa",
    1024: "#5e35b1",
    2048: "#b8860b",
}
DEFAULT_TILE_BG = "#37474f"

# Type alias for the board mapping (x, y) -> tile value
BoardType = Dict[Tuple[int, int], int]


def build_layout() -> str:
    """Return grid layout of labels (each independent cell)."""
    row = ",".join(['`""'] * COLS)
    return "\n".join([row for _ in range(ROWS)])


def update_ui(pad, board: BoardType) -> None:
    """Render board mapping into the ButtonPad cells."""
    for y in range(ROWS):
        for x in range(COLS):
            val = board[(x, y)]
            el = pad[x, y]  # type: ignore[index]
            el.text = str(val) if val else ""
            el.text_color = TEXT_COLOR
            el.font_size = FONT_SIZE
            el.bg_color = TILE_BG.get(val, DEFAULT_TILE_BG)

def empty_positions(board: BoardType) -> List[Tuple[int, int]]:
    """Return list of coordinates currently holding 0 (empty)."""
    positions: List[Tuple[int, int]] = []
    for y in range(ROWS):
        for x in range(COLS):
            if board[(x, y)] == 0:
                positions.append((x, y))
    return positions

def add_random_tile(board: BoardType) -> bool:
    """Place a 2 (90%) or 4 (10%) in a random empty spot; return success."""
    empties = empty_positions(board)
    if not empties:
        return False
    x, y = random.choice(empties)
    board[(x, y)] = 4 if random.random() < 0.1 else 2
    return True

def move_line(line: List[int]) -> Tuple[List[int], bool, bool]:
    """Slide and merge a single row/column list.

    Returns (new_line, moved_flag, made_2048_flag).
    Merging rule: Each pair can merge at most once per move from the side
    we're pushing toward, so we scan left-to-right after filtering zeros.
    """
    original = line[:]
    tiles = [v for v in line if v != 0]
    merged: List[int] = []
    i = 0
    made_2048 = False
    while i < len(tiles):
        if i + 1 < len(tiles) and tiles[i] == tiles[i + 1]:
            nv = tiles[i] * 2
            if nv == 2048:
                made_2048 = True
            merged.append(nv)
            i += 2
        else:
            merged.append(tiles[i])
            i += 1
    merged += [0] * (len(line) - len(merged))
    moved = merged != original
    return merged, moved, made_2048

def apply_move(direction: str, pad, board: BoardType) -> bool:
    """Apply movement in direction; return True if any tile changed/merged.

    Direction logic: we re-orient each affected row/col into a list so that
    move_line always processes as if moving "left"; we reverse lists for
    right/down and reverse back when writing results.
    """
    moved_any = False
    won_this_move = False
    if direction == "left":
        for y in range(ROWS):
            xs = list(range(COLS))
            line = [board[(x, y)] for x in xs]
            nl, moved, made_2048 = move_line(line)
            moved_any |= moved
            won_this_move |= made_2048
            for idx, x in enumerate(xs):
                board[(x, y)] = nl[idx]
    elif direction == "right":
        for y in range(ROWS):
            xs = list(reversed(range(COLS)))
            line = [board[(x, y)] for x in xs]
            nl, moved, made_2048 = move_line(line)
            moved_any |= moved
            won_this_move |= made_2048
            nl = list(reversed(nl))
            for idx, x in enumerate(range(COLS)):
                board[(x, y)] = nl[idx]
    elif direction == "up":
        for x in range(COLS):
            ys = list(range(ROWS))
            line = [board[(x, y)] for y in ys]
            nl, moved, made_2048 = move_line(line)
            moved_any |= moved
            won_this_move |= made_2048
            for idx, y in enumerate(ys):
                board[(x, y)] = nl[idx]
    elif direction == "down":
        for x in range(COLS):
            ys = list(reversed(range(ROWS)))
            line = [board[(x, y)] for y in ys]
            nl, moved, made_2048 = move_line(line)
            moved_any |= moved
            won_this_move |= made_2048
            nl = list(reversed(nl))
            for idx, y in enumerate(range(ROWS)):
                board[(x, y)] = nl[idx]
    else:
        return False
    if moved_any:
        if won_this_move or any(v == 2048 for v in board.values()):
            update_ui(pad, board)
            try:
                buttonpad.alert("You win!")
            except Exception:
                pass
            new_game(pad, board)
            return True
        add_random_tile(board)
        update_ui(pad, board)
        any_moves_possible = False
        if empty_positions(board):
            any_moves_possible = True
        for y in range(ROWS):
            for x in range(COLS):
                v = board[(x, y)]
                if x + 1 < COLS and board[(x + 1, y)] == v:
                    any_moves_possible = True
                    break
                if y + 1 < ROWS and board[(x, y + 1)] == v:
                    any_moves_possible = True
                    break
        if not any_moves_possible:
            try:
                buttonpad.alert("Game Over")
            except Exception:
                pass
            new_game(pad, board)
    return moved_any


def new_game(pad, board: BoardType) -> None:
    """Reset board to all zeros then add two starting tiles."""
    for y in range(ROWS):
        for x in range(COLS):
            board[(x, y)] = 0
    add_random_tile(board)
    add_random_tile(board)
    update_ui(pad, board)


def main() -> None:
    """Create the window, bind keys, start a new game, and run loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=90,
        cell_height=90,
        padx=6,
        pady=6,
        border=10,
        title="2048",
        default_bg_color=EMPTY_BG,
        default_text_color=TEXT_COLOR,
        window_bg_color=WINDOW_BG,
        resizable=True,
    )
    board: BoardType = {(x, y): 0 for y in range(ROWS) for x in range(COLS)}
    try:
        bind = pad.root.bind_all
        bind("<Left>", lambda e: apply_move("left", pad, board))
        bind("<Right>", lambda e: apply_move("right", pad, board))
        bind("<Up>", lambda e: apply_move("up", pad, board))
        bind("<Down>", lambda e: apply_move("down", pad, board))
        for ch, dirn in ("a","left"),("A","left"),("d","right"),("D","right"),("w","up"),("W","up"),("s","down"),("S","down"):
            bind(f"<KeyPress-{ch}>", lambda e, d=dirn: apply_move(d, pad, board))
    except Exception:
        pass
    new_game(pad, board)
    for y in range(ROWS):
        for x in range(COLS):
            el = pad[x, y]  # type: ignore[index]
            el.text_color = TEXT_COLOR
            el.font_size = FONT_SIZE
    pad.run()


if __name__ == "__main__":
    main()
