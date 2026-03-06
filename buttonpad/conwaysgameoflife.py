"""Conway's Game of Life implemented with ButtonPad.

This version is written in a very beginner-friendly style:
	* The grid is 20 x 20 cells of life. A separate control row of 4 buttons
		(Play/Pause, Clear, Random, Invert) is placed BELOW the grid.
	* Each cell is either OFF (0) or ON (1). The board is stored in a dictionary
		mapping (x, y) -> 0/1. This makes lookups explicit and easy to read.
	* The simulation follows the classic Life rules:
				- Any live cell with 2 or 3 live neighbors survives.
				- Any dead cell with exactly 3 live neighbors becomes alive.
				- All other live cells die; all other dead cells stay dead.
	* We repeatedly "step" the board while the game is in the playing state.
	* Lambdas are used to attach click handlers that know which cell they toggle.

Reading order suggestion for learners:
	1. Constants (grid size & colors)
	2. Small helpers (bounds checks, grid building, setting a cell)
	3. Simulation logic (count_neighbors, step)
	4. Control button handlers (start, pause, clear, random, invert)
	5. main() which wires everything together and starts the GUI loop.
"""

from __future__ import annotations

import random
import buttonpad
from typing import Tuple, Dict

COLS = 20
ROWS = 20  # cell rows (a control row is added below)

# Ensure there are at least 4 columns so the 4 control buttons can each span >= 1 col
if COLS < 4:
	COLS = 4

# UI
WINDOW_BG = "#0e1220"  # dark backdrop
OFF_BG = "#0b1a3b"     # dark blue (off)
ON_BG = "#ffffff"      # white (on)
TEXT_COLOR = "#ffffff"

PLAY_CHAR = "▶"
PAUSE_CHAR = "⏸"
STEP_INTERVAL_MS = 500

Coord = Tuple[int, int]


def _control_spans(cols: int) -> tuple[list[int], list[int]]:
	"""Return layout info for the 4 control buttons.

	We want 4 control buttons across the bottom row to each span roughly the same
	width. Example: if cols == 20 we would like spans like [5,5,5,5]; if cols == 22
	we might get [6,6,5,5].

	Returns:
		(spans, starts)
		spans  - list of 4 integers whose sum == cols (width of each control)
		starts - list of the starting x positions (left edges) for each control
	"""
	base = cols // 4
	rem = cols % 4
	spans = [base + (1 if i < rem else 0) for i in range(4)]
	starts: list[int] = []
	acc = 0
	for s in spans:
		starts.append(acc)
		acc += s
	return spans, starts


def build_layout() -> str:
	"""Build the layout string passed to ButtonPad.

	ButtonPad expects a multi-line comma-separated layout description. Each line
	represents a row of the interface. The last row is the merged control buttons
	(Play/Pause, Clear, Random, Invert). The earlier rows are the Life cells.
	"""
	# Top grid: no-merge buttons (each cell is an independent square). We use the
	# backtick ` token which creates an empty label cell in ButtonPad.
	top_row = ",".join(["`"] * COLS)
	top = "\n".join([top_row for _ in range(ROWS)])
	# Bottom control row: four merged buttons spanning across COLS. We replicate
	# each label token for however many columns it should span.
	spans, _starts = _control_spans(COLS)
	labels = [PLAY_CHAR, "Clear", "Random", "Invert"]
	control_tokens: list[str] = []
	for label, span in zip(labels, spans):
		control_tokens.extend([label] * span)
	control = ",".join(control_tokens)
	return "\n".join([top, control])


def in_bounds(x: int, y: int) -> bool:
	"""Return True if (x, y) is a valid cell coordinate inside the Life grid."""
	return 0 <= x < COLS and 0 <= y < ROWS


BoardType = Dict[Tuple[int, int], int]


def set_cell(pad, board: BoardType, x: int, y: int, val: int) -> None:
	"""Set a single cell's value and immediately update its visual appearance."""
	board[(x, y)] = 1 if val else 0
	el = pad[x, y]  # type: ignore[index]
	el.bg_color = ON_BG if board[(x, y)] else OFF_BG
	el.text = ""


def update_grid(pad, board: BoardType) -> None:
	"""Update every cell's appearance to match the underlying board dict."""
	for y in range(ROWS):
		for x in range(COLS):
			el = pad[x, y]  # type: ignore[index]
			el.bg_color = ON_BG if board[(x, y)] else OFF_BG
			el.text = ""


def count_neighbors(board: BoardType, x: int, y: int) -> int:
	"""Return how many of the 8 neighboring cells around (x,y) are alive.

	We iterate through the 3x3 square centered at (x,y), skipping the middle cell
	itself. Coordinates outside the grid are ignored.
	"""
	cnt = 0
	for dy in (-1, 0, 1):
		for dx in (-1, 0, 1):
			if dx == 0 and dy == 0:
				continue
			nx, ny = x + dx, y + dy
			if in_bounds(nx, ny) and board[(nx, ny)]:
				cnt += 1
	return cnt


