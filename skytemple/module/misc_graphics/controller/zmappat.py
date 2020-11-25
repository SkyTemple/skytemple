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
import os
import sys
from typing import TYPE_CHECKING, Optional

import cairo

from skytemple.core.error_handler import display_error
from skytemple_files.graphics.zmappat.model import ZMappaT, ZMappaTVariation
from skytemple_files.graphics.zmappat import *

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController

logger = logging.getLogger(__name__)


class ZMappaTController(AbstractController):
    def __init__(self, module: 'MiscGraphicsModule', item: str):
        self.module = module
        self.filename = item
        self.zmappat: ZMappaT = self.module.get_dungeon_bin_file(self.filename)

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'zmappat.glade')
        self._init_zmappat()
        self._reinit_image()
        self.builder.connect_signals(self)
        self.builder.get_object('draw_tiles').connect('draw', self.draw_tiles)
        self.builder.get_object('draw_masks').connect('draw', self.draw_masks)
        return self.builder.get_object('editor')

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserDialog(
            "Export zmappat in folder...",
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            for v in ZMappaTVariation:
                fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.png')
                fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.png')
                surface = self.zmappat.to_pil_tiles_minimized(v).save(fn_tiles, "PNG")
                mask = self.zmappat.to_pil_masks_minimized(v).save(fn_masks, "PNG")
        pass
            
    def on_import_clicked(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Import zmappat from folder...",
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            try:
                imgs = [None]*ZMAPPAT_NB_VARIATIONS
                masks = [None]*ZMAPPAT_NB_VARIATIONS
                for v in ZMappaTVariation:
                    fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.png')
                    fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.png')
                    imgs[v.value] = Image.open(fn_tiles, 'r')
                    masks[v.value] = Image.open(fn_masks, 'r')
                self.zmappat.from_pil_minimized(imgs, masks)
                self.module.mark_zmappat_as_modified(self.zmappat, self.filename)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    "Error importing zmappat."
                )
            self._reinit_image()
            
    def _init_zmappat(self):
        # Init available variations
        cb_store: Gtk.ListStore = self.builder.get_object('variation_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('zmappat_variation')
        self._fill_available_zmappat_variations_into_store(cb_store)
        
        cb.set_active(0)
        
    def _reinit_image(self):
        cb_store: Gtk.ListStore = self.builder.get_object('variation_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('zmappat_variation')
        v : int = cb_store[cb.get_active_iter()][0]
        if self.builder.get_object('switch_minimized').get_active():
            surface = self.zmappat.to_pil_tiles_minimized(ZMappaTVariation(v))
            mask = self.zmappat.to_pil_masks_minimized(ZMappaTVariation(v))
        else:
            surface = self.zmappat.to_pil_tiles(ZMappaTVariation(v))
            mask = self.zmappat.to_pil_masks(ZMappaTVariation(v))
        surface = surface.resize((surface.width*4, surface.height*4))
        self.surface = pil_to_cairo_surface(surface.convert('RGBA'))
        mask = mask.resize((mask.width*4, mask.height*4))
        self.mask = pil_to_cairo_surface(mask.convert('RGBA'))
        self.builder.get_object('draw_tiles').queue_draw()
        self.builder.get_object('draw_masks').queue_draw()

    def on_switch_minimized_state_set(self, *args):
        self._reinit_image()
        
    def on_zmappat_variation_changed(self, widget):
        self._reinit_image()
    
    def _fill_available_zmappat_variations_into_store(self, cb_store):
        variations = [
            v for v in ZMappaTVariation
        ]
        # Init combobox
        cb_store.clear()
        for v in variations:
            cb_store.append([v.value, v.description])
    
    def draw_tiles(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
    def draw_masks(self, wdg, ctx: cairo.Context, *args):
        if self.mask:
            ctx.fill()
            ctx.set_source_surface(self.mask, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
