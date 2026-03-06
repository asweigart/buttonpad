"""Gomoku game (Five in a Row) implemented with ButtonPad.

Rules (simplified):
    * Two players (White then Black) alternate placing stones on a 15x15 board.
    * First player to get 5 stones in a row (horizontal, vertical, or diagonal) wins.
    * After a win, the winner is announced and the board resets for a new game.

Implementation notes for beginners:
    * The board is stored as a 2D list of ints: 0 empty, 1 white, 2 black.
    * The GUI grid mirrors this structure; each board cell has a corresponding
        ButtonPad element whose background color we update after each move.
    * To detect a win we count how many same-color stones extend in both
        directions along each of the 4 line orientations passing through the last move.
"""

from __future__ import annotations

import buttonpad
from typing import List

SIZE = 15
WHITE_BG = "#ffffff"
BLACK_BG = "#222222"
EMPTY_BG = "#cd780a"  # matches default background for clearing


def build_layout() -> str:
    """Return the layout string for a SIZE x SIZE board of unmerged cells.

    Each token is a backtick (`) meaning an empty label/button cell that can
    take clicks and have its background color changed.
    """
    row = ",".join(["`"] * SIZE)
    return "\n".join([row for _ in range(SIZE)])


def in_bounds(x: int, y: int) -> bool:
    """Return True if (x,y) is a valid coordinate on the board."""
    return 0 <= x < SIZE and 0 <= y < SIZE


def count_in_direction(
    board: List[List[int]], x: int, y: int, dx: int, dy: int, who: int
) -> int:
    """Count consecutive stones for player 'who' from (x,y) stepping (dx,dy).

    We advance one step first (so we don't recount the origin cell) then keep
    moving while we stay on the board and keep seeing the same player's stone.
    """
    cnt = 0
    cx, cy = x + dx, y + dy
    while in_bounds(cx, cy) and board[cy][cx] == who:
        cnt += 1
        cx += dx
        cy += dy
    return cnt


def has_five(board: List[List[int]], x: int, y: int, who: int) -> bool:
    """Return True if placing at (x,y) gives player 'who' a line of 5+ stones."""
    # We only need to check lines that pass through the last move.
    for dx, dy in ((1, 0), (0, 1), (1, 1), (1, -1)):
        total = 1  # count the stone just placed
        total += count_in_direction(board, x, y, dx, dy, who)
        total += count_in_direction(board, x, y, -dx, -dy, who)
        if total >= 5:
            return True
    return False


def main() -> None:
    """Create the window, manage game state, and run the event loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=40,
        cell_height=40,
        padx=0,
        pady=0,
        border=2,
        title="Gomoku",
        default_bg_color="#cd780a",
        window_bg_color="#804d00",
        resizable=True,
    )

    # Board state: 0 empty, 1 white, 2 black
    board: List[List[int]] = [[0 for _ in range(SIZE)] for _ in range(SIZE)]

    turn = {"who": 1}  # Mutable dict used so inner functions can modify current player
    game = {"over": False}  # Track if game ended to ignore extra clicks

    def set_cell_color(x: int, y: int, who: int) -> None:
        """Update the GUI color of the cell at (x,y) for player 'who'."""
        el = pad[x, y]  # type: ignore[index]
        if who == 1:
            el.bg_color = WHITE_BG
        else:
            el.bg_color = BLACK_BG

    def clear_board() -> None:
        """Reset board state and visuals for a new game."""
        for y in range(SIZE):
            for x in range(SIZE):
                board[y][x] = 0
                pad[x, y].bg_color = EMPTY_BG  # type: ignore[index]
        turn["who"] = 1
        game["over"] = False

    def announce_winner(who: int) -> None:
        """Show a dialog announcing the winner then reset the board."""
        game["over"] = True
        winner = "White" if who == 1 else "Black"
        buttonpad.alert(f"{winner} wins!", title="Gomoku")
        clear_board()

    def handle_click(el, x: int, y: int) -> None:
        """Handle a board cell click: place a stone, check win, switch turns."""
        if game["over"]:
            return  # Ignore clicks after game end (until reset)
        if board[y][x] != 0:
            return  # Occupied cell
        who = turn["who"]
        board[y][x] = who
        set_cell_color(x, y, who)

        if has_five(board, x, y, who):
            announce_winner(who)
            return

        turn["who"] = 2 if who == 1 else 1  # Alternate player

    # Wire click handler for every cell so we know which (x,y) was clicked.
    for y in range(SIZE):
        for x in range(SIZE):
            pad[x, y].on_click = handle_click  # type: ignore[index]

    pad.run()


if __name__ == "__main__":
    main()
