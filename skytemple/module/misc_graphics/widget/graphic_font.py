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
import os
import sys
from typing import TYPE_CHECKING, cast
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import assert_not_none, data_dir, safe_destroy
import cairo
from skytemple.core.error_handler import display_error
from skytemple_files.graphics.fonts.graphic_font.model import GraphicFont
from PIL import Image
from gi.repository import Gtk
from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.common.i18n_util import _

from skytemple.init_locale import LocalePatchedGtkTemplate

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule, FontOpenSpec
IMAGE_ZOOM = 4
MAX_ENTRIES = 10000


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "misc_graphics", "graphic_font.ui"))
class StMiscGraphicsGraphicFontPage(Gtk.Paned):
    __gtype_name__ = "StMiscGraphicsGraphicFontPage"
    module: MiscGraphicsModule
    item_data: FontOpenSpec
    dialog_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_cancel: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    nb_entries_import: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())
    button_import: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    export: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    entry_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    no_entry_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    entry_viewer: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    draw_area: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    entry_id: Gtk.SpinButton = cast(Gtk.SpinButton, Gtk.Template.Child())
    table_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())

    def __init__(self, module: MiscGraphicsModule, item_data: FontOpenSpec):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.font: GraphicFont = assert_not_none(self.module.get_graphic_font(self.item_data))
        assert self.font is not None
        self._init_font()
        self.draw_area.connect("draw", self.exec_draw)

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.dialog_import)

    @Gtk.Template.Callback()
    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Export font in folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"),
            None,
        )
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            assert self.font
            for i in range(self.font.get_nb_entries()):
                e = self.font.get_entry(i)
                if e:
                    path = os.path.join(fn, f"{i:0>4}.png")
                    e.save(path)

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, w: Gtk.MenuToolButton):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "To import, select a folder containing all the files that were created when exporting the font.\nIMPORTANT: All image files must be indexed PNGs and use the same palette!"
            ),
            title=_("Import Font"),
        )
        md.run()
        md.destroy()
        fdialog = Gtk.FileChooserNative.new(
            _("Import font from folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None,
            None,
        )
        response = fdialog.run()
        fn = fdialog.get_filename()
        fdialog.destroy()
        if response == Gtk.ResponseType.ACCEPT:
            dialog = self.dialog_import
            self.nb_entries_import.set_increments(1, 1)
            self.nb_entries_import.set_range(1, MAX_ENTRIES - 1)
            self.nb_entries_import.set_text(str(self.font.get_nb_entries()))
            dialog.set_attached_to(MainController.window())
            dialog.set_transient_for(MainController.window())
            resp = dialog.run()
            dialog.hide()
            if resp == Gtk.ResponseType.OK and fn is not None:
                try:
                    lst_entries: list[Image.Image | None] = []
                    for i in range(int(self.nb_entries_import.get_text())):
                        path = os.path.join(fn, f"{i:0>4}.png")
                        if os.path.exists(path):
                            lst_entries.append(Image.open(path, "r"))
                        else:
                            lst_entries.append(None)
                    self.font.set_entries(lst_entries)
                    self.module.mark_font_as_modified(self.item_data)
                except Exception as err:
                    display_error(sys.exc_info(), str(err), _("Error importing font."))
                self._init_font()

    def _init_font(self):
        self.entry_id.set_text(str(0))
        self.entry_id.set_increments(1, 1)
        self.entry_id.set_range(0, self.font.get_nb_entries() - 1)
        self._switch_entry()

    @Gtk.Template.Callback()
    def on_entry_id_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        if val < 0:
            val = 0
            widget.set_text(str(val))
        elif val >= self.font.get_nb_entries():
            val = self.font.get_nb_entries() - 1
            widget.set_text(str(val))
        self._switch_entry()

    @Gtk.Template.Callback()
    def on_nb_entries_import_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        if val <= 0:
            val = 1
            widget.set_text(str(val))
        elif val >= MAX_ENTRIES + 1:
            val = MAX_ENTRIES
            widget.set_text(str(val))

    def _switch_entry(self):
        surface = self.font.get_entry(int(self.entry_id.get_text()))
        stack = self.entry_stack
        if surface:
            stack.set_visible_child(self.entry_viewer)
            surface = surface.resize((surface.width * IMAGE_ZOOM, surface.height * IMAGE_ZOOM))
            self.surface = pil_to_cairo_surface(surface.convert("RGBA"))
            self.draw_area.queue_draw()
        else:
            stack.set_visible_child(self.no_entry_label)
            self.surface = pil_to_cairo_surface(Image.new("RGBA", size=(1, 1)))

    def exec_draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
