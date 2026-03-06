"""Human vs Human Tic Tac Toe.

Implementation overview for beginners:
  * Board stored in a dictionary mapping (x,y) -> symbol ("X" / "O" / "").
  * We check victory after each move by enumerating 8 possible winning lines.
  * A simple state dict tracks whose turn it is and cumulative win/tie counts.
"""
from __future__ import annotations

import buttonpad
from typing import List, Optional, Tuple, Dict

SIZE = 3
EMPTY_BG = "#f0f0f0"
TEXT_COLOR = "#222222"

BoardType = Dict[Tuple[int, int], str]

def winner(board: BoardType) -> Optional[str]:
    """Return 'X' or 'O' if a winning line exists; else None."""
    lines: List[List[Tuple[int, int]]] = []
    for i in range(SIZE):
        lines.append([(x, i) for x in range(SIZE)])  # rows
        lines.append([(i, y) for y in range(SIZE)])  # cols
    lines.append([(i, i) for i in range(SIZE)])      # main diag
    lines.append([(i, SIZE - 1 - i) for i in range(SIZE)])  # anti-diag
    for line in lines:
        vals = [board[(x, y)] for (x, y) in line]
        if vals[0] and all(v == vals[0] for v in vals):
            return vals[0]
    return None

def board_full(board: BoardType) -> bool:
    """Return True if there are no empty cells."""
    for y in range(SIZE):
        for x in range(SIZE):
            if board[(x, y)] == "":
                return False
    return True

pad = None  # type: ignore
board: BoardType = {}
state = {"who": "X", "over": False, "x_wins": 0, "o_wins": 0, "ties": 0}

def update_status_bar() -> None:
    """Refresh scoreboard in status bar."""
    if pad is None:
        return
    try:
        pad.status_bar = f"X Wins: {state['x_wins']}  O Wins: {state['o_wins']}  Ties: {state['ties']}"
    except Exception:
        pass

def update_ui() -> None:
    """Write board symbols into UI cells."""
    if pad is None:
        return
    for y in range(SIZE):
        for x in range(SIZE):
            el = pad[x, y]  # type: ignore[index]
            el.text = board.get((x, y), "")
            el.font_size = 28

def reset_board() -> None:
    """Clear the board and set turn to X."""
    for y in range(SIZE):
        for x in range(SIZE):
            board[(x, y)] = ""
    state["who"] = "X"
    state["over"] = False
    update_ui()

def end_game(sym: Optional[str]) -> None:
    """Announce winner (sym) or tie and then reset board & update scores."""
    state["over"] = True
    if sym is None:
        state["ties"] += 1
    elif sym == "X":
        state["x_wins"] += 1
    else:
        state["o_wins"] += 1
    try:
        if sym is None:
            buttonpad.alert("It's a tie!")
        else:
            buttonpad.alert(f"{sym} wins!")
    except Exception:
        pass
    update_status_bar()
    reset_board()

def handle_click(el, x: int, y: int) -> None:
    """Place current player's symbol and check for win/tie."""
    if state["over"] or board[(x, y)] != "":
        return
    who = state["who"]
    board[(x, y)] = who
    el.text = who
    el.font_size = 28
    w = winner(board)
    if w is not None:
        end_game(w)
        return
    if board_full(board):
        end_game(None)
        return
    state["who"] = "O" if who == "X" else "X"

def main() -> None:
    """Set up window, initialize state dictionary, wire event handlers."""
    global pad, board, state
    pad = buttonpad.ButtonPad(
        layout="""`,`,`
                  `,`,`
                  `,`,`""",
        cell_width=72,
        cell_height=72,
        padx=4,
        pady=4,
        border=12,
        title="Tic Tac Toe",
        default_bg_color=EMPTY_BG,
        default_text_color=TEXT_COLOR,
        window_bg_color="#ffffff",
        resizable=False,
        status_bar="X Wins: 0  O Wins: 0  Ties: 0",
    )
    board = {(x, y): "" for y in range(SIZE) for x in range(SIZE)}
    state = {"who": "X", "over": False, "x_wins": 0, "o_wins": 0, "ties": 0}
    for y in range(SIZE):
        for x in range(SIZE):
            pad[x, y].on_click = handle_click  # type: ignore[index]
            pad[x, y].font_size = 28  # type: ignore[index]
    update_ui()
    pad.run()


if __name__ == "__main__":
    main()
