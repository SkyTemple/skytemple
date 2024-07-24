#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
#
#  This file is part of SkyTemple.
#
#  SkyTemple is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  SkyTemple is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with SkyTemple.  If not, see <https://www.gnu.org/licenses/>.
from __future__ import annotations
import logging
import sys
from typing import TYPE_CHECKING, cast
import cairo
from range_typed_integers import u32, u16, u16_checked
from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import (
    add_dialog_png_filter,
    catch_overflow,
    iter_tree_model,
    data_dir,
    safe_destroy,
)
from skytemple_files.common.util import add_extension_if_missing
from skytemple_files.graphics.wte.model import Wte, WteImageType
from skytemple_files.graphics.wtu.model import Wtu, WtuEntry
from PIL import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule, WteOpenSpec
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "misc_graphics", "wte_wtu.ui"))
class StMiscGraphicsWteWtuPage(Gtk.Paned):
    __gtype_name__ = "StMiscGraphicsWteWtuPage"
    module: MiscGraphicsModule
    item_data: WteOpenSpec
    dialog_map_import_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_collision_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_layers_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    image_type_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    png_filter: Gtk.FileFilter = cast(Gtk.FileFilter, Gtk.Template.Child())
    dialog_import_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    btn_cancel: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image_path_setting: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())
    clear_image_path: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image_type_setting: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    chk_discard_palette: Gtk.CheckButton = cast(Gtk.CheckButton, Gtk.Template.Child())
    wtu_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    button_import: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    export: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    draw_area: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    info_image_only: Gtk.InfoBar = cast(Gtk.InfoBar, Gtk.Template.Child())
    info_palette_only: Gtk.InfoBar = cast(Gtk.InfoBar, Gtk.Template.Child())
    lbl_canvas_size: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    wte_palette_variant: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())
    lbl_image_type: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    wtu_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    no_wtu_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    wtu_editor: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    wtu_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    wtu_x: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    wtu_y: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    wtu_width: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    wtu_height: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    btn_add: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_remove: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, module: MiscGraphicsModule, item_data: WteOpenSpec):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.wtu: Wtu | None = None
        if item_data.in_dungeon_bin:
            self.wte: Wte = self.module.get_dungeon_bin_file(item_data.wte_filename)
            if item_data.wtu_filename is not None:
                self.wtu = self.module.get_dungeon_bin_file(item_data.wtu_filename)
        else:
            self.wte = self.module.get_wte(item_data.wte_filename)
            if item_data.wtu_filename is not None:
                self.wtu = self.module.get_wtu(item_data.wtu_filename)
        self._init_wtu()
        self._reinit_image()
        self._init_wte()
        self.draw_area.connect("draw", self.exec_draw)

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.dialog_import_settings)

    @Gtk.Template.Callback()
    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Export image as PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            _("_Save"),
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, "png")
            if self.wte.has_image():
                self.wte.to_pil_canvas(int(self.wte_palette_variant.get_text())).save(fn)
            else:
                self.wte.to_pil_palette().save(fn)

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, *args):
        dialog = self.dialog_import_settings
        self.image_path_setting.unselect_all()
        # Init available categories
        cb_store = self.image_type_store
        cb = self.image_type_setting
        self._fill_available_image_types_into_store(cb_store)
        # Set current WTE file settings by default
        for i, depth in enumerate(iter_tree_model(cb_store)):
            if self.wte.image_type.value == depth[0]:
                cb.set_active(i)
        self.chk_discard_palette.set_active(not self.wte.has_palette())
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            img_fn = self.image_path_setting.get_filename()
            if img_fn is not None:
                try:
                    img_pil = Image.open(img_fn, "r")
                except Exception as err:
                    display_error(sys.exc_info(), str(err), _("Filename not specified."))
                    return
                titer = cb.get_active_iter()
                assert titer is not None
                depth = cb_store[titer][0]
                discard: bool = self.chk_discard_palette.get_active()
                try:
                    self.wte.from_pil(img_pil, WteImageType(depth), discard)  # type: ignore
                except ValueError as err:
                    display_error(sys.exc_info(), str(err), _("Imported image size too big."))
                except AttributeError as err:
                    display_error(sys.exc_info(), str(err), _("Not an indexed image."))
                self.module.mark_wte_as_modified(self.item_data, self.wte, self.wtu)
                self._init_wte()
                self._reinit_image()
                if self.wtu:
                    self.wtu.image_mode = u32(self.wte.get_mode())

    def _init_wte(self):
        info_palette_only = self.info_palette_only
        info_palette_only.set_revealed(not self.wte.has_image())
        info_palette_only.set_message_type(Gtk.MessageType.WARNING)
        info_image_only = self.info_image_only
        info_image_only.set_revealed(not self.wte.has_palette())
        info_image_only.set_message_type(Gtk.MessageType.WARNING)
        self.wte_palette_variant.set_text(str(0))
        self.wte_palette_variant.set_increments(1, 1)
        self.wte_palette_variant.set_range(0, self.wte.nb_palette_variants() - 1)
        dimensions: tuple[int, int] = self.wte.actual_dimensions()
        if self.wte.has_image():
            self.lbl_canvas_size.set_text(f"{self.wte.width}x{self.wte.height} [{dimensions[0]}x{dimensions[1]}]")
        else:
            self.lbl_canvas_size.set_text(f"{self.wte.width}x{self.wte.height} [No image data]")
        self.lbl_image_type.set_text(self.wte.image_type.explanation)

    def _init_wtu(self):
        wtu_stack = self.wtu_stack
        if not self.wtu:
            wtu_stack.set_visible_child(self.no_wtu_label)
        else:
            wtu_stack.set_visible_child(self.wtu_editor)
            wtu_store = self.wtu_store
            for entry in self.wtu.entries:
                wtu_store.append([str(entry.x), str(entry.y), str(entry.width), str(entry.height)])

    def _reinit_image(self):
        try:
            val = int(self.wte_palette_variant.get_text())
        except ValueError:
            val = 0
        self.surface = pil_to_cairo_surface(self.wte.to_pil_canvas(val).convert("RGBA"))
        self.draw_area.queue_draw()

    @Gtk.Template.Callback()
    def on_wte_variant_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        if val < 0:
            val = 0
            widget.set_text(str(val))
        elif val >= self.wte.nb_palette_variants():
            val = self.wte.nb_palette_variants() - 1
            widget.set_text(str(val))
        self._reinit_image()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_wtu_x_edited(self, widget, path, text):
        try:
            u16_checked(int(text))
        except ValueError:
            return
        wtu_store = self.wtu_store
        wtu_store[path][0] = text
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_wtu_y_edited(self, widget, path, text):
        try:
            u16_checked(int(text))
        except ValueError:
            return
        wtu_store = self.wtu_store
        wtu_store[path][1] = text
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_wtu_width_edited(self, widget, path, text):
        try:
            u16_checked(int(text))
        except ValueError:
            return
        wtu_store = self.wtu_store
        wtu_store[path][2] = text
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_wtu_height_edited(self, widget, path, text):
        try:
            u16_checked(int(text))
        except ValueError:
            return
        wtu_store = self.wtu_store
        wtu_store[path][3] = text
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    def on_btn_add_clicked(self, *args):
        store = self.wtu_store
        store.append(["0", "0", "0", "0"])
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    def on_btn_remove_clicked(self, *args):
        # Deletes all selected WTU entries
        # Allows multiple deletions
        active_rows: list[Gtk.TreePath] = self.wtu_tree.get_selection().get_selected_rows()[1]
        store = self.wtu_store
        for x in reversed(sorted(active_rows, key=lambda x: x.get_indices())):
            del store[x.get_indices()[0]]
        self._regenerate_wtu()

    @Gtk.Template.Callback()
    def on_wtu_tree_selection_changed(self, *args):
        self._reinit_image()

    @Gtk.Template.Callback()
    def on_clear_image_path_clicked(self, *args):
        self.image_path_setting.unselect_all()

    def _fill_available_image_types_into_store(self, cb_store):
        image_types = [v for v in WteImageType]
        # Init combobox
        cb_store.clear()
        for img_type in image_types:
            cb_store.append([img_type.value, img_type.explanation])

    def _regenerate_wtu(self):
        wtu_store = self.wtu_store
        assert self.wtu is not None
        self.wtu.entries = []
        for row in iter_tree_model(wtu_store):
            self.wtu.entries.append(
                WtuEntry(
                    u16(int(row[0])),
                    u16(int(row[1])),
                    u16(int(row[2])),
                    u16(int(row[3])),
                )
            )
        self.module.mark_wte_as_modified(self.item_data, self.wte, self.wtu)

    def exec_draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
            # Draw rectangles on the WTE image representing the selected WTU entries
            # Allows multiple selections
            active_rows: list[Gtk.TreePath] = self.wtu_tree.get_selection().get_selected_rows()[1]
            store = self.wtu_store
            for x in active_rows:
                row = store[x.get_indices()[0]]
                ctx.set_line_width(4)
                ctx.set_source_rgba(1, 1, 1, 1)
                ctx.rectangle(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
                ctx.stroke()
                ctx.set_line_width(2)
                ctx.set_source_rgba(0, 0, 0, 1)
                ctx.rectangle(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
                ctx.stroke()
        return True
