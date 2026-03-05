from __future__ import annotations

import subprocess
import sys
import os
from pathlib import Path
from typing import List, Tuple

import buttonpad

# Launcher: grid of 6 x 5 buttons launching example scripts (hard-coded list).
ROWS = 7
COLS = 4  # 30 cells total

EXAMPLES_DIR = Path(__file__).parent

# (Label, filename) pairs (relative to examples folder). Remaining cells blank.
EXAMPLES: List[Tuple[str, str]] = [
    ("Calculator", "calculator.py"),
    ("Connect Four", "connectfour.py"),
    ("Game of Life", "conwaysgameoflife.py"),
    ("Enter/Exit Demo", "demoenterexit.py"),
    ("Phone Demo", "demophonekeypad.py"),
    ("Phone Demo 2", "demophonekeypad2.py"),
    ("Dodger Race", "dodgerrace.py"),
    ("Emoji Copy Pad", "emojicopypad.py"),
    ("Fish Tank", "fishtank.py"),
    ("Flood It", "floodit.py"),
    ("Gomoku", "gomoku.py"),
    ("Lights Out", "lightsout.py"),
    ("Magic 8 Ball", "magic8ball.py"),
    ("Memory Puzzle", "memorypuzzle.py"),
    ("Othello", "othello.py"),
    ("Othello vs CPU", "othellovscpu.py"),
    ("Peg Solitaire", "pegsolitaire.py"),
    ("Pixel Editor", "pixeleditor.py"),
    ("Same Game", "samegame.py"),
    ("Simon", "simon.py"),
    ("Slide Puzzle", "slidepuzzle.py"),
    ("Stopwatch", "stopwatch.py"),
    ("Tic Tac Toe", "tictactoe.py"),
    ("TTT vs CPU", "tictactoevscpu.py"),
    ("8 Queens", "eightqueens.py"),
    ("2048", "twentyfortyeight.py"),
]  # 26 entries; remaining 4 cells left blank

def main() -> None:
    """Create and run the ButtonPad launcher window.

    Exposed so callers can do:
        import buttonpad.launcher; buttonpad.launcher.main()
    or via module entry point (python -m buttonpad) which already imports this.
    """
    # Build layout string
    layout_rows: List[str] = []
    for r in range(ROWS):
        tokens: List[str] = []
        for c in range(COLS):
            idx = r * COLS + c
            if idx < len(EXAMPLES):
                tokens.append(EXAMPLES[idx][0])
                tokens.append('View Source: ' + EXAMPLES[idx][0])
            else:
                tokens.append("`'',`''")  # blank label
        layout_rows.append(",".join(tokens))
    layout = '\n'.join(layout_rows)

    pad = buttonpad.ButtonPad(
        layout,
        cell_width=110,
        cell_height=50,
        padx=6,
        pady=6,
        default_bg_color='#dddddd',
        default_text_color='black',
        title='ButtonPad Launcher',
        border=12,
    )

    # Map label text -> script path for launching
    label_to_path = {label: EXAMPLES_DIR / filename for (label, filename) in EXAMPLES}
    py_exec = sys.executable or 'python'

    def make_launch_handler(script_name: str):
        def handler(el, x, y):
            path = label_to_path.get(script_name)
            if not path:
                return
            try:
                if sys.platform == 'win32':
                    creationflags = subprocess.CREATE_NEW_CONSOLE  # type: ignore[attr-defined]
                    subprocess.Popen([py_exec, str(path)], creationflags=creationflags)
                else:
                    subprocess.Popen([py_exec, str(path)], start_new_session=True)
            except Exception as e:
                try:
                    buttonpad.alert(f'Failed to launch {script_name}: {e}', title='Launcher Error')
                except Exception:
                    pass
        return handler

    def make_view_source_handler(script_name: str):
        def handler(el, x, y):
            path = label_to_path.get(script_name.removeprefix('View Source: '))
            if not path:
                return
            try:
                if sys.platform.startswith("darwin"):
                    subprocess.run(["open", str(path)])
                elif os.name == "nt":
                    os.startfile(str(path))
                else:
                    subprocess.run(["xdg-open", str(path)])
            except Exception as e:
                try:
                    buttonpad.alert(f'Failed to view source for {script_name}: {e}', title='View Source Error')
                except Exception:
                    pass
        return handler

    # Assign handlers
    for r in range(ROWS):
        for c in range(COLS):
            el = pad[c * 2, r]
            name = el.text.strip()
            if not name:
                continue
            el.on_click = make_launch_handler(name)
            el.tooltip = f'Run {name}'

            el = pad[c * 2 + 1, r]
            name = el.text.strip()
            if not name:
                continue
            el.on_click = make_view_source_handler(name)
            el.tooltip = f'{name}'


    pad.run()


if __name__ == '__main__':  # Allow running this file directly
    main()
