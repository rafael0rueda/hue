# SPDX-FileCopyrightText: 2026 Rafael Rueda
# SPDX-License-Identifier: GPL-3.0-or-later

from __future__ import annotations

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango

from . import APP_NAME
from .canvas import Canvas
from .clipboard import has_image, read_image, texture_from_surface
from .color import ColorBar, ColorState
from .document import DEFAULT_HEIGHT, DEFAULT_WIDTH, MAX_SIZE, Document, new_surface
from .file_io import image_filters, load_document, save_document
from .text import FONT_SIZE_RANGE, font_size, font_without_size, with_font_size
from .tools import TOOL_CLASSES

# The one size slider serves the brush and, with the text tool up, the font.
BRUSH_SIZE_RANGE = (1, 64)

TOOL_ACCELS = {
    "pencil": "p",
    "brush": "b",
    "eraser": "e",
    "line": "l",
    "rectangle": "r",
    "ellipse": "o",
    "text": "t",
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
        self.canvas.connect("resize-preview", self._on_resize_preview)
        self.canvas.connect("floating-changed", self._on_floating_changed)
        self._closing = False
        self._typing = False
        self._syncing_size = False

        self._title = Adw.WindowTitle(title=APP_NAME)
        self.toasts = Adw.ToastOverlay()

        toolbars = Adw.ToolbarView()
        toolbars.add_top_bar(self._build_header())
        toolbars.add_bottom_bar(self._build_bottom_bar())
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
        edit_section = Gio.Menu()
        edit_section.append("Copy", "win.copy")
        edit_section.append("Paste", "win.paste")
        menu.append_section(None, edit_section)
        file_section = Gio.Menu()
        file_section.append("Save As…", "win.save-as")
        file_section.append("Canvas Size…", "win.resize")
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

    def _build_bottom_bar(self) -> Gtk.Widget:
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        colors = ColorBar(self.colors)
        colors.set_hexpand(True)
        bar.append(colors)

        # The canvas size lives here rather than in the header subtitle, which
        # renders too small to read at larger interface font sizes.
        self._canvas_size_label = Gtk.Label()
        self._canvas_size_label.add_css_class("numeric")
        button = Gtk.Button(tooltip_text="Canvas size (Ctrl+E)")
        button.set_child(self._canvas_size_label)
        button.add_css_class("flat")
        button.set_valign(Gtk.Align.CENTER)
        button.set_margin_end(12)
        button.set_action_name("win.resize")
        bar.append(button)
        return bar

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

        self._size_label = Gtk.Label(xalign=0)
        self._size_label.add_css_class("caption")
        sidebar.append(self._size_label)

        self._size_scale = Gtk.Scale.new_with_range(
            Gtk.Orientation.HORIZONTAL, *BRUSH_SIZE_RANGE, 1
        )
        self._size_scale.set_value(self.canvas.brush_size)
        self._size_scale.set_draw_value(False)
        self._size_scale.connect("value-changed", self._on_size_changed)
        sidebar.append(self._size_scale)
        self._sync_size_scale()

        self._fill_check = Gtk.CheckButton(label="Fill shape")
        self._fill_check.set_sensitive(False)
        self._fill_check.connect("toggled", self._on_fill_toggled)
        sidebar.append(self._fill_check)

        # A caption of our own rather than a GtkFontDialogButton, whose label
        # grows the sidebar to fit whatever font name it is showing. It leaves
        # the size out, because that is what the slider above is for.
        self._font_label = Gtk.Label(label=font_without_size(self.canvas.font), xalign=0)
        self._font_label.add_css_class("caption")
        self._font_label.set_ellipsize(Pango.EllipsizeMode.END)
        sidebar.append(self._font_label)

        self._font_button = Gtk.Button(label="Font…", tooltip_text="Typeface for the text tool")
        self._font_button.set_sensitive(False)
        self._font_button.connect("clicked", self._choose_font)
        sidebar.append(self._font_button)

        return sidebar

    # Actions

    def _install_actions(self) -> None:
        simple_actions = {
            "new": self._action_new,
            "open": self._action_open,
            "save": lambda *_: self._save(),
            "save-as": lambda *_: self._save_as(),
            "undo": self._action_undo,
            "redo": lambda *_: self.canvas.document.redo(),
            "copy": lambda *_: self._copy(),
            "paste": lambda *_: self._paste(),
            "swap-colors": lambda *_: self.colors.swap(),
            "resize": lambda *_: self._prompt_canvas_size(),
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
            "win.copy": ["<Control>c"],
            "win.paste": ["<Control>v"],
            "win.undo": ["<Control>z"],
            "win.redo": ["<Control><Shift>z", "<Control>y"],
            "win.swap-colors": ["x"],
            "win.resize": ["<Control>e"],
            "app.quit": ["<Control>q"],
        }
        for tool_id, key in TOOL_ACCELS.items():
            accels[f"win.tool::{tool_id}"] = [key]
        for action_name, keys in accels.items():
            app.set_accels_for_action(action_name, keys)

        # Typing into a text box must not trip the shortcuts that are a bare key.
        self._single_key_accels = {
            name: keys
            for name, keys in accels.items()
            if all("<" not in key for key in keys)
        }

        clipboard = self.get_clipboard()
        clipboard.connect("changed", lambda *_: self._sync_paste_action())
        self._sync_paste_action()

    def _on_tool_changed(self, action, value: GLib.Variant) -> None:
        self.canvas.commit_floating()
        action.set_state(value)
        self.canvas.select_tool(value.get_string())
        self._fill_check.set_sensitive(self.canvas.supports_fill)
        self._font_button.set_sensitive(self.canvas.supports_font)
        self._sync_size_scale()

    def _on_size_changed(self, scale: Gtk.Scale) -> None:
        if self._syncing_size:
            return
        size = int(scale.get_value())
        if self.canvas.supports_font:
            self.canvas.set_font(with_font_size(self.canvas.font, size))
        else:
            self.canvas.brush_size = size
        self._show_size(size)

    def _sync_size_scale(self) -> None:
        """Hand the slider over to the font while the text tool is selected."""
        text = self.canvas.supports_font
        size = font_size(self.canvas.font) if text else self.canvas.brush_size
        # Moving the range moves the value with it, which would write the brush
        # size into the font and back again.
        self._syncing_size = True
        self._size_scale.set_range(*(FONT_SIZE_RANGE if text else BRUSH_SIZE_RANGE))
        self._size_scale.set_value(size)
        self._syncing_size = False
        self._show_size(size)

    def _show_size(self, size: int) -> None:
        unit = "pt" if self.canvas.supports_font else "px"
        self._size_label.set_label(f"Size: {size} {unit}")

    def _on_fill_toggled(self, check: Gtk.CheckButton) -> None:
        self.canvas.fill_shapes = check.get_active()

    def _choose_font(self, *_) -> None:
        dialog = Gtk.FontDialog(title="Text font")

        def on_done(source, result):
            try:
                description = source.choose_font_finish(result)
            except GLib.Error:
                return
            font = description.to_string()
            self._font_label.set_label(font_without_size(font))
            self.canvas.set_font(font)
            # The dialog carries a size of its own; the slider follows it.
            self._sync_size_scale()

        dialog.choose_font(self, Pango.FontDescription(self.canvas.font), None, on_done)

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
        # While a paste or a text box floats this counts out the size a commit
        # would leave.
        width, height = self.canvas.pending_size
        self._canvas_size_label.set_label(f"{width} × {height} px")
        # Undo also takes back what has not been stamped down yet.
        self.lookup_action("undo").set_enabled(document.can_undo or self.canvas.has_floating)
        self.lookup_action("redo").set_enabled(document.can_redo)

    def _on_floating_changed(self, *_) -> None:
        self._sync_state()
        self._sync_typing_accels()

    def _sync_typing_accels(self) -> None:
        """Give the one-key shortcuts back and forth as a text box comes and goes."""
        if self.canvas.is_typing == self._typing:
            return
        self._typing = self.canvas.is_typing
        app = self.get_application()
        for name, keys in self._single_key_accels.items():
            app.set_accels_for_action(name, [] if self._typing else keys)

    def _on_resize_preview(self, canvas, width: int, height: int) -> None:
        """Count out the pending size while a resize grip is being dragged."""
        self._canvas_size_label.set_label(f"{width} × {height} px")

    # Clipboard

    def _sync_paste_action(self) -> None:
        self.lookup_action("paste").set_enabled(has_image(self.get_clipboard()))

    def _copy(self) -> None:
        self.canvas.commit_floating()
        document = self.canvas.document
        texture = texture_from_surface(document.surface)
        self.get_clipboard().set_content(Gdk.ContentProvider.new_for_value(texture))
        # The clipboard's own notification is asynchronous; do not wait for it.
        self._sync_paste_action()
        self._toast("Copied to clipboard")

    def _paste(self) -> None:
        read_image(self.get_clipboard(), self.canvas.begin_paste, self._toast)

    def _action_undo(self, *_) -> None:
        # A paste or a text box has not been stamped down yet, so undo drops it.
        if not self.canvas.cancel_floating():
            self.canvas.document.undo()

    def _toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message))

    def _confirm_discard(self, proceed) -> None:
        self.canvas.commit_floating()
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

    def _prompt_size(self, heading, body, size, accept_id, accept_label, on_accept) -> None:
        """Ask for a width/height pair, then hand it to on_accept."""
        spins = []
        for value in size:
            spin = Gtk.SpinButton.new_with_range(1, MAX_SIZE, 1)
            spin.set_value(value)
            # Wide enough for the largest allowed size in any interface font.
            spin.set_width_chars(len(str(MAX_SIZE)) + 1)
            spins.append(spin)
        width_spin, height_spin = spins

        grid = Gtk.Grid(row_spacing=6, column_spacing=12, margin_top=12)
        grid.attach(Gtk.Label(label="Width", xalign=1), 0, 0, 1, 1)
        grid.attach(width_spin, 1, 0, 1, 1)
        grid.attach(Gtk.Label(label="Height", xalign=1), 0, 1, 1, 1)
        grid.attach(height_spin, 1, 1, 1, 1)

        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.set_extra_child(grid)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response(accept_id, accept_label)
        dialog.set_response_appearance(accept_id, Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response(accept_id)
        dialog.set_close_response("cancel")

        def on_response(_dialog, response: str) -> None:
            if response == accept_id:
                on_accept(int(width_spin.get_value()), int(height_spin.get_value()))

        dialog.connect("response", on_response)
        dialog.present(self)

    def _prompt_new_size(self) -> None:
        def create(width: int, height: int) -> None:
            self._set_document(Document(new_surface(width, height)))

        self._prompt_size(
            "New image",
            "Choose a canvas size in pixels.",
            (DEFAULT_WIDTH, DEFAULT_HEIGHT),
            "create",
            "Create",
            create,
        )

    def _prompt_canvas_size(self) -> None:
        self.canvas.commit_floating()
        document = self.canvas.document

        self._prompt_size(
            "Canvas size",
            "The image keeps its top-left corner; extra space is filled with white.",
            (document.width, document.height),
            "resize",
            "Resize",
            document.resize,
        )

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
        # What gets written should match what is on screen.
        self.canvas.commit_floating()
        document = self.canvas.document
        if document.file is None:
            self._save_as(then)
            return
        self._write(document.file, then)

    def _save_as(self, then=None) -> None:
        self.canvas.commit_floating()
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
