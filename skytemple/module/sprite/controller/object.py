#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
from typing import TYPE_CHECKING, List

import cairo

from skytemple.core.ui_utils import builder_get_assert
from skytemple_files.common.i18n_util import f, _

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
        self._draws: List[Gtk.DrawingArea] = []
        self._surfaces: List[cairo.Surface] = []

        self.builder: Gtk.Builder = None  # type: ignore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'object.glade')
        self.builder.connect_signals(self)
        self._sprite_provider.reset()
        builder_get_assert(self.builder, Gtk.Label, 'file_name').set_text(self.item_id)
        if self.module.get_gfxcrunch().is_available():
            builder_get_assert(self.builder, Gtk.Label, 'explanation_text').set_markup(_("""SkyTemple can not edit sprites. 
However you can export the sprite in the gfxcrunch format and import it back again.
Warning: SkyTemple does not validate the files you import."""))

        return builder_get_assert(self.builder, Gtk.Widget, 'main_box')

    def on_explanation_text_activate_link(self, *args):
        self.module.open_gfxcrunch_page()

    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        sprite, x, y, w, h = self._sprite_provider.get_for_object(
            self.item_id[:-4], lambda: GLib.idle_add(widget.queue_draw)
        )
        ctx.scale(scale, scale)
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ww, wh = widget.get_size_request()
        if ww < w or wh < h:
            widget.set_size_request(w * scale, h * scale)
        ctx.scale(1 / scale, 1 / scale)
        return True

    def on_export_clicked(self, *args):
        self.module.export_a_sprite(self.module.get_object_sprite_raw(self.item_id))

    def on_import_clicked(self, *args):
        sprite = self.module.import_a_sprite()
        if sprite is None:
            return
        self.module.save_object_sprite(self.item_id, sprite)
        MainController.reload_view()

    def on_importimage_clicked(self, *args):
        sprite = self.module.import_an_image()
        if sprite is None:
            return
        self.module.save_object_sprite(self.item_id, sprite)
        MainController.reload_view()
