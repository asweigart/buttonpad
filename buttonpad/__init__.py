from __future__ import annotations

__version__ = "0.4.1"

# TODO - be able to attach hotkeys to callback functions on the ButtonPad object.

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union, Any, TYPE_CHECKING
import tkinter as tk
from pymsgbox import (
    # Import with different names so they can be wrapped for refocusing feature.
    alert as _pymsgbox_alert,
    confirm as _pymsgbox_confirm,
    prompt as _pymsgbox_prompt,
    password as _pymsgbox_password,
)
import warnings
import logging
import inspect

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.disable(logging.CRITICAL)

"""NOTE: Since this was vibe coded, there are a lot of places (mostly dealing
with the tkinter library) where there are bare except statements with nothing
but a pass statement. I've replaced them with the following:

logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

...because I want a record of if these exceptions ever actually happen. I
imagine that these try/excepts will be removed or handled with the actual
error handling code later."""

def __LINE__():
    """Return the current line number in our program. Used for logging."""
    return inspect.getframeinfo(inspect.currentframe().f_back).lineno  # type: ignore

def __FUNC__():
    """Return the current function name in our program. Used for logging."""
    return inspect.getframeinfo(inspect.currentframe().f_back).function  # type: ignore


def _normalize_color(value: Optional[Union[str, Tuple[int, int, int], Sequence[int]]]) -> Optional[str]:
    """
    Normalize a color value to a Tk-friendly hex string.

    Accepts:
      - None -> None
      - str (e.g. "#ff0000", "red") -> returned unchanged
      - tuple/list of three ints (r,g,b) where each is 0..255 -> "#rrggbb"

    Returns a string suitable for Tk (or None).
    Raises TypeError/ValueError on clearly invalid inputs.
    """
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, (tuple, list)):
        if len(value) != 3:
            raise ValueError("RGB tuple/list must have length 3")
        try:
            r, g, b = int(value[0]), int(value[1]), int(value[2])
        except Exception as e:
            raise TypeError("RGB components must be integers") from e
        for comp in (r, g, b):
            if comp < 0 or comp > 255:
                raise ValueError("RGB components must be in range 0..255")
        return f"#{r:02x}{g:02x}{b:02x}"
    raise TypeError("color must be a string or an (r,g,b) tuple/list")


# --- Optional macOS support for colorable buttons ---
# This was added because tk.Button on macOS does not support bg/fg color changes.
# Hence we try to load the https://pypi.org/project/tkmacosx/ package if available.
try:
    from tkmacosx import Button as MacButton  # type: ignore
except Exception:
    MacButton = None  # fallback to tk.Button when unavailable

__all__ = [
    "ButtonPad",
    "BPButton",
    "BPLabel",
    "BPTextBox",
    "BPImage",
    # Re-exported pymsgbox helpers
    "alert",
    "confirm",
    "prompt",
    "password",
]

# ---------- widget wrappers ----------

# All widget callbacks receive: (widget_object, x, y)
BPWidgetType = Union["BPButton", "BPLabel", "BPTextBox", "BPImage"]
BPCallbackType = Optional[Callable[["BPWidgetType", int, int], None]]

# Track the last-created Tk root so we can restore focus after dialogs
_last_root: Optional[tk.Tk] = None

def _refocus_root() -> None:
    """Attempt to bring focus back to the most recent ButtonPad window. This is used after PyMsgBox dialogs are closed."""
    try:
        last_root = globals().get("_last_root")
        if last_root is not None and hasattr(last_root, "winfo_exists") and last_root.winfo_exists():
            try:
                last_root.lift()  # Lift the window to the front to ensure visibility
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            try:
                last_root.focus_force()  # Try to force focus back to the window
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
    except Exception:
        logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

def alert(text: str = "", title: str = "PyMsgBox", button: str = "OK") -> Optional[str]:  # type: ignore[override]
    """Wraps the PyMsgBox alert() function. Displays a dialogue box with text and an OK button."""
    result = _pymsgbox_alert(text=text, title=title, button=button)
    _refocus_root()
    return result

def confirm(text: str = "", title: str = "PyMsgBox", buttons: Union[str, Sequence[str]] = ("OK", "Cancel")) -> Optional[str]:  # type: ignore[override]
    """Wraps the PyMsgBox confirm() function. Displays a dialogue box with text and OK/Cancel buttons."""
    result = _pymsgbox_confirm(text=text, title=title, buttons=buttons)
    _refocus_root()
    return result

def prompt(text: str = "", title: str = "PyMsgBox", default: str = "") -> Optional[str]:  # type: ignore[override]
    """Wraps the PyMsgBox prompt() function. Displays a dialogue box with text and an input field."""
    result = _pymsgbox_prompt(text=text, title=title, default=default)
    _refocus_root()
    return result

def password(text: str = "", title: str = "PyMsgBox", default: str = "", mask: str = "*") -> Optional[str]:  # type: ignore[override]
    """Wraps the PyMsgBox password() function. Displays a dialogue box with text and a masked password input field."""
    result = _pymsgbox_password(text=text, title=title, default=default, mask=mask)
    _refocus_root()
    return result


