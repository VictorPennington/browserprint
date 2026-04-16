---
name: toga-api
description: "Use when writing or reviewing Toga UI code: widgets, layout, windows, dialogs, the Pack style engine, event handlers, or app startup. Covers the full Toga 0.5.3 API for Windows (WinForms backend)."
---

# Toga API Reference (Windows / WinForms)

> Version: Toga 0.5.3 — Windows backend (`toga-winforms`) — Python.NET / WinForms
> Live docs: https://toga.beeware.org/en/stable/reference/api/

---

## 1. App Lifecycle

```python
import toga

class MyApp(toga.App):
    def startup(self):
        self.main_window = toga.MainWindow(title="My App")
        self.main_window.content = toga.Box(children=[...])
        self.main_window.show()

    async def on_running(self):
        pass  # event loop is ready

    def on_exit(self) -> bool:
        return True  # False prevents exit

if __name__ == "__main__":
    MyApp("Formal Name", "com.example.myapp").main_loop()
```

**Key `toga.App` members:**

| Member | Notes |
|--------|-------|
| `startup()` | Override; must assign `self.main_window` |
| `on_running()` | Can be `async` |
| `on_exit() -> bool` | Return `False` to block exit |
| `main_loop()` | Blocks on desktop until the app exits |
| `exit()` | Immediate unconditional exit (skips `on_exit`) |
| `request_exit()` | Respects `on_exit` handler |
| `main_window` | Assign a `Window`, `None`, or `App.BACKGROUND` |
| `windows` | `WindowSet` of all open windows |
| `widgets` | Look up widgets by ID across all windows: `app.widgets["my_id"]` |
| `loop` | `asyncio.AbstractEventLoop` of the main thread |
| `paths` | `app.paths.data`, `.cache`, `.logs`, etc. |
| `commands` | `CommandSet` — the app's menu commands |
| `dark_mode` | `bool | None` |
| `screens` | `list[Screen]` |

**Constructor signature:**
```python
toga.App(
    formal_name: str | None = None,
    app_id: str | None = None,
    app_name: str | None = None,
    *,
    icon=None, author=None, version=None,
    home_page=None, description=None,
    startup=None,          # callable alternative to subclassing
    on_running=None,
    on_exit=None,
)
```

---

## 2. Windows

### `toga.Window`

```python
window = toga.Window(
    id=None, title=None,
    position=None,           # (x, y) tuple or toga.Position
    size=(640, 480),         # (w, h) tuple or toga.Size
    resizable=True, closable=True, minimizable=True,
    on_close=None, content=None,
)
window.content = toga.Box(children=[...])
window.show()
```

**Key members:**

| Member | Notes |
|--------|-------|
| `content` | Any `Widget`; usually a `Box` |
| `title` | Window title string |
| `size` | `toga.Size`; raises `RuntimeError` in fullscreen/presentation |
| `position` | `toga.Position` (absolute, origin = top-left of primary screen) |
| `state` | `toga.constants.WindowState` enum |
| `visible` / `show()` / `hide()` | Show/hide the window |
| `close()` | Closes unconditionally (no `on_close` invoked) |
| `on_close` | `OnCloseHandler(window, **kwargs) -> bool` |
| `on_gain_focus` / `on_lose_focus` | Focus events |
| `on_show` / `on_hide` | Visibility events |
| `on_resize` | `OnResizeHandler` |
| `widgets` | `FilteredWidgetRegistry` — look up by ID |
| `async dialog(dialog)` | Display a dialog modal to this window |
| `closed` | `bool` — whether window was closed |

> Once closed, a window cannot be reused.

### `toga.MainWindow`

Subclass of `Window`. Adds:
- `toolbar` — `CommandSet` for toolbar buttons
- On Windows: shows a menu bar at the top of the window

```python
self.main_window = toga.MainWindow(title="App Name")
self.main_window.content = content_widget
self.main_window.show()
```

---

## 3. Layout: Pack Style Engine

