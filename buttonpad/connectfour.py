"""Connect Four implemented with ButtonPad.

Beginner-friendly notes:
    * The visual grid has 7 columns. Row 0 holds the clickable "Drop" buttons.
    * Rows 1..6 display the placed discs (total playable rows = 6).
    * We store the logical board in a dictionary mapping (col, row) -> int:
                0 = empty, 1 = red player, 2 = black player.
    * A move finds the lowest empty row in the chosen column and places a disc.
    * After each move we check for a win (4 in a row horizontally, vertically,
        or on either diagonal) or a tie (board full with no winner).

Read top-to-bottom: constants, state, helpers, gameplay functions, then main().
"""

from __future__ import annotations

from typing import List, Optional, Dict, Tuple

from buttonpad import ButtonPad, BPButton, BPLabel, alert


COLS = 7  # columns (top row has 7 buttons)
ROWS = 6  # play rows beneath buttons; total grid rows = 1 + ROWS = 7

# Colors
EMPTY_COLOR = "white"
RED = "red"
BLACK = "black"
BTN_BG = "#e0e0e0"
BTN_FG = "black"


pad: ButtonPad  # initialized in main()
BoardType = Dict[Tuple[int, int], int]
board: BoardType
current: int
game_over: bool
buttons: List[BPButton]
cells: List[List[BPLabel]]


def color_for(player: int) -> str:
    """Return the display color string for the given player id (1 or 2)."""
    return RED if player == 1 else BLACK


def lowest_empty_row(col: int) -> Optional[int]:
    """Return the lowest (largest index) empty row in a column, or None if full."""
    for r in range(ROWS - 1, -1, -1):
        if board[(col, r)] == 0:
            return r
    return None


def count_line(c: int, r: int, dc: int, dr: int, player: int) -> int:
    """Count consecutive discs for player starting at (c,r) in direction (dc,dr).

    We expand forward and backward from the start cell to accumulate the length
    of a contiguous line of the player's discs. Returns the line length at that
    origin/direction pair (minimum 1, the starting disc itself).
    """
    count = 1
    cc, rr = c + dc, r + dr
    while 0 <= cc < COLS and 0 <= rr < ROWS and board[(cc, rr)] == player:
        count += 1
        cc += dc
        rr += dr
    cc, rr = c - dc, r - dr
    while 0 <= cc < COLS and 0 <= rr < ROWS and board[(cc, rr)] == player:
        count += 1
        cc -= dc
        rr -= dr
    return count


def check_win(c: int, r: int, player: int) -> bool:
    """Return True if the last move at (c,r) by player completes a 4-in-a-row."""
    return (
        count_line(c, r, 1, 0, player) >= 4 or  # horizontal
        count_line(c, r, 0, 1, player) >= 4 or  # vertical
        count_line(c, r, 1, 1, player) >= 4 or  # diag down-right
        count_line(c, r, 1, -1, player) >= 4    # diag up-right
    )


def new_game() -> None:
    """Reset board to empty state and restore button colors / current player."""
    global current, game_over
    for c in range(COLS):
        for r in range(ROWS):
            board[(c, r)] = 0
            cell = cells[c][r]
            cell.bg_color = EMPTY_COLOR
    for btn in buttons:
        btn.bg_color = BTN_BG
        btn.text_color = BTN_FG
    current = 1
    game_over = False


def drop(col: int) -> None:
    """Attempt to drop a disc in column 'col'; handle win / tie / turn switch."""
    global current, game_over
    if game_over:
        return
    row = lowest_empty_row(col)
    if row is None:
        return
    player = current
    board[(col, row)] = player
    cells[col][row].bg_color = color_for(player)
    if check_win(col, row, player):
        game_over = True
        try:
            alert(f"{'Red' if player == 1 else 'Black'} player wins!", title="Connect Four")
        except Exception:
            pass
        new_game()
        return
    # Tie detection: if no empty (0) cells remain
    if all(board[(c, r)] != 0 for c in range(COLS) for r in range(ROWS)):
        game_over = True
        try:
            alert("It's a tie!", title="Connect Four")
        except Exception:
            pass
        new_game()
        return
    current = 2 if current == 1 else 1


def make_drop_handler(col: int):
    """Return a click handler closure bound to a specific column."""
    def handler(el, x, y):  # ButtonPad callback signature: (element, x, y)
        drop(col)
    return handler


def main() -> None:
    """Construct the UI, initialize state, wire events, then start event loop."""
    global pad, board, current, game_over, buttons, cells
    top_buttons = ",".join(str(i + 1) for i in range(COLS))
    label_row = ",".join("`''" for _ in range(COLS))
    layout = "\n".join([top_buttons] + [label_row for _ in range(ROWS)])
    pad = ButtonPad(
        layout,
        cell_width=60,
        cell_height=60,
        padx=4,
        pady=4,
        default_bg_color=BTN_BG,
        default_text_color=BTN_FG,
        title="Connect Four",
        border=10,
    )
    board = {(c, r): 0 for c in range(COLS) for r in range(ROWS)}
    current = 1
    game_over = False
    buttons = [pad[c, 0] for c in range(COLS)]  # type: ignore[assignment]
    cells = [[pad[c, r + 1] for r in range(ROWS)] for c in range(COLS)]  # type: ignore[list-item]
    for c in range(COLS):
        btn = buttons[c]
        btn.on_click = make_drop_handler(c)
        btn.text = "Drop\nHere"
    new_game()
    pad.run()


if __name__ == "__main__":
    main()