def step(pad, board: BoardType, playing: dict, after_id: dict) -> None:
	"""Advance the simulation by one generation and re-schedule if playing.

	We build a new board (nxt) using the Life rules, then only update changed
	cells for efficiency. If the game is still marked as playing we schedule the
	next call to step() using Tk's after() timer.
	"""
	nxt: BoardType = {}
	for y in range(ROWS):
		for x in range(COLS):
			n = count_neighbors(board, x, y)
			cur = board[(x, y)]
			if cur == 1:
				nxt[(x, y)] = 1 if (n == 2 or n == 3) else 0
			else:
				nxt[(x, y)] = 1 if n == 3 else 0
	for y in range(ROWS):
		for x in range(COLS):
			if nxt[(x, y)] != board[(x, y)]:
				set_cell(pad, board, x, y, nxt[(x, y)])
	if playing["value"]:
		after_id["id"] = pad.root.after(STEP_INTERVAL_MS, lambda: step(pad, board, playing, after_id))
	else:
		after_id["id"] = None


def start(pad, board: BoardType, playing: dict, after_id: dict) -> None:
	"""Begin automatic stepping if not already playing."""
	if playing["value"]:
		return
	playing["value"] = True
	play_btn = pad[0, ROWS]
	play_btn.text = PAUSE_CHAR
	after_id["id"] = pad.root.after(STEP_INTERVAL_MS, lambda: step(pad, board, playing, after_id))


def pause(pad, playing: dict, after_id: dict) -> None:
	"""Stop automatic stepping if currently playing."""
	if not playing["value"]:
		return
	playing["value"] = False
	play_btn = pad[0, ROWS]
	play_btn.text = PLAY_CHAR
	if after_id["id"] is not None:
		try:
			pad.root.after_cancel(after_id["id"])  # type: ignore[arg-type]
		except Exception:
			pass
		after_id["id"] = None


def on_play_pause(pad, board: BoardType, playing: dict, after_id: dict, _el=None, _x=None, _y=None):
	"""Toggle between starting and pausing the automatic simulation."""
	if playing["value"]:
		pause(pad, playing, after_id)
	else:
		start(pad, board, playing, after_id)


def on_clear(pad, board: BoardType, _el=None, _x=None, _y=None):
	"""Turn every cell off (empty board) and refresh the display."""
	for y in range(ROWS):
		for x in range(COLS):
			board[(x, y)] = 0
	update_grid(pad, board)


def on_random(pad, board: BoardType, _el=None, _x=None, _y=None):
	"""Assign each cell a random 0/1 value and refresh the display."""
	for y in range(ROWS):
		for x in range(COLS):
			board[(x, y)] = random.randint(0, 1)
	update_grid(pad, board)


def on_invert(pad, board: BoardType, _el=None, _x=None, _y=None):
	"""Flip each cell: ON becomes OFF, OFF becomes ON, then refresh display."""
	for y in range(ROWS):
		for x in range(COLS):
			board[(x, y)] = 0 if board[(x, y)] else 1
	update_grid(pad, board)


def toggle_cell(pad, board: BoardType, x: int, y: int) -> None:
	"""Invert a single cell (user click) if inside the grid."""
	if not in_bounds(x, y):
		return
	set_cell(pad, board, x, y, 0 if board[(x, y)] else 1)


def main() -> None:
	"""Create the GUI, initialize state, wire handlers, and start the app.

	Steps performed:
	 1. Build a text layout that describes the grid + control row.
	 2. Create the ButtonPad window using that layout.
	 3. Initialize the board data structure (all cells off).
	 4. Attach click handlers for cells and control buttons.
	 5. Draw the initial grid and enter the GUI event loop.
	"""
	layout = build_layout()
	pad = buttonpad.ButtonPad(
		layout=layout,
		cell_width=20,
		cell_height=20,
		padx=0,
		pady=0,
		border=10,
		title="Conway's Game of Life",
		default_bg_color=OFF_BG,
		default_text_color=TEXT_COLOR,
		window_bg_color=WINDOW_BG,
		resizable=True,
	)

	# Board: 0=off, 1=on
	board: BoardType = {(x, y): 0 for y in range(ROWS) for x in range(COLS)}
	playing = {"value": False}
	after_id = {"id": None}

	# Wire grid cell toggles with lambdas capturing coordinates
	for y in range(ROWS):
		for x in range(COLS):
			# Handler must accept (el, x, y) even if we ignore runtime x,y in favor of captured coords
			pad[x, y].on_click = (lambda el, _cx, _cy, xx=x, yy=y: toggle_cell(pad, board, xx, yy))  # type: ignore[index]

	# Wire control buttons using dynamic spans across COLS
	_spans, starts = _control_spans(COLS)
	play_x, clear_x, random_x, invert_x = starts
	pad[play_x, ROWS].on_click = (lambda el, _x, _y: on_play_pause(pad, board, playing, after_id, el))  # type: ignore[index]
	pad[play_x, ROWS].text = PLAY_CHAR
	pad[clear_x, ROWS].on_click = (lambda el, _x, _y: on_clear(pad, board, el))  # type: ignore[index]
	pad[clear_x, ROWS].text = "Clear"
	pad[random_x, ROWS].on_click = (lambda el, _x, _y: on_random(pad, board, el))  # type: ignore[index]
	pad[random_x, ROWS].text = "Random"
	pad[invert_x, ROWS].on_click = (lambda el, _x, _y: on_invert(pad, board, el))  # type: ignore[index]
	pad[invert_x, ROWS].text = "Invert"

	# Initialize visuals
	update_grid(pad, board)
	pad.run()


if __name__ == "__main__":
	main()