Toga uses its own **Pack** style system, similar to CSS Flexbox. Every widget has a `style` object. Apply styles via constructor kwargs or a `Pack` object.

```python
from toga.style import Pack
from toga.style.pack import COLUMN, ROW

widget = toga.Label("Hello", style=Pack(flex=1, padding=10))
# or via kwargs shorthand:
widget = toga.Label("Hello", flex=1, padding=10)
```

### Layout Properties

| Property | Values | Notes |
|----------|--------|-------|
| `direction` | `"row"` (default), `"column"` | Direction children are stacked |
| `align_items` | `"start"` (default), `"center"`, `"end"` | Cross-axis alignment |
| `justify_content` | `"start"` (default), `"center"`, `"end"` | Main-axis alignment (only if no flex children) |
| `flex` | `float` (default `0`) | Proportion of remaining space to consume |
| `width` | `int` or `"none"` | Fixed width in CSS px |
| `height` | `int` or `"none"` | Fixed height in CSS px |
| `gap` | `int` | Space between adjacent children |
| `margin` | `int` or 1-4-tuple | Outside spacing (TRBL shorthand) |
| `margin_top/right/bottom/left` | `int` | Individual margin sides |
| `display` | `"pack"`, `"none"` | `"none"` removes from layout (space still allocated) |
| `visibility` | `"visible"`, `"hidden"` | `"hidden"` hides but keeps space |

### Text/Font Properties

| Property | Values |
|----------|--------|
| `color` | color or `None` |
| `background_color` | color, `"transparent"`, or `None` |
| `text_align` | `"left"`, `"right"`, `"center"`, `"justify"` |
| `text_direction` | `"ltr"`, `"rtl"` |
| `font_family` | list of strings; `"system"`, `"serif"`, `"sans-serif"`, `"monospace"`, etc. |
| `font_style` | `"normal"`, `"italic"` (Windows: `"oblique"` falls back to `"italic"`) |
| `font_variant` | `"normal"` (Windows: `"small_caps"` falls back to `"normal"`) |
| `font_weight` | `"normal"`, `"bold"` |
| `font_size` | `int` in CSS points; `-1` = system default |

**Constants** (importable from `toga.style.pack`):
`COLUMN`, `ROW`, `CENTER`, `LEFT`, `RIGHT`, `TOP`, `BOTTOM`, `BOLD`, `ITALIC`, `NORMAL`, `SMALL_CAPS`, `SYSTEM`, `SERIF`, `SANS_SERIF`, `CURSIVE`, `FANTASY`, `MONOSPACE`

**Windows CSS-pixel note:** 1 CSS px = 1 physical px at 100% scale; scaled at higher DPI factors.

---

## 4. Containers / Layout Widgets

### `toga.Box` (primary layout building block)

```python
box = toga.Box(
    style=Pack(direction=COLUMN, flex=1, padding=5),
    children=[widget1, widget2],
)
box.add(widget3)
box.insert(0, widget4)
box.remove(widget1)
```

Shortcuts:
- `toga.Row(*args, **kwargs)` — Box with `direction="row"`
- `toga.Column(*args, **kwargs)` — Box with `direction="column"`

### `toga.ScrollContainer`

```python
scroll = toga.ScrollContainer(
    content=inner_box,
    horizontal=False,
    vertical=True,
    on_scroll=handler,
)
scroll.vertical_position = 0  # programmatic scroll
```

Key attrs: `content`, `horizontal`, `vertical`, `horizontal_position`, `vertical_position`, `max_horizontal_position`, `max_vertical_position`, `position` (toga.Position).

> Supported on Windows.

### `toga.OptionContainer` (tab panel)

```python
container = toga.OptionContainer(
    content=[("Tab 1", tab1_widget), ("Tab 2", tab2_widget)],
)
container.current_tab = container.content[1]
```

### `toga.SplitContainer`

```python
split = toga.SplitContainer(
    content=[left_widget, right_widget],
    direction=toga.SplitContainer.VERTICAL,
)
```

Supported on Windows.

---

## 5. Widgets (Windows support confirmed)

