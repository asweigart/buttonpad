"""Othello (Reversi) implemented with ButtonPad.

Overview:
    * Standard 8x8 board; players alternate placing discs.
    * A legal move must bracket at least one opponent disc in a straight line
        (horizontal, vertical, or diagonal) between the new disc and another disc
        of the moving player; all bracketed discs flip to the moving player's color.
    * If a player has no legal moves, their turn is skipped; if neither side
        can move the game ends and the winner is the player with more discs.
    * After a game ends, we show an alert and reset to the starting position.

Beginner notes:
    * Board is stored as a dict keyed by (x, y) -> int: 0 empty, 1 white, 2 black.
    * We keep 'turn' in a dict so inner handler closure can mutate it.
    * find_flips() returns the list of opponent coordinates that would be
        flipped if a move is placed at (x,y); empty list means move is illegal.
    * The status bar is updated with counts after each successful move.
"""

from __future__ import annotations

import buttonpad
from typing import List, Tuple, Dict

SIZE = 8

# UI
WINDOW_BG = "#6b4e2e"      # brown window
BOARD_BG = "#2f6d2f"       # slightly dark green for cells
WHITE_BG = "#ffffff"
BLACK_BG = "#111111"


def build_layout() -> str:
    """Return layout string for an SIZE x SIZE grid of independent cells."""
    row = ",".join(["`"] * SIZE)
    return "\n".join([row for _ in range(SIZE)])


BoardType = Dict[Tuple[int, int], int]

DIRS: Tuple[Tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
)


def in_bounds(x: int, y: int) -> bool:
    """Return True if coordinate (x,y) lies on the board."""
    return 0 <= x < SIZE and 0 <= y < SIZE


def opponent(p: int) -> int:
    """Return the opposite player number (1<->2)."""
    return 2 if p == 1 else 1


def set_cell_color(pad, board: BoardType, x: int, y: int, who: int) -> None:
    """Apply appropriate background color for board cell (x,y)."""
    widget = pad[x, y]  # type: ignore[index]
    if who == 0:
        widget.bg_color = BOARD_BG
    elif who == 1:
        widget.bg_color = WHITE_BG
    else:
        widget.bg_color = BLACK_BG


def update_status(pad, board: BoardType) -> None:
    """Recompute counts and update the status bar text."""
    wcnt = sum(1 for v in board.values() if v == 1)
    bcnt = sum(1 for v in board.values() if v == 2)
    try:
        pad.status_bar = f"White: {wcnt}  Black: {bcnt}"
    except Exception:
        pass


def update_ui(pad, board: BoardType) -> None:
    """Refresh the entire board colors then update the status bar."""
    for y in range(SIZE):
        for x in range(SIZE):
            set_cell_color(pad, board, x, y, board[(x, y)])
    update_status(pad, board)


def find_flips(board: BoardType, p: int, x: int, y: int) -> List[Tuple[int, int]]:
    """Return list of opponent discs that would flip if player p moves at (x,y).

    Algorithm:
      1. A move is illegal if target square is not empty.
      2. For each direction, step outward collecting contiguous opponent discs.
      3. If that run is followed by one of our own discs, those opponent discs
         flip; otherwise discard that direction.
    """
    if board[(x, y)] != 0:
        return []
    flips: List[Tuple[int, int]] = []
    opp = opponent(p)
    for dx, dy in DIRS:
        cx, cy = x + dx, y + dy
        line: List[Tuple[int, int]] = []
        if not in_bounds(cx, cy) or board[(cx, cy)] != opp:
            continue
        while in_bounds(cx, cy) and board[(cx, cy)] == opp:
            line.append((cx, cy))
            cx += dx
            cy += dy
        if not in_bounds(cx, cy):
            continue
        if board[(cx, cy)] == p and line:
            flips.extend(line)
    return flips


def has_any_move(board: BoardType, p: int) -> bool:
    """Return True if player p has at least one legal move."""
    for yy in range(SIZE):
        for xx in range(SIZE):
            if board[(xx, yy)] == 0 and find_flips(board, p, xx, yy):
                return True
    return False


def place_and_flip(pad, board: BoardType, p: int, x: int, y: int) -> bool:
    """Attempt to place player p's disc at (x,y); flip captured discs.

    Returns True if move was legal and performed, else False.
    """
    flips = find_flips(board, p, x, y)
    if not flips:
        return False
    board[(x, y)] = p
    for fx, fy in flips:
        board[(fx, fy)] = p
    update_ui(pad, board)
    return True


def announce_winner(pad, board: BoardType, turn) -> None:
    """Show final score dialog and reset board for a new game."""
    wcnt = sum(1 for v in board.values() if v == 1)
    bcnt = sum(1 for v in board.values() if v == 2)
    if wcnt == bcnt:
        msg = f"Tie game!\nWhite: {wcnt}  Black: {bcnt}"
    elif wcnt > bcnt:
        msg = f"White wins!\nWhite: {wcnt}  Black: {bcnt}"
    else:
        msg = f"Black wins!\nWhite: {wcnt}  Black: {bcnt}"
    try:
        buttonpad.alert(msg, title="Othello Result")
    except Exception:
        pass
    # Reset board to starting four discs
    for yy in range(SIZE):
        for xx in range(SIZE):
            board[(xx, yy)] = 0
    mid2 = SIZE // 2
    board[(mid2 - 1, mid2 - 1)] = 1
    board[(mid2, mid2)] = 1
    board[(mid2 - 1, mid2)] = 2
    board[(mid2, mid2 - 1)] = 2
    turn["who"] = 2  # Black moves next (standard alt after reset)
    update_ui(pad, board)


def handle_click(pad, board: BoardType, turn):
    """Return an on_click handler closure bound to this board & turn dict."""
    def _handler(_el, x: int, y: int) -> None:
        p = turn["who"]
        moved = place_and_flip(pad, board, p, x, y)
        if not moved:  # Illegal move: ignore silently (could add feedback)
            return
        np = opponent(p)
        if has_any_move(board, np):
            turn["who"] = np
        elif has_any_move(board, p):  # Opponent had none; current goes again
            turn["who"] = p
        else:  # Neither can move -> game over
            announce_winner(pad, board, turn)
    return _handler


def main() -> None:
    """Create window, set initial board position, wire events, run loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=46,
        cell_height=46,
        padx=2,
        pady=2,
        border=12,
        title="Othello",
        default_bg_color=BOARD_BG,
        default_text_color="white",
        window_bg_color=WINDOW_BG,
        resizable=True,
        status_bar="White: 2  Black: 2",
    )
    board: BoardType = {(x, y): 0 for y in range(SIZE) for x in range(SIZE)}
    turn = {"who": 2}
    # Starting four discs in the center (white NW-SE, black NE-SW)
    mid = SIZE // 2
    board[(mid - 1, mid - 1)] = 1
    board[(mid, mid)] = 1
    board[(mid - 1, mid)] = 2
    board[(mid, mid - 1)] = 2
    update_ui(pad, board)
    h = handle_click(pad, board, turn)
    for y in range(SIZE):
        for x in range(SIZE):
            pad[x, y].on_click = h  # type: ignore[index]
    pad.run()


if __name__ == "__main__":
    main()
