"""Othello (Reversi) versus a simple CPU opponent using ButtonPad.

Features / rules:
    * 8x8 board; BLACK (CPU) moves first, WHITE is the human player.
    * Legal human moves are displayed as small yellow hint dots (".").
    * Clicking a hinted square places a WHITE disc and flips bracketed BLACK discs.
    * CPU responds automatically using a very small greedy heuristic.
    * If a player has no legal moves, the turn skips. Game ends when neither side
        can move; winner is the player with more discs.

Beginner notes:
    * Board is a dict mapping (x,y) -> int (0 empty, 1 white, 2 black).
    * The state dict holds current turn and game-over flag.
    * find_flips() implements core Othello legality: collects bracketed discs.
    * The CPU's move selection is deliberately simple and NOT a strong strategy.
"""

from __future__ import annotations

import buttonpad
from typing import List, Tuple, Optional, Dict

SIZE = 8

# UI
WINDOW_BG = "#6b4e2e"      # brown window
BOARD_BG = "#2f6d2f"       # slightly dark green for cells
WHITE_BG = "#ffffff"
BLACK_BG = "#111111"
TEXT_DEFAULT = "white"
HINT_COLOR = "#ffd54a"     # warm yellow for move hints
HINT_CHAR = "."
SYMBOL_FONT_SIZE = 18

# Players
EMPTY = 0
WHITE = 1  # human
BLACK = 2  # cpu

# Directions
DIRS: Tuple[Tuple[int, int], ...] = (
    (-1, -1), (0, -1), (1, -1),
    (-1,  0),          (1,  0),
    (-1,  1), (0,  1), (1,  1),
)


def build_layout() -> str:
    """Return the layout string for an 8x8 grid of independent cells."""
    row = ",".join(["`"] * SIZE)
    return "\n".join([row for _ in range(SIZE)])


def in_bounds(x: int, y: int) -> bool:
    """Return True if (x,y) is on the board."""
    return 0 <= x < SIZE and 0 <= y < SIZE


def opponent(p: int) -> int:
    """Return the opposing player constant."""
    return BLACK if p == WHITE else WHITE


BoardType = Dict[Tuple[int, int], int]


def find_flips(board: BoardType, p: int, x: int, y: int) -> List[Tuple[int, int]]:
    """Return list of opponent discs flipped if player p plays at (x,y).

    Algorithm: For each of 8 directions, step outward collecting opponent
    discs until hitting (a) own disc (legal -> add collected), (b) empty/out
    of bounds (illegal -> discard collected). Target must be EMPTY.
    """
    if board[(x, y)] != EMPTY:
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


def legal_moves(board: BoardType, p: int) -> List[Tuple[int, int]]:
    """Return list of all coordinates where player p can legally move."""
    out: List[Tuple[int, int]] = []
    for y in range(SIZE):
        for x in range(SIZE):
            if board[(x, y)] == EMPTY and find_flips(board, p, x, y):
                out.append((x, y))
    return out


def any_move(board: BoardType, p: int) -> bool:
    """Return True if player p has at least one legal move."""
    for y in range(SIZE):
        for x in range(SIZE):
            if board[(x, y)] == EMPTY and find_flips(board, p, x, y):
                return True
    return False