All widgets inherit from `toga.Widget`. Common constructor kwargs shared by all widgets:
- `id: str | None` — look up via `app.widgets["id"]` or `window.widgets["id"]`
- `style: StyleT | None` — Pack style object
- `**kwargs` — shorthand style properties (e.g. `flex=1, padding=5`)

### Text Widgets

```python
# Label - static text
label = toga.Label("Hello", style=Pack(flex=1))
label.text = "Updated text"

# TextInput - single-line editable
field = toga.TextInput(
    value="initial", placeholder="Type here...",
    readonly=False,
    on_change=handler,  # handler(widget, **kwargs)
    on_confirm=handler, on_lose_focus=handler,
    validators=[toga.validators.MinLength(3)],
)
field.value  # str

# MultilineTextInput - scrollable multi-line
area = toga.MultilineTextInput(
    value="line1\nline2",
    placeholder="Enter text...",
    readonly=False,
    on_change=handler,
)
area.scroll_to_bottom()
area.scroll_to_top()
# Windows note: TRANSPARENT background is rendered as white
```

### Buttons

```python
# Text button
btn = toga.Button("Click me", on_press=handler, enabled=True)
btn.text = "New label"

# Icon button (no text)
btn = toga.Button(icon=toga.Icon("resources/icon"), on_press=handler)
btn.icon = toga.Icon("resources/other")
```

### Selection / Input Widgets

```python
# Selection - dropdown
sel = toga.Selection(
    items=["Option A", "Option B", "Option C"],
    value="Option A",
    on_change=handler,
)
sel.value  # current item

# Switch - on/off toggle with label
sw = toga.Switch("Enable feature", value=False, on_change=handler)
sw.value  # bool

# Slider - range selector
slider = toga.Slider(
    value=50, min=0, max=100,
    on_change=handler, on_press=handler, on_release=handler,
)

# NumberInput
num = toga.NumberInput(
    value=0, min=None, max=None, step=1,
    readonly=False, on_change=handler,
)
num.value  # Decimal

# PasswordInput
pwd = toga.PasswordInput(value="", placeholder="Password", on_change=handler)

# DateInput / TimeInput
date_input = toga.DateInput(value=datetime.date.today(), on_change=handler)
time_input = toga.TimeInput(value=datetime.time(12, 0), on_change=handler)
```

### Progress & Activity

```python
# ProgressBar
bar = toga.ProgressBar(max=100, value=0, running=False)
bar.value = 50
bar.start()   # indeterminate animation (max=None)
bar.stop()

# ActivityIndicator - spinner
spinner = toga.ActivityIndicator(running=False)
spinner.start()
spinner.stop()
spinner.is_running  # bool
```

### Display Widgets

```python
# ImageView
img_view = toga.ImageView(image=toga.Image("resources/logo.png"))
img_view.image = toga.Image(Path("other.png"))

# Divider
div = toga.Divider(direction=toga.Divider.HORIZONTAL)  # or VERTICAL

# WebView (requires Edge WebView2 on Windows 10; built-in on Win 11)
web = toga.WebView(url="https://example.com", on_webview_load=handler)
web.url = "https://other.com"
await web.evaluate_javascript("document.title")
web.set_content("text/html", "<h1>Hello</h1>")
```

### Table / List Widgets

```python
# Table
table = toga.Table(
    headings=["Name", "Value"],
    data=[("Row 1", "A"), ("Row 2", "B")],
    on_select=handler,
    on_activate=handler,  # double-click
)
table.data.append(("Row 3", "C"))  # ListSource
```

---

## 6. Dialogs

Dialogs are **async** — must be `await`-ed inside an `async` handler, or scheduled with `asyncio.create_task`.

```python
# In an async handler:
async def my_handler(self, widget, **kwargs):
    # App-modal
    result = await self.dialog(toga.QuestionDialog("Title", "Are you sure?"))

    # Window-modal
    result = await self.main_window.dialog(toga.ConfirmDialog("Confirm", "Proceed?"))
    if result:
        ...

# Synchronous context:
def sync_handler(self, widget, **kwargs):
    task = asyncio.create_task(self.main_window.dialog(toga.InfoDialog("Done", "Finished.")))
    task.add_done_callback(lambda t: None)
```

