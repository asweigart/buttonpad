"""Tic Tac Toe: Human (X) vs Simple CPU (O).

CPU heuristic order:
    1. Take winning move if available.
    2. Block opponent's winning move.
    3. Take center, else a corner, else a side.

Design notes:
    * Board uses dictionary (x,y) -> symbol for simplicity.
    * After each move we test for victory or tie before switching turns.
    * CPU move runs after a small delay for better user feedback.
"""

from __future__ import annotations

import buttonpad
from typing import List, Optional, Tuple, Dict

SIZE = 3

# UI tuning
EMPTY_BG = "#f0f0f0"
TEXT_COLOR = "#222222"

XYCoordType = Tuple[int, int]


BoardType = Dict[Tuple[int, int], str]

def winner(board: BoardType) -> Optional[str]:
    """Return 'X' or 'O' if a winning line exists; else None."""
    lines: List[List[XYCoordType]] = []
    for i in range(SIZE):
        lines.append([(x, i) for x in range(SIZE)])
        lines.append([(i, y) for y in range(SIZE)])
    lines.append([(i, i) for i in range(SIZE)])
    lines.append([(i, SIZE - 1 - i) for i in range(SIZE)])
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


def empty_cells(board: BoardType) -> List[XYCoordType]:
    """Return list of coordinates that are empty."""
    return [(x, y) for y in range(SIZE) for x in range(SIZE) if board[(x, y)] == ""]


def choose_cpu_move(board: BoardType) -> Optional[XYCoordType]:
    """Return chosen coordinate for CPU using simple priority heuristic."""
    empties = empty_cells(board)
    if not empties:
        return None
    def try_place(sym: str) -> Optional[XYCoordType]:
        for x, y in empties:
            board[(x, y)] = sym
            if winner(board) == sym:
                board[(x, y)] = ""
                return (x, y)
            board[(x, y)] = ""
        return None
    mv = try_place("O")
    if mv: 
        return mv
    mv = try_place("X")
    if mv: 
        return mv
    if board[(1, 1)] == "": 
        return (1, 1)
    for x, y in [(0, 0), (2, 0), (0, 2), (2, 2)]:
        if board[(x, y)] == "": 
            return (x, y)
    for x, y in [(1, 0), (0, 1), (2, 1), (1, 2)]:
        if board[(x, y)] == "": 
            return (x, y)
    return empties[0]


pad = None  # type: ignore
board: BoardType = {}
state = {"who": "X", "over": False}

def update_ui() -> None:
    """Refresh cell text from board mapping."""
    if pad is None:
        return
    for y in range(SIZE):
        for x in range(SIZE):
            el = pad[x, y]  # type: ignore[index]
            el.text = board.get((x, y), "")
            el.font_size = 28

def reset_board() -> None:
    """Empty all cells and set turn to human (X)."""
    for y in range(SIZE):
        for x in range(SIZE):
            board[(x, y)] = ""
    state["who"] = "X"
    state["over"] = False
    update_ui()

def end_game(sym: Optional[str]) -> None:
    """Show result dialog then reset board for a new game."""
    state["over"] = True
    try:
        if sym is None: 
            buttonpad.alert("It's a tie!")
        else: 
            buttonpad.alert(f"{sym} wins!")
    except Exception: 
        pass
    reset_board()

def after_move_checks() -> bool:
    """Return True if game ended (win or tie) after a move."""
    w = winner(board)
    if w is not None:
        end_game(w)
        return True
    if board_full(board):
        end_game(None)
        return True
    return False

def cpu_move() -> None:
    """Select and play CPU's move, then switch turn to human if game not over."""
    if state["over"] or state["who"] != "O": 
        return
    mv = choose_cpu_move(board)
    if mv is None:
        if not after_move_checks(): 
            end_game(None)
        return
    x, y = mv
    if board[(x, y)] != "":
        empties = empty_cells(board)
        if not empties:
            if not after_move_checks(): 
                end_game(None)
            return
        x, y = empties[0]
    board[(x, y)] = "O"
    if pad is not None:
        pad[x, y].text = "O"
        pad[x, y].font_size = 28  # type: ignore[index]
    if after_move_checks(): 
        return
    state["who"] = "X"

def handle_click(el, x: int, y: int) -> None:
    """Handle human move then queue CPU's move."""
    if state["over"] or state["who"] != "X" or board[(x, y)] != "": 
        return
    board[(x, y)] = "X"
    el.text = "X"
    el.font_size = 28
    if after_move_checks(): 
        return
    state["who"] = "O"
    if pad is not None:
        pad.root.after(120, cpu_move)

def main() -> None:
    """Initialize window, board, and event handlers then start loop."""
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
        title="Tic Tac Toe (vs CPU)",
        default_bg_color=EMPTY_BG,
        default_text_color=TEXT_COLOR,
        window_bg_color="#ffffff",
        resizable=False,
    )
    board = {(x, y): "" for y in range(SIZE) for x in range(SIZE)}
    state = {"who": "X", "over": False}
    for y in range(SIZE):
        for x in range(SIZE):
            pad[x, y].on_click = handle_click  # type: ignore[index]
            pad[x, y].font_size = 28  # type: ignore[index]
    update_ui()
    pad.run()


if __name__ == "__main__":
    main()
