"""Emoji Copy Pad.

Purpose: Quickly browse groups of emojis and copy one to the system
clipboard with a single click. The top row contains category buttons; the
remaining rows show emojis for the selected category.

Beginner walkthrough:
  1. A layout string (built by build_layout()) creates a 5-row grid: the
      top row for 8 category buttons, and 4 rows (4*8=32 cells) for emojis.
  2. Each category has a name, an icon (shown in its button), and a list of
      emojis. We slice/repeat that list to fill the 32 emoji cells.
  3. Clicking a category repopulates the lower 32 cells with that category's
      emojis; clicking an emoji copies it to the clipboard (pyperclip if
      installed, otherwise Tk's clipboard API).
  4. A helper chooses an emoji-capable font so glyphs render nicely across
      platforms.
  5. Tooltips (if supported) show the human-readable emoji name.
"""

from __future__ import annotations

from typing import Dict, List, Sequence
import sys
import tkinter.font as tkfont
import unicodedata as _ucd

try:
    import pyperclip  # type: ignore
except Exception:
    pyperclip = None  # optional; we'll fall back to Tk clipboard

try:
    import buttonpad  # local package/module name
except Exception:
    # Fallback for environments where it's installed with different casing
    import ButtonPad as buttonpad  # type: ignore

COLS = 8
ROWS = 5  # 1 category row + 4 emoji rows (total 8x5)
TOP_BG = "#87b5ff"      # blue background for category buttons
BOTTOM_BG = "#f3f3f3"

# Categories: name -> (icon, emoji list)
# Clothing category removed per request; trimmed to 8 categories to match 8 columns (dropped Flags to keep common sets).
CATEGORIES: List[Dict[str, object]] = [
    {"name": "Smileys", "icon": "😊", "emojis": [
        "😀","😃","😄","😁","😆","😅","😂","🙂","🙃","😉","😊","😇","😍","🤩","😘","🥰","😗","😙","😚","😋","😛","😝","😜","🤪","🤗","🤭","🫢","🫣","🤫","🤔","🤐","🤨","😐","😑","😶","🫥","🙄","😏","😣","😥","😮\u200d💨","😮","😯","😲","🥱","😴","🤤","😪","😵","😵\u200d💫","🤒","🤕","🤧","🤮","🤢","🥴","😎","🤓","🧐","🤠","🥳","🤯","🤥","🥹"
    ]},
    {"name": "People & Body", "icon": "🧑", "emojis": [
        # 32 unique entries (exactly fills 4x8 grid) – duplicates & invalid placeholders removed/replaced
        "🧑","👶","👧","👦","👵","👴","👩","👨","👷",
        "🧑\u200d🎓","🧑\u200d🏫","🧑\u200d💻","🧑\u200d🔬","🧑\u200d🎨","🧑\u200d🚀","🧑\u200d🌾",
        "🧑\u200d🔧","🧑\u200d⚕️","🧑\u200d✈️","🧑\u200d🍳","🧑\u200d🚒","🧑\u200d🎤","🧑\u200d💼",
        "🤰","�","�","�","🧑\u200d🦽","🧑\u200d🦯","🧑\u200d🩼","🧑\u200d🦼","🧑\u200d⚖️"
    ]},
    {"name": "Hand Gestures", "icon": "✋", "emojis": [
        "👍","👎","👌","✌️","🤞","🤟","🤘","🤌","🤏","✋","🤚","🖐️","🖖","👋","🤙","💪","🙏","☝️","👆","👇","👈","👉","🖕","✍️","🤲","🫶","🫰","🫵"
    ]},
    {"name": "Animals", "icon": "🐶", "emojis": [
        "🐶","🐱","🐭","🐹","🐰","🦊","🐻","🐼","🐻\u200d❄️","🐨","🐯","🦁","🐮","🐷","🐸","🐵","🐔","🐧","🐦","🐤","🦆","🦅","🦉","🦇","🐺","🦄","🐝","🪲","🦋","🐢","🐍","🦖","🦕","🐙","🦑","🦞","🦀","🐡","🦔","🦝"
    ]},
    {"name": "Nature", "icon": "🌿", "emojis": [
        "🌲","🌳","🌴","🌵","🌾","🌿","☘️","🍀","🍁","🍂","🍃","🌱","🌸","🌼","🌻","🌺","🌷","🌹"
    ]},
    {"name": "Weather & Sky", "icon": "☀️", "emojis": [
        "☀️","🌤️","⛅","🌥️","☁️","🌧️","⛈️","🌩️","🌨️","❄️","🌬️","🌪️","🌫️","🌈","🌙","🌕","🌖","🌗","🌘","🌑","🌒","🌓","🌔","⭐","✨","☔"
    ]},
    {"name": "Symbols", "icon": "❤️", "emojis": [
        "❤️","🧡","💛","💚","💙","💜","🖤","🤍","💟","💖","💘","💝","⭕","✅","❌","⚠️","‼️","❓","❗","➡️","⬅️","⬆️","⬇️","↔️","↕️","🔁","♻️","♾️","™️","©️","®️","☮️","⚛️","✝️","☪️","☯️","☸️","✡️"
    ]},
    {"name": "Food & Drink", "icon": "🍎", "emojis": [
        "🍎","🍊","🍋","🍌","🍉","🍇","🍓","🫐","🍒","🍑","🥭","🍍","🥝","🍅","🍆","🥑","🥦","🥬","🥒","🌶️","🧄","🧅","🥔","🍠","🍞","🥐","🥖","🥨","🥯","🧇","🥞","🧈","🧀","🍗","🥩","🥓","🍔","🍟","🍕","🌭","🥪","🌮","🌯","🫔","🥙","🥗","🍝","🍜","🍣","🍱","🍦","🍩","🍪","🎂","🍰","🧁","🍫","🍬","🍭","🍯","☕","🍺"
    ]},
]