def choose_cpu_move(board: BoardType) -> Optional[Tuple[int, int]]:
    """Return a greedy BLACK move maximizing flips with simple tie-breakers.

    Tie-breaking priority (after number of flips): corner > closer to center > edge.
    This is a naive heuristic just for demonstration, not a real AI.
    """
    moves = legal_moves(board, BLACK)
    if not moves:
        return None

    def move_score(mv: Tuple[int, int]) -> Tuple[int, int, int, int]:
        x, y = mv
        flips = len(find_flips(board, BLACK, x, y))
        corner = 1 if (x, y) in ((0, 0), (0, SIZE - 1), (SIZE - 1, 0), (SIZE - 1, SIZE - 1)) else 0
        center_dist = abs(x - (SIZE // 2)) + abs(y - (SIZE // 2))
        center_pref = -center_dist
        edge = 1 if (x in (0, SIZE - 1) or y in (0, SIZE - 1)) else 0
        return (flips, corner, center_pref, edge)

    moves.sort(key=move_score, reverse=True)
    return moves[0]


def set_cell_color(pad, x: int, y: int, who: int) -> None:
    """Paint the background color for the disc value at (x,y)."""
    el = pad[x, y]  # type: ignore[index]
    if who == EMPTY:
        el.bg_color = BOARD_BG
    elif who == WHITE:
        el.bg_color = WHITE_BG
    else:
        el.bg_color = BLACK_BG


def update_status(pad, board: BoardType) -> None:
    """Update status bar with current disc counts."""
    wcnt = sum(1 for v in board.values() if v == WHITE)
    bcnt = sum(1 for v in board.values() if v == BLACK)
    try:
        pad.status_bar = f"White: {wcnt}  Black: {bcnt}"
    except Exception:
        pass


def update_ui(pad, board: BoardType, state, show_hints: bool = True) -> None:
    """Redraw all cells and optionally show legal move hints for WHITE."""
    for y in range(SIZE):
        for x in range(SIZE):
            set_cell_color(pad, x, y, board[(x, y)])
            el = pad[x, y]  # type: ignore[index]
            el.text = ""
            el.text_color = TEXT_DEFAULT
            el.font_size = SYMBOL_FONT_SIZE
    if show_hints and state["turn"] == WHITE and not state["over"]:
        for x, y in legal_moves(board, WHITE):
            el = pad[x, y]  # type: ignore[index]
            el.text = HINT_CHAR
            el.text_color = HINT_COLOR
            el.font_size = SYMBOL_FONT_SIZE
    update_status(pad, board)


def place_and_flip(pad, board: BoardType, state, p: int, x: int, y: int) -> bool:
    """Attempt to place disc for p at (x,y); flip bracketed discs; return success."""
    flips = find_flips(board, p, x, y)
    if not flips:
        return False
    board[(x, y)] = p
    for fx, fy in flips:
        board[(fx, fy)] = p
    update_ui(pad, board, state, show_hints=(p != BLACK))
    return True


def end_and_announce_winner(pad, board: BoardType, state) -> None:
    """Show final result dialog and automatically start a new game."""
    wcnt = sum(1 for v in board.values() if v == WHITE)
    bcnt = sum(1 for v in board.values() if v == BLACK)
    state["over"] = True
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
    reset_game(pad, board, state)


def advance_turn(pad, board: BoardType, state) -> None:
    """Advance the turn, handling skip logic and scheduling CPU if needed."""
    p = state["turn"]
    np = opponent(p)
    if any_move(board, np):
        state["turn"] = np
    elif any_move(board, p):  # Opponent had none; current plays again
        state["turn"] = p
    else:  # Neither side can move -> game ends
        end_and_announce_winner(pad, board, state)
        return
    update_ui(pad, board, state, show_hints=(state["turn"] == WHITE))
    if state["turn"] == BLACK and not state["over"]:
        try:
            pad.root.after(200, lambda: cpu_move(pad, board, state))
        except Exception:
            cpu_move(pad, board, state)


def handle_click(pad, board: BoardType, state, _el, x: int, y: int) -> None:
    """Process a human (WHITE) click on board coordinate (x,y)."""
    if state["over"] or state["turn"] != WHITE:
        return
    if board[(x, y)] != EMPTY:
        return
    if not place_and_flip(pad, board, state, WHITE, x, y):
        return
    advance_turn(pad, board, state)


def cpu_move(pad, board: BoardType, state) -> None:
    """Let the CPU (BLACK) choose and execute a move, then advance turn."""
    if state["over"] or state["turn"] != BLACK:
        return
    mv = choose_cpu_move(board)
    if mv is None:
        advance_turn(pad, board, state)
        return
    x, y = mv
    if not place_and_flip(pad, board, state, BLACK, x, y):
        # Fallback: if chosen move somehow illegal, pick first legal.
        moves = legal_moves(board, BLACK)
        if not moves:
            advance_turn(pad, board, state)
            return
        x, y = moves[0]
        place_and_flip(pad, board, state, BLACK, x, y)
    advance_turn(pad, board, state)


def reset_game(pad, board: BoardType, state) -> None:
    """Reset to starting position and let BLACK (CPU) make first move."""
    for y in range(SIZE):
        for x in range(SIZE):
            board[(x, y)] = EMPTY
    mid = SIZE // 2
    board[(mid - 1, mid - 1)] = WHITE
    board[(mid, mid)] = WHITE
    board[(mid - 1, mid)] = BLACK
    board[(mid, mid - 1)] = BLACK
    state["turn"] = BLACK
    state["over"] = False
    update_ui(pad, board, state, show_hints=False)
    try:
        pad.root.after(250, lambda: cpu_move(pad, board, state))
    except Exception:
        cpu_move(pad, board, state)


def main() -> None:
    """Create window, initialize game state, wire events, start game loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=46,
        cell_height=46,
        padx=2,
        pady=2,
        border=12,
        title="Othello (vs CPU)",
        default_bg_color=BOARD_BG,
        default_text_color=TEXT_DEFAULT,
        window_bg_color=WINDOW_BG,
        resizable=True,
        status_bar="White: 2  Black: 2",
    )
    board: BoardType = {(x, y): EMPTY for y in range(SIZE) for x in range(SIZE)}
    state = {"turn": BLACK, "over": False}
    for y in range(SIZE):
        for x in range(SIZE):
            pad[x, y].on_click = (lambda el, xx=x, yy=y: handle_click(pad, board, state, el, xx, yy))  # type: ignore[index]
            pad[x, y].font_size = SYMBOL_FONT_SIZE  # type: ignore[index]
    reset_game(pad, board, state)
    update_status(pad, board)
    pad.run()


if __name__ == "__main__":
    main()
