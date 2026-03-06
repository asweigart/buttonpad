"""15-Puzzle (sliding tiles) implemented with ButtonPad.

Gameplay basics:
    * 4x4 board contains tiles 1..15 plus one blank (0 represents blank).
    * Click a tile adjacent (orthogonally) to the blank to slide it into the blank.
    * Keyboard: Arrow keys or WASD also slide tiles (by moving the tile toward the blank).
    * Shuffle produces a random solvable configuration using a series of blank moves.
    * Solve button animates the reverse of user moves then the generation moves, restoring the solved board.

Implementation notes:
    * Board stored as list of lists of ints; 0 denotes blank.
    * Two histories: gen_moves (blank displacements during shuffle) and user_moves
        (blank displacements caused by player). Solve replays them backwards.
    * We count player moves only (shuffling doesn't increment the move counter).
"""

from __future__ import annotations

from typing import List, Tuple
import random

try:
    import buttonpad  # local module name
except Exception:
    import ButtonPad as buttonpad  # type: ignore

COLS = 4
ROWS = 4  # puzzle rows (control row added separately)
WINDOW_BG = "#f5f5f5"
TILE_BG = "#e0e0e0"
EMPTY_BG = "#ffffff"
TEXT_COLOR = "#222222"
FONT_SIZE = 20

Coord = Tuple[int, int]


def build_layout() -> str:
    """Return layout with control row (New/Solve) plus 4x4 puzzle area."""
    control = ",".join(["New", "New", "Solve", "Solve"])
    row = ",".join(["`"] * COLS)
    grid = "\n".join([row for _ in range(ROWS)])
    return "\n".join([control, grid])


def flatten(board: List[List[int]]) -> List[int]:
    """Return board values in row-major order (used for checks)."""
    return [board[y][x] for y in range(ROWS) for x in range(COLS)]


def count_inversions(arr: List[int]) -> int:
    """Return number of out-of-order tile pairs (ignoring the blank)."""
    a = [v for v in arr if v != 0]
    inv = 0
    for i in range(len(a)):
        for j in range(i + 1, len(a)):
            if a[i] > a[j]:
                inv += 1
    return inv


def blank_row_from_bottom(board: List[List[int]]) -> int:
    """Return 1-based blank row index counting upward from bottom."""
    for y in range(ROWS - 1, -1, -1):
        for x in range(COLS):
            if board[y][x] == 0:
                return ROWS - y
    return 1


def is_solved(board: List[List[int]]) -> bool:
    """Return True if tiles are in ascending order with blank at end."""
    return flatten(board) == list(range(1, COLS * ROWS)) + [0]


def is_solvable(board: List[List[int]]) -> bool:
    """Return True if board configuration is solvable.

    For even width (4): solvable iff (blank row from bottom is odd AND inversions even)
    OR (blank row from bottom is even AND inversions odd).
    (For odd widths, which we don't use here, inversion count must be even.)
    """
    arr = flatten(board)
    inv = count_inversions(arr)
    blank_from_bottom = blank_row_from_bottom(board)
    if COLS % 2 == 0:
        return (blank_from_bottom % 2 == 1 and inv % 2 == 0) or (
            blank_from_bottom % 2 == 0 and inv % 2 == 1
        )
    return inv % 2 == 0


def random_solvable_board() -> List[List[int]]:
    """Generate a random solvable puzzle board not already solved."""
    while True:
        nums = list(range(1, COLS * ROWS)) + [0]
        random.shuffle(nums)
        board = [[nums[y * COLS + x] for x in range(COLS)] for y in range(ROWS)]
        if is_solvable(board) and not is_solved(board):
            return board


