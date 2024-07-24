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

import os
from typing import Any

import cairo
from gi.repository import Gtk

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.sprite_provider import SpriteAndOffsetAndDims
from skytemple.core.ui_utils import data_dir
from skytemple.init_locale import LocalePatchedGtkTemplate

ORANGE_RGB = (1, 0.65, 0)


class StSpriteData:
    __slots__ = [
        "load_fn",
        "parameters",
        "passed_fn_supports_callback",
        "tint_placeholder",
        "scale",
    ]
    # (*parameters, callback_fn) -> SpriteAndOffsetAndDims
    load_fn: Any  # TODO: type. Type of function is first parameters, then callback.
    parameters: Any
    # If True, will pass a reload callback at end of parameters. If False, will not.
    passed_fn_supports_callback: bool
    # If True, will tint this sprite in orange.
    tint_placeholder: bool
    scale: int

    def __init__(
        self,
        load_fn: Any,
        parameters: Any,
        passed_fn_supports_callback=True,
        tint_placeholder=False,
        scale=1,
    ):
        self.load_fn = load_fn
        self.parameters = parameters
        self.passed_fn_supports_callback = passed_fn_supports_callback
        self.tint_placeholder = tint_placeholder
        self.scale = scale


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "sprite.ui"))
class StSprite(Gtk.DrawingArea):
    """
    Draws a sprite using SpriteProvider (or any compatible loading function). While it is loading,
    draws a placeholder (see SpriteProvider).
    """

    __gtype_name__ = "StSprite"

    module: AbstractModule
    sprite_data: StSpriteData
    loaded_sprite: SpriteAndOffsetAndDims | None

    def __init__(self, sprite_data: StSpriteData):
        super().__init__()

        assert isinstance(sprite_data, StSpriteData)

        self.sprite_data = sprite_data
        self.loaded_sprite = None

        self.reload_sprite()

    def reload_sprite(self):
        if self.sprite_data.passed_fn_supports_callback:
            self.loaded_sprite = self.sprite_data.load_fn(*self.sprite_data.parameters, self.reload_sprite)
        else:
            self.loaded_sprite = self.sprite_data.load_fn(*self.sprite_data.parameters)
        self.queue_draw()

    @Gtk.Template.Callback()
    def on_draw(self, _, ctx: cairo.Context):
        if self.loaded_sprite is None:
            return
        sprite, x, y, w, h = self.loaded_sprite

        if self.sprite_data.tint_placeholder:
            sp_ctx = cairo.Context(sprite)
            sp_ctx.set_source_rgb(*ORANGE_RGB)
            sp_ctx.rectangle(0, 0, w, h)
            sp_ctx.set_operator(cairo.OPERATOR_IN)
            sp_ctx.fill()

        if self.sprite_data.scale != 1:
            ctx.scale(self.sprite_data.scale, self.sprite_data.scale)
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if self.sprite_data.scale != 1:
            ctx.scale(1 / self.sprite_data.scale, 1 / self.sprite_data.scale)
        if self.get_size_request() != (
            w * self.sprite_data.scale,
            h * self.sprite_data.scale,
        ):
            self.set_size_request(w * self.sprite_data.scale, h * self.sprite_data.scale)
        return True