class _BPBase:
    """Base class for the BPButton, BPTextBox, and BPLabel classes."""

    # Runtime-flexible types for Tk widgets and optionally imported PIL objects
    _pos: Tuple[int, int]  # (x,y) position in the pad grid
    _tooltip_text: Optional[str]  # hover tooltip text
    _tooltip_after: Optional[Union[int, str]]  # Tk after ID for tooltip delay
    _tooltip_window: Optional[tk.Toplevel]  # tooltip window if shown
    _pil_image: Any  # Pillow Image object if used (BPImage only)
    _photo: Any  # Tk PhotoImage if used (BPImage only)
    _anchor: str  # alignment for labels, buttons, and text boxes. Example: 'center', 'w', 'e'

    def __init__(
        self,
        widget: tk.Widget,
        text: str = "",
        text_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        bg_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        tooltip: Optional[str] = None,
        anchor: Optional[str] = "center",
        font_name: str = "TkDefaultFont",
        font_size: int = 12,
        on_click: BPCallbackType = None,
        on_enter: BPCallbackType = None,
        on_exit: BPCallbackType = None,
    ) -> None:
        self.widget: tk.Widget = widget
        self._font_name = font_name
        self._font_size = font_size

        # Text handling:
        # - Use textvariable only for widgets known to support it reliably (Label/Entry).
        # - For buttons (tk.Button, tkmacosx Button), set text directly to avoid macOS issues.
        self._text = text
        self._textvar = tk.StringVar(value=text)
        self._uses_textvariable = False
        if isinstance(widget, tk.Label) or isinstance(widget, tk.Entry):
            # Attempt to use a textvariable for live updates
            try:
                self.widget.configure(textvariable=self._textvar) # pyright: ignore[reportCallIssue]
                self._uses_textvariable = True
            except tk.TclError:
                self._uses_textvariable = False
        if not self._uses_textvariable:
            # Fallback for widgets without textvariable (e.g. tkmacosx buttons)
            try:
                self.widget.configure(text=text) # pyright: ignore[reportCallIssue]
            except tk.TclError:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        # Background / text colors: use provided values when non-None, otherwise use
        # widget/system defaults retrieved via widget.cget (best-effort).
        try:
            default_bg = widget.cget("bg")
        except Exception:
            default_bg = "#f0f0f0"
        try:
            default_fg = widget.cget("fg")
        except Exception:
            default_fg = "black"

        # Store and apply background color (if provided)
        self._bg_color = default_bg
        if bg_color is not None:
            try:
                nbg = _normalize_color(bg_color) or bg_color
                try:
                    self.widget.configure(bg=nbg) # pyright: ignore[reportCallIssue]
                    self._bg_color = nbg
                except Exception:
                    # fall back to default already stored
                    pass
            except Exception:
                # invalid color input - ignore and leave default
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: invalid bg_color")

        # Store and apply text color (if provided)
        self._text_color = default_fg
        if text_color is not None:
            try:
                nt = _normalize_color(text_color) or text_color
                try:
                    self.widget.configure(fg=nt) # pyright: ignore[reportCallIssue]
                    self._text_color = nt
                except Exception:
                    # fall back to default already stored
                    pass
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: invalid text_color")

        # text/label/button anchor (left/center/right semantics)
        self._anchor = (anchor or "center")

        # Callback hooks (ButtonPad will invoke these)
        self._on_click: BPCallbackType = on_click
        self._on_enter: BPCallbackType = on_enter
        self._on_exit: BPCallbackType = on_exit

        # hotkey strings (lowercased keysym strings) stored as immutable tuple; None means no hotkeys.
        self._hotkeys: Optional[Tuple[str, ...]] = None

        # Filled in by ButtonPad when placed
        self._pos = (0, 0)
        # Tooltip data (managed by ButtonPad on hover)
        self._tooltip_text = tooltip or None
        # Tk's `after` can return int or str depending on Tcl/Tk build; accept both
        self._tooltip_after = None
        self._tooltip_window = None
        # Optional Pillow runtime storage
        self._pil_image = None
        self._photo = None

    # ----- text (robust across tk / tkmacosx) -----
    @property
    def text(self) -> str:
        """The text displayed by the widget, either the button caption, the label text, or the text in the text box."""
        if self._uses_textvariable:
            try:
                self._text = self._textvar.get()
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        else:
            # If we can read the live widget text, do so
            try:
                self._text = str(self.widget.cget("text"))
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        return self._text

    @text.setter
    def text(self, value: str) -> None:
        self._text = value
        if self._uses_textvariable:
            try:
                self._textvar.set(value)
                return
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        # Fallback for widgets without textvariable (e.g., some tkmacosx buttons)
        try:
            self.widget.configure(text=value) # pyright: ignore[reportCallIssue]
        except tk.TclError:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # ----- tooltip -----
    @property
    def tooltip(self) -> Optional[str]:
        """Optional hover tooltip text. Set to a string to enable; None/'' to disable."""
        return self._tooltip_text

    @tooltip.setter
    def tooltip(self, value: Optional[str]) -> None:
        self._tooltip_text = value or None

    # ----- anchor (alignment for labels, buttons, and text boxes) -----
    @property
    def anchor(self) -> str:
        return getattr(self, "_anchor", "center")

    @anchor.setter
    def anchor(self, value: Optional[str]) -> None:
        # Normalize value
        v = (value or "").strip()
        if not v:
            v = "center"
        self._anchor = v
        # Apply to widgets that support anchor (Label/Button)
        try:
            try:
                self.widget.configure(anchor=v) # pyright: ignore[reportCallIssue]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            # For Text widgets, use tag justification
            if isinstance(self.widget, tk.Text):
                just = "center"
                lv = v.lower()
                if lv in ("w", "left", "west"):
                    just = "left"
                elif lv in ("e", "right", "east"):
                    just = "right"
                try:
                    # configure a persistent tag and apply to all text
                    self.widget.tag_configure("bp_align", justify=just)
                    self.widget.tag_add("bp_align", "1.0", "end")
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # ----- colors -----
    @property
    def bg_color(self) -> str:
        return self._bg_color

    @bg_color.setter
    def bg_color(self, value: Union[str, Tuple[int, int, int], Sequence[int]]) -> None:
        try:
            n = _normalize_color(value) or value
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: invalid color")
            return
        self._bg_color = n
        try:
            self.widget.configure(bg=n) # pyright: ignore[reportCallIssue]
        except tk.TclError:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    @property
    def text_color(self) -> str:
        return self._text_color

    @text_color.setter
    def text_color(self, value: Union[str, Tuple[int, int, int], Sequence[int]]) -> None:
        try:
            n = _normalize_color(value) or value
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: invalid color")
            return
        self._text_color = n
        try:
            self.widget.configure(fg=n) # pyright: ignore[reportCallIssue]
        except tk.TclError:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # ----- font -----
    @property
    def font_name(self) -> str:
        return self._font_name

    @font_name.setter
    def font_name(self, value: str) -> None:
        self._font_name = value
        self._apply_font()

    @property
    def font_size(self) -> int:
        return self._font_size

    @font_size.setter
    def font_size(self, value: int) -> None:
        self._font_size = int(value)
        self._apply_font()

    def _apply_font(self) -> None:
        try:
            self.widget.configure(font=(self._font_name, self._font_size)) # pyright: ignore[reportCallIssue]
        except tk.TclError:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # ----- unified click handler (set by user; fired by ButtonPad) -----
    @property
    def on_click(self) -> BPCallbackType:
        return self._on_click

    @on_click.setter
    def on_click(self, func: BPCallbackType) -> None:
        self._on_click = func

    # ----- unified enter handler -----
    @property
    def on_enter(self) -> BPCallbackType:  # type: ignore[override]
        return self._on_enter

    @on_enter.setter
    def on_enter(self, func: BPCallbackType) -> None:  # type: ignore[override]
        self._on_enter = func

    # ----- unified exit handler -----
    @property
    def on_exit(self) -> BPCallbackType:  # type: ignore[override]
        return self._on_exit

    @on_exit.setter
    def on_exit(self, func: BPCallbackType) -> None:  # type: ignore[override]
        self._on_exit = func

    # ----- hotkey mapping (unified on base) -----
    @property
    def hotkey(self) -> Optional[Tuple[str, ...]]:
        """Get or set keyboard hotkeys for this widget.

        Accepts None, a single string, or a tuple of strings. Keys are normalized to
        lowercase keysyms and mapped via the owning ButtonPad to trigger this
        widget's on_click when pressed.
        """
        return self._hotkeys

    @hotkey.setter
    def hotkey(self, value: Optional[Union[str, Tuple[str, ...]]]) -> None:
        # Remove existing mappings first (only those that point to this widget's pos)
        try:
            pad = getattr(self, "_buttonpad", None)
            if pad is not None and self._hotkeys:
                to_delete = []
                for k in self._hotkeys:
                    pos = pad._keymap.get(k)
                    if pos == getattr(self, "_pos", None):
                        to_delete.append(k)
                for k in to_delete:
                    try:
                        del pad._keymap[k]
                    except Exception:
                        logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        if value is None:
            self._hotkeys = None
            return

        # Normalize to iterable of strings; only allow str or tuple
        if isinstance(value, str):
            keys_iter = [value]
        elif isinstance(value, tuple):
            keys_iter = list(value)
        else:
            raise TypeError("hotkey must be a string, tuple of strings, or None")
        seen = set()
        ordered: List[str] = []
        for k in keys_iter:
            if not isinstance(k, str):
                continue
            kk = k.strip().lower()
            if not kk or kk in seen:
                continue
            seen.add(kk)
            ordered.append(kk)
        self._hotkeys = tuple(ordered) if ordered else None

        # Register with ButtonPad map_key if attached and positioned
        try:
            pad = getattr(self, "_buttonpad", None)
            if pad is not None and self._hotkeys:
                x, y = getattr(self, "_pos", (None, None))
                if x is not None and y is not None:
                    for k in self._hotkeys:
                        pad.map_key(k, x, y)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")


