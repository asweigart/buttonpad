"""Animated fish tank demo using ButtonPad.

Description:
    * Creates a grid of water cells with a sand bottom row.
    * Random fish (emojis) swim around the water area, moving one cell at a time
        with randomized delays (each fish has its own speed).
    * One or two bottom creatures (crab/lobster) pace back and forth along the sand.
    * Simple occupancy tracking prevents creatures from overlapping.

Beginner pointers:
    * We store each moving creature as a dictionary with position, speed (ms),
        and direction (for walkers). This keeps code explicit & easy to inspect.
    * Movement is scheduled with Tk's after(): each fish re-schedules its own
        move_fish_one() call when done.
    * The 'occupied' set holds coordinates currently used by any creature to
        avoid overlapping moves.
"""

import random
from typing import Dict, List, Optional, Set, Tuple
import buttonpad

COLS = 16
ROWS = 10
SAND_ROW = ROWS - 1

WATER_COLOR = "#87CEEB"  # skyblue
SAND_COLOR = "#FFD54F"   # warm yellow

# Water creatures (must not overlap)
FISH_EMOJIS = [
    "🐟",  # fish
    "🐠",  # tropical fish
    "🐡",  # blowfish
    "🦈",  # shark
    "🐋",  # whale
    "🐬",  # dolphin
    "🐙",  # octopus
    "🦑",  # squid
]

BOTTOM_EMOJIS = ["🦀", "🦞"]  # crab, lobster


def build_empty_label_layout(cols: int, rows: int) -> str:
    """Return a layout string (cols x rows) of empty label cells.

    Each cell token is `"" (backtick + empty quoted string) which makes a
    blank label we can later color and place emojis into.
    """
    line = ",".join(["`\"\""] * cols)
    return "\n".join([line for _ in range(rows)])


def main() -> None:
    """Create the fish tank window, spawn creatures, start animations."""
    layout = build_empty_label_layout(COLS, ROWS)

    bp = buttonpad.ButtonPad(
        layout=layout,
        cell_width=40,
        cell_height=40,
        padx=1,
        pady=1,
        window_bg_color="#000000",  # thin grid lines look nicer against black window bg
        default_bg_color=WATER_COLOR,
        default_text_color="black",
        title="Fish Tank",
        resizable=True,
        border=4,
    )

    # Color water and sand, clear any text
    for y in range(ROWS):
        for x in range(COLS):
            el = bp[x, y]
            if y == SAND_ROW:
                el.bg_color = SAND_COLOR
            else:
                el.bg_color = WATER_COLOR
            el.text = ""

    # Occupancy of all animated emojis (both water and bottom)
    occupied: Set[Tuple[int, int]] = set()

    # ---- spawn fish in water (rows 0..SAND_ROW-1) ----
    water_cells = [(x, y) for y in range(0, SAND_ROW) for x in range(COLS)]

    # Choose a reasonable count: not too crowded
    fish_count = min(20, max(8, (COLS * (ROWS - 1)) // 12))

    # Build fish list with varying speeds
    fish: List[Dict] = []
    rng = random.Random()

    for i in range(fish_count):
        # Pick emoji cycling through list for variety
        emoji = FISH_EMOJIS[i % len(FISH_EMOJIS)]
        # Find a free starting position among water cells
        rng.shuffle(water_cells)
        start: Optional[Tuple[int, int]] = None
        for pos in water_cells:
            if pos not in occupied:
                start = pos
                break
        if start is None:  # No free water cell left
            break
        occupied.add(start)
        x, y = start
        bp[x, y].text = emoji
        # Moderate vs slow speeds (in milliseconds)
        if i % 2 == 0:
            speed = rng.randint(800, 1300)
        else:
            speed = rng.randint(1600, 2600)
        fish.append({"pos": start, "emoji": emoji, "ms": speed})

    # ---- bottom walkers (1-2 across sand) ----
    walkers: List[Dict] = []
    walker_count = rng.randint(1, 2)
    rng.shuffle(BOTTOM_EMOJIS)
    candidates = BOTTOM_EMOJIS[:walker_count]
    for emoji in candidates:
        # Choose free x on sand
        xs = list(range(COLS))
        rng.shuffle(xs)
        start_x = None
        for x in xs:
            if (x, SAND_ROW) not in occupied:
                start_x = x
                break
        if start_x is None:
            continue
        occupied.add((start_x, SAND_ROW))
        bp[start_x, SAND_ROW].text = emoji
        dir_ = rng.choice([-1, 1])  # initial direction: left or right
        walkers.append({"pos": (start_x, SAND_ROW), "emoji": emoji, "dir": dir_, "ms": rng.randint(1200, 2200)})

    # ---- movement logic ----
    def free(p: Tuple[int, int]) -> bool:
        """Return True if coordinate p is inside grid and unoccupied."""
        x, y = p
        return (0 <= x < COLS) and (0 <= y < ROWS) and (p not in occupied)

    def in_water(p: Tuple[int, int]) -> bool:
        """Return True if p is above the sand row (i.e., in water)."""
        return 0 <= p[0] < COLS and 0 <= p[1] < SAND_ROW

    def move_fish_one(idx: int) -> None:
        """Move a single fish one step (random 4-neighborhood) then reschedule."""
        if idx >= len(fish):
            return
        info = fish[idx]
        x, y = info["pos"]
        emoji = info["emoji"]
        # Candidate neighbor cells (right, left, down, up). We shuffle order.
        candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
        rng.shuffle(candidates)
        # With small chance, remain stationary this tick.
        if rng.random() < 0.15:
            bp.root.after(info["ms"], lambda i=idx: move_fish_one(i))
            return
        for nx, ny in candidates:
            np = (nx, ny)
            if in_water(np) and free(np):
                bp[x, y].text = ""
                occupied.discard((x, y))
                bp[nx, ny].text = emoji
                occupied.add(np)
                info["pos"] = np
                break
        bp.root.after(info["ms"], lambda i=idx: move_fish_one(i))

    def move_walker_one(idx: int) -> None:
        """Move a sand walker horizontally; reverse on edges or obstacles."""
        if idx >= len(walkers):
            return
        info = walkers[idx]
        (x, y) = info["pos"]
        emoji = info["emoji"]
        dir_ = info["dir"]
        nx = x + dir_
        np = (nx, SAND_ROW)
        # Reverse direction if would leave board or cell is occupied
        if not (0 <= nx < COLS) or not free(np):
            dir_ = -dir_
            info["dir"] = dir_
            nx = x + dir_
            np = (nx, SAND_ROW)
        if 0 <= nx < COLS and free(np):
            bp[x, y].text = ""
            occupied.discard((x, y))
            bp[nx, SAND_ROW].text = emoji
            occupied.add(np)
            info["pos"] = np
        bp.root.after(info["ms"], lambda i=idx: move_walker_one(i))

    # Kick off animations (stagger initial delays so they don't all move at once)
    for i in range(len(fish)):
        bp.root.after(random.randint(0, 800), lambda i=i: move_fish_one(i))
    for i in range(len(walkers)):
        bp.root.after(random.randint(0, 600), lambda i=i: move_walker_one(i))

    bp.run()


if __name__ == "__main__":
    main()
