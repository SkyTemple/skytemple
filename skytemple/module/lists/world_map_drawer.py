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
from typing import Tuple, Union, Callable, Optional, List, Dict

import cairo
from gi.repository import Gtk

from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.module.lists.controller import WORLD_MAP_DEFAULT_ID
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.hardcoded.dungeons import MapMarkerPlacement


ALPHA_T = 0.3
RAD = 2
COLOR_MARKERS = (1.0, 0.3, 0)
COLOR_SELECT = (0.7, 0.7, 1, 0.7)
Num = Union[int, float]
Color = Tuple[Num, Num, Num]


class WorldMapDrawer:
    def __init__(
            self, draw_area: Gtk.Widget, markers: List[MapMarkerPlacement],
            cb_dungeon_name: Callable[[int], str], scale: int
    ):
        self.draw_area = draw_area

        self.markers: List[MapMarkerPlacement] = markers
        self.markers_at_pos: Dict[Tuple[int, int], List[MapMarkerPlacement]] = {}
        self.map_bg = None
        self.level_id = None

        self.draw_tile_grid = True

        self._cb_dungeon_name = cb_dungeon_name

        # Interaction
        self.mouse_x = 99999
        self.mouse_y = 99999
        self._selected: Optional[MapMarkerPlacement] = None
        self._editing = None
        self._editing_pos = None
        self._hide = None

        self.tile_grid_plugin = GridDrawerPlugin(
            BPC_TILE_DIM, BPC_TILE_DIM, color=(0.2, 0.2, 0.2, 0.1)
        )

        self.scale = scale

        self.drawing_is_active = False

    def start(self):
        """Start drawing on the DrawingArea"""
        self.drawing_is_active = True
        if isinstance(self.draw_area, Gtk.DrawingArea):
            self.draw_area.connect('draw', self.draw)
        self.draw_area.queue_draw()

    def draw(self, wdg, ctx: cairo.Context):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)
        # Background
        if self.map_bg is not None:
            if self.level_id == WORLD_MAP_DEFAULT_ID:
                # We display the bottom right of the map.
                ctx.set_source_surface(self.map_bg, -504, -1008)
            else:
                ctx.set_source_surface(self.map_bg, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()

        size_w, size_h = self.draw_area.get_size_request()
        size_w /= self.scale
        size_h /= self.scale

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # Selection
        self._handle_selection(ctx)

        # RENDER MARKERS
        self.markers_at_pos = {}
        for i, marker in enumerate(self.markers):
            if marker != self._editing and marker != self._hide and marker.level_id == self.level_id and marker.reference_id <= -1:
                self._draw_marker(ctx, marker)

        if self._editing:
            # Black out
            ctx.set_source_rgba(0, 0, 0, 0.5)
            ctx.rectangle(0, 0, size_w, size_h)
            ctx.fill()
            # Render editing marker
            self._draw_marker(ctx, self._editing)

        # nah, too crowded.
        #for (x, y), list_of_markers in self.markers_at_pos.items():
        #    ms = [self.markers.index(m) for m in list_of_markers]
        #    self._draw_name(ctx, ms, x, y)
        return True

    def get_under_mouse(self) -> Optional[MapMarkerPlacement]:
        """
        Returns the first marker under the mouse position, if any.
        """
        for i, marker in enumerate(self.markers):
            if marker.level_id == self.level_id and marker.reference_id <= -1:
                bb = (marker.x - RAD * 2, marker.y - RAD * 2, RAD * 4, RAD * 4)
                if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                    return marker
        return None

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        if self._selected is not None and self._selected__drag is not None:
            # Draw dragged:
            x, y = self.get_current_drag_entity_pos()
            self._draw_marker(ctx, self._selected, x, y)

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def _draw_marker(self, ctx: cairo.Context, marker: MapMarkerPlacement, x=None, y=None):
        x, y = self._get_marker_xy(marker, x, y)
        if (x, y) not in self.markers_at_pos:
            self.markers_at_pos[(x, y)] = []
        self.markers_at_pos[(x, y)].append(marker)

        # Outline + Fill
        bb_cords = (x - RAD, y - RAD, RAD * 2, RAD * 2)
        ctx.rectangle(*bb_cords)
        ctx.set_line_width(1.0)
        ctx.set_source_rgb(0, 0, 0)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*COLOR_MARKERS, 0.8)
        ctx.fill()

    def _get_marker_xy(self, marker: MapMarkerPlacement, x=None, y=None):
        if marker == self._editing:
            return self._editing_pos

        ref_marker = marker
        if marker.reference_id > -1:
            ref_marker = self.markers[marker.reference_id]
        if x is None:
            x = ref_marker.x
        if y is None:
            y = ref_marker.y

        return x, y

    def _handle_selection(self, ctx: cairo.Context):
        if self._selected is None:
            return
        if self._selected.level_id != self.level_id:
            return
        x, y = self._get_marker_xy(self._selected)
        x, y, w, h = (x - RAD * 2, y - RAD * 2,
                      RAD * 4, RAD * 4)

        ctx.set_source_rgba(0, 0, 1, 0.6)
        ctx.rectangle(x, y, w, h)
        ctx.fill()

    def _draw_name(self, ctx: cairo.Context, marker_ids: List[int], x: int, y: int):
        ctx.set_source_rgb(*COLOR_MARKERS)
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(4 * self.scale)
        ctx.move_to(x, y - 4 * self.scale)
        label = ""
        for mid in marker_ids:
            if self.markers[mid].reference_id > -1:
                dlabel = self._cb_dungeon_name(mid)
                if dlabel == '':
                    dlabel = f'{mid}'
                label += f'{dlabel}, '
        ctx.show_text(label.strip(', '))

    def set_selected(self, entity: Optional[MapMarkerPlacement]):
        self._selected = entity
        self.draw_area.queue_draw()

    def set_editing(self, entity: Optional[MapMarkerPlacement],
                    editing_pos: Tuple[int, int] = None, hide: Optional[MapMarkerPlacement] = None):
        self._editing = entity
        if editing_pos is None:
            editing_pos = (entity.x, entity.y)
        self._editing_pos = editing_pos
        self._selected = entity
        self._hide = hide
        self.draw_area.queue_draw()

    def _redraw(self):
        if self.draw_area is None or self.draw_area.get_parent() is None:
            return
        self.draw_area.queue_draw()

    @staticmethod
    def _is_in_bb(bb_x, bb_y, bb_w, bb_h, mouse_x, mouse_y):
        return bb_x <= mouse_x < bb_x + bb_w and bb_y <= mouse_y < bb_y + bb_h