class BPButton(_BPBase):
    def __init__(
        self,
        widget: tk.Widget,
        text: str,
        text_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        bg_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        tooltip: Optional[str] = None,
        anchor: Optional[str] = "center",
        on_click: BPCallbackType = None,
        on_enter: BPCallbackType = None,
        on_exit: BPCallbackType = None,
    ) -> None:
        super().__init__(
            widget,
            text,
            text_color=text_color,
            bg_color=bg_color,
            tooltip=tooltip,
            anchor=anchor,
            on_click=on_click,
            on_enter=on_enter,
            on_exit=on_exit,
        )
        # default click prints text (ButtonPad calls via dispatcher) unless overridden
        if self.on_click is None:
            # Use a bound lambda that prints the current text property
            self.on_click = lambda el, x, y: print(self.text)
    # hotkeys are handled on _BPBase.hotkey


class BPLabel(_BPBase):
    def __init__(
        self,
        widget: tk.Label,
        text: str,
        text_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        bg_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        tooltip: Optional[str] = None,
        anchor: str = "center",
        on_click: BPCallbackType = None,
        on_enter: BPCallbackType = None,
        on_exit: BPCallbackType = None,
    ) -> None:
        super().__init__(
            widget,
            text,
            text_color=text_color,
            bg_color=bg_color,
            tooltip=tooltip,
            anchor=anchor,
            on_click=on_click,
            on_enter=on_enter,
            on_exit=on_exit,
        )
        self._anchor = anchor
        try:
            widget.configure(anchor=anchor) # pyright: ignore[reportArgumentType]
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # --- hotkey property (same semantics as BPButton.hotkey) ---
    # use hotkey on _BPBase


class BPTextBox(_BPBase):
    def __init__(
        self,
        widget: tk.Text,
        text: str,
        text_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        bg_color: Optional[Union[str, Tuple[int, int, int], Sequence[int]]] = None,
        tooltip: Optional[str] = None,
        anchor: Optional[str] = None,
        on_click: BPCallbackType = None,
        on_enter: BPCallbackType = None,
        on_exit: BPCallbackType = None,
    ) -> None:
        # Initialize base without relying on textvariable/text configure
        super().__init__(
            widget,
            text,
            text_color=text_color,
            bg_color=bg_color,
            tooltip=tooltip,
            anchor=anchor,
            on_click=on_click,
            on_enter=on_enter,
            on_exit=on_exit,
        )
        # Ensure initial text is shown in Text widget
        try:
            widget.delete("1.0", "end")
            if text:
                widget.insert("1.0", text)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # Override text property to work with tk.Text (multiline)
    @property  # type: ignore[override]
    def text(self) -> str:  # type: ignore[override]
        try:
            self._text = self.widget.get("1.0", "end-1c")  # pyright: ignore[reportAttributeAccessIssue] # omit trailing newline
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        return self._text

    @text.setter  # type: ignore[override]
    def text(self, value: str) -> None:  # type: ignore[override]
        self._text = value or ""
        try:
            self.widget.delete("1.0", "end") # pyright: ignore[reportAttributeAccessIssue]
            if self._text:
                self.widget.insert("1.0", self._text) # pyright: ignore[reportAttributeAccessIssue]
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # Note: For BPTextBox anchor, only horizontal alignments make sense.
    # Valid values are 'w' (left), 'center', and 'e' (right).