def build_layout() -> str:
        """Return the ButtonPad layout string for the UI.

        Layout explanation:
            * First row: 8 unmerged cells each showing a category icon.
            * Remaining 4 rows: 32 unmerged placeholder cells that become emoji.
        We use backtick tokens (`) with text to make label cells.
        """
        # First row: category icons (no-merge) each cell like `😊
        top = ",".join("`" + str(cat["icon"]) for cat in CATEGORIES)
        # Emoji grid rows: placeholder cells (`.) replaced later with actual emojis.
        row = ",".join(["`."] * COLS)
        body = "\n".join([row for _ in range(ROWS - 1)])
        return "\n".join([top, body])


def cycle_fill(emojis: Sequence[str], count: int) -> List[str]:
    """Return 'count' emojis cycling through the given list.

    If the source list is shorter than needed we repeat it; if it's empty we
    return placeholders (empty strings) so the grid can still be drawn.
    """
    if not emojis:
        return [""] * count
    out: List[str] = []
    i = 0
    n = len(emojis)
    for _ in range(count):
        out.append(emojis[i % n])
        i += 1
    return out


def _sanitize_emojis(seq: Sequence[str]) -> List[str]:
    """Return a filtered list without invalid replacement characters.

    Some scraped emoji lists include the Unicode replacement char (�/U+FFFD)
    which we don't want to display. This strips those entries.
    """
    cleaned: List[str] = []
    for s in seq:
        if not s:
            continue
        if "\ufffd" in s or "�" in s:
            continue
        cleaned.append(s)
    return cleaned


def _pick_emoji_font(root) -> str:
    """Choose a suitable emoji-capable font name for the current platform."""
    families = set(tkfont.families(root))
    candidates = []
    if sys.platform == "darwin":
        candidates = ["Apple Color Emoji", "LastResort", "Helvetica"]
    elif sys.platform.startswith("win"):
        candidates = ["Segoe UI Emoji", "Segoe UI Symbol", "Arial Unicode MS"]
    else:
        candidates = ["Noto Color Emoji", "EmojiOne Color", "DejaVu Sans"]
    for name in candidates:
        if name in families:
            return name
    return "TkDefaultFont"


def _emoji_name(s: str) -> str:
    """Return a best-effort human-friendly name for emoji string 's'.

    Strategy:
      1. Try unicodedata.name on the whole string (works for single codepoint).
      2. If that fails and the emoji is a flag sequence (regional indicators),
         build a name like "FLAG: US".
      3. Otherwise join component code point names, skipping joiners & variation
         selectors for readability.
    """
    if not s:
        return ""
    try:
        return _ucd.name(s)
    except Exception:
        pass
    ris = [ord(ch) for ch in s if 0x1F1E6 <= ord(ch) <= 0x1F1FF]
    if ris:  # Potential flag sequence
        try:
            letters = ''.join(chr(65 + (cp - 0x1F1E6)) for cp in ris)
            return f"FLAG: {letters}"
        except Exception:
            pass
    parts: List[str] = []
    for ch in s:
        cp = ord(ch)
        if cp in (0x200D, 0xFE0F):  # ZWJ / variation selector
            continue
        nm = _ucd.name(ch, None)
        if nm:
            parts.append(nm)
    if parts:
        return " + ".join(parts)
    return "emoji"

