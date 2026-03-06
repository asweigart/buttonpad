"""Simon memory game implemented with ButtonPad.

Gameplay:
    * Watch the sequence of flashing colored quadrants and then reproduce it.
    * Each round appends one new random quadrant to the existing sequence.
    * Your score equals the number of rounds (length of completed sequences).

Implementation notes for beginners:
    * The board is a simple 2x2 layout of colored labels (no need for button widgets).
    * We store the sequence as a list of indices 0..3 (row-major order).
    * `playback_sequence()` flashes each index in sequence using chained after() calls.
    * User clicks are disabled while the sequence is playing (state['busy']).
    * High score persists until the program is closed (not saved to disk).
"""

from __future__ import annotations
import random
from typing import List
import buttonpad

COLS = 2
ROWS = 2

# UI
WINDOW_BG = "#0e1220"  # dark backdrop
TEXT_COLOR = "#ffffff"

# Base and lit colors per quadrant (index: y*2 + x)
BASE_COLORS = [
    "#2ecc71",  # green
    "#e74c3c",  # red
    "#3498db",  # blue
    "#f1c40f",  # yellow
]
LIT_COLORS = [
    "#6ff7a8",  # light green
    "#ff8a73",  # light red
    "#7cbcff",  # light blue
    "#ffe27a",  # light yellow
]

FLASH_MS = 450
GAP_MS = 160
BETWEEN_ROUNDS_MS = 500
CLICK_FLASH_MS = 180


def build_layout() -> str:
    """Return a 2x2 layout using label cells (no click highlight default)."""
    # Use backtick + quoted empty string to force label creation and prevent merges.
    row = ",".join(['`""'] * COLS)
    return "\n".join([row for _ in range(ROWS)])


essential_indices = [0, 1, 2, 3]


def main() -> None:
    """Create window, set up game state, and start first round."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=200,
        cell_height=200,
        padx=4,
        pady=4,
        border=8,
        title="Simon",
        default_text_color=TEXT_COLOR,
        window_bg_color=WINDOW_BG,
        resizable=True,
    )
    try:
        pad.status_bar = "Score: 0  High: 0"
    except Exception:
        pass

    label_chars = ["Q", "W", "A", "S"]
    subtle_text_colors = ["#146c3b", "#82271d", "#1a5078", "#7d6a10"]
    keysyms = ["q", "w", "a", "s"]
    for y in range(ROWS):
        for x in range(COLS):
            idx = y * COLS + x
            el = pad[x, y]  # type: ignore[index]
            el.bg_color = BASE_COLORS[idx]
            el.text = label_chars[idx]
            try:
                el.text_color = subtle_text_colors[idx]
                el.hotkey = keysyms[idx]
            except Exception:
                try:
                    pad.map_key(keysyms[idx], x, y)
                except Exception:
                    pass

    sequence: List[int] = []
    state = {
        "busy": False,
        "expect": 0,
        "accept": False,
        "timer_id": None,
        "score": 0,
        "high_score": 0,
    }

    def set_lit(idx: int, lit: bool) -> None:
        """Turn a quadrant on (bright) or off (base)."""
        x, y = idx % COLS, idx // COLS
        pad[x, y].bg_color = LIT_COLORS[idx] if lit else BASE_COLORS[idx]  # type: ignore[index]

    def flash_idx(idx: int, on_ms: int, after_cb) -> None:
        """Flash a single index for on_ms then call after_cb."""
        set_lit(idx, True)
        pad.root.after(on_ms, lambda: (set_lit(idx, False), after_cb()))

    def playback_sequence() -> None:
        """Play back the current sequence of indices using timed flashes."""
        state["busy"] = True
        state["accept"] = False
        state["expect"] = 0
        i = 0

        def next_step():
            nonlocal i
            if i >= len(sequence):
                state["busy"] = False
                state["accept"] = True
                return
            idx = sequence[i]

            def cont():
                pad.root.after(GAP_MS, advance)

            flash_idx(idx, FLASH_MS, cont)

        def advance():
            nonlocal i
            i += 1
            next_step()

        next_step()

    def add_step_and_play() -> None:
        """Append a random quadrant to the sequence and replay everything."""
        sequence.append(random.choice(essential_indices))
        pad.root.after(BETWEEN_ROUNDS_MS, playback_sequence)

    def _update_status_bar() -> None:
        """Periodic status bar refresh (also drives high score display)."""
        try:
            pad.status_bar = f"Score: {state['score']}  High: {state['high_score']}"
        except Exception:
            pass
        try:
            state["timer_id"] = pad.root.after(500, _update_status_bar)
        except Exception:
            pass

    def game_over() -> None:
        """Show a dialog then immediately start a new game."""
        length_achieved = max(0, len(sequence) - 1)
        try:
            buttonpad.alert(f"Game Over\nScore: {length_achieved}")
        except Exception:
            pass
        new_game()

    def on_cell_click(_el, x: int, y: int) -> None:
        """Handle player click; verify expected index or end game."""
        if state["busy"] or not state["accept"]:
            return
        idx = y * COLS + x
        set_lit(idx, True)
        pad.root.after(CLICK_FLASH_MS, lambda: set_lit(idx, False))
        expected = sequence[state["expect"]]
        if idx == expected:
            state["expect"] += 1
            if state["expect"] == len(sequence):  # completed round
                state["accept"] = False
                state["score"] += 1
                if state["score"] > state["high_score"]:
                    state["high_score"] = state["score"]
                _update_status_bar()
                add_step_and_play()
        else:
            game_over()

    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y].on_click = on_cell_click  # type: ignore[index]

    def new_game() -> None:
        """Reset sequence and score; begin a fresh round."""
        if state.get("timer_id") is not None:
            try:
                pad.root.after_cancel(state["timer_id"])  # type: ignore[arg-type]
            except Exception:
                pass
            state["timer_id"] = None
        sequence.clear()
        state["busy"] = False
        state["accept"] = False
        state["expect"] = 0
        state["score"] = 0
        try:
            pad.status_bar = f"Score: 0  High: {state['high_score']}"
        except Exception:
            pass
        _update_status_bar()
        add_step_and_play()

    new_game()
    pad.run()


if __name__ == "__main__":
    main()
