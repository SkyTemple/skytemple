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
from typing import TYPE_CHECKING, Optional

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
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
from skytemple_files.common.i18n_util import f, _

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule


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
        w.get_menu().popup(None, None, None, None, 0, Gtk.get_current_event_time())
            
    def on_import_clicked(self, w: Gtk.MenuToolButton):
        w.get_menu().popup(None, None, None, None, 0, Gtk.get_current_event_time())
    
    def on_export_minimized_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export zmappat minimized in folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            for v in ZMappaTVariation:
                fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.min.png')
                fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.min.png')
                surface = self.zmappat.to_pil_tiles_minimized(v).save(fn_tiles, "PNG")
                mask = self.zmappat.to_pil_masks_minimized(v).save(fn_masks, "PNG")

    def on_export_full_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export full zmappat in folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            for v in ZMappaTVariation:
                fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.png')
                fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.png')
                surface = self.zmappat.to_pil_tiles(v).save(fn_tiles, "PNG")
                mask = self.zmappat.to_pil_masks(v).save(fn_masks, "PNG")
        
    def on_import_minimized_activate(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("To import, select a folder containing all the image files that were created when exporting the minimized version.\n"
              "IMPORTANT: All image files must be indexed PNGs and use the same palette!"),
            title=_("Import Minimized Version")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import zmappat minimized from folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                imgs = [None]*ZMAPPAT_NB_VARIATIONS
                masks = [None]*ZMAPPAT_NB_VARIATIONS
                for v in ZMappaTVariation:
                    fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.min.png')
                    fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.min.png')
                    imgs[v.value] = Image.open(fn_tiles, 'r')
                    masks[v.value] = Image.open(fn_masks, 'r')
                self.zmappat.from_pil_minimized(imgs, masks)
                self.module.mark_zmappat_as_modified(self.zmappat, self.filename)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing minimized zmappat.")
                )
            self._reinit_image()
        
    def on_minimized_info_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("The game uses 4x4 'mini-tiles' tiles to render the map.\n"
              "However, as the system only uses 8x8 tiles, the game render each 8x8 tile by applying 4 mini-tiles with their respective masks.\n"
              "To do this, all mini-tiles have been duplicated to cover the 4 possibilites for placing the mini-tile in 8x8 tiles (top left, top right, bottom left, bottom right).\n"
              "The mask is then used to apply the mini-tile only on the correct part of the resulting 8x8 tile.\n"
              "The minimized version reduces the tileset to only 4x4 mini-tiles and handles the duplication when importing.\n"
              "But remember that the full tileset allows more exploits as you can render tiles differently depending on where they are placed."),
            title=_("Minimized Version Info")
        )
        md.run()
        md.destroy()
        
    def on_import_full_activate(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("To import, select a folder containing all the image files that were created when exporting the full tileset."),
            title=_("Import Full Tileset")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import full zmappat from folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                imgs = [None]*ZMAPPAT_NB_VARIATIONS
                masks = [None]*ZMAPPAT_NB_VARIATIONS
                for v in ZMappaTVariation:
                    fn_tiles = os.path.join(fn, f'zmappat-{v.filename}-tiles.png')
                    fn_masks = os.path.join(fn, f'zmappat-{v.filename}-masks.png')
                    imgs[v.value] = Image.open(fn_tiles, 'r')
                    masks[v.value] = Image.open(fn_masks, 'r')
                self.zmappat.from_pil(imgs, masks)
                self.module.mark_zmappat_as_modified(self.zmappat, self.filename)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing full zmappat.")
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
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
    def draw_masks(self, wdg, ctx: cairo.Context, *args):
        if self.mask:
            wdg.set_size_request(self.mask.get_width(), self.mask.get_height())
            ctx.fill()
            ctx.set_source_surface(self.mask, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
