"""Magic 8-Ball animation using ButtonPad.

Features:
    * 5x5 grid where the center cell shows a white "8" when idle.
    * Clicking any cell triggers an animated sequence:
            1. Center turns black.
            2. Outer cells rapidly randomize dark colors for a while.
            3. All cells fade to black one-by-one.
            4. A short pause on the all-black screen.
            5. The center reveals a random fortune (answer text) in a dark blue tile.
    * Clicking again while the answer is visible resets everything back to idle.

Beginner notes:
    * We store a single global state dict with a 'mode' string (idle/anim/answer)
        and an 'after' list of scheduled callback IDs so we can cancel them if the
        user interrupts the animation.
    * The animation is a chain of functions; each schedules the next step using
        Tk's after() via pad.root.after(milliseconds, callback).
    * All cell updates go through the helper set_cell() for consistency.
"""

from __future__ import annotations

from typing import List, Tuple
import random

try:
    import buttonpad  # local module name
except Exception:
    import ButtonPad as buttonpad  # type: ignore

COLS = 5
ROWS = 5

# Colors
BLACK = "#000000"
WHITE = "#ffffff"
DARK_GRAY = "#2b2b31"
DARK_PURPLE = "#2a1548"
DARK_BLUE = "#0f1d3a"
RANDOM_COLORS = [BLACK, DARK_GRAY, DARK_PURPLE, DARK_BLUE]

# Animation timing
RANDOM_TICKS = 30
RANDOM_TICK_MS = 50
FADE_DELAY_MS = 20
PAUSE_BLACK_MS = 1000

# Fonts
ANSWER_FONT_SIZE = 12  # adjust the revealed answer text size here

ANSWERS = [
    "IT IS\nCERTAIN",
    "IT IS\nDECIDEDLY\nSO",
    "YES\nDEFINITELY",
    "REPLY HAZY\nTRY AGAIN",
    "ASK\nAGAIN\nLATER",
    "CONCENTRATE\nAND\nASK\nAGAIN",
    "MY REPLY\nIS NO",
    "OUTLOOK\nNOT SO\nGOOD",
    "VERY\nDOUBTFUL",
]

Coord = Tuple[int, int]
CENTER = (COLS // 2, ROWS // 2)

# Global objects/state initialized in main()
pad = None  # type: ignore[assignment]
state: dict


def build_layout() -> str:
    """Return a COLS x ROWS layout of independent cells (all backticks)."""
    row = ",".join(["`"] * COLS)
    return "\n".join([row for _ in range(ROWS)])


def all_cells() -> List[Coord]:
    """Return a list of all (x,y) coordinate pairs on the grid."""
    return [(x, y) for y in range(ROWS) for x in range(COLS)]


def set_cell(x: int, y: int, bg: str, text: str = "", fg: str = WHITE, size: int | None = None) -> None:
    """Convenience: update background, text, text color, and optionally font size."""
    el = pad[x, y]  # type: ignore[index]
    el.bg_color = bg
    el.text_color = fg
    el.text = text
    if size is not None:
        el.font_size = size


def clear_after() -> None:
    """Cancel all scheduled callbacks stored in state['after'].

    This lets us interrupt an animation safely (e.g., if the user clicks to
    reset during animation). We silently ignore errors if the window closed or
    an ID is invalid.
    """
    ids = state["after"]
    state["after"] = []
    for aid in ids:
        try:
            pad.root.after_cancel(aid)  # type: ignore[arg-type]
        except Exception:
            pass


def set_idle_ui() -> None:
    """Display the idle screen: all black, center white with an '8'."""
    for x, y in all_cells():
        set_cell(x, y, BLACK, "", WHITE)
    cx, cy = CENTER
    set_cell(cx, cy, WHITE, "8", BLACK, size=42)
    state["mode"] = "idle"


def randomize_tick(remaining: int) -> None:
    """One frame of the random color shuffle phase.

    We skip the center (already turned black) and randomize dark colors for
    the outer 24 cells. When frames run out, we proceed to fade_to_black().
    """
    if remaining <= 0:
        fade_to_black()
        return
    for x, y in all_cells():
        if (x, y) == CENTER:
            continue
        set_cell(x, y, random.choice(RANDOM_COLORS), "")
    aid = pad.root.after(RANDOM_TICK_MS, lambda: randomize_tick(remaining - 1))  # type: ignore[arg-type]
    state["after"].append(aid)


def fade_to_black() -> None:
    """Fade all cells to black one-by-one in random order.

    We ensure the center fades first by moving it to the front of the shuffled
    list, giving a consistent visual focal point before the reveal.
    """
    cells = [(x, y) for x, y in all_cells()]
    random.shuffle(cells)
    if CENTER in cells:
        cells.remove(CENTER)
    cells.insert(0, CENTER)

    def step(i: int) -> None:
        if i >= len(cells):
            pause_then_answer()
            return
        x, y = cells[i]
        set_cell(x, y, BLACK, "")
        aid = pad.root.after(FADE_DELAY_MS, lambda: step(i + 1))  
        state["after"].append(aid)

    step(0)


def pause_then_answer() -> None:
    """Hold on all-black briefly, then show the final answer."""
    aid = pad.root.after(PAUSE_BLACK_MS, show_answer)
    state["after"].append(aid)


def show_answer() -> None:
    """Pick a random fortune and display it in the center cell."""
    ans = random.choice(ANSWERS)
    cx, cy = CENTER
    for x, y in all_cells():
        set_cell(x, y, BLACK, "")
    set_cell(cx, cy, DARK_BLUE, ans, WHITE, size=ANSWER_FONT_SIZE)
    state["mode"] = "answer"


def start_animation() -> None:
    """Begin a new animation cycle from idle state."""
    state["mode"] = "anim"
    clear_after()
    set_cell(*CENTER, BLACK, "")
    randomize_tick(RANDOM_TICKS)


def on_click(_el, _x, _y) -> None:
    """Respond to any cell click based on current mode.

    Modes:
      idle   -> start animation
      anim   -> ignore (let animation finish)
      answer -> reset back to idle
    """
    if state["mode"] == "anim":
        return
    if state["mode"] == "answer":
        clear_after()
        set_idle_ui()
        return
    start_animation()


def main() -> None:
    """Create the window, initialize state, and enter the event loop."""
    global pad, state
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=100,
        cell_height=100,
        padx=6,
        pady=6,
        border=14,
        title="Magic 8-Ball",
        default_bg_color=BLACK,
        default_text_color=WHITE,
        window_bg_color="#0b0b0b",
        resizable=True,
    )
    state = {"mode": "idle", "after": []}
    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y].on_click = on_click  # type: ignore[index]
    set_idle_ui()
    pad.run()


if __name__ == "__main__":
    main()