### Dialog Types

| Class | Returns | Buttons |
|-------|---------|---------|
| `toga.InfoDialog(title, message)` | `None` | OK |
| `toga.ErrorDialog(title, message)` | `None` | OK |
| `toga.QuestionDialog(title, message)` | `bool` | Yes / No |
| `toga.ConfirmDialog(title, message)` | `bool` | OK / Cancel |
| `toga.StackTraceDialog(title, message, content, retry=False)` | `bool or None` | Retry/Quit or OK |
| `toga.OpenFileDialog(title, initial_directory=None, file_types=None, multiple_select=False)` | `Path or list[Path] or None` | File picker |
| `toga.SaveFileDialog(title, suggested_filename, file_types=None)` | `Path or None` | File picker |
| `toga.SelectFolderDialog(title, initial_directory=None, multiple_select=False)` | `Path or list[Path] or None` | Folder picker |

> Windows (WinForms): `SelectFolderDialog` does **not** support `multiple_select`.

---

## 7. Commands (Menu / Toolbar)

```python
cmd = toga.Command(
    handler,
    text="My Action",
    tooltip="Tooltip text",
    icon=toga.Icon("resources/icon"),
    shortcut=toga.Key.MOD_1 + "s",
    group=toga.Group.FILE,
    order=10,
    enabled=True,
)
self.app.commands.add(cmd)
self.main_window.toolbar.add(cmd)
```

---

## 8. Resources

### Icons
```python
icon = toga.Icon("resources/myicon")       # auto-selects .ico/.png
icon = toga.Icon("resources/myicon.png")
toga.Icon.APP_ICON  # default app icon
```

### Images
```python
img = toga.Image("resources/logo.png")
img = toga.Image(Path("path/to/image.png"))
```

### Fonts
```python
toga.Font.register("MyFont", "resources/MyFont.ttf")
# Use in style:
style=Pack(font_family="MyFont", font_size=14)
```

### Data Sources
```python
from toga.sources import ListSource, ValueSource

ls = ListSource(data=["a", "b", "c"])
ls.append("d")
ls.remove(ls[0])
```

---

## 9. Windows Platform Notes (WinForms)

| Feature | Windows behavior |
|---------|-----------------|
| Backend | Python.NET + Windows Forms API (`toga-winforms`) |
| Requirements | Python 3.10+, Windows 10+, Python.NET |
| WebView | Requires Edge WebView2 on Win 10; built-in on Win 11 |
| Menu bar | Shown **inside** the MainWindow (not app-level like macOS) |
| `font_variant: "small_caps"` | Falls back to `"normal"` |
| `font_style: "oblique"` | Falls back to `"italic"` |
| MultilineTextInput transparent BG | Renders as white |
| Label `JUSTIFIED` text align | Falls back to left |
| SelectFolderDialog `multiple_select` | Not supported |
| `DetailedList` | Partial support |
| `Tree` | **Not supported** |
| `SplitContainer` | Fully supported |
| `Canvas` | Fully supported |
| `Table` | Fully supported |
| `StatusIcons` | Fully supported (system tray) |

---

## 10. Common Patterns

### Columnar form layout
```python
from toga.style.pack import Pack, COLUMN

def make_form():
    return toga.Box(
        style=Pack(direction=COLUMN, padding=10, gap=8),
        children=[
            toga.Label("Username:"),
            toga.TextInput(placeholder="Enter username", style=Pack(flex=1)),
            toga.Label("Password:"),
            toga.PasswordInput(placeholder="Enter password", style=Pack(flex=1)),
            toga.Button("Login", on_press=handle_login, style=Pack(padding_top=10)),
        ]
    )
```

