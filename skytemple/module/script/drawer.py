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
from enum import auto
from typing import Tuple, Union, Callable, Optional

import cairo
from gi.repository import Gtk

from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptDirection
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.actor import SsaActor
from skytemple_files.script.ssa_sse_sss.event import SsaEvent
from skytemple_files.script.ssa_sse_sss.model import Ssa
from skytemple_files.script.ssa_sse_sss.object import SsaObject
from skytemple_files.script.ssa_sse_sss.performer import SsaPerformer
from skytemple_files.script.ssa_sse_sss.position import ACTOR_DEFAULT_HITBOX_W, ACTOR_DEFAULT_HITBOX_H


ALPHA_T = 0.3
COLOR_ACTORS = (1.0, 0, 1.0)
COLOR_OBJECTS = (1.0, 0.627, 0)
COLOR_PERFORMER = (0, 1.0, 1.0)
COLOR_EVENTS = (0, 0, 1.0)
COLOR_LAYER_HIGHLIGHT = (0.7, 0.7, 1, 0.7)
Num = Union[int, float]
Color = Tuple[Num, Num, Num]


class Drawer:
    def __init__(
            self, draw_area: Gtk.Widget, ssa: Ssa, cb_trigger_label: Callable[[int], str]
    ):
        self.draw_area = draw_area

        self.ssa = ssa
        self.map_bg = None

        self.draw_tile_grid = False

        # Interaction
        self.mouse_x = 99999
        self.mouse_y = 99999

        self._cb_trigger_label = cb_trigger_label
        self._sectors_visible = [True for _ in range(0, len(self.ssa.layer_list))]
        self._sectors_solo = [False for _ in range(0, len(self.ssa.layer_list))]
        self._sector_highlighted = None
        self._selected = None
        # If not None, drag is active and value is coordinate
        self._selected__drag: Optional[Tuple[int, int]] = None

        self.selection_plugin = SelectionDrawerPlugin(
            BPC_TILE_DIM, BPC_TILE_DIM, self.selection_draw_callback
        )
        self.tile_grid_plugin = GridDrawerPlugin(
            BPC_TILE_DIM, BPC_TILE_DIM,
            offset_x=-BPC_TILE_DIM / 2, offset_y=-BPC_TILE_DIM / 2
        )

        self.scale = 1

        self.drawing_is_active = False

    def start(self):
        """Start drawing on the DrawingArea"""
        self.drawing_is_active = True
        if isinstance(self.draw_area, Gtk.DrawingArea):
            self.draw_area.connect('draw', self.draw)
        self.draw_area.queue_draw()

    def draw(self, wdg, ctx: cairo.Context, do_translates=True):
        ctx.set_antialias(cairo.Antialias.NONE)
        ctx.scale(self.scale, self.scale)
        # Background
        if self.map_bg is not None:
            ctx.set_source_surface(self.map_bg, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()

        size_w, size_h = self.draw_area.get_size_request()
        size_w /= self.scale
        size_h /= self.scale

        # Black out bg a bit
        ctx.set_source_rgba(0, 0, 0, 0.5)
        ctx.rectangle(0, 0, size_w, size_h)
        ctx.fill()

        # Tile Grid
        if self.draw_tile_grid:
            self.tile_grid_plugin.draw(ctx, size_w, size_h, self.mouse_x, self.mouse_y)

        # RENDER ENTITIES
        for layer_i, layer in enumerate(self.ssa.layer_list):
            if not self._is_layer_visible(layer_i):
                continue

            for actor in layer.actors:
                if not self._is_dragged(actor):
                    bb = self.get_bb_actor(actor)
                    if actor != self._selected:
                        self._handle_layer_highlight(ctx, layer_i, *bb)
                    self._draw_hitbox_actor(ctx, actor)
                    self._draw_actor(ctx, actor, *bb)
            for obj in layer.objects:
                if not self._is_dragged(obj):
                    bb = self.get_bb_object(obj)
                    if obj != self._selected:
                        self._handle_layer_highlight(ctx, layer_i, *bb)
                    self._draw_hitbox_object(ctx, obj)
                    self._draw_object(ctx, obj, *bb)
            for trigger in layer.events:
                if not self._is_dragged(trigger):
                    bb = self.get_bb_trigger(trigger)
                    if trigger != self._selected:
                        self._handle_layer_highlight(ctx, layer_i, *bb)
                    self._draw_trigger(ctx, trigger, *bb)
            for performer in layer.performers:
                if not self._is_dragged(performer):
                    bb = self.get_bb_performer(performer)
                    if performer != self._selected:
                        self._handle_layer_highlight(ctx, layer_i, *bb)
                    self._draw_hitbox_performer(ctx, performer)
                    self._draw_performer(ctx, performer, *bb)

        # Cursor / Active selected / Place mode
        self._handle_selection(ctx)
        x, y, w, h = self._handle_drag_and_place_modes()
        self.selection_plugin.set_size(w, h)
        self.selection_plugin.draw(ctx, size_w, size_h, x, y, ignore_obb=True)

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        if self._selected is not None and self._selected__drag is not None:
            # Draw dragged:
            x, y = self.get_current_drag_entity_pos()
            if isinstance(self._selected, SsaActor):
                x, y, w, h = self.get_bb_actor(self._selected, x=x, y=y)
                self._draw_actor(ctx, self._selected, x, y, w, h)
            elif isinstance(self._selected, SsaObject):
                x, y, w, h = self.get_bb_object(self._selected, x=x, y=y)
                self._draw_object(ctx, self._selected, x, y, w, h)
            elif isinstance(self._selected, SsaPerformer):
                x, y, w, h = self.get_bb_performer(self._selected, x=x, y=y)
                self._draw_performer(ctx, self._selected, x, y, w, h)
            elif isinstance(self._selected, SsaEvent):
                x, y, w, h = self.get_bb_trigger(self._selected, x=x, y=y)
                self._draw_trigger(ctx, self._selected, x, y, w, h)

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def get_under_mouse(self) -> Tuple[Optional[int], Optional[Union[SsaActor, SsaObject, SsaPerformer, SsaEvent]]]:
        """
        Returns the first entity under the mouse position, if any, and it's layer number.
        Not visible layers are not searched.
        Elements are searched in reversed drawing order (so what's drawn on top is also taken).
        """
        for layer_i, layer in enumerate(reversed(self.ssa.layer_list)):
            layer_i = len(self.ssa.layer_list) - layer_i - 1
            if not self._is_layer_visible(layer_i):
                continue

            for performer in reversed(layer.performers):
                bb = self.get_bb_performer(performer)
                if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                    return layer_i, performer
            for trigger in reversed(layer.events):
                bb = self.get_bb_trigger(trigger)
                if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                    return layer_i, trigger
            for obj in reversed(layer.objects):
                bb = self.get_bb_object(obj)
                if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                    return layer_i, obj
            for actor in reversed(layer.actors):
                bb = self.get_bb_actor(actor)
                if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                    return layer_i, actor
        return None, None

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_scale(self, v):
        self.scale = v

    def get_bb_actor(self, actor: SsaActor, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = actor.pos.x_absolute
        if y is None:
            y = actor.pos.y_absolute
        return self._get_pmd_bounding_box(
            # todo: this needs to be sprite dims later, but use this for PLAYER, PARTNER, etc (in else case).
            x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3,
            y_offset=ACTOR_DEFAULT_HITBOX_H
        )

    def _draw_hitbox_actor(self, ctx: cairo.Context, actor: SsaActor):
        coords_hitbox = self._get_pmd_bounding_box(
            actor.pos.x_absolute, actor.pos.y_absolute, ACTOR_DEFAULT_HITBOX_W, ACTOR_DEFAULT_HITBOX_H
        )
        self._draw_hitbox(ctx, COLOR_ACTORS, *coords_hitbox)

    def _draw_actor(self, ctx: cairo.Context, actor: SsaActor, *sprite_coords):
        # TODO: Sprite rendering - if no unique sprite available, work with placeholders (eg. PLAYER actor)
        # Draw sprite representation
        if actor.actor.entid > 0:
            # TODO actual sprite rendering
            self._draw_generic_placeholder(ctx, COLOR_ACTORS, actor.actor.name, *sprite_coords, actor.pos.direction)
        else:
            # Special "variable" actor placeholder
            self._draw_generic_placeholder(ctx, COLOR_ACTORS, actor.actor.name, *sprite_coords, actor.pos.direction)

    def get_bb_object(self, object: SsaObject, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = object.pos.x_absolute
        if y is None:
            y = object.pos.y_absolute
        if object.object.name != 'NULL':
            return self._get_pmd_bounding_box(
                # todo: this needs to be sprite dims later
                x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3,
                y_offset=object.hitbox_h * BPC_TILE_DIM
            )
        return self._get_pmd_bounding_box(
            x, y, object.hitbox_w * BPC_TILE_DIM, object.hitbox_h * BPC_TILE_DIM
        )

    def _draw_hitbox_object(self, ctx: cairo.Context, object: SsaObject):
        coords_hitbox = self._get_pmd_bounding_box(
            object.pos.x_absolute, object.pos.y_absolute, object.hitbox_w * BPC_TILE_DIM, object.hitbox_h * BPC_TILE_DIM
        )
        self._draw_hitbox(ctx, COLOR_OBJECTS, *coords_hitbox)

    def _draw_object(self, ctx: cairo.Context, object: SsaObject, *sprite_coords):
        # TODO: Sprite rendering - if no unique sprite available, work with placeholders (eg. NULL objects)
        #       + hitbox dims returned
        # Draw sprite representation
        if object.object.name != 'NULL':
            # TODO actual sprite rendering
            self._draw_generic_placeholder(ctx, COLOR_OBJECTS, object.object.unique_name, *sprite_coords, object.pos.direction)
            return
        self._draw_generic_placeholder(ctx, COLOR_OBJECTS, object.object.unique_name, *sprite_coords, object.pos.direction)

    def get_bb_performer(self, performer: SsaPerformer, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = performer.pos.x_absolute
        if y is None:
            y = performer.pos.y_absolute
        return self._get_pmd_bounding_box(
            x, y,
            performer.hitbox_w * BPC_TILE_DIM, performer.hitbox_h * BPC_TILE_DIM
        )

    def _draw_hitbox_performer(self, ctx: cairo.Context, performer: SsaPerformer):
        self._draw_hitbox(ctx, COLOR_PERFORMER, *self.get_bb_performer(performer))

    def _draw_performer(self, ctx: cairo.Context, performer: SsaPerformer, x, y, w, h):
        # Label
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_source_rgb(*COLOR_PERFORMER)
        ctx.set_font_size(12)
        ctx.move_to(x - 4, y - 8)
        ctx.show_text(f'{performer.type}')
        # Direction arrow
        arrow_left = x - int(BPC_TILE_DIM / 2)
        arrow_top = y - int(BPC_TILE_DIM / 2)
        self._triangle(ctx, arrow_left, arrow_top, BPC_TILE_DIM, COLOR_PERFORMER, performer.pos.direction.id)

    def get_bb_trigger(self, trigger: SsaEvent, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = trigger.pos.x_absolute
        if y is None:
            y = trigger.pos.y_absolute
        return (
            x, y,
            trigger.trigger_width * BPC_TILE_DIM, trigger.trigger_height * BPC_TILE_DIM
        )

    def _draw_trigger(self, ctx: cairo.Context, trigger: SsaEvent, *coords_hitbox):
        # Draw hitbox
        self._draw_hitbox(ctx, COLOR_PERFORMER, *coords_hitbox)
        # Label
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_source_rgb(1, 1, 1)
        ctx.set_font_size(12)
        ctx.move_to(coords_hitbox[0] + 4, coords_hitbox[1] + 14)
        ctx.show_text(f'{self._cb_trigger_label(trigger.trigger_id)}')

        return coords_hitbox

    def _is_layer_visible(self, layer_i: int) -> bool:
        return self._sectors_solo[layer_i] or (not any(self._sectors_solo) and self._sectors_visible[layer_i])

    def _is_dragged(self, entity: Union[SsaActor, SsaObject, SsaPerformer, SsaEvent]):
        return entity == self._selected and self._selected__drag is not None

    def _handle_layer_highlight(self, ctx: cairo.Context, layer: int, x: int, y: int, w: int, h: int):
        if layer == self._sector_highlighted:
            padding = 2
            x -= padding
            y -= padding
            w += padding * 2
            h += padding * 2
            ctx.set_source_rgba(*COLOR_LAYER_HIGHLIGHT)
            ctx.set_line_width(1.5)
            ctx.rectangle(x, y, w, h)
            ctx.set_dash([1.0])
            ctx.stroke()
            ctx.set_dash([])

    def _handle_selection(self, ctx: cairo.Context):
        if self._selected is None:
            return
        if isinstance(self._selected, SsaActor):
            x, y, w, h = self.get_bb_actor(self._selected)
        elif isinstance(self._selected, SsaObject):
            x, y, w, h = self.get_bb_object(self._selected)
        elif isinstance(self._selected, SsaPerformer):
            x, y, w, h = self.get_bb_performer(self._selected)
        elif isinstance(self._selected, SsaEvent):
            x, y, w, h = self.get_bb_trigger(self._selected)
        else:
            return
        padding = 2
        x -= padding
        y -= padding
        w += padding * 2
        h += padding * 2
        ctx.set_source_rgba(*COLOR_LAYER_HIGHLIGHT)
        ctx.set_line_width(3)
        ctx.rectangle(x, y, w, h)
        ctx.set_dash([1.0])
        ctx.stroke()
        ctx.set_dash([])

    def _handle_drag_and_place_modes(self):
        # IF DRAGGED
        if self._selected is not None and self._selected__drag is not None:
            # Draw dragged:
            x, y = self.get_current_drag_entity_pos()
            if isinstance(self._selected, SsaActor):
                x, y, w, h = self.get_bb_actor(self._selected, x=x, y=y)
            elif isinstance(self._selected, SsaObject):
                x, y, w, h = self.get_bb_object(self._selected, x=x, y=y)
            elif isinstance(self._selected, SsaPerformer):
                x, y, w, h = self.get_bb_performer(self._selected, x=x, y=y)
            elif isinstance(self._selected, SsaEvent):
                x, y, w, h = self.get_bb_trigger(self._selected, x=x, y=y)
            return x, y, w, h
        # DEFAULT
        return self.mouse_x, self.mouse_y, BPC_TILE_DIM, BPC_TILE_DIM
        # TODO: Tool modes

    def _get_pmd_bounding_box(self, x_center: int, y_center: int, w: int, h: int,
                              y_offset=0.0) -> Tuple[int, int, int, int]:
        left = x_center - int(w / 2)
        top = y_center - int(h / 2) - int(y_offset)
        return left, top, w, h

    def _draw_hitbox(self, ctx: cairo.Context, color: Color, x: int, y: int, w: int, h: int):
        ctx.set_source_rgba(*color, ALPHA_T)
        ctx.rectangle(x, y, w, h)
        ctx.fill()

    def _draw_generic_placeholder(self, ctx: cairo.Context, color: Color, label: str,
                                  x: int, y: int, w: int, h: int, direction: Pmd2ScriptDirection):
        # Rectangle
        ctx.set_source_rgb(*color)
        ctx.set_line_width(1)
        ctx.rectangle(x, y, w, h)
        ctx.stroke()
        # Label
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(6)
        ctx.move_to(x, y - 4)
        ctx.show_text(label)
        # Direction arrow
        a_sz = int(BPC_TILE_DIM / 2)
        self._triangle(ctx,
                       x + int(w/2) - int(a_sz / 2), y + h - a_sz - int(a_sz / 2),
                       a_sz,
                       (1, 1, 1), direction.id)

    def _triangle(self, ctx: cairo.Context, x: int, y: int, a_sz: int, color: Color, direction_id: int):
        if direction_id == 1 or direction_id == 0:
            # Down
            self._polygon(ctx, [(x, y), (x + a_sz, y), (x + int(a_sz / 2), y + a_sz)], color=color)
        elif direction_id == 2:
            # DownRight
            self._polygon(ctx, [(x + a_sz, y), (x + a_sz, y + a_sz), (x, y + a_sz)], color=color)
        elif direction_id == 3:
            # Right
            self._polygon(ctx, [(x, y), (x + a_sz, y + int(a_sz / 2)), (x, y + a_sz)], color=color)
        elif direction_id == 4:
            # UpRight
            self._polygon(ctx, [(x, y), (x + a_sz, y), (x + a_sz, y + a_sz)], color=color)
        elif direction_id == 5:
            # Up
            self._polygon(ctx, [(x, y + a_sz), (x + a_sz, y + a_sz), (x + int(a_sz / 2), y)], color=color)
        elif direction_id == 6:
            # UpLeft
            self._polygon(ctx, [(x, y + a_sz), (x, y), (x + a_sz, y)], color=color)
        elif direction_id == 7:
            # Left
            self._polygon(ctx, [(x + a_sz, y), (x, y + int(a_sz / 2)), (x + a_sz, y + a_sz)], color=color)
        elif direction_id == 8:
            # DownLeft
            self._polygon(ctx, [(x, y), (x, y + a_sz), (x + a_sz, y + a_sz)], color=color)

    def _polygon(self, ctx: cairo.Context, points, color, outline=None):
        ctx.new_path()
        for point in points:
            ctx.line_to(*point)
        ctx.close_path()
        ctx.set_source_rgba(*color)
        if outline is not None:
            ctx.fill_preserve()
            ctx.set_source_rgba(*outline)
            ctx.set_line_width(1)
            ctx.stroke()
        else:
            ctx.fill()

    def set_sector_visible(self, sector_id, value):
        self._sectors_visible[sector_id] = value
        self.draw_area.queue_draw()

    def set_sector_solo(self, sector_id, value):
        self._sectors_solo[sector_id] = value
        self.draw_area.queue_draw()

    def set_sector_highlighted(self, sector_id):
        self._sector_highlighted = sector_id
        self.draw_area.queue_draw()

    def set_selected(self, entity: Optional[Union[SsaActor, SsaObject, SsaPerformer, SsaEvent]]):
        self._selected = entity
        self.draw_area.queue_draw()

    def set_drag_position(self, x: int, y: int):
        """Start dragging. x/y is the offset on the entity, where the dragging was started."""
        self._selected__drag = (x, y)

    def end_drag(self):
        self._selected__drag = None

    def sector_added(self):
        self._sectors_solo.append(False)
        self._sectors_visible.append(True)

    def sector_removed(self, id):
        del self._sectors_solo[id]
        del self._sectors_visible[id]
        if self._sector_highlighted == id:
            self._sector_highlighted = None
        elif self._sector_highlighted > id:
            self._sector_highlighted -= 1

    def get_current_drag_entity_pos(self) -> Tuple[int, int]:
        corrected_mouse_x = self.mouse_x - self._selected__drag[0]
        corrected_mouse_y = self.mouse_y - self._selected__drag[1]
        # Snap
        x = corrected_mouse_x - corrected_mouse_x % (BPC_TILE_DIM / 2)
        y = corrected_mouse_y - corrected_mouse_y % (BPC_TILE_DIM / 2)
        return x, y

    @staticmethod
    def _is_in_bb(bb_x, bb_y, bb_w, bb_h, mouse_x, mouse_y):
        return bb_x <= mouse_x < bb_x + bb_w and bb_y <= mouse_y < bb_y + bb_h
