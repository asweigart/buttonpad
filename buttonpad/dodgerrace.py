"""Dodgerace mini-game using ButtonPad.

Goal: Move the blue player square to the green goal square while avoiding
moving red hazards. Each time you reach the goal, your score increases by 1
and the goal teleports to the opposite side. Touching a hazard ends the game
and immediately restarts it (keeping your session high score).

Beginner guide:
    * The board is a 21x21 grid of simple label cells. We redraw only cells that change.
    * Player movement: Arrow keys OR WASD. Movement is clamped to the edges (no wrapping).
    * Hazards: Spawn randomly at edges and drift in a straight line. Each new hazard
        briefly "waits" (STARTING_PAUSE_TICKS) to telegraph before it starts moving.
    * Blocked zone: A solid black 7x7 square in the middle that stops the player
        but not hazards. Hazards pass through it visually.
    * State storage: Everything (player position, hazards, score, etc.) lives in
        a single dictionary called 'state' passed to functions. This keeps globals
        minimal and makes resetting simpler.
    * Timing: Tk's after() schedules the tick() function every TICK_MS ms.
"""

from __future__ import annotations
import random
from typing import Dict, List, Tuple, Set

try:
    import buttonpad
except Exception:
    import ButtonPad as buttonpad  # type: ignore

# Grid
COLS = 21
ROWS = 21
WINDOW_BG = "#f0f0f0"
PLAYER_BG = "#2b78ff"
HAZARD_BG = "#ff5a5a"
BLOCK_BG = "#000000"
GOAL_BG = "#2ecc71"

INSTRUCTIONS = "WASD/Arrow Keys to move. Get green. Avoid red."

TICK_MS = 140
SPAWN_PROB_PER_TICK = 0.35
STARTING_PAUSE_TICKS = 2  # pause duration before hazards start moving

# Coordinates
START_POS: Tuple[int, int] = (10, 3)
GOAL_A: Tuple[int, int] = (10, 3)
GOAL_B: Tuple[int, int] = (10, 17)
BLOCK_MIN = 7
BLOCK_MAX = 13  # inclusive


def build_label_grid(cols: int, rows: int) -> str:
    """Return a layout string of size cols x rows of plain label cells.

    The token `'' creates an empty label (backtick = label, '' = blank text).
    We avoid merged cells so that each grid location can have its own color.
    """
    row = ",".join(["`''"] * cols)
    return "\n".join([row for _ in range(rows)])


def is_block(x: int, y: int) -> bool:
    """Return True if (x,y) lies inside the central blocked zone."""
    return (BLOCK_MIN <= x <= BLOCK_MAX) and (BLOCK_MIN <= y <= BLOCK_MAX)


def draw_cell(pad, state: Dict[str, object], x: int, y: int) -> None:
    """Draw a single cell's background color based on game state priority.

    Priority order (top wins):
      1. Player
      2. Hazard
      3. Goal
      4. Blocked zone
      5. Empty background
    """
    el = pad[x, y]
    el.text = ""  # keep cells text-free; color conveys meaning
    px = state["player"]["x"]  # type: ignore[index]
    py = state["player"]["y"]  # type: ignore[index]
    hset: Set[Tuple[int, int]] = state["hazard_set"]  # type: ignore[assignment]
    goal: Tuple[int, int] = state["goal"]  # type: ignore[assignment]
    if x == px and y == py:
        bg = PLAYER_BG
    elif (x, y) in hset:
        bg = HAZARD_BG
    elif (x, y) == goal:
        bg = GOAL_BG
    elif is_block(x, y):
        bg = BLOCK_BG
    else:
        bg = WINDOW_BG
    try:
        el.bg_color = bg
    except Exception:
        pass  # Some environments might not allow color change; ignore.


def draw_all(pad, state: Dict[str, object]) -> None:
    """Redraw every cell (used at game start or full refresh)."""
    for y in range(ROWS):
        for x in range(COLS):
            draw_cell(pad, state, x, y)


def update_status(pad, state: Dict[str, object]) -> None:
    """Display current score & high score in the status bar."""
    try:
        pad.status_bar = (
            INSTRUCTIONS + f"Score: {state['score']}  High score: {state['high_score']}"
        )
    except Exception:
        pass