class BPImage(_BPBase):
    """Image widget wrapper created from IMAGE: tokens in the layout.

    Usage in layout:
        IMAGE:cat.png, IMAGE:cat.png  -> a 2x1 merged image frame (merging identical tokens works like buttons/labels)

    image property accepts:
      - str / Path: filename to load
      - Pillow Image object (if Pillow installed)

        Stretch behavior:
            - stretch=False (default): scale image (down or up) to the largest size that fits within the frame while
                preserving aspect ratio.
            - stretch=True: forcibly resize image to exactly the frame size (aspect ratio may change).

    Pillow is optional. Without Pillow only formats supported directly by tk.PhotoImage (e.g. GIF/PNG on many builds) can load,
    and no scaling occurs (unless Pillow is present). Tooltips, bg_color, and on_click/on_enter/on_exit are supported
    the same as other widgets.
    """

    def __init__(self, widget: tk.Label, frame_width: int, frame_height: int):
        super().__init__(widget, text="")
        self._frame_size = (frame_width, frame_height)
        self._image_source: Any = None
        self._pil_image: Any = None
        self._photo: Optional[tk.PhotoImage] = None
        self._stretch: bool = False
        try:
            widget.configure(bg=self._bg_color)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # stretch property
    @property
    def stretch(self) -> bool:
        return self._stretch

    @stretch.setter
    def stretch(self, value: bool) -> None:
        self._stretch = bool(value)
        self._refresh_render()

    # image property
    @property
    def image(self) -> Any:
        return self._image_source

    @image.setter
    def image(self, value: Any) -> None:
        self._image_source = value
        self._load_source(value)
        # Immediate attempt (may be 1x1 before geometry); then schedule another after idle
        self._refresh_render()
        try:
            self.widget.after_idle(self._refresh_render)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _load_source(self, value: Any) -> None:
        self._pil_image = None
        if value is None:
            self._photo = None
            try:
                self.widget.configure(image="") # pyright: ignore[reportCallIssue]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            return
        if isinstance(value, (str, Path)):
            path = Path(str(value))
            if not path.exists():
                return
            try:
                from PIL import Image  # type: ignore
                self._pil_image = Image.open(path)
            except Exception:
                warnings.warn('Pillow is not installed. ButtonPad will not support image scaling.')
                # fallback direct PhotoImage (no scaling)
                try:
                    self._photo = tk.PhotoImage(file=str(path))
                    self.widget.configure(image=self._photo) # pyright: ignore[reportCallIssue]
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            return
        # Attempt treat as PIL Image object
        try:
            from PIL import Image  # type: ignore
            if hasattr(value, "size") and getattr(value.__class__, "__name__", "") == "Image":
                self._pil_image = value
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _refresh_render(self) -> None:
        if self._pil_image is None:
            return
        try:
            from PIL import Image, ImageTk  # type: ignore
        except Exception:
            warnings.warn('Pillow is not installed. ButtonPad will not support image scaling.')
        fw, fh = self._frame_size  # fallback frame size computed at placement or last resize
        try:
            # Use actual widget size if it looks realized (>2px); otherwise fallback to stored frame size
            cur_w = int(self.widget.winfo_width())
            cur_h = int(self.widget.winfo_height())
            if cur_w >= 3 and cur_h >= 3:  # treat tiny (1x1 / 2x2) as not yet laid out
                fw, fh = cur_w, cur_h
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        img = self._pil_image
        iw, ih = img.size
        if self._stretch:
            target_w, target_h = max(1, fw), max(1, fh)
        else:
            # Proportionally fit inside frame (allow upscaling as needed)
            if iw <= 0 or ih <= 0:
                return
            scale = min(fw / iw, fh / ih)
            target_w = max(1, int(round(iw * scale)))
            target_h = max(1, int(round(ih * scale)))
        try:
            resized = img.resize((target_w, target_h), Image.LANCZOS) # type: ignore (LANCZOS is valid, I don't know why Pyrite is complaining here)
        except Exception:
            resized = img
        try:
            self._photo = ImageTk.PhotoImage(resized)
            self.widget.configure(image=self._photo) # pyright: ignore[reportCallIssue]
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _on_container_resize(self, width: int, height: int) -> None:
        self._frame_size = (width, height)
        self._refresh_render()


# ---------- layout & parsing ----------

@dataclass
class _Spec:
    kind: str  # "button" | "label" | "entry" | "image"
    text: str  # for entry, this is initial text
    anchor: Optional[str] = None
    no_merge: bool = False


