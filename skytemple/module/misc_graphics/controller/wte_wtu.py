#  Copyright 2020 Parakoopa
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
import logging
import sys
from typing import TYPE_CHECKING, Optional

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_files.graphics.wte.model import Wte, ColorDepth
from skytemple_files.graphics.wtu.model import Wtu, WtuEntry

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule, WteOpenSpec

logger = logging.getLogger(__name__)


class WteWtuController(AbstractController):
    def __init__(self, module: 'MiscGraphicsModule', item: 'WteOpenSpec'):
        self.module = module
        self.item = item
        self.wtu: Optional[Wtu] = None
        if item.in_dungeon_bin:
            self.wte: Wte = self.module.get_dungeon_bin_file(item.wte_filename)
            if item.wtu_filename is not None:
                self.wtu = self.module.get_dungeon_bin_file(item.wtu_filename)
        else:
            self.wte: Wte = self.module.get_wte(item.wte_filename)
            if item.wtu_filename is not None:
                self.wtu = self.module.get_wtu(item.wtu_filename)

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'wte_wtu.glade')
        self._init_wtu()
        self._reinit_image()
        self._init_wte()
        self.builder.connect_signals(self)
        self.builder.get_object('draw').connect('draw', self.draw)
        return self.builder.get_object('editor')

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        w.get_menu().popup(None, None, None, None, 0, Gtk.get_current_event_time())
        
    def on_palette_export_clicked(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Export palette as PNG...",
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            if '.' not in fn:
                fn += '.png'
            self.wte.to_pil_palette().save(fn)
            
    def on_image_export_clicked(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Export image as PNG...",
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            if '.' not in fn:
                fn += '.png'
            self.wte.to_pil_canvas(0).save(fn)

    def on_import_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_import_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.APPLY:
            img_fn : Optional[str] = dialog.get_object('image_path_setting').get_filename()
            pal_fn : Optional[str] = dialog.get_object('palette_path_setting').get_filename()
            img_pil : Optional[Image.Image] = None
            if img_fn!=None:
                try:
                    img_pil = Image.open(img_fn, 'r')
                except Exception as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        "Error importing the image."
                    )
            if pal_fn!=None:
                try:
                    img_pil = Image.open(pal_fn, 'r')
                except Exception as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        "Error importing the palette."
                    )
            self.wte.from_pil(img_fn, pal_fn, ColorDepth.COLOR_4BPP)
            self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)
            self._reinit_image()
            if self.wtu:
                self.wtu.image_mode = self.wte.get_mode()

    def _init_wte(self):
        info_weird: Gtk.InfoBar = self.builder.get_object('info_weird')
        info_weird.set_revealed(self.wte.is_weird)
        info_weird.set_message_type(Gtk.MessageType.WARNING)

        self.builder.get_object('wte_variation').set_text(str(0))
        self.builder.get_object('wte_variation').set_increments(1,1)
        self.builder.get_object('wte_variation').set_range(0, self.wte.max_variation()-1)
        
        self.builder.get_object('wte_canvas_width').set_text(str(self.wte.width))
        self.builder.get_object('wte_canvas_height').set_text(str(self.wte.height))

    def _init_wtu(self):
        wtu_stack: Gtk.Stack = self.builder.get_object('wtu_stack')
        if not self.wtu:
            wtu_stack.set_visible_child(self.builder.get_object('no_wtu_label'))
        else:
            wtu_stack.set_visible_child(self.builder.get_object('wtu_editor'))
            self.builder.get_object('wtu_unkc').set_text(str(self.wtu.unkC))
            wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
            for entry in self.wtu.entries:
                wtu_store.append([str(entry.unk0), str(entry.unk1), str(entry.unk2), str(entry.unk3)])

    def _reinit_image(self):
        try:
            val = int(self.builder.get_object('wte_variation').get_text())
        except ValueError:
            val = 0
        self.surface = pil_to_cairo_surface(self.wte.to_pil(val).convert('RGBA'))
        self.builder.get_object('draw').queue_draw()

    def on_wte_variation_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        
        if val<0:
            val = 0
            widget.set_text(str(val))
        elif val>=self.wte.max_variation():
            val=self.wte.max_variation()-1
            widget.set_text(str(val))
        self._reinit_image()
        
    def on_wte_canvas_width_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        self.wte.width = val
        self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)

    def on_wte_canvas_height_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        self.wte.height = val
        self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)

    def on_wtu_unkc_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        self.wtu.unkC = val
        self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)

    def on_wtu_unk0_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][0] = text
        self._regenerate_wtu()

    def on_wtu_unk1_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][1] = text
        self._regenerate_wtu()

    def on_wtu_unk2_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][2] = text
        self._regenerate_wtu()

    def on_wtu_unk3_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][3] = text
        self._regenerate_wtu()

    def on_btn_add_clicked(self, *args):
        store: Gtk.ListStore = self.builder.get_object('wtu_store')
        store.append(["0", "0", "0", "0"])

    def on_btn_remove_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('wtu_store')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            model.remove(treeiter)

    def _regenerate_wtu(self):
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        self.wtu.entries = []
        for row in wtu_store:
            self.wtu.entries.append(WtuEntry(
                int(row[0]), int(row[1]), int(row[2]), int(row[3])
            ))
        self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)

    def draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
