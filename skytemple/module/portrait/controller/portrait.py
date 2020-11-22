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
import math
import os
import re
import sys
from functools import partial
from typing import TYPE_CHECKING

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple.module.portrait.sprite_bot_sheet import SpriteBotSheet

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.graphics.kao.model import SUBENTRIES, KaoImage

if TYPE_CHECKING:
    from skytemple.module.portrait.module import PortraitModule
logger = logging.getLogger(__name__)


class PortraitController(AbstractController):
    def __init__(self, module: 'PortraitModule', item_id: int, mark_as_modified_cb):
        self.module = module
        self.item_id = item_id
        self._portrait_provider = self.module.get_portrait_provider()
        self._draws = []
        self._mark_as_modified_cb = mark_as_modified_cb
        self.kao = self.module.kao

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'portrait.glade')
        self.builder.connect_signals(self)

        for index, subindex, kao in self.kao:
            gui_number = subindex + 1
            portrait_name = self._get_portrait_name(subindex)
            self.builder.get_object(f'portrait_label{gui_number}').set_text(portrait_name)
            draw = self.builder.get_object(f'portrait_draw{gui_number}')
            self._draws.append(draw)
            draw.connect('draw', partial(self.on_draw, subindex))

        return self.builder.get_object('box_main')

    def on_draw(self, subindex: int, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        portrait = self._portrait_provider.get(self.item_id, subindex,
                                               lambda: GLib.idle_add(widget.queue_draw), False)
        ctx.set_source_rgb(1, 1, 1)
        ctx.rectangle(0, 0, *widget.get_size_request())
        ctx.fill()
        ctx.scale(scale, scale)
        ctx.set_source_surface(portrait)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.scale(1 / scale, 1 / scale)
        return True

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        w.get_menu().popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def on_import_clicked(self, w: Gtk.MenuToolButton):
        w.get_menu().popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def on_separate_export_activate(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Export all portraits as PNGs...",
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            base_filename = os.path.join(fn, f'{self.item_id + 1}')
            for subindex in range(0, SUBENTRIES):
                kao = self.kao.get(self.item_id, subindex)
                if kao:
                    filename = f'{base_filename}_{subindex}.png'
                    img = kao.get()
                    img.save(filename)

    def on_separate_import_activate(self, *args):
        md = Gtk.MessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            f"To import, select a directory to import from. Files with the pattern '{self.item_id + 1}_XX.png'\n"
            f"will be imported, where XX is a number between 0 and 40.",
            title="Import Portraits"
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserDialog(
            "Import portraits from PNGs...",
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            r = re.compile(rf"{self.item_id + 1}_(\d+)\.png", re.IGNORECASE)
            imgs = {int(match[1]): name
                    for match, name in self._try_match_import(r, os.listdir(fn))
                    if match is not None and int(match[1]) <= 40}
            for subindex, image_fn in imgs.items():
                try:
                    with open(os.path.join(fn, image_fn), 'rb') as f:
                        image = Image.open(f)
                        kao = self.kao.get(self.item_id, subindex)
                        if kao:
                            # Replace
                            kao.set(image)
                        else:
                            # New
                            self.kao.set(self.item_id, subindex, KaoImage.new(image))
                except Exception as err:
                    name = self._get_portrait_name(subindex)
                    logger.error(f"Failed importing image '{name}'.", exc_info=err)
                    display_error(
                        sys.exc_info(),
                        f'Failed importing image "{name}":\n{err}',
                        f"Error for '{name}'."
                    )
            # Re-render
            self._portrait_provider.reset()
            for draw in self._draws:
                draw.queue_draw()
            # Mark as modified
            self.module.mark_as_modified()
            self._mark_as_modified_cb()

    def on_spritebot_export_activate(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Export portrait as PNG sheet...",
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        if '.' not in fn:
            fn += '.png'
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            SpriteBotSheet.create(self.kao, self.item_id).save(fn)

    def on_spritebot_import_activate(self, *args):
        dialog = Gtk.FileChooserDialog(
            "Import portraits from PNG sheet...",
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.OK:
            try:
                for subindex, image in SpriteBotSheet.load(fn, self._get_portrait_name):
                    try:
                        kao = self.kao.get(self.item_id, subindex)
                        if kao:
                            # Replace
                            kao.set(image)
                        else:
                            # New
                            self.kao.set(self.item_id, subindex, KaoImage.new(image))
                    except Exception as err:
                        name = self._get_portrait_name(subindex)
                        logger.error(f"Failed importing image '{name}'.", exc_info=err)
                        display_error(
                            sys.exc_info(),
                            f'Failed importing image "{name}":\n{err}',
                            f"Error for '{name}'."
                        )
            except Exception as err:
                logger.error(f"Failed importing portraits sheet: {err}", exc_info=err)
                display_error(
                    sys.exc_info(),
                    f'Failed importing portraits sheet:\n{err}',
                    f"Could not import."
                )
            # Re-render
            self._portrait_provider.reset()
            for draw in self._draws:
                draw.queue_draw()
            # Mark as modified
            self.module.mark_as_modified()
            self._mark_as_modified_cb()

    def _try_match_import(self, r, names):
        for name in names:
            yield r.match(name), name

    def _get_portrait_name(self, subindex):
        portrait_name = self.module.project.get_rom_module().get_static_data().script_data.face_names__by_id[
            math.floor(subindex / 2)
        ].name.replace('-', '_')
        portrait_name = f'{subindex}: {portrait_name}'
        if subindex % 2 != 0:
            portrait_name += ' (flip)'
        return portrait_name
