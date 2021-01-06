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
import re
import sys
from functools import partial
from typing import TYPE_CHECKING

import cairo

from skytemple.core.error_handler import display_error

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController

if TYPE_CHECKING:
    from skytemple.module.sprite.module import SpriteModule

logger = logging.getLogger(__name__)


class ObjectController(AbstractController):
    def __init__(self, module: 'SpriteModule', item_id: str):
        self.module = module
        self.item_id = item_id
        self._sprite_provider = module.get_sprite_provider()
        self._draws = []
        self._surfaces = []

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'object.glade')
        self.builder.connect_signals(self)
        self._sprite_provider.reset()
        self.builder.get_object('file_name').set_text(self.item_id)

        return self.builder.get_object('main_box')

    def on_explanation_text_activate_link(self, *args):
        self.module.open_gfxcrunch_page()

    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        sprite, x, y, w, h = self._sprite_provider.get_for_object(
            self.item_id[:-4], lambda: GLib.idle_add(widget.queue_draw)
        )
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if widget.get_size_request() != (w, h):
            widget.set_size_request(w, h)
        return True

    def on_export_clicked(self, *args):
        pass  # todo
        dialog = Gtk.FileChooserNative.new(
            "Export WAN sprite...",
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )
        filter = Gtk.FileFilter()
        filter.set_name("WAN sprite (*.wan)")
        filter.add_pattern("*.wan")
        dialog.add_filter(filter)

        response = dialog.run()
        fn = dialog.get_filename()

        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.wan'
            with open(fn, 'wb') as f:
                f.write(self.module.get_object_sprite_raw(self.item_id))

    def on_import_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            "Import WAN sprite...",
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.wan'
            with open(fn, 'rb') as f:
                self.module.save_object_sprite(self.item_id, f.read())
            MainController.reload_view()