def copy_emoji(el, _x: int, _y: int) -> None:
    """Copy the emoji in the clicked cell to the system clipboard.

    We try pyperclip (cross-platform convenience). If unavailable we fall
    back to using the Tk root's clipboard methods.
    """
    emoji = el.text
    if pyperclip is not None:  # Try pyperclip first
        try:
            pyperclip.copy(emoji)  # type: ignore[attr-defined]
            return
        except Exception:
            pass
    pad = getattr(el, "_buttonpad", None)  # Fallback: Tk clipboard
    if pad is None:
        return
    try:
        pad.root.clipboard_clear()
        pad.root.clipboard_append(emoji)
        pad.root.update()
    except Exception:
        pass


def show_category(pad, idx: int, grid_cells, emoji_font: str, current: Dict[str, int]) -> None:
    """Fill the emoji grid with the emojis of category index 'idx'."""
    current["index"] = idx
    emojis = CATEGORIES[idx]["emojis"]  # type: ignore[index]
    sanitized = _sanitize_emojis(list(emojis))  # type: ignore[list-item]
    if not sanitized:
        sanitized = ["🙂"]
    flat = cycle_fill(sanitized, (ROWS - 1) * COLS)
    for k, cell in enumerate(grid_cells):
        cell.text = flat[k]
        cell.font_name = emoji_font
        cell.font_size = 22
        cell.on_click = copy_emoji
        try:
            cell.tooltip = _emoji_name(cell.text)  # type: ignore[attr-defined]
        except Exception:
            pass
    try:
        pad.root.update_idletasks()
    except Exception:
        pass


def make_category_handler(pad, idx: int, grid_cells, emoji_font: str, current: Dict[str, int]):
    """Return an on_click handler that switches to category 'idx'."""
    return lambda _el, _x, _y: show_category(pad, idx, grid_cells, emoji_font, current)


def main() -> None:
    """Build the UI, wire handlers, show first category, start event loop."""
    layout = build_layout()
    pad = buttonpad.ButtonPad(
        layout=layout,
        cell_width=48,
        cell_height=48,
        padx=4,
        pady=4,
        border=10,
        title="Emoji Copy to Clipboard Pad",
        default_bg_color=BOTTOM_BG,
        default_text_color="black",
        window_bg_color="#f0f0f0",
        resizable=True,
    )

    # Category buttons (top row) and flat list of emoji cells (remaining rows)
    cat_buttons: List[buttonpad.BPButton] = [pad[x, 0] for x in range(COLS)]  # type: ignore[list-item]
    grid_cells: List[buttonpad.BPButton] = [pad[x, y] for y in range(1, ROWS) for x in range(COLS)]  # type: ignore[list-item]

    # Pick font that can display as many emojis as possible.
    EMOJI_FONT = _pick_emoji_font(pad.root)

    # Style category buttons and add tooltips with category names.
    for x, cat in enumerate(CATEGORIES):
        btn = cat_buttons[x]
        btn.bg_color = TOP_BG
        btn.font_name = EMOJI_FONT
        btn.font_size = 20
        try:
            btn.tooltip = str(cat["name"])  # type: ignore[attr-defined]
        except Exception:
            pass

    current: Dict[str, int] = {"index": 0}  # Track which category is displayed.

    # Attach click handlers to category buttons (switch displayed emoji set).
    for i in range(COLS):
        cat_buttons[i].on_click = make_category_handler(pad, i, grid_cells, EMOJI_FONT, current)

    # Ensure top row shows the category icons.
    for x, cat in enumerate(CATEGORIES):
        cat_buttons[x].text = str(cat["icon"])  # type: ignore[index]
        cat_buttons[x].font_name = EMOJI_FONT

    # Show initial category (index 0) and start the application.
    show_category(pad, 0, grid_cells, EMOJI_FONT, current)
    pad.run()


if __name__ == "__main__":
    main()