### Log panel (scrollable)
```python
log_output = toga.MultilineTextInput(readonly=True, style=Pack(flex=1))
scroll = toga.ScrollContainer(content=log_output, horizontal=False, style=Pack(flex=1))

def append_log(message: str):
    log_output.value += message + "\n"
    log_output.scroll_to_bottom()
```

### Async operation with spinner and error dialog
```python
async def run_operation(self, widget, **kwargs):
    spinner = self.app.widgets["spinner"]
    spinner.start()
    try:
        result = await asyncio.get_event_loop().run_in_executor(None, blocking_fn)
    except Exception as e:
        await self.main_window.dialog(toga.ErrorDialog("Error", str(e)))
    finally:
        spinner.stop()
```

### Tab panels (OptionContainer)
```python
tabs = toga.OptionContainer(
    style=Pack(flex=1),
    content=[
        ("Settings", build_settings_panel()),
        ("Logs", build_log_panel()),
    ],
)
tabs.current_tab = tabs.content["Logs"]
```

---

## 11. Quick Widget Reference (Windows)

| Widget | Windows | Key attrs |
|--------|---------|-----------|
| `ActivityIndicator` | YES | `running`, `start()`, `stop()` |
| `Button` | YES | `text`, `icon`, `on_press`, `enabled` |
| `Canvas` | YES | Drawing context |
| `DateInput` | YES | `value` (date), `on_change` |
| `DetailedList` | PARTIAL | `data`, `on_select` |
| `Divider` | YES | `direction` |
| `ImageView` | YES | `image` |
| `Label` | YES | `text` |
| `MultilineTextInput` | YES | `value`, `readonly`, `placeholder`, `on_change` |
| `NumberInput` | YES | `value`, `min`, `max`, `step`, `on_change` |
| `PasswordInput` | YES | `value`, `placeholder`, `on_change` |
| `ProgressBar` | YES | `value`, `max`, `running`, `start()`, `stop()` |
| `Selection` | YES | `items`, `value`, `on_change` |
| `Slider` | YES | `value`, `min`, `max`, `on_change` |
| `Switch` | YES | `text`, `value`, `on_change` |
| `Table` | YES | `headings`, `data`, `on_select`, `on_activate` |
| `TextInput` | YES | `value`, `placeholder`, `readonly`, `on_change` |
| `TimeInput` | YES | `value` (time), `on_change` |
| `Tree` | NO | Not supported on Windows |
| `WebView` | YES | `url`, `on_webview_load`, `evaluate_javascript()` |
| `Box` | YES | `children`, `add()`, `insert()`, `remove()` |
| `ScrollContainer` | YES | `content`, `horizontal`, `vertical`, `*_position` |
| `SplitContainer` | YES | `content`, `direction` |
| `OptionContainer` | YES | `content`, `current_tab` |

---

## 12. Full API Documentation URLs

- **API index**: https://toga.beeware.org/en/stable/reference/api/
- **App**: https://toga.beeware.org/en/stable/reference/api/app/
- **Window**: https://toga.beeware.org/en/stable/reference/api/window/
- **MainWindow**: https://toga.beeware.org/en/stable/reference/api/mainwindow/
- **Box**: https://toga.beeware.org/en/stable/reference/api/containers/box/
- **ScrollContainer**: https://toga.beeware.org/en/stable/reference/api/containers/scrollcontainer/
- **OptionContainer**: https://toga.beeware.org/en/stable/reference/api/containers/optioncontainer/
- **SplitContainer**: https://toga.beeware.org/en/stable/reference/api/containers/splitcontainer/
- **Pack style engine**: https://toga.beeware.org/en/stable/reference/style/pack/
- **Dialogs**: https://toga.beeware.org/en/stable/reference/api/resources/dialogs/
- **Command**: https://toga.beeware.org/en/stable/reference/api/resources/command/
- **Windows platform**: https://toga.beeware.org/en/stable/reference/platforms/windows/
- **APIs by platform**: https://toga.beeware.org/en/stable/reference/widgets_by_platform/
- **Widget layout topic**: https://toga.beeware.org/en/stable/topics/layout/
