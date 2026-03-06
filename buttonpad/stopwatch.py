"""Simple stopwatch with Start/Stop, Lap, and Reset.

Beginner notes:
    * We keep track of elapsed time using time.monotonic() which always moves forward
        (unaffected by system clock changes).
    * "running" flag tells us whether to keep scheduling periodic updates.
    * base_elapsed stores the total number of seconds accumulated while previously
        running. When we pause we freeze it; when we resume we add new time to it.
    * Laps are just appended lines in a multi-line entry widget like a text log.
"""
import sys
import time

# Allow local import when running from repo
sys.path.insert(0, __file__.split('/examples/')[0])
import buttonpad

# Layout: 3 columns
# Row0: time label spans 3 cols (repeat same quoted text to merge)
# Row1: Start | Lap | Reset buttons
# Row2: "Laps:" | [entry spans 2 cols]
LAYOUT = "\n".join([
    "'00:00.00','00:00.00','00:00.00'",
    "Start,Lap,Reset",
    "'Laps:',[],[]",
])


def format_elapsed(seconds: float) -> str:
    """Return M:SS.HH style string for a floating elapsed second count."""
    if seconds < 0:
        seconds = 0.0
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    hundredths = int((seconds - int(seconds)) * 100)
    return f"{minutes:02d}:{secs:02d}.{hundredths:02d}"


"""Global state variables used by the stopwatch functions (initialized in main)."""
bp = None  # type: ignore
time_label = None  # type: ignore
start_btn = None  # type: ignore
lap_btn = None  # type: ignore
reset_btn = None  # type: ignore
laps_entry = None  # type: ignore
running = False
start_time: float = 0.0
base_elapsed: float = 0.0

def update_display() -> None:
    """Refresh the time label and reschedule if still running."""
    global running, time_label, start_time, base_elapsed, bp
    if bp is None or time_label is None:
        return
    now_elapsed = base_elapsed + (time.monotonic() - start_time) if running else base_elapsed
    time_label.text = format_elapsed(now_elapsed)
    if running and bp is not None:
        try:
            bp.root.after(50, update_display)
        except Exception:
            pass

def set_running(new_state: bool) -> None:
    """Start or stop the stopwatch based on new_state."""
    global running, start_time, start_btn
    if new_state == running:
        return
    running = new_state
    if running:
        start_time = time.monotonic()
        if start_btn is not None:
            start_btn.text = "Stop"
        update_display()
    else:
        elapsed_now = base_elapsed + (time.monotonic() - start_time)
        set_base_elapsed(elapsed_now)
        if start_btn is not None:
            start_btn.text = "Start"

def set_base_elapsed(value: float) -> None:
    """Change stored elapsed time (used during reset/pause)."""
    global base_elapsed, time_label
    base_elapsed = max(0.0, float(value))
    if time_label is not None:
        time_label.text = format_elapsed(base_elapsed)

def on_start_stop(_: buttonpad.BPButton, _x: int, _y: int) -> None:
    """Toggle running / paused state when Start/Stop clicked."""
    set_running(not running)

def on_lap(_: buttonpad.BPButton, _x: int, _y: int) -> None:
    """Capture current display time and append to lap log."""
    if time_label is None or laps_entry is None:
        return
    stamp = time_label.text
    text = laps_entry.text.strip()
    laps_entry.text = stamp if not text else f"{text}\n{stamp}"

def on_reset(_: buttonpad.BPButton, _x: int, _y: int) -> None:
    """Reset elapsed time (and laps). Keep running state if active."""
    global start_time, laps_entry
    if running:
        start_time = time.monotonic()
        set_base_elapsed(0.0)
    else:
        set_base_elapsed(0.0)
    if laps_entry is not None:
        laps_entry.text = ""

def main() -> None:
    """Build the UI, wire callbacks, and start the ButtonPad loop."""
    global bp, time_label, start_btn, lap_btn, reset_btn, laps_entry, running, start_time, base_elapsed
    bp = buttonpad.ButtonPad(
        layout=LAYOUT,
        cell_width=90,
        cell_height=56,
        padx=4,
        pady=4,
        title="Stopwatch",
        resizable=True,
        border=8,
    )
    time_label = bp[0, 0]
    start_btn = bp[0, 1]
    lap_btn = bp[1, 1]
    reset_btn = bp[2, 1]
    laps_entry = bp[1, 2]
    try:
        time_label.font_size = 28
    except Exception:
        pass
    running = False
    start_time = 0.0
    base_elapsed = 0.0
    start_btn.on_click = on_start_stop
    lap_btn.on_click = on_lap
    reset_btn.on_click = on_reset
    try:
        start_btn.hotkey = "space"  # type: ignore[attr-defined]
        lap_btn.hotkey = "l"        # type: ignore[attr-defined]
        reset_btn.hotkey = "r"      # type: ignore[attr-defined]
    except Exception:
        try:
            bp.map_key("space", 0, 1)
            bp.map_key("l", 1, 1)
            bp.map_key("r", 2, 1)
        except Exception:
            pass
    set_base_elapsed(0.0)
    bp.run()


if __name__ == "__main__":
    main()
