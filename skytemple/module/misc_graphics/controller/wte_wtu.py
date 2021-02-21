#  Copyright 2020-2021 Parakoopa and the SkyTemple Contributors
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
import os
import sys
from typing import TYPE_CHECKING, Optional, Tuple, List

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_files.graphics.wte.model import Wte, WteImageType
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
from skytemple_files.common.i18n_util import f, _


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
        dialog = Gtk.FileChooserNative.new(
            _("Export image as PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            _("_Save"), None
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.png'
            if self.wte.has_image():
                self.wte.to_pil_canvas().save(fn)
            else:
                self.wte.to_pil_palette().save(fn)
            
    def on_import_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_import_settings')
        self.builder.get_object('image_path_setting').unselect_all()
        # Init available categories
        cb_store: Gtk.ListStore = self.builder.get_object('image_type_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('image_type_setting')
        self._fill_available_image_types_into_store(cb_store)

        # Set current WTE file settings by default
        for i, depth in  enumerate(cb_store):
            if self.wte.image_type.value==depth[0]:
                cb.set_active(i)
        self.builder.get_object('chk_discard_palette').set_active(not self.wte.has_palette())
        
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            img_fn : str = self.builder.get_object('image_path_setting').get_filename()
            try:
                img_pil = Image.open(img_fn, 'r')
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Filename not specified.")
                )
            if img_fn is not None:
                depth : int = cb_store[cb.get_active_iter()][0]
                discard : bool = self.builder.get_object('chk_discard_palette').get_active()
                try:
                    self.wte.from_pil(img_pil, WteImageType(depth), discard)
                except ValueError as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        _("Imported image size too big.")
                    )
                except AttributeError as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        _("Not an indexed image.")
                    )
                self.module.mark_wte_as_modified(self.item, self.wte, self.wtu)
                self._init_wte()
                self._reinit_image()
                if self.wtu:
                    self.wtu.image_mode = self.wte.get_mode()

    def _init_wte(self):
        info_palette_only: Gtk.InfoBar = self.builder.get_object('info_palette_only')
        info_palette_only.set_revealed(not self.wte.has_image())
        info_palette_only.set_message_type(Gtk.MessageType.WARNING)
        info_image_only: Gtk.InfoBar = self.builder.get_object('info_image_only')
        info_image_only.set_revealed(not self.wte.has_palette())
        info_image_only.set_message_type(Gtk.MessageType.WARNING)

        self.builder.get_object('wte_palette_variant').set_text(str(0))
        self.builder.get_object('wte_palette_variant').set_increments(1,1)
        self.builder.get_object('wte_palette_variant').set_range(0, self.wte.nb_palette_variants()-1)

        dimensions : Tuple[int, int] = self.wte.actual_dimensions()
        if self.wte.has_image():
            self.builder.get_object('lbl_canvas_size').set_text(f"{self.wte.width}x{self.wte.height} [{dimensions[0]}x{dimensions[1]}]")
        else:
            self.builder.get_object('lbl_canvas_size').set_text(f"{self.wte.width}x{self.wte.height} [No image data]")
        self.builder.get_object('lbl_image_type').set_text(self.wte.image_type.explanation)

    def _init_wtu(self):
        wtu_stack: Gtk.Stack = self.builder.get_object('wtu_stack')
        if not self.wtu:
            wtu_stack.set_visible_child(self.builder.get_object('no_wtu_label'))
        else:
            wtu_stack.set_visible_child(self.builder.get_object('wtu_editor'))
            wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
            for entry in self.wtu.entries:
                wtu_store.append([str(entry.x), str(entry.y), str(entry.width), str(entry.height)])

    def _reinit_image(self):
        try:
            val = int(self.builder.get_object('wte_palette_variant').get_text())
        except ValueError:
            val = 0
        self.surface = pil_to_cairo_surface(self.wte.to_pil_canvas(val).convert('RGBA'))
        self.builder.get_object('draw').queue_draw()

    def on_wte_variant_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        
        if val<0:
            val = 0
            widget.set_text(str(val))
        elif val>=self.wte.nb_palette_variants():
            val=self.wte.nb_palette_variants()-1
            widget.set_text(str(val))
        self._reinit_image()

    def on_wtu_x_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][0] = text
        self._regenerate_wtu()

    def on_wtu_y_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][1] = text
        self._regenerate_wtu()

    def on_wtu_width_edited(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        wtu_store: Gtk.ListStore = self.builder.get_object('wtu_store')
        wtu_store[path][2] = text
        self._regenerate_wtu()

    def on_wtu_height_edited(self, widget, path, text):
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
        self._regenerate_wtu()

    def on_btn_remove_clicked(self, *args):
        # Deletes all selected WTU entries
        # Allows multiple deletions
        active_rows : List[Gtk.TreePath] = self.builder.get_object('wtu_tree').get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = self.builder.get_object('wtu_store')
        for x in reversed(sorted(active_rows, key=lambda x:x.get_indices())):
            del store[x.get_indices()[0]]
        self._regenerate_wtu()

    def on_wtu_tree_selection_changed(self, *args):
        self._reinit_image()
    def on_clear_image_path_clicked(self, *args):
        self.builder.get_object('image_path_setting').unselect_all()
    
    def _fill_available_image_types_into_store(self, cb_store):
        image_types = [
            v for v in WteImageType
        ]
        # Init combobox
        cb_store.clear()
        for img_type in image_types:
            cb_store.append([img_type.value, img_type.explanation])
    
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
            # Draw rectangles on the WTE image representing the selected WTU entries
            # Allows multiple selections
            active_rows : List[Gtk.TreePath] = self.builder.get_object('wtu_tree').get_selection().get_selected_rows()[1]
            store: Gtk.ListStore = self.builder.get_object('wtu_store')
            for x in active_rows:
                row = store[x.get_indices()[0]]
                ctx.set_line_width(4)
                ctx.set_source_rgba(1,1,1, 1)
                ctx.rectangle(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
                ctx.stroke()
                ctx.set_line_width(2)
                ctx.set_source_rgba(0,0,0, 1)
                ctx.rectangle(int(row[0]), int(row[1]), int(row[2]), int(row[3]))
                ctx.stroke()
        return True