class ButtonPad:
    def __init__(
        self,
        layout: str,  # """Button, 'Label 1', "Label 2", [Text Box], IMAGE:~/monalisa.png"""
        cell_width: Union[int, Sequence[int]] = 60,  # width of each grid cell in pixels; int for all cells or list of ints for per-column widths
        cell_height: Union[int, Sequence[int]] = 60,  # height of each grid cell in pixels; int for all cells or list of ints for per-row heights
        padx: int = 0,  # horizontal gap/padding between cells in pixels
        pady: int = 0,  # vertical gap/padding between cells in pixels
        window_bg_color: Union[str, Tuple[int, int, int], Sequence[int]] = '#f0f0f0',  # background color of the window
        default_bg_color: Union[str, Tuple[int, int, int], Sequence[int]] = '#f0f0f0',  # default background color for widgets
        default_text_color: Union[str, Tuple[int, int, int], Sequence[int]] = 'black',  # default text color for widgets
        title: str = 'ButtonPad App',  # window title
        resizable: bool = True,  # whether the window is resizable
        border: int = 0,  # padding between the grid and the window edge
        status_bar: Optional[str] = None,  # initial status bar text; None means no status bar
        menu: Optional[Dict[str, Any]] = None,  # menu definition dict; see menu property for details
        font_name: str = "TkDefaultFont",  # default font name for all widgets
        font_size: int = 12,  # default font size for all widgets
    ):
        self._layout = layout
        self._cell_width_input = cell_width
        self._cell_height_input = cell_height
        self.padx = int(padx)
        self.pady = int(pady)
        # Normalize allowed color formats (strings or RGB tuples). Use best-effort so invalid inputs don't crash.
        try:
            self.window_bg_color = _normalize_color(window_bg_color) or window_bg_color
        except Exception:
            self.window_bg_color = window_bg_color
        try:
            self.default_bg_color = _normalize_color(default_bg_color) or default_bg_color
        except Exception:
            self.default_bg_color = default_bg_color
        try:
            self.default_text_color = _normalize_color(default_text_color) or default_text_color
        except Exception:
            self.default_text_color = default_text_color
        self.border = int(border)

        self.root = tk.Tk()
        self.root.title(title)
        # Apply normalized window bg if possible
        try:
            self.root.configure(bg=self.window_bg_color)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        self.root.resizable(resizable, resizable)
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        # Remember last root for post-dialog refocus
        try:
            globals()["_last_root"] = self.root
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        # Optional status bar (created on-demand when status_bar is set)
        self._status_frame = None
        self._status_label = None
        self._status_text = None
        # Defaults: background inherits window background; text inherits default button text color
        self._status_bg_color = self.window_bg_color
        self._status_text_color = self.default_text_color

        # Menu internals
        self._menubar = None
        self._menu_def = None
        self._menu_bindings = []

        # Optional message if macOS without tkmacosx
        if sys.platform == "darwin" and MacButton is None:
            try:
                warnings.warn(
                    "[ButtonPad] tkmacosx not found; using tk.Button (colors may not update on macOS). "
                    "Install with: pip install tkmacosx",
                    RuntimeWarning,
                )
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        # Default font for all widgets
        self._default_font_name = font_name
        self._default_font_size = font_size

    
        # Outer container; border controls padding to window edges
        self._container = tk.Frame(self.root, bg=self.window_bg_color)
        self._container.pack(padx=self.border, pady=self.border, fill="both", expand=True)

        # storage: keyed by (x, y) == (col, row)
        self._cell_to_widget = {}
        self._widgets = []
        self._destroyed = False

        # global click hooks (user sets these) — receive the widget wrapper
        self.on_pre_click = None
        self.on_post_click = None

        # keyboard mapping: keysym(lowercased) -> (x, y)
        self._keymap = {}
        # Bind globally so focus doesn't matter; handle both forms for robustness
        self.root.bind_all("<Key>", self._on_key)
        self.root.bind_all("<KeyPress>", self._on_key)

        # Build initial grid
        self._build_from_config(layout)

        # Initialize status bar if requested
        if status_bar is not None:
            try:
                self.status_bar = str(status_bar)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        # Initialize menu if provided
        if menu:
            try:
                self.menu = menu
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    @property
    def layout(self) -> str:
        """Get or set the raw layout string used to build the grid.

        Reading returns the original configuration string passed to the constructor
        or last assigned value. Assigning a new string will rebuild the UI.
        """
        return self._layout

    @layout.setter
    def layout(self, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError("layout must be a string")
        # use update() to rebuild from the new configuration
        self.update(value)

    # ----- status bar API -----
    @property
    def status_bar(self) -> Optional[str]:
        """Get or set the text shown in a bottom status bar.

        - None (default) means no status bar is shown.
        - Setting to a string shows/updates a bottom status bar with that text.
        - Setting to None removes the status bar widget.
        """
        return self._status_text

    @status_bar.setter
    def status_bar(self, value: Optional[str]) -> None:
        # Normalize: empty string still shows an empty bar; None removes it
        if value is None:
            self._status_text = None
            # Destroy if exists
            if self._status_frame is not None:
                try:
                    self._status_frame.destroy()
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            self._status_frame = None
            self._status_label = None
            return

        # Ensure frame/label exist
        self._status_text = str(value)
        if self._status_frame is None or self._status_label is None:
            try:
                frame = tk.Frame(self.root, bg=self._status_bg_color, bd=1, relief="sunken")
                # Place at bottom; allow main container to expand above it
                frame.pack(side="bottom", fill="x")
                label = tk.Label(
                    frame,
                    text=self._status_text,
                    anchor="w",
                    bg=self._status_bg_color,
                    fg=self._status_text_color,
                    padx=6,
                    pady=2,
                )
                label.pack(side="left", fill="x", expand=True)
                self._status_frame = frame
                self._status_label = label
            except Exception:
                # If creation fails, just keep the text state; no hard crash
                self._status_frame = None
                self._status_label = None
                return

        # Update text if already created
        try:
            if self._status_label is not None:
                self._status_label.configure(text=self._status_text)
                # also ensure colors are in sync
                try:
                    self._status_label.configure(bg=self._status_bg_color, fg=self._status_text_color)
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            if self._status_frame is not None:
                try:
                    self._status_frame.configure(bg=self._status_bg_color)
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    @property
    def status_bar_bg_color(self) -> str:
        """Background color for the status bar. Defaults to window_bg_color."""
        return self._status_bg_color

    @status_bar_bg_color.setter
    def status_bar_bg_color(self, value: Union[str, Tuple[int, int, int], Sequence[int]]) -> None:
        try:
            self._status_bg_color = _normalize_color(value) or str(value)
        except Exception:
            self._status_bg_color = str(value)
        # Update live widgets if present
        if self._status_frame is not None:
            try:
                self._status_frame.configure(bg=self._status_bg_color)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        if self._status_label is not None:
            try:
                self._status_label.configure(bg=self._status_bg_color)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    @property
    def status_bar_text_color(self) -> str:
        """Text color for the status bar. Defaults to default_button_text_color."""
        return self._status_text_color

    @status_bar_text_color.setter
    def status_bar_text_color(self, value: Union[str, Tuple[int, int, int], Sequence[int]]) -> None:
        try:
            self._status_text_color = _normalize_color(value) or str(value)
        except Exception:
            self._status_text_color = str(value)
        if self._status_label is not None:
            try:
                self._status_label.configure(fg=self._status_text_color)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    # ----- menu API -----
    @property
    def menu(self) -> Optional[Dict[str, Any]]:
        """Get or set the menu definition dict.
        Structure:
          {
            "File": { "Open": func, "Quit": (func, "Ctrl+Q") },
            "Help": { "About": func },
            "Reload": func  # command directly on the menubar
          }
        A value can be:
          - callable -> command
          - (callable, accelerator_str) -> command with displayed accelerator and key binding
          - dict -> submenu (recursively parsed)
        """
        return getattr(self, "_menu_def", None)

    @menu.setter
    def menu(self, value: Optional[Dict[str, Any]]) -> None:
        # Clear existing
        self._menu_clear()
        self._menu_def = None
        if not value:
            return
        # Build new menubar
        try:
            menubar = tk.Menu(self.root)
            self._menu_build_recursive(menubar, value)
            self.root.config(menu=menubar)
            self._menubar = menubar
            self._menu_def = value
        except Exception:
            # Best-effort: leave no menu if building fails
            try:
                self.root.config(menu="")
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            self._menubar = None
            self._menu_def = None

    # -- menu helpers --
    def _menu_clear(self) -> None:
        # Unbind previous accelerators
        binds = getattr(self, "_menu_bindings", [])
        for seq in binds:
            try:
                self.root.unbind_all(seq)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        self._menu_bindings = []
        # Remove existing menubar
        if getattr(self, "_menubar", None) is not None:
            try:
                self.root.config(menu="")
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            try:
                self._menubar.destroy()
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        self._menubar = None

    def _menu_build_recursive(self, menu_widget: tk.Menu, definition: Dict[str, Any]) -> None:
        for label, spec in definition.items():
            if isinstance(spec, dict):
                # Submenu
                submenu = tk.Menu(menu_widget, tearoff=0)
                self._menu_build_recursive(submenu, spec)
                menu_widget.add_cascade(label=label, menu=submenu)
            else:
                cmd, accel_text, bind_seq = self._coerce_menu_item(spec)
                if cmd is None:
                    # skip invalid entries silently
                    continue
                if accel_text:
                    try:
                        menu_widget.add_command(label=label, command=cmd, accelerator=accel_text)
                    except Exception:
                        menu_widget.add_command(label=label, command=cmd)
                else:
                    menu_widget.add_command(label=label, command=cmd)
                # Bind accelerator sequence
                if bind_seq:
                    self._menu_bind_accel(bind_seq, cmd)

    def _coerce_menu_item(self, spec: Any) -> Tuple[Optional[Callable[[], None]], Optional[str], Optional[str]]:
        func: Optional[Callable[[], None]] = None
        accel: Optional[str] = None
        if callable(spec):
            func = lambda f=spec: f()
        elif isinstance(spec, tuple) and len(spec) >= 1 and callable(spec[0]):
            func = lambda f=spec[0]: f()
            if len(spec) >= 2 and isinstance(spec[1], str):
                accel = spec[1]
        else:
            return (None, None, None)
        seq = self._parse_accelerator(accel) if accel else None
        return (func, accel, seq)

    def _menu_bind_accel(self, seq: str, func: Callable[[], None]) -> None:
        try:
            self.root.bind_all(seq, lambda e: func())
            self._menu_bindings.append(seq)
            # If Command on non-mac, also bind Control variant for convenience
            if "Command" in seq and sys.platform != "darwin":
                ctrl_seq = seq.replace("Command", "Control")
                self.root.bind_all(ctrl_seq, lambda e: func())
                self._menu_bindings.append(ctrl_seq)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _parse_accelerator(self, accel: str) -> Optional[str]:
        if not accel:
            return None
        parts = [p.strip() for p in accel.replace("+", "-").split("-") if p.strip()]
        if not parts:
            return None
        mods_map = {
            "ctrl": "Control", "control": "Control",
            "cmd": "Command", "command": "Command",
            "alt": "Alt", "option": "Alt",
            "shift": "Shift",
        }
        key = parts[-1]
        mods = [mods_map.get(p.lower(), None) for p in parts[:-1]]
        mods = [m for m in mods if m]
        # Normalize key
        named = {
            "enter": "Return", "return": "Return",
            "esc": "Escape", "escape": "Escape",
            "space": "space",
            "left": "Left", "right": "Right", "up": "Up", "down": "Down",
            "tab": "Tab", "backspace": "BackSpace", "delete": "Delete",
        }
        if len(key) == 1:
            ksym = key.lower()
        else:
            ksym = named.get(key.lower(), key)
        seq = "<" + ("-".join(mods + [ksym])) + ">" if mods else f"<{ksym}>"
        return seq

    # ----- public API -----
    def run(self) -> None:
        self.root.mainloop()

    def quit(self) -> None:
        """Quit the application and destroy the window (idempotent)."""
        if self._destroyed:
            return
        try:
            self.root.quit()
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            self.root.destroy()
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        self._destroyed = True

    def update(self, new_configuration: str) -> None:
        """Rebuild the layout with a new configuration string."""
        self._layout = new_configuration
        # destroy old widgets except the container/root
        for w in self._widgets:
            try:
                w.destroy()
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        self._widgets.clear()
        self._cell_to_widget.clear()

        self._build_from_config(new_configuration)

    # Public accessor uses Cartesian order: [x, y]
    def __getitem__(self, key: Tuple[int, int]) -> BPWidgetType:
        return self._cell_to_widget[tuple(key)]

    def map_key(self, key: str, x: int, y: int) -> None:
        """
        Map a keyboard key to trigger the widget at (x, y).
        `key` should be a Tk keysym (e.g., "1", "a", "Escape", "space", "Return").
        """
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string (Tk keysym).")
        self._keymap[key.lower()] = (int(x), int(y))

    # ----- internals -----
    def _on_key(self, event) -> None:
        # Some Tk builds omit keysym for synthetic events; fall back to char.
        ks = ""
        if getattr(event, "keysym", None):
            ks = event.keysym
        elif getattr(event, "char", None):
            ks = event.char
        ks = (ks or "").lower()
        if not ks:
            return
        pos = self._keymap.get(ks)  # (x, y)
        if pos is None:
            return
        widget = self._cell_to_widget.get(pos)  # keyed by (x, y)
        if widget is not None:
            self._fire_click(widget)

    def _fire_click(self, widget: BPWidgetType) -> None:
        """Invoke pre->on_click->post sequence safely, delivering (widget, x, y)."""
        x, y = widget._pos  # set during placement
        # Hide tooltip upon click
        try:
            self._tooltip_hide(widget)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            if self.on_pre_click:
                self.on_pre_click(widget)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            if widget.on_click:
                widget.on_click(widget, x, y)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            if self.on_post_click:
                self.on_post_click(widget)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _fire_enter(self, widget: BPWidgetType) -> None:
        x, y = widget._pos
        # Schedule tooltip show if present
        try:
            self._tooltip_schedule(widget)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            if widget.on_enter:
                widget.on_enter(widget, x, y)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _fire_exit(self, widget: BPWidgetType) -> None:
        x, y = widget._pos
        # Hide tooltip on exit
        try:
            self._tooltip_hide(widget)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        try:
            if widget.on_exit:
                widget.on_exit(widget, x, y)
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
    # The remainder (_tooltip helpers, build_from_config, _place_widget, parser, etc.) remain unchanged.
    # ...existing methods continue unchanged...
    def _tooltip_schedule(self, widget: BPWidgetType) -> None:
        text = getattr(widget, "_tooltip_text", None)
        if not text:
            return
        # cancel previous timer
        after_id = getattr(widget, "_tooltip_after", None)
        if after_id:
            try:
                self.root.after_cancel(after_id)  # type: ignore[arg-type]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        widget._tooltip_after = self.root.after(350, lambda e=widget: self._tooltip_show(e))

    def _tooltip_show(self, widget: BPWidgetType) -> None:
        text = getattr(widget, "_tooltip_text", None)
        if not text:
            return
        tw = getattr(widget, "_tooltip_window", None)
        if tw is None:
            tw = tk.Toplevel(self.root)
            tw.wm_overrideredirect(True)
            try:
                tw.attributes("-topmost", True)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            frame = tk.Frame(tw, bg="#333333", bd=0, highlightthickness=0)
            frame.pack(fill="both", expand=True)
            label = tk.Label(frame, text=text, bg="#333333", fg="white", padx=6, pady=3, justify="left")
            label.pack()
            widget._tooltip_window = tw
        else:
            # update text
            try:
                for child in tw.winfo_children():
                    for gc in child.winfo_children():
                        if isinstance(gc, tk.Label):
                            gc.configure(text=text)
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        # position near mouse pointer
        try:
            x = self.root.winfo_pointerx() + 12
            y = self.root.winfo_pointery() + 16
            tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    def _tooltip_hide(self, widget: BPWidgetType) -> None:
        after_id = getattr(widget, "_tooltip_after", None)
        if after_id:
            try:
                self.root.after_cancel(after_id)  # type: ignore[arg-type]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        widget._tooltip_after = None
        tw = getattr(widget, "_tooltip_window", None)
        if tw is not None:
            try:
                tw.destroy()
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        widget._tooltip_window = None

    def _build_from_config(self, configuration: str) -> None:
        grid_specs = self._parse_configuration(configuration)

        # Detect non-rectangular layouts (rows with differing numbers of cells)
        row_lengths = [len(r) for r in grid_specs]
        self._row_cell_counts = row_lengths  # expose for introspection/debug
        if row_lengths:
            max_len = max(row_lengths)
            if any(l != max_len for l in row_lengths):
                try:
                    warnings.warn(
                        (
                            "[ButtonPad] Non-rectangular layout detected. "
                            f"Row cell counts: {row_lengths} (max columns = {max_len}). "
                            "Shorter rows will leave unused empty space."
                        ),
                        RuntimeWarning,
                    )
                except Exception:
                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

        rows = len(grid_specs)
        cols = max((len(r) for r in grid_specs), default=0)

        # Resolve column widths / row heights from input (int or sequence)
        self.column_widths = self._resolve_sizes(self._cell_width_input, cols, "cell_width/columns")
        self.row_heights = self._resolve_sizes(self._cell_height_input, rows, "cell_height/rows")

        # Configure the grid geometry manager with per-row/col sizes
        for r in range(rows):
            self._container.rowconfigure(r, minsize=self.row_heights[r], weight=1)
        for c in range(cols):
            self._container.columnconfigure(c, minsize=self.column_widths[c], weight=1)

        # Determine merged rectangles
        assigned = [[False] * cols for _ in range(rows)]
        for r in range(rows):
            for c in range(len(grid_specs[r])):
                if assigned[r][c]:
                    continue
                spec = grid_specs[r][c]
                if spec is None:
                    continue

                if spec.no_merge:
                    self._place_widget(r, c, 1, 1, spec)
                    assigned[r][c] = True
                else:
                    r2, c2 = self._max_rectangle(grid_specs, r, c)
                    self._place_widget(r, c, r2 - r + 1, c2 - c + 1, spec)
                    for rr in range(r, r2 + 1):
                        for cc in range(c, c2 + 1):
                            assigned[rr][cc] = True

        # Ensure a deterministic focus target so Key events route consistently
        try:
            self._container.focus_set()
        except Exception:
            logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")

    @staticmethod
    def _resolve_sizes(val: Union[int, Sequence[int]], n: int, what: str) -> List[int]:
        if n <= 0:
            return []
        # int => uniform sizes
        if isinstance(val, int):
            return [int(val)] * n
        # sequence => must match length n
        try:
            seq = list(val)  # type: ignore[arg-type]
        except Exception as e:
            raise TypeError(f"{what} must be int or sequence of ints") from e
        if len(seq) != n:
            raise ValueError(f"Length of {what} sequence must match {n}; got {len(seq)}")
        sizes: List[int] = []
        for x in seq:
            if not isinstance(x, int):
                raise TypeError(f"{what} sequence must contain ints; got {type(x).__name__}")
            sizes.append(int(x))
        return sizes

    def _max_rectangle(self, grid: List[List[Optional[_Spec]]], r: int, c: int) -> Tuple[int, int]:
        rows = len(grid)
        base = grid[r][c]
        if base is None:
            return (r, c)

        # grow rightwards while same spec and within row length
        max_c = c
        while True:
            nc = max_c + 1
            if nc >= len(grid[r]):
                break
            cell = grid[r][nc]
            if not self._merge_compatible(base, cell):
                break
            max_c = nc

        # grow downward ensuring each new row has the whole horizontal run identical
        max_r = r
        while True:
            nr = max_r + 1
            if nr >= rows:
                break
            if len(grid[nr]) <= max_c:
                break
            row_ok = True
            for cc in range(c, max_c + 1):
                if not self._merge_compatible(base, grid[nr][cc]):
                    row_ok = False
                    break
            if not row_ok:
                break
            max_r = nr

        return (max_r, max_c)

    @staticmethod
    def _merge_compatible(a: Optional[_Spec], b: Optional[_Spec]) -> bool:
        if a is None or b is None:
            return False
        if a.no_merge or b.no_merge:
            return False
        return (a.kind == b.kind) and (a.text == b.text) and (a.anchor == b.anchor)

    def _place_widget(self, r: int, c: int, rowspan: int, colspan: int, spec: _Spec) -> None:
        # Compute fixed pixel size of the merged cell from per-row/col sizes
        width = sum(self.column_widths[c: c + colspan])
        height = sum(self.row_heights[r: r + rowspan])

        # Each cell/merged region gets a frame; paddings apply here
        frame = tk.Frame(
            self._container,
            width=width,
            height=height,
            bg=self.window_bg_color,
            highlightthickness=0,
            bd=0,
        )
        frame.grid(
            row=r,
            column=c,
            rowspan=rowspan,
            columnspan=colspan,
            padx=self.padx // 2,
            pady=self.pady // 2,
            sticky="nsew",
        )
        frame.grid_propagate(False)

        if spec.kind == "button":
            ButtonCls = MacButton if (sys.platform == "darwin" and MacButton is not None) else tk.Button
            extra_kwargs = {}
            if ButtonCls is MacButton:
                extra_kwargs.update({"borderless": 1, "focuscolor": ""})
            w = ButtonCls(
                frame,
                text=spec.text,
                bg=self.default_bg_color,
                fg=self.default_text_color,
                anchor="center",
                justify="center",
                padx=0,
                pady=0,
                bd=0,
                relief="flat",
                highlightthickness=0,
                **extra_kwargs,
            )
            w.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            widget: BPWidgetType = BPButton(w, text=spec.text)
            try:
                widget._buttonpad = self  # type: ignore[attr-defined]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            w.configure(command=lambda e=widget: self._fire_click(e)) # pyright: ignore[reportCallIssue]

        elif spec.kind == "label":
            w = tk.Label(
                frame,
                text=spec.text,
                bg=self.window_bg_color,
                fg="black",
                anchor=spec.anchor or "center",
                padx=0,
                pady=0,
                highlightthickness=0,
            )
            w.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            widget = BPLabel(w, text=spec.text, anchor=spec.anchor or "center")
            try:
                widget._buttonpad = self  # type: ignore[attr-defined]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            w.bind("<ButtonRelease-1>", lambda evt, e=widget: self._fire_click(e))

        elif spec.kind == "entry":
            w = tk.Text(
                frame,
                relief="sunken",
                highlightthickness=0,
                wrap="word",
                bd=1,
                bg=self.default_bg_color,     # match other widgets
                fg=self.default_text_color,   # match other widgets
                insertbackground=self.default_text_color,  # cursor color on some platforms
            )
            w.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            widget = BPTextBox(w, text=spec.text)
            try:
                widget._buttonpad = self  # type: ignore[attr-defined]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            w.bind("<ButtonRelease-1>", lambda evt, e=widget: self._fire_click(e))

        elif spec.kind == "image":
            w = tk.Label(
                frame,
                text="",
                bg=self.default_bg_color,
                fg=self.default_text_color,
                anchor="center",
                padx=0,
                pady=0,
                highlightthickness=0,
                bd=0,
            )
            w.place(relx=0, rely=0, relwidth=1.0, relheight=1.0)
            widget = BPImage(w, frame_width=width, frame_height=height)
            try:
                widget._buttonpad = self  # type: ignore[attr-defined]
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            w.bind("<ButtonRelease-1>", lambda evt, e=widget: self._fire_click(e))
            try:
                frame.bind("<Configure>", lambda evt, e=widget: e._on_container_resize(evt.width, evt.height))
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            # Auto-load image if token suffix references an existing file (absolute, ~, or relative).
            try:
                token = spec.text  # e.g. IMAGE:cat.png or IMAGE:/abs/path/to/img.png or IMAGE:~/pic.png
                if token.startswith("IMAGE:"):
                    fname = token[6:].strip()
                    if fname:
                        # Expand ~ to home directory if present
                        expanded = str(Path(fname).expanduser())
                        p = Path(expanded)
                        if p.is_absolute():
                            # Absolute path (including ~ expanded): use as-is
                            if p.exists():
                                try:
                                    widget.image = p
                                except Exception:
                                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
                        else:
                            # Relative path: only try CWD
                            cwd_p = Path.cwd() / expanded
                            if cwd_p.exists():
                                try:
                                    widget.image = cwd_p
                                except Exception:
                                    logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
            except Exception:
                logging.debug(f"Ignored exception in {__FUNC__()} at line {__LINE__()}, version {__version__}: {sys.exc_info()[1]}")
        else:
            raise ValueError(f"Unknown spec kind: {spec.kind}")

        widget._pos = (c, r)
        w.bind("<Enter>", lambda evt, e=widget: self._fire_enter(e))
        w.bind("<Leave>", lambda evt, e=widget: self._fire_exit(e))
        for rr in range(r, r + rowspan):
            for cc in range(c, c + colspan):
                self._cell_to_widget[(cc, rr)] = widget
        self._widgets.append(frame)
        self._widgets.append(widget.widget)

    # ----- config parsing -----
    def _parse_configuration(self, configuration: str) -> List[List[Optional[_Spec]]]:
        rows: List[List[Optional[_Spec]]] = []
        # Iterate raw lines; ignore any that are blank or only whitespace so layout authors
        # can add visual spacing without creating empty rows.
        for rline in configuration.splitlines():
            if not rline.strip():
                continue  # skip blank/whitespace-only line
            raw_items = rline.split(",")
            row: List[Optional[_Spec]] = []
            for token in raw_items:
                tok = token.strip()
                if tok == "":
                    # treat as an empty button to preserve a cell
                    row.append(_Spec(kind="button", text="", no_merge=False))
                    continue

                no_merge = tok.startswith("`")
                if no_merge:
                    tok = tok[1:].lstrip()

                # label?
                if ((len(tok) >= 2) and ((tok[0] == tok[-1]) and tok[0] in ("'", '"'))) or tok.startswith("LABEL:"):
                    if tok.startswith("LABEL:"):
                        text = tok[6:].lstrip()
                    else:
                        text = tok[1:-1]
                    row.append(_Spec(kind="label", text=text, anchor="center", no_merge=no_merge))
                    continue

                # text box?
                if (tok.startswith("[") and tok.endswith("]")) or (tok.startswith("TEXTBOX:")):
                    if tok.startswith("TEXTBOX:"):
                        text = tok[8:].lstrip()
                    else:
                        text = tok[1:-1]
                    row.append(_Spec(kind="entry", text=text, no_merge=no_merge))
                    continue

                # image token (IMAGE:) 
                if tok.startswith("IMAGE:"):
                    row.append(_Spec(kind="image", text=tok, no_merge=no_merge))
                    continue

                # plain button
                if tok.startswith("BUTTON:"):
                    tok = tok[7:].lstrip()
                row.append(_Spec(kind="button", text=tok, no_merge=no_merge))
            rows.append(row)
        return rows
