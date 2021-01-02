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
from typing import Callable

import cairo

from skytemple.core.mapbg_util.drawer_plugin.abstract import AbstractDrawerPlugin


class SelectionDrawerPlugin(AbstractDrawerPlugin):
    def __init__(self, brush_width: int, brush_height: int, callback_draw_content: Callable):
        self.brush_width = brush_width
        self.brush_height = brush_height
        self.callback_draw_content = callback_draw_content

    def set_size(self, brush_width: int, brush_height: int):
        self.brush_width = brush_width
        self.brush_height = brush_height

    def draw(self, ctx: cairo.Context, size_w: int, size_h: int, mouse_x: int, mouse_y: int, ignore_obb=False):
        if ignore_obb or (mouse_x < size_w and mouse_y < size_h):
            # Background
            ctx.set_source_rgba(0, 0, 1, 0.3)
            ctx.rectangle(
                mouse_x - 3, mouse_y - 3,
                self.brush_width + 6,
                self.brush_height + 6
            )
            ctx.fill()
            # Draw content
            self.callback_draw_content(ctx, mouse_x, mouse_y)
