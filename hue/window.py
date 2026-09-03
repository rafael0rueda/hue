from __future__ import annotations

from gi.repository import Adw, Gio, GLib, Gtk

from . import APP_NAME
from .canvas import Canvas
from .color import ColorBar, ColorState
from .document import DEFAULT_HEIGHT, DEFAULT_WIDTH, Document
from .file_io import image_filters, load_document, save_document
from .tools import TOOL_CLASSES

TOOL_ACCELS = {
    "pencil": "p",
    "brush": "b",
    "eraser": "e",
    "line": "l",
    "rectangle": "r",
    "ellipse": "o",
    "fill": "f",
    "picker": "k",
}


class HueWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, document: Document | None = None):
        super().__init__(application=application, title=APP_NAME)
        self.set_default_size(1120, 800)
        self.set_size_request(640, 480)

        self.colors = ColorState()
        self.canvas = Canvas(document or Document(), self.colors)
        self.canvas.connect("color-picked", self._on_color_picked)
        self._closing = False

        self._title = Adw.WindowTitle(title=APP_NAME)
        self.toasts = Adw.ToastOverlay()

        toolbars = Adw.ToolbarView()
        toolbars.add_top_bar(self._build_header())
        toolbars.add_bottom_bar(ColorBar(self.colors))
        toolbars.set_content(self._build_content())

        self.toasts.set_child(toolbars)
        self.set_content(self.toasts)

        self._install_actions()
        self._watch_document()
        self.connect("close-request", self._on_close_request)

    # UI construction

    def _build_header(self) -> Adw.HeaderBar:
        header = Adw.HeaderBar()
        header.set_title_widget(self._title)

        for icon, action, tooltip in (
            ("document-new-symbolic", "win.new", "New image (Ctrl+N)"),
            ("document-open-symbolic", "win.open", "Open image (Ctrl+O)"),
            ("hue-save-symbolic", "win.save", "Save (Ctrl+S)"),
        ):
            button = Gtk.Button(icon_name=icon, tooltip_text=tooltip)
            button.set_action_name(action)
            header.pack_start(button)

        history = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        history.add_css_class("linked")
        for icon, action, tooltip in (
            ("edit-undo-symbolic", "win.undo", "Undo (Ctrl+Z)"),
            ("edit-redo-symbolic", "win.redo", "Redo (Ctrl+Shift+Z)"),
        ):
            button = Gtk.Button(icon_name=icon, tooltip_text=tooltip)
            button.set_action_name(action)
            history.append(button)

        menu = Gio.Menu()
        file_section = Gio.Menu()
        file_section.append("Save As…", "win.save-as")
        menu.append_section(None, file_section)
        app_section = Gio.Menu()
        app_section.append(f"About {APP_NAME}", "app.about")
        app_section.append("Quit", "app.quit")
        menu.append_section(None, app_section)

        menu_button = Gtk.MenuButton(icon_name="open-menu-symbolic", tooltip_text="Main menu")
        menu_button.set_menu_model(menu)

        header.pack_end(menu_button)
        header.pack_end(history)
        return header

    def _build_content(self) -> Gtk.Widget:
        content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        content.append(self._build_sidebar())
        content.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        scrolled = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        scrolled.add_css_class("hue-canvas-area")
        scrolled.set_child(self.canvas)
        content.append(scrolled)
        return content

    def _build_sidebar(self) -> Gtk.Widget:
        sidebar = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        sidebar.add_css_class("hue-sidebar")
        sidebar.set_size_request(128, -1)

        tools = Gtk.Grid(row_spacing=6, column_spacing=6, halign=Gtk.Align.CENTER)
        for index, tool in enumerate(TOOL_CLASSES):
            accel = TOOL_ACCELS[tool.id].upper()
            button = Gtk.ToggleButton(
                icon_name=tool.icon_name,
                tooltip_text=f"{tool.label} ({accel})",
            )
            button.add_css_class("hue-tool")
            button.set_action_name("win.tool")
            button.set_action_target_value(GLib.Variant.new_string(tool.id))
            tools.attach(button, index % 2, index // 2, 1, 1)
        sidebar.append(tools)

        sidebar.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))

        self._size_label = Gtk.Label(label="Size: 4 px", xalign=0)
        self._size_label.add_css_class("caption")
        sidebar.append(self._size_label)

        size_scale = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, 1, 64, 1)
        size_scale.set_value(self.canvas.brush_size)
        size_scale.set_draw_value(False)
        size_scale.connect("value-changed", self._on_size_changed)
        sidebar.append(size_scale)

        self._fill_check = Gtk.CheckButton(label="Fill shape")
        self._fill_check.set_sensitive(False)
        self._fill_check.connect("toggled", self._on_fill_toggled)
        sidebar.append(self._fill_check)

        return sidebar

    # Actions

    def _install_actions(self) -> None:
        simple_actions = {
            "new": self._action_new,
            "open": self._action_open,
            "save": lambda *_: self._save(),
            "save-as": lambda *_: self._save_as(),
            "undo": lambda *_: self.canvas.document.undo(),
            "redo": lambda *_: self.canvas.document.redo(),
            "swap-colors": lambda *_: self.colors.swap(),
        }
        for name, callback in simple_actions.items():
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)

        tool_action = Gio.SimpleAction.new_stateful(
            "tool", GLib.VariantType.new("s"), GLib.Variant.new_string("pencil")
        )
        tool_action.connect("change-state", self._on_tool_changed)
        self.add_action(tool_action)

        app = self.get_application()
        accels = {
            "win.new": ["<Control>n"],
            "win.open": ["<Control>o"],
            "win.save": ["<Control>s"],
            "win.save-as": ["<Control><Shift>s"],
            "win.undo": ["<Control>z"],
            "win.redo": ["<Control><Shift>z", "<Control>y"],
            "win.swap-colors": ["x"],
            "app.quit": ["<Control>q"],
        }
        for tool_id, key in TOOL_ACCELS.items():
            accels[f"win.tool::{tool_id}"] = [key]
        for action_name, keys in accels.items():
            app.set_accels_for_action(action_name, keys)

    def _on_tool_changed(self, action, value: GLib.Variant) -> None:
        action.set_state(value)
        self.canvas.select_tool(value.get_string())
        self._fill_check.set_sensitive(self.canvas.supports_fill)

    def _on_size_changed(self, scale: Gtk.Scale) -> None:
        size = int(scale.get_value())
        self.canvas.brush_size = size
        self._size_label.set_label(f"Size: {size} px")

    def _on_fill_toggled(self, check: Gtk.CheckButton) -> None:
        self.canvas.fill_shapes = check.get_active()

    def _on_color_picked(self, canvas, color, button) -> None:
        from gi.repository import Gdk

        if button == Gdk.BUTTON_SECONDARY:
            self.colors.secondary = color
        else:
            self.colors.primary = color

    # Document lifecycle

    def _watch_document(self) -> None:
        document = self.canvas.document
        document.connect("state-changed", lambda *_: self._sync_state())
        self._sync_state()

    def _set_document(self, document: Document) -> None:
        self.canvas.document = document
        self._watch_document()

    def _sync_state(self) -> None:
        document = self.canvas.document
        marker = " •" if document.modified else ""
        self._title.set_title(f"{document.title}{marker}")
        self._title.set_subtitle(f"{document.width} × {document.height}")
        self.lookup_action("undo").set_enabled(document.can_undo)
        self.lookup_action("redo").set_enabled(document.can_redo)

    def _toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))

    def _confirm_discard(self, proceed) -> None:
        document = self.canvas.document
        if not document.modified:
            proceed()
            return

        dialog = Adw.AlertDialog(
            heading="Save changes?",
            body=f"“{document.title}” has unsaved changes.",
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("discard", "Discard")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("discard", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response: str) -> None:
            if response == "discard":
                proceed()
            elif response == "save":
                self._save(proceed)

        dialog.connect("response", on_response)
        dialog.present(self)

    def _action_new(self, *_) -> None:
        self._confirm_discard(self._prompt_new_size)

    def _prompt_new_size(self) -> None:
        width_spin = Gtk.SpinButton.new_with_range(1, 8192, 1)
        width_spin.set_value(DEFAULT_WIDTH)
        height_spin = Gtk.SpinButton.new_with_range(1, 8192, 1)
        height_spin.set_value(DEFAULT_HEIGHT)

        grid = Gtk.Grid(row_spacing=6, column_spacing=12, margin_top=12)
        grid.attach(Gtk.Label(label="Width", xalign=1), 0, 0, 1, 1)
        grid.attach(width_spin, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Height", xalign=1), 0, 1, 1, 1)
        grid.attach(height_spin, 1, 1, 1, 1)

        dialog = Adw.AlertDialog(heading="New image", body="Choose a canvas size in pixels.")
        dialog.set_extra_child(grid)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")

        def on_response(_dialog, response: str) -> None:
            if response != "create":
                return
            from .document import new_surface

            surface = new_surface(int(width_spin.get_value()), int(height_spin.get_value()))
            self._set_document(Document(surface))

        dialog.connect("response", on_response)
        dialog.present(self)

    def _action_open(self, *_) -> None:
        self._confirm_discard(self._show_open_dialog)

    def _show_open_dialog(self) -> None:
        dialog = Gtk.FileDialog(title="Open Image", filters=image_filters())

        def on_done(source, result):
            try:
                file = source.open_finish(result)
            except GLib.Error:
                return
            try:
                self._set_document(load_document(file))
            except GLib.Error as error:
                self._toast(f"Could not open image: {error.message}")

        dialog.open(self, None, on_done)

    def _save(self, then=None) -> None:
        document = self.canvas.document
        if document.file is None:
            self._save_as(then)
            return
        self._write(document.file, then)

    def _save_as(self, then=None) -> None:
        document = self.canvas.document
        dialog = Gtk.FileDialog(title="Save Image", filters=image_filters())
        dialog.set_initial_name(document.title if document.file else "Untitled.png")

        def on_done(source, result):
            try:
                file = source.save_finish(result)
            except GLib.Error:
                return
            self._write(file, then)

        dialog.save(self, None, on_done)

    def _write(self, file: Gio.File, then=None) -> None:
        try:
            save_document(self.canvas.document, file)
        except GLib.Error as error:
            self._toast(f"Could not save image: {error.message}")
            return
        self._toast(f"Saved {file.get_basename()}")
        if then is not None:
            then()

    def _on_close_request(self, *_) -> bool:
        if self._closing:
            return False

        def close():
            self._closing = True
            self.close()

        self._confirm_discard(close)
        return True