def main() -> None:
    """Create window, initialize puzzle state, wire controls, run game loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=72,
        cell_height=72,
        padx=6,
        pady=6,
        border=12,
        title="15-Puzzle",
        default_bg_color=TILE_BG,
        default_text_color=TEXT_COLOR,
        window_bg_color=WINDOW_BG,
        resizable=True,
        status_bar="Moves: 0",
    )

    board: List[List[int]] = [[0 for _ in range(COLS)] for _ in range(ROWS)]
    solving = {"active": False}
    move_state = {"count": 0}

    def update_status() -> None:
        """Refresh move count in status bar."""
        try:
            pad.status_bar = f"Moves: {move_state['count']}"
        except Exception:
            pass

    gen_moves: List[Tuple[int, int]] = []  # blank displacements building shuffle
    user_moves: List[Tuple[int, int]] = []  # blank displacements from player actions

    def update_ui() -> None:
        """Redraw tiles (offset by +1 row due to control row)."""
        for y in range(ROWS):
            for x in range(COLS):
                el = pad[x, y + 1]  # type: ignore[index]
                v = board[y][x]
                if v == 0:
                    el.text = ""
                    el.bg_color = EMPTY_BG
                else:
                    el.text = str(v)
                    el.bg_color = TILE_BG
                el.font_size = FONT_SIZE

    def neighbors(x: int, y: int) -> List[Coord]:
        """Return list of valid neighbor coordinates (4-directional)."""
        out: List[Coord] = []
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < COLS and 0 <= ny < ROWS:
                out.append((nx, ny))
        return out

    def find_blank() -> Coord:
        """Locate coordinates of blank (0)."""
        for yy in range(ROWS):
            for xx in range(COLS):
                if board[yy][xx] == 0:
                    return (xx, yy)
        return (0, 0)

    def move_blank(dx: int, dy: int) -> bool:
        """Swap blank with neighbor in direction (dx,dy); return success."""
        bx, by = find_blank()
        nx, ny = bx + dx, by + dy
        if 0 <= nx < COLS and 0 <= ny < ROWS:
            board[by][bx], board[ny][nx] = board[ny][nx], board[by][bx]
            update_ui()
            return True
        return False

    def key_slide(tile_dx: int, tile_dy: int) -> None:
        """Slide tile toward blank using keyboard (tile movement vector)."""
        if solving["active"]:
            return
        bx, by = find_blank()
        tx, ty = bx - tile_dx, by - tile_dy
        if 0 <= tx < COLS and 0 <= ty < ROWS:
            board[by][bx], board[ty][tx] = board[ty][tx], board[by][bx]
            user_moves.append((-tile_dx, -tile_dy))
            move_state["count"] += 1
            update_status()
            update_ui()

    keymap_tiles = {
        "Up": (0, -1),
        "w": (0, -1),
        "Down": (0, 1),
        "s": (0, 1),
        "Left": (-1, 0),
        "a": (-1, 0),
        "Right": (1, 0),
        "d": (1, 0),
    }
    for ks, (tdx, tdy) in keymap_tiles.items():
        try:
            pad.root.bind_all(
                f"<KeyPress-{ks}>", lambda e, tdx=tdx, tdy=tdy: key_slide(tdx, tdy)
            )
        except Exception:
            pass

    def try_move(x: int, y: int) -> None:
        """Slide clicked tile into blank if adjacent."""
        if solving["active"]:
            return
        bx, by = find_blank()
        for nx, ny in neighbors(x, y):
            if board[ny][nx] == 0:
                dx, dy = x - nx, y - ny
                board[ny][nx], board[y][x] = board[y][x], board[ny][nx]
                user_moves.append((dx, dy))
                move_state["count"] += 1
                update_status()
                update_ui()
                return

    def on_click(_el, x: int, y: int) -> None:
        """Handle mouse click (y offset by control row)."""
        if y == 0:
            return
        try_move(x, y - 1)

    def animate_undo(moves: List[Tuple[int, int]], idx: int, done_cb) -> None:
        """Recursively undo moves list (blank displacements) in reverse order."""
        if idx < 0:
            done_cb()
            return
        dx, dy = moves[idx]
        move_blank(-dx, -dy)
        pad.root.after(100, lambda: animate_undo(moves, idx - 1, done_cb))

    def do_solve() -> None:
        """Animate solution by undoing user moves then generation moves."""
        if solving["active"]:
            return
        solving["active"] = True

        def after_user():
            animate_undo(gen_moves, len(gen_moves) - 1, finish)

        def finish():
            solving["active"] = False
            user_moves.clear()
            gen_moves.clear()

        animate_undo(user_moves, len(user_moves) - 1, after_user)

    def new_game() -> None:
        """Shuffle board via random blank moves (recording path)."""
        if solving["active"]:
            return
        nums = list(range(1, COLS * ROWS)) + [0]
        for y in range(ROWS):
            for x in range(COLS):
                board[y][x] = nums[y * COLS + x]
        gen_moves.clear()
        user_moves.clear()
        move_state["count"] = 0
        update_status()
        update_ui()
        last = (0, 0)
        steps = 80
        for _ in range(steps):
            bx, by = find_blank()
            cand: List[Tuple[int, int]] = []
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = bx + dx, by + dy
                if (
                    0 <= nx < COLS
                    and 0 <= ny < ROWS
                    and (dx, dy) != (-last[0], -last[1])
                ):
                    cand.append((dx, dy))
            if not cand:
                cand = [(1, 0), (-1, 0), (0, 1), (0, -1)]
            dx, dy = random.choice(cand)
            move_blank(dx, dy)
            gen_moves.append((dx, dy))
            last = (dx, dy)
        if is_solved(board):  # extremely rare; reshuffle smaller loop
            last = (0, 0)
            gen_moves.clear()
            for _ in range(50):
                bx, by = find_blank()
                cand: List[Tuple[int, int]] = []
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = bx + dx, by + dy
                    if (
                        0 <= nx < COLS
                        and 0 <= ny < ROWS
                        and (dx, dy) != (-last[0], -last[1])
                    ):
                        cand.append((dx, dy))
                if not cand:
                    cand = [(1, 0), (-1, 0), (0, 1), (0, -1)]
                dx, dy = random.choice(cand)
                move_blank(dx, dy)
                gen_moves.append((dx, dy))
                last = (dx, dy)
        update_status()

    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y + 1].on_click = on_click  # type: ignore[index]
    pad[0, 0].on_click = lambda _e, _x, _y: new_game()
    pad[0, 0].text = "New"
    pad[2, 0].on_click = lambda _e, _x, _y: do_solve()
    pad[2, 0].text = "Solve"

    update_ui()
    new_game()
    pad.run()


if __name__ == "__main__":
    main()
