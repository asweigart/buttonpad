# ButtonPad

ButtonPad lets you create a GUI of a grid of buttons, labels, text boxes, and images using a compact, CSV-like layout string and control it with simple Python callbacks. It’s built on the Tkinter standard library and works on Windows, macOS, and Linux. (On macOS, it optionally uses tkmacosx for better button color support.)

For example, this layout string is for a calculator app:

```
LAYOUT = """
'','','',''
C,(,),⌫
7,8,9,÷
4,5,6,x
1,2,3,-
0,.,=,+
"""
```

Keep in mind that the text on buttons and labels can include emoji!

Key features:

* Pure-Python code that only depends on the standard library, built on top of tkinter. (Pillow is optional.)
* A CSV-like layout configuration string generates the grid of widgets.
* Callback functions handle click, enter, and exit events.
* Each widget can be assigned tool tip text, hotkey mappings, and custom font and colors.
* Optional status bar with custom colors.
* Optional menubar configuration.
* Adjustable per-column/row sizing, margins, borders, and resizable windows
* PyMsgBox dialog boxes: `alert()`, `confirm()`, `prompt()`, `password()`


## Check Out Demo Programs with the Launcher

Run `python -m buttonpad` to run the launcher program to view several demo programs and games made with Buttonpad. The source code for these demo programs can be found at [https://github.com/asweigart/buttonpad/tree/main/buttonpad](https://github.com/asweigart/buttonpad/tree/main/buttonpad)

![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-2048.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-calc.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-conway.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-eightqueens.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-emoji.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-lightsout.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-magic8ball.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-samegame.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-slide.webp)
![Screenshot](https://raw.githubusercontent.com/asweigart/buttonpad/main/screenshot-stopwatch.webp)





## Quick Start Example Code

Here's a complete program for a simulated keypad. By default, buttons print their text with `print()`:

```python
# Phone keypad example
import buttonpad

# Multi-line string defines 4 rows of 3 cells each (a 3x4 grid).
bp = buttonpad.ButtonPad(
    """[],[],[]
    1,2,3
    4,5,6
    7,8,9
    *,0,#
    Call,Call,Cancel""",
)

bp.run()  # run the app
```

The buttonpad grid is split by commas and newlines.

The top row has empty square brackets to create an empty text box. Since all three have the same text (nothing), they are merged into one 3x1 text box.

Text without square brackets create buttons with the text as the button text.

The bottom row has two "Call" text which merges into a single 2x1 button labelled "Call". The default click callback function prints the label of the button. Here's an expanded version:

```python
# Phone keypad example
import buttonpad

# Multi-line string defines 4 rows of 3 cells each (a 3x4 grid).
bp = buttonpad.ButtonPad(
	"""[],[],[]
    1,2,3
	4,5,6
	7,8,9
	*,0,#
	Call,Call,Cancel""",
	cell_width=100,  # width of each cell, in pixels
	cell_height=60,  # height of each cell, in pixels
	padx=10,  # horizontal padding in between cells, in pixels
	pady=5,  # vertical padding in between cells, in pixels
	border=20,  # padding at the edges of the window, in pixels
	default_bg_color='lightblue',  # background color of widgets (buttons, etc)
	default_text_color='darkblue', # color of widget text
	window_bg_color='whitesmoke',  # background color of the window
	title="Telephone Keypad Demo",  # title text of the app window
)

# Callback functions receive three arguments: the widget object that
# was clicked/entered/exited, and the xy position of the widget in the
# buttonpad grid.

# Create callback functions for the buttons:
def cancel_call(widget, x, y):
    bp[0,0].text = ''  # Clear the display

def call_number(widget, x, y):
    buttonpad.alert("Simulate calling " + bp[0,0].text)  # Show alert dialog

def add_button_label_to_display(widget, x, y):
    bp[0, 0].text += widget.text  # Append the pressed key to the display

# Assign callbacks to buttons:
for x in range(3):
    for y in range(1, 5):  # rows 1-4 contain keys 1..9,*,0,#
        bp[x,y].on_click = add_button_label_to_display

bp[2, 5].on_click = cancel_call  # Cancel button

bp[0, 5].on_click = call_number  # Call button

bp[0, 0].font_size = 24  # Make the display text larger

bp.run()  # run the app
```

ButtonPad color values are strings of [tkinter color names](https://inventwithpython.com/blog/complete-list-tkinter-colors-valid-and-tested.html), in `'#ff00ff'` style of RGB value, or as a tuple of three RGB integers like `(255, 0, 0)`.

## Configuring the GUI with a Layout String

The multiline string of comma-separated widgets in ButtonPad is called the *layout string*: commas separate columns, newlines separate rows. You can specify different user interface (UI) widgets in this string:

- Buttons: any unquoted text, e.g. `A`, `Click`, `7` (or prefixed with `BUTTON:`)
- Label: uneditable text enclosed in single or double quotes, e.g. `'Hello'` or `"Ready"` (or prefix with `LABEL:`)
- Text box (multiline and editable): text enclosed in square brackets, e.g. `[Name]` (or prefix with `TEXTBOX:`)
- Image: Prefix with `IMAGE:` followed by the image filename.

Widgets with the same text in a rectangular area in the layout string will be merged into a single widget. If you want to have separate, unmerged widgets with the same name, put a backtick prefix.

For example, this creates a top row with three buttons (labelled "A", "B", and "C"). The second row is a single wide, 3x1 cell button labelled "Play". The third row has two text labels that say "Status" and "Enabled", next to a text box with the placeholder text, "Name". The bottom row has three separate buttons, each labelled "Start":

```
A,B,C
Play,Play,Play
"Status","Enabled",[Name]
`Start,`Start,`Start
```

TODO: Add feature to allow escape characters so commas can be the text. Also check that a backtick prefix before a "BUTTON:" prefix still works.


## Setting Event Callback Functions for Click, Enter, and Exit Handlers

Callback functions receive three arguments: the widget object that was clicked/entered/exited, and the xy position of the widget in the buttonpad grid.



## Extra Widget Features: Tooltips, Custom Colors, Custom Fonts, Hotkeys

Widgets (buttons, text boxes, etc.) have the following attributes that you can change:

* `text` - The text label or text contents of the widget.
* `tooltip` - The tooltip text that appears when the mouse cursor hovers over the widget.
* `text_color` - The color of the text label or text contents.
* `bg_color` - The background color of the widget.
* `font_name` - Set the font of the widget text.
* `font_size` - Set the font size of the widget text.
* `anchor` - Set the alignment of the widget text; same as tkinter values: `'n'` or `'s'` or `'center'`, etc.
* `hotkey` - Set a string or tuple of strings to create independent hotkeys (case-insensitive).

## Extra Window Features: Resizeable Windows, Status Bar, and Menu Bar

TODO

## API

### ButtonPad

Constructor:

```python
    def __init__(
        self,
        layout: str,  # """Button, 'Label 1', "Label 2", [Text Box], IMAGE:~/monalisa.png"""
        cell_width: Union[int, Sequence[int]] = 60,  # width of each grid cell in pixels; int for all cells or list of ints for per-column widths
        cell_height: Union[int, Sequence[int]] = 60,  # height of each grid cell in pixels; int for all cells or list of ints for per-row heights
        padx: int = 0,  # horizontal gap/padding between cells in pixels
        pady: int = 0,  # vertical gap/padding between cells in pixels
        window_bg_color: str = '#f0f0f0',  # background color of the window
        default_bg_color: str = '#f0f0f0',  # default background color for widgets
        default_text_color: str = 'black',  # default text color for widgets
        title: str = 'ButtonPad App',  # window title
        resizable: bool = True,  # whether the window is resizable
        border: int = 0,  # padding between the grid and the window edge
        status_bar: Optional[str] = None,  # initial status bar text; None means no status bar
        menu: Optional[Dict[str, Any]] = None,  # menu definition dict; see menu property for details
    ):
```

Notes:
- `cell_width`/`cell_height` can be a single int (uniform) or a list matching the number of columns/rows.
- `padx`/`pady` set the internal spacing between cells; `border` is outer margin.
- The window is resizable by default.

Instance methods and properties:
- `run()` — start the Tkinter event loop.
- `quit()` — quit the program.
- `update(new_layout: str)` — rebuild the grid from a new layout string.
- `[x, y]` — index into the grid to get an element wrapper at column x, row y.
- Status bar: `status_bar` (string or None) plus `status_bar_bg_color`, `status_bar_text_color`.
- Menu: assign a nested dict to `menu` to build a menubar with optional accelerators.
- Global hooks: `on_pre_click(element)`, `on_post_click(element)` called around every click.

Re-exported dialogs from pymsgbox: 
- `alert(text: str = "", title: str = "PyMsgBox", button: str = "OK")` - Displays a message.
- `confirm(text: str = "", title: str = "PyMsgBox", buttons: Union[str, Sequence[str]] = ("OK", "Cancel"))` - Displays OK/Cancel box and returns selection.
- `prompt(text: str = "", title: str = "PyMsgBox", default: str = "")` - Lets user type a resonse and returns it.
- `password(text: str = "", title: str = "PyMsgBox", default: str = "", mask: str = "*")` - Like `prompt()` but hides the typed characters.


If [Pillow](https://pypi.org/project/pillow/) isn't installed, then the image widget is shown in its grid cell at its normal size. If Pillow is installed, then ButtonPad automatically resizes it to fit proportionately in its cell. (You can also have it stretch to always fill the cell by setting the image widget's `stretch` attribute to `True`.


## Keyboard Mapping

Map keys to cells with `map_key`. Keys are Tk keysyms (case-insensitive): `"1"`, `"a"`, `"space"`, `"Return"`, `"Escape"`, etc.

```python
pad.map_key("1", 0, 0)
pad.map_key("space", 1, 0)
```


## Platform Notes

- macOS: For fully colorable buttons, install `tkmacosx`. When unavailable, ButtonPad falls back to the system `tk.Button` (colors may not update on some macOS builds). You’ll see a console message suggesting: `pip install tkmacosx`.
- Dialog helpers use `pymsgbox` and are re-exported for convenience.

## Road Map

- Complete type hints and doc strings
- Checkboxes / "Toggle" buttons
- Slider
