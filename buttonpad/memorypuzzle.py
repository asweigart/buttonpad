"""Memory (Concentration) Puzzle using ButtonPad.

Rules / gameplay:
    * A 6 x 4 grid holds 24 face-down cards (12 matching emoji pairs).
    * Click a hidden card to reveal it. Then click a second card:
            - If they match, they stay revealed with a green background.
            - If they don't match, they briefly stay revealed and then flip back.
    * Each pair attempt (whether match or mismatch) increments the 'tries' count.
    * When all pairs are matched, an alert displays the number of tries and a
        new shuffled game automatically starts.

Implementation highlights (beginner friendly):
    * Board data is stored in dictionaries keyed by (x, y) tuples for clarity.
    * 'board' maps coordinates to the emoji on that card.
    * 'revealed' stores which cards are currently face-up temporarily.
    * 'matched' stores which cards are permanently face-up (already matched).
    * A simple 'state' dict tracks the first picked card, whether clicks are
        locked (to prevent double-clicking during flip-back), and the number of tries.
    * We update cell UI via set_cell_ui() so the logic for the look of a cell is
        centralized in one function.
"""

from __future__ import annotations

import random
from typing import Tuple, Dict

import buttonpad

COLS = 6
ROWS = 4

# UI
WINDOW_BG = "#0e1220"      # dark backdrop
HIDDEN_BG = "#1f2640"      # hidden card background
REVEAL_BG = "#2a3358"      # temporarily revealed background
MATCHED_BG = "#2e7d32"     # permanently matched background (greenish)
TEXT_COLOR = "#ffffff"
FONT_SIZE = 28

# 12 emoji pairs (visible and distinct)
EMOJIS = [
    "🍎", "🍌", "🍇", "🍓", "🍒", "🍍",
    "🍑", "🥝", "🍉", "🍋", "🍊", "🥥",
]


def build_layout(cols: int, rows: int) -> str:
    """Return a grid layout string with unmerged buttons for the puzzle.

    Each backtick token represents one clickable card position.
    """
    row = ",".join(["`"] * cols)
    return "\n".join([row for _ in range(rows)])

BoardType = Dict[Tuple[int, int], str]
BoolBoard = Dict[Tuple[int, int], bool]

# Globals initialized in main()
pad = None  # type: ignore[assignment]
board: BoardType
revealed: BoolBoard
matched: BoolBoard
state: Dict[str, object]


def set_cell_ui(x: int, y: int) -> None:
    """Apply the correct appearance to the (x,y) card based on state.

    Order of precedence:
      1. If the card is matched, show its emoji on a green background.
      2. Else if it's temporarily revealed, show emoji on the reveal background.
      3. Else it's hidden: blank text with hidden background.
    """
    el = pad[x, y]  # type: ignore[index]
    val = board[(x, y)]
    if matched[(x, y)]:
        el.text = val
        el.bg_color = MATCHED_BG
    elif revealed[(x, y)]:
        el.text = val
        el.bg_color = REVEAL_BG
    else:
        el.text = ""
        el.bg_color = HIDDEN_BG
    el.text_color = TEXT_COLOR
    el.font_size = FONT_SIZE


def update_ui() -> None:
    """Redraw every card (simple but fine for small boards)."""
    for y in range(ROWS):
        for x in range(COLS):
            set_cell_ui(x, y)


def all_matched() -> bool:
    """Return True if every card has been permanently matched."""
    for y in range(ROWS):
        for x in range(COLS):
            if not matched[(x, y)]:
                return False
    return True


def new_game() -> None:
    """Start (or restart) a game: shuffle and reset all state structures."""
    cards = EMOJIS * 2  # two copies of each emoji
    random.shuffle(cards)
    i = 0
    for y in range(ROWS):
        for x in range(COLS):
            board[(x, y)] = cards[i]
            revealed[(x, y)] = False
            matched[(x, y)] = False
            i += 1
    state["first"] = None  # coordinate of first revealed card (or None)
    state["lock"] = False  # prevents click spam while cards flip back
    state["tries"] = 0
    update_ui()


def reveal(x: int, y: int) -> None:
    """Show the card at (x,y)."""
    revealed[(x, y)] = True
    set_cell_ui(x, y)


def hide(x: int, y: int) -> None:
    """Hide (flip face-down) the card at (x,y)."""
    revealed[(x, y)] = False
    set_cell_ui(x, y)


def mark_matched(a: Tuple[int, int], b: Tuple[int, int]) -> None:
    """Mark both coordinates as permanently matched and update UI."""
    ax, ay = a
    bx, by = b
    matched[(ax, ay)] = True
    matched[(bx, by)] = True
    set_cell_ui(ax, ay)
    set_cell_ui(bx, by)


def on_cell_click(_el, x: int, y: int) -> None:
    """Handle user clicking a card; manage reveal/match logic.

    Flow:
      1. Ignore if we're temporarily locked (during mismatch flip-back).
      2. Ignore if card already matched or currently revealed.
      3. If no first card selected: record this coordinate and reveal it.
      4. Else: reveal second card, increment tries, compare symbols.
         * Match -> mark both cards; check for win.
         * Mismatch -> lock inputs, schedule flip-back after delay.
    """
    if state["lock"]:
        return
    if matched[(x, y)] or revealed[(x, y)]:
        return
    if state["first"] is None:
        state["first"] = (x, y)
        reveal(x, y)
        return
    fx, fy = state["first"]  # type: ignore[assignment]
    state["first"] = None
    reveal(x, y)
    state["tries"] = int(state["tries"]) + 1  # Count this pair attempt
    if board[(fx, fy)] == board[(x, y)]:  # Match
        mark_matched((fx, fy), (x, y))
        if all_matched():
            try:
                buttonpad.alert(f"You win!\nTries: {state['tries']}")
            except Exception:
                pass
            new_game()
    else:  # Mismatch -> schedule hiding both after delay
        state["lock"] = True
        def flip_back():
            hide(fx, fy)
            hide(x, y)
            state["lock"] = False
        pad.root.after(700, flip_back)


def main() -> None:
    """Create the window, initialize boards/state, start first game."""
    global pad, board, revealed, matched, state
    layout = build_layout(COLS, ROWS)
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=80,
        cell_height=80,
        padx=6,
        pady=6,
        border=10,
        title="Memory Puzzle",
        default_bg_color=HIDDEN_BG,
        default_text_color=TEXT_COLOR,
        window_bg_color=WINDOW_BG,
        resizable=True,
    )
    board = {(x, y): "" for y in range(ROWS) for x in range(COLS)}
    revealed = {(x, y): False for y in range(ROWS) for x in range(COLS)}
    matched = {(x, y): False for y in range(ROWS) for x in range(COLS)}
    state = {"first": None, "lock": False, "tries": 0}
    for y in range(ROWS):
        for x in range(COLS):
            pad[x, y].on_click = on_cell_click  # type: ignore[index]
            el = pad[x, y]  # type: ignore[index]
            el.text = ""  # Start hidden
            el.bg_color = HIDDEN_BG
            el.text_color = TEXT_COLOR
            el.font_size = FONT_SIZE
    new_game()
    pad.run()


if __name__ == "__main__":
    main()