def schedule_next_tick(pad, state: Dict[str, object]) -> None:
    """Schedule the next game loop tick via Tk's after()."""
    try:
        state["after_id"] = pad.root.after(TICK_MS, lambda: tick(pad, state))
    except Exception:
        state["after_id"] = None


def start_game(pad, state: Dict[str, object]) -> None:
    """Reset and start a new game session.

    Clears existing hazards, resets score & player position, sets the goal
    to GOAL_B (the opposite corner from the starting player) and begins ticking.
    """
    after_id = state.get("after_id")
    if after_id:
        try:
            pad.root.after_cancel(after_id)  # type: ignore[arg-type]
        except Exception:
            pass
        state["after_id"] = None
    state["hazards"] = []
    state["hazard_set"] = set()
    state["score"] = 0
    state["goal"] = GOAL_B
    state["player"] = {"x": START_POS[0], "y": START_POS[1]}
    state["running"] = True
    update_status(pad, state)
    draw_all(pad, state)
    schedule_next_tick(pad, state)


def game_over(pad, state: Dict[str, object]) -> None:
    """Handle player collision with a hazard then restart a new game."""
    state["running"] = False
    after_id = state.get("after_id")
    if after_id:
        try:
            pad.root.after_cancel(after_id)  # type: ignore[arg-type]
        except Exception:
            pass
        state["after_id"] = None
    try:
        buttonpad.alert("Game Over")
    except Exception:
        pass
    start_game(pad, state)


def spawn_hazard(pad, state: Dict[str, object]) -> None:
    """Create a new hazard at a random edge with a direction into the grid.

    Hazards store x,y plus a direction vector (dx, dy) and a small 'wait'
    counter used to telegraph their spawn before they start moving.
    """
    side = random.choice(["left", "right", "top", "bottom"])
    if side == "left":
        x = 0
        y = random.randrange(ROWS)
        dx, dy = 1, 0
    elif side == "right":
        x = COLS - 1
        y = random.randrange(ROWS)
        dx, dy = -1, 0
    elif side == "top":
        x = random.randrange(COLS)
        y = 0
        dx, dy = 0, 1
    else:  # bottom
        x = random.randrange(COLS)
        y = ROWS - 1
        dx, dy = 0, -1
    hset: Set[Tuple[int, int]] = state["hazard_set"]  # type: ignore[assignment]
    if (x, y) in hset:  # Already something there; skip spawn.
        return
    hazards: List[Dict[str, int]] = state["hazards"]  # type: ignore[assignment]
    hazards.append({"x": x, "y": y, "dx": dx, "dy": dy, "wait": STARTING_PAUSE_TICKS})
    hset.add((x, y))
    draw_cell(pad, state, x, y)


def move_hazards(pad, state: Dict[str, object]) -> bool:
    """Advance all hazards one step; return True if player was hit.

    We build new hazard lists/sets to make collision & redraw logic simple.
    Hazards off the board are discarded. Hazards in 'wait' state just decrement
    their wait counter and stay put that tick.
    """
    hazards: List[Dict[str, int]] = state["hazards"]  # type: ignore[assignment]
    hset: Set[Tuple[int, int]] = state["hazard_set"]  # type: ignore[assignment]
    if not hazards:
        return False
    px = state["player"]["x"]  # type: ignore[index]
    py = state["player"]["y"]  # type: ignore[index]
    old_set = set(hset)
    new_list: List[Dict[str, int]] = []
    new_set: Set[Tuple[int, int]] = set()
    for h in hazards:
        if h.get("wait", 0) > 0:  # Telegraphing phase
            h["wait"] -= 1
            new_list.append(h)
            new_set.add((h["x"], h["y"]))
            continue
        nx = h["x"] + h["dx"]
        ny = h["y"] + h["dy"]
        if nx < 0 or nx >= COLS or ny < 0 or ny >= ROWS:  # Left the board
            continue
        if nx == px and ny == py:  # Collision with player
            return True
        new_list.append({"x": nx, "y": ny, "dx": h["dx"], "dy": h["dy"], "wait": 0})
        new_set.add((nx, ny))
    state["hazards"] = new_list
    state["hazard_set"] = new_set
    affected = old_set | new_set  # Union of old & new cells to repaint
    for ax, ay in affected:
        draw_cell(pad, state, ax, ay)
    return False


