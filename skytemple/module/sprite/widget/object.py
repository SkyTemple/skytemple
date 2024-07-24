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
from typing import TYPE_CHECKING, cast
import cairo
from skytemple.core.ui_utils import data_dir
from skytemple_files.common.i18n_util import _
from gi.repository import Gtk, GLib
from skytemple.controller.main import MainController
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.sprite.module import SpriteModule
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "sprite", "object.ui"))
class StSpriteObjectPage(Gtk.Box):
    __gtype_name__ = "StSpriteObjectPage"
    module: SpriteModule
    item_data: str
    file_name: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    draw_sprite: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    explanation_text: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    button_import: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    export: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    importimage: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, module: SpriteModule, item_data: str):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._sprite_provider = module.get_sprite_provider()
        self._draws: list[Gtk.DrawingArea] = []
        self._surfaces: list[cairo.Surface] = []
        self._sprite_provider.reset()
        self.file_name.set_text(self.item_data)
        if self.module.get_gfxcrunch().is_available():  # noqa: W291
            self.explanation_text.set_markup(
                _(
                    "SkyTemple can not edit sprites. \nHowever you can export the sprite in the gfxcrunch format and import it back again.\nWarning: SkyTemple does not validate the files you import."
                )
            )

    @Gtk.Template.Callback()
    def on_explanation_text_activate_link(self, *args):
        self.module.open_gfxcrunch_page()

    @Gtk.Template.Callback()
    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        sprite, x, y, w, h = self._sprite_provider.get_for_object(
            self.item_data[:-4], lambda: GLib.idle_add(widget.queue_draw)
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

    @Gtk.Template.Callback()
    def on_export_clicked(self, *args):
        self.module.export_a_sprite(self.module.get_object_sprite_raw(self.item_data))

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, *args):
        sprite = self.module.import_a_sprite()
        if sprite is None:
            return
        self.module.save_object_sprite(self.item_data, sprite)
        MainController.reload_view()

    @Gtk.Template.Callback()
    def on_importimage_clicked(self, *args):
        sprite = self.module.import_an_image()
        if sprite is None:
            return
        self.module.save_object_sprite(self.item_data, sprite)
        MainController.reload_view()
