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
from enum import auto, Enum
from typing import Tuple, Union, Callable, Optional, List

import cairo
from gi.repository import Gtk, GLib

from explorerscript.source_map import SourceMapPositionMark
from skytemple.core.mapbg_util.drawer_plugin.grid import GridDrawerPlugin
from skytemple.core.mapbg_util.drawer_plugin.selection import SelectionDrawerPlugin
from skytemple.core.sprite_provider import SpriteProvider
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
COLOR_WHITE = (1.0, 1.0, 1.0)
COLOR_BLACK = (0, 0, 0)
COLOR_OBJECTS = (1.0, 0.627, 0)
COLOR_PERFORMER = (0, 1.0, 1.0)
COLOR_EVENTS = (0, 0, 1.0)
COLOR_POS_MARKS = (0, 1.0, 0)
COLOR_LAYER_HIGHLIGHT = (0.7, 0.7, 1, 0.7)
Num = Union[int, float]
Color = Tuple[Num, Num, Num]


class InteractionMode(Enum):
    SELECT = auto()
    PLACE_ACTOR = auto()
    PLACE_OBJECT = auto()
    PLACE_PERFORMER = auto()
    PLACE_TRIGGER = auto()


class Drawer:
    def __init__(
            self, draw_area: Gtk.Widget, ssa: Ssa, cb_trigger_label: Callable[[int], str],
            sprite_provider: SpriteProvider
    ):
        self.draw_area = draw_area

        self.ssa = ssa
        self.map_bg = None
        self.position_marks: List[SourceMapPositionMark] = []

        self.draw_tile_grid = False

        # Interaction
        self.interaction_mode = InteractionMode.SELECT
        self.mouse_x = 99999
        self.mouse_y = 99999

        self.sprite_provider = sprite_provider

        self._cb_trigger_label = cb_trigger_label
        self._sectors_visible = [True for _ in range(0, len(self.ssa.layer_list))]
        self._sectors_solo = [False for _ in range(0, len(self.ssa.layer_list))]
        self._sector_highlighted = None
        self._selected = None
        # If not None, drag is active and value is coordinate
        self._selected__drag: Optional[Tuple[int, int]] = None
        self._edit_pos_marks = False

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

    def draw(self, wdg, ctx: cairo.Context):
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
        if not self._edit_pos_marks:
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
                    self._draw_actor(ctx, actor, *bb)
                    self._draw_hitbox_actor(ctx, actor)
            for obj in layer.objects:
                if not self._is_dragged(obj):
                    bb = self.get_bb_object(obj)
                    if obj != self._selected:
                        self._handle_layer_highlight(ctx, layer_i, *bb)
                    self._draw_object(ctx, obj, *bb)
                    self._draw_hitbox_object(ctx, obj)
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

        # Black out bg a bit
        if self._edit_pos_marks:
            ctx.set_source_rgba(0, 0, 0, 0.5)
            ctx.rectangle(0, 0, size_w, size_h)
            ctx.fill()

        # RENDER POSITION MARKS
        for pos_mark in self.position_marks:
            bb = self.get_bb_pos_mark(pos_mark)
            self._draw_pos_mark(ctx, pos_mark, *bb)

        # Cursor / Active selected / Place mode
        self._handle_selection(ctx)
        x, y, w, h = self._handle_drag_and_place_modes()
        self.selection_plugin.set_size(w, h)
        self.selection_plugin.draw(ctx, size_w, size_h, x, y, ignore_obb=True)

        # Position
        ctx.scale(1 / self.scale, 1 / self.scale)
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_source_rgb(*COLOR_WHITE)
        ctx.set_font_size(18)
        try:
            sw: Gtk.ScrolledWindow = self.draw_area.get_parent().get_parent().get_parent()
            s = sw.get_allocated_size()
            ctx.move_to(sw.get_hadjustment().get_value() + 30, s[0].height + sw.get_vadjustment().get_value() - 30)
            if self._selected__drag is not None:
                sx, sy = self.get_current_drag_entity_pos()
            else:
                sx, sy = self._snap_pos(self.mouse_x, self.mouse_y)
            sx /= BPC_TILE_DIM
            sy /= BPC_TILE_DIM
            ctx.text_path(f"X: {sx}, Y: {sy}")
            ctx.set_source_rgb(*COLOR_BLACK)
            ctx.set_line_width(0.3)
            ctx.set_source_rgb(*COLOR_WHITE)
            ctx.fill_preserve()
            ctx.stroke()
        except BaseException:
            pass

        return True

    def selection_draw_callback(self, ctx: cairo.Context, x: int, y: int):
        if self.interaction_mode == InteractionMode.SELECT:
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
                elif isinstance(self._selected, SourceMapPositionMark):
                    x, y, w, h = self.get_bb_pos_mark(self._selected, x=x, y=y)
                    self._draw_pos_mark(ctx, self._selected, x, y, w, h)
            return
        # Tool modes
        elif self.interaction_mode == InteractionMode.PLACE_ACTOR:
            self._surface_place_actor(ctx, x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3)
        elif self.interaction_mode == InteractionMode.PLACE_OBJECT:
            self._surface_place_object(ctx, x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3)
        elif self.interaction_mode == InteractionMode.PLACE_PERFORMER:
            self._surface_place_performer(ctx, x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3)
        elif self.interaction_mode == InteractionMode.PLACE_TRIGGER:
            self._surface_place_trigger(ctx, x, y, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3)

    def set_mouse_position(self, x, y):
        self.mouse_x = x
        self.mouse_y = y

    def get_under_mouse(self) -> Tuple[Optional[int], Optional[Union[SsaActor, SsaObject, SsaPerformer, SsaEvent]]]:
        """
        Returns the first entity under the mouse position, if any, and it's layer number.
        Not visible layers are not searched.
        Elements are searched in reversed drawing order (so what's drawn on top is also taken).
        Does not return positon marks under the mouse.
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

    def get_pos_mark_under_mouse(self) -> Optional[SourceMapPositionMark]:
        """
        Returns the first position mark under the mouse position, if any.
        Elements are searched in reversed drawing order (so what's drawn on top is also taken).
        """
        for pos_mark in reversed(self.position_marks):
            bb = self.get_bb_pos_mark(pos_mark)
            if self._is_in_bb(*bb, self.mouse_x, self.mouse_y):
                return pos_mark
        return None

    def set_draw_tile_grid(self, v):
        self.draw_tile_grid = v

    def set_scale(self, v):
        self.scale = v

    def get_bb_actor(self, actor: SsaActor, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = actor.pos.x_absolute
        if y is None:
            y = actor.pos.y_absolute
        if actor.actor.entid <= 0:
            _, cx, cy, w, h = self.sprite_provider.get_actor_placeholder(actor.actor.id, actor.pos.direction.id, lambda: GLib.idle_add(self._redraw))
        else:
            _, cx, cy, w, h = self.sprite_provider.get_monster(actor.actor.entid, actor.pos.direction.id, lambda: GLib.idle_add(self._redraw))
        return x - cx, y - cy, w, h

    def _draw_hitbox_actor(self, ctx: cairo.Context, actor: SsaActor):
        coords_hitbox = self._get_pmd_bounding_box(
            actor.pos.x_absolute, actor.pos.y_absolute, ACTOR_DEFAULT_HITBOX_W, ACTOR_DEFAULT_HITBOX_H
        )
        self._draw_hitbox(ctx, COLOR_ACTORS, *coords_hitbox)

    def _draw_actor(self, ctx: cairo.Context, actor: SsaActor, *sprite_coords):
        self._draw_actor_sprite(ctx, actor, sprite_coords[0], sprite_coords[1])
        self._draw_name(ctx, COLOR_ACTORS, actor.actor.name, sprite_coords[0], sprite_coords[1])

    def get_bb_object(self, object: SsaObject, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = object.pos.x_absolute
        if y is None:
            y = object.pos.y_absolute
        if object.object.name != 'NULL':
            # Load sprite to get dims.
            _, cx, cy, w, h = self.sprite_provider.get_for_object(object.object.name, lambda: GLib.idle_add(self._redraw))
            return x - cx, y - cy, w, h
        return self._get_pmd_bounding_box(
            x, y, object.hitbox_w * BPC_TILE_DIM, object.hitbox_h * BPC_TILE_DIM
        )

    def _draw_hitbox_object(self, ctx: cairo.Context, object: SsaObject):
        coords_hitbox = self._get_pmd_bounding_box(
            object.pos.x_absolute, object.pos.y_absolute, object.hitbox_w * BPC_TILE_DIM, object.hitbox_h * BPC_TILE_DIM
        )
        self._draw_hitbox(ctx, COLOR_OBJECTS, *coords_hitbox)

    def _draw_object(self, ctx: cairo.Context, object: SsaObject, *sprite_coords):
        # Draw sprite representation
        if object.object.name != 'NULL':
            self._draw_object_sprite(ctx, object, sprite_coords[0], sprite_coords[1])
            self._draw_name(ctx, COLOR_OBJECTS, object.object.name, sprite_coords[0], sprite_coords[1])
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
        self._triangle(ctx, x, y, BPC_TILE_DIM, COLOR_PERFORMER, performer.pos.direction.id)

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

    def get_bb_pos_mark(self, pos_mark: SourceMapPositionMark, x=None, y=None) -> Tuple[int, int, int, int]:
        if x is None:
            x = pos_mark.x_with_offset * BPC_TILE_DIM
        if y is None:
            y = pos_mark.y_with_offset * BPC_TILE_DIM
        return x - BPC_TILE_DIM, y - BPC_TILE_DIM, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3

    def _draw_pos_mark(self, ctx: cairo.Context, pos_mark: SourceMapPositionMark, *bb_cords):
        # Outline
        ctx.set_source_rgba(*COLOR_POS_MARKS, 0.8)
        ctx.rectangle(*bb_cords)
        ctx.set_line_width(4.0)
        ctx.set_dash([1.0])
        ctx.stroke()
        ctx.set_dash([])
        # Inner
        ctx.rectangle(bb_cords[0] + BPC_TILE_DIM, bb_cords[1] + BPC_TILE_DIM, BPC_TILE_DIM, BPC_TILE_DIM)
        ctx.fill()
        # Label
        self._draw_name(ctx, COLOR_POS_MARKS, pos_mark.name, bb_cords[0], bb_cords[1], scale=2)

    def _is_layer_visible(self, layer_i: int) -> bool:
        return self._sectors_solo[layer_i] or (not any(self._sectors_solo) and self._sectors_visible[layer_i])

    def _is_dragged(self, entity: Union[SsaActor, SsaObject, SsaPerformer, SsaEvent, SourceMapPositionMark]):
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
        elif isinstance(self._selected, SourceMapPositionMark):
            x, y, w, h = self.get_bb_pos_mark(self._selected)
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
        if self.interaction_mode == InteractionMode.SELECT:
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
                elif isinstance(self._selected, SourceMapPositionMark):
                    x, y, w, h = self.get_bb_pos_mark(self._selected, x=x, y=y)
                return x, y, w, h
            # DEFAULT
            return self.mouse_x, self.mouse_y, BPC_TILE_DIM, BPC_TILE_DIM
        # Tool modes
        x = self.mouse_x - self.mouse_x % (BPC_TILE_DIM / 2)
        y = self.mouse_y - self.mouse_y % (BPC_TILE_DIM / 2)
        return x - BPC_TILE_DIM * 1.5, y - BPC_TILE_DIM * 1.5, BPC_TILE_DIM * 3, BPC_TILE_DIM * 3

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
        self._draw_name(ctx, color, label, x, y)
        # Direction arrow
        a_sz = int(BPC_TILE_DIM / 2)
        self._triangle(ctx,
                       x + int(w/2) - int(a_sz / 2), y + h - a_sz - int(a_sz / 2),
                       a_sz,
                       (1, 1, 1), direction.id)

    def _draw_name(self, ctx: cairo.Context, color: Color, label: str, x: int, y: int, scale=1):
        ctx.set_source_rgb(*color)
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(6 * scale)
        ctx.move_to(x, y - 4 * scale)
        ctx.show_text(label)

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

    def _draw_actor_sprite(self, ctx: cairo.Context, actor: SsaActor, x, y):
        """Draws the sprite for an actor"""
        if actor.actor.entid == 0:
            sprite = self.sprite_provider.get_actor_placeholder(
                actor.actor.id, actor.pos.direction.id, self._redraw
            )[0]
        else:
            sprite = self.sprite_provider.get_monster(
                actor.actor.entid, actor.pos.direction.id, lambda: GLib.idle_add(self._redraw)
            )[0]
        ctx.translate(x, y)
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-x, -y)

    def _draw_object_sprite(self, ctx: cairo.Context, obj: SsaObject, x, y):
        """Draws the sprite for an object"""
        sprite = self.sprite_provider.get_for_object(obj.object.name, lambda: GLib.idle_add(self._redraw))[0]
        ctx.translate(x, y)
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.translate(-x, -y)

    def _surface_place_actor(self, ctx: cairo.Context, x, y, w, h):
        ctx.set_line_width(1)
        sprite_surface = self.sprite_provider.get_monster_outline(1, 1)[0]

        ctx.translate(x, y)
        ctx.set_source_surface(sprite_surface)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        self._draw_plus(ctx)
        ctx.translate(-x, -y)

    def get_pos_place_actor(self) -> Tuple[int, int]:
        """Get the X and Y position on the grid to place the actor on, in PLACE_ACTOR mode."""
        return self._snap_pos(
            self.mouse_x,
            self.mouse_y + BPC_TILE_DIM
        )

    def _surface_place_object(self, ctx: cairo.Context, x, y, w, h):
        ctx.set_line_width(1)
        cx, cy = x + w / 2, y + h / 2
        rect_dim = BPC_TILE_DIM * 2
        ctx.set_source_rgb(1, 1, 1)
        ctx.rectangle(
            cx - rect_dim / 2,
            cy - rect_dim / 2,
            rect_dim, rect_dim
        )
        ctx.stroke()
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(6)
        ctx.move_to(cx - 5, cy - 2)
        ctx.show_text(f'OBJ')
        ctx.translate(x, y)
        self._draw_plus(ctx)
        ctx.translate(-x, -y)

    def get_pos_place_object(self) -> Tuple[int, int]:
        """Get the X and Y position on the grid to place the object on, in PLACE_OBJECT mode."""
        return self._snap_pos(
            self.mouse_x,
            self.mouse_y
        )

    def _surface_place_performer(self, ctx: cairo.Context, x, y, w, h):
        ctx.set_line_width(1)
        cx, cy = x + w / 2, y + h / 2
        self._triangle(ctx, cx - BPC_TILE_DIM / 2, cy - BPC_TILE_DIM / 2, BPC_TILE_DIM, (255, 255, 255), 1)
        ctx.translate(x, y)
        self._draw_plus(ctx)
        ctx.translate(-x, -y)

    def get_pos_place_performer(self) -> Tuple[int, int]:
        """Get the X and Y position on the grid to place the performer on, in PLACE_PERFORMER mode."""
        return self._snap_pos(
            self.mouse_x,
            self.mouse_y
        )

    def _surface_place_trigger(self, ctx: cairo.Context, x, y, w, h):
        ctx.set_line_width(1)
        cx, cy = x + w / 2, y + h / 2
        rect_dim = BPC_TILE_DIM * 2
        ctx.set_source_rgb(1, 1, 1)
        ctx.rectangle(
            cx - rect_dim / 2,
            cy - rect_dim / 2,
            rect_dim, rect_dim
        )
        ctx.stroke()
        ctx.select_font_face("monospace", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_NORMAL)
        ctx.set_font_size(6)
        ctx.move_to(cx - 5, cy - 2)
        ctx.show_text(f'TRG')
        ctx.translate(x, y)
        self._draw_plus(ctx)
        ctx.translate(-x, -y)

    def get_pos_place_trigger(self) -> Tuple[int, int]:
        """Get the X and Y position on the grid to place the trigger on, in PLACE_TRIGGER mode."""
        return self._snap_pos(
            self.mouse_x - BPC_TILE_DIM,
            self.mouse_y - BPC_TILE_DIM
        )

    def _draw_plus(self, ctx: cairo.Context):
        arrow_len = BPC_TILE_DIM / 4
        ctx.set_source_rgb(1, 1, 1)
        ctx.translate(-arrow_len, 0)
        ctx.move_to(0, 0)
        ctx.rel_line_to(arrow_len * 2, 0)
        ctx.stroke()
        ctx.translate(arrow_len, -arrow_len)
        ctx.move_to(0, 0)
        ctx.rel_line_to(0, arrow_len * 2)
        ctx.stroke()
        ctx.translate(0, arrow_len)

    def set_sector_visible(self, sector_id, value):
        self._sectors_visible[sector_id] = value
        self.draw_area.queue_draw()

    def set_sector_solo(self, sector_id, value):
        self._sectors_solo[sector_id] = value
        self.draw_area.queue_draw()

    def set_sector_highlighted(self, sector_id):
        self._sector_highlighted = sector_id
        self.draw_area.queue_draw()

    def get_sector_highlighted(self):
        return self._sector_highlighted

    def set_selected(self, entity: Optional[Union[SsaActor, SsaObject, SsaPerformer, SsaEvent, SourceMapPositionMark]]):
        self._selected = entity
        self.draw_area.queue_draw()

    def add_position_marks(self, pos_marks):
        self.position_marks += pos_marks

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
        return self._snap_pos(
            self.mouse_x - self._selected__drag[0],
            self.mouse_y - self._selected__drag[1]
        )

    def _redraw(self):
        if self.draw_area is None or self.draw_area.get_parent() is None:
            return
        self.draw_area.queue_draw()

    def edit_position_marks(self):
        self._edit_pos_marks = True

    @staticmethod
    def _is_in_bb(bb_x, bb_y, bb_w, bb_h, mouse_x, mouse_y):
        return bb_x <= mouse_x < bb_x + bb_w and bb_y <= mouse_y < bb_y + bb_h

    @staticmethod
    def _snap_pos(x, y):
        x = x - x % (BPC_TILE_DIM / 2)
        y = y - y % (BPC_TILE_DIM / 2)
        return x, y