def tick(pad, state: Dict[str, object]) -> None:
    """Main game loop step: maybe spawn, move hazards, reschedule next tick."""
    if not state["running"]:
        return
    if random.random() < SPAWN_PROB_PER_TICK:
        spawn_hazard(pad, state)
    if move_hazards(pad, state):  # Player was hit.
        game_over(pad, state)
        return
    schedule_next_tick(pad, state)


def try_move(pad, state: Dict[str, object], dx: int, dy: int) -> None:
    """Attempt to move the player by (dx,dy); handle collisions & goals."""
    if not state["running"]:
        return
    px = state["player"]["x"]  # type: ignore[index]
    py = state["player"]["y"]  # type: ignore[index]
    # Clamp movement to board bounds.
    nx = max(0, min(COLS - 1, px + dx))
    ny = max(0, min(ROWS - 1, py + dy))
    if nx == px and ny == py:  # No movement
        return
    if is_block(nx, ny):  # Blocked tile stops player
        return
    if (nx, ny) in state["hazard_set"]:  # Hazard collision
        game_over(pad, state)
        return
    # Perform move visually
    state["player"] = {"x": nx, "y": ny}
    draw_cell(pad, state, px, py)
    draw_cell(pad, state, nx, ny)
    # Check for reaching goal; if so, update score, high score, toggle goal.
    cur_goal: Tuple[int, int] = state["goal"]  # type: ignore[assignment]
    if (nx, ny) == cur_goal:
        state["score"] = int(state["score"]) + 1
        if state["score"] > state["high_score"]:  # type: ignore[operator]
            state["high_score"] = state["score"]
        update_status(pad, state)
        new_goal = GOAL_A if cur_goal == GOAL_B else GOAL_B
        old_goal = cur_goal
        state["goal"] = new_goal
        draw_cell(pad, state, old_goal[0], old_goal[1])
        draw_cell(pad, state, new_goal[0], new_goal[1])


def on_left(pad, state: Dict[str, object], _evt=None):
    """Move player one cell left."""
    try_move(pad, state, -1, 0)


def on_right(pad, state: Dict[str, object], _evt=None):
    """Move player one cell right."""
    try_move(pad, state, 1, 0)


def on_up(pad, state: Dict[str, object], _evt=None):
    """Move player one cell up."""
    try_move(pad, state, 0, -1)


def on_down(pad, state: Dict[str, object], _evt=None):
    """Move player one cell down."""
    try_move(pad, state, 0, 1)


def main() -> None:
    """Set up the UI, initialize state, bind keys, and start the game loop."""
    layout = build_label_grid(COLS, ROWS)
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=34,
        cell_height=34,
        padx=2,
        pady=2,
        border=8,
        title="Dodgerace",
        window_bg_color=WINDOW_BG,
        resizable=True,
        status_bar="Score: 0  High score: 0",
    )
    state: Dict[str, object] = {
        "player": {"x": START_POS[0], "y": START_POS[1]},
        "hazards": [],
        "hazard_set": set(),
        "goal": GOAL_B,  # Player starts near GOAL_A so first target is GOAL_B
        "score": 0,
        "high_score": 0,
        "running": False,
        "after_id": None,  # Tk 'after' id for cancelling scheduled ticks
    }
    # Bind both arrow keys and WASD (upper & lower case) for movement.
    try:
        pad.root.bind_all("<Left>", lambda e: on_left(pad, state, e))
        pad.root.bind_all("<Right>", lambda e: on_right(pad, state, e))
        pad.root.bind_all("<Up>", lambda e: on_up(pad, state, e))
        pad.root.bind_all("<Down>", lambda e: on_down(pad, state, e))
        pad.root.bind_all("<KeyPress-a>", lambda e: on_left(pad, state, e))
        pad.root.bind_all("<KeyPress-A>", lambda e: on_left(pad, state, e))
        pad.root.bind_all("<KeyPress-d>", lambda e: on_right(pad, state, e))
        pad.root.bind_all("<KeyPress-D>", lambda e: on_right(pad, state, e))
        pad.root.bind_all("<KeyPress-w>", lambda e: on_up(pad, state, e))
        pad.root.bind_all("<KeyPress-W>", lambda e: on_up(pad, state, e))
        pad.root.bind_all("<KeyPress-s>", lambda e: on_down(pad, state, e))
        pad.root.bind_all("<KeyPress-S>", lambda e: on_down(pad, state, e))
    except Exception:
        pass
    start_game(pad, state)
    pad.run()


if __name__ == "__main__":
    main()
