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
import math

import cairo

from skytemple.core.mapbg_util.drawer_plugin.abstract import AbstractDrawerPlugin


class GridDrawerPlugin(AbstractDrawerPlugin):
    """This plugin draws a grid."""
    def __init__(self, dist_x: int, dist_y: int, color=(0.2, 0.2, 0.2, 0.25), offset_x=0, offset_y=0):
        self.dist_x = dist_x
        self.dist_y = dist_y
        self.color = color
        self.offset_y = offset_y
        self.offset_x = offset_x

    def draw(self, ctx: cairo.Context, size_w: int, size_h: int, mouse_x: int, mouse_y: int):
        ctx.translate(self.offset_x, self.offset_y)
        ctx.set_line_width(1)
        ctx.set_source_rgba(*self.color)
        width_in_lines = int(size_w / self.dist_x) - int(math.floor(self.offset_x / self.dist_x))
        height_in_lines = int(size_h / self.dist_y) - int(math.floor(self.offset_y / self.dist_y))
        for i in range(0, width_in_lines * height_in_lines):
            ctx.rectangle(
                0, 0,
                self.dist_x,
                self.dist_y
            )
            ctx.stroke()
            if (i + 1) % width_in_lines == 0:
                # Move to beginning of next line
                ctx.translate(-self.dist_x * (width_in_lines - 1), self.dist_y)
            else:
                # Move to next tile in line
                ctx.translate(self.dist_x, 0)
        # Move back to beginning
        ctx.translate(0, -self.dist_y * height_in_lines)
        ctx.translate(-self.offset_x, -self.offset_y)
