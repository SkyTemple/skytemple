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

# TODO: This module shares quite some code with SsaController.
import math
import os
from typing import List, Optional, Tuple

import cairo
from gi.repository import Gtk, Gdk

from explorerscript.source_map import SourceMapPositionMark
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.core.ui_utils import APP, make_builder
from skytemple.module.script.drawer import Drawer, InteractionMode
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptLevel
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.model import Ssa
from skytemple_files.script.ssa_sse_sss.trigger import SsaTrigger
from skytemple_files.common.i18n_util import f, _

SIZE_REQUEST_NONE = 500


class PosMarkEditorController:
    def __init__(self, ssa: Ssa, parent_window: Gtk.Window, sprite_provider: SpriteProvider,
                 level: Pmd2ScriptLevel, map_bg_module,
                 pos_marks: List[SourceMapPositionMark], pos_mark_to_edit: int):
        """A controller for a dialog for editing position marks for an Ssb file."""
        path = os.path.abspath(os.path.dirname(__file__))
        self.builder = make_builder(os.path.join(path, 'pos_mark_editor.glade'))
        self.sprite_provider = sprite_provider
        self.ssa: Ssa = ssa
        self.map_bg_module = map_bg_module

        self.pos_marks = pos_marks
        # intial to edit, index
        self.pos_mark_to_edit = pos_mark_to_edit

        self.level = level
        self.mapbg_id = self.level.mapid

        self._scale_factor = 1
        self._bg_draw_is_clicked__location: Optional[Tuple[int, int]] = None
        self._bg_draw_is_clicked__drag_active = False
        self._map_bg_width = SIZE_REQUEST_NONE
        self._map_bg_height = SIZE_REQUEST_NONE
        self._map_bg_surface = None
        self._currently_selected_mark: Optional[SourceMapPositionMark] = None

        self._w_ssa_draw: Gtk.DrawingArea = self.builder.get_object('ssa_draw')

        self.drawer: Optional[Drawer] = None

        self.window: Gtk.Dialog = self.builder.get_object('dialog')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        self.title = _('Edit Position Marks')

        self.builder.connect_signals(self)

    def run(self):
        """Run the dialog and return the response. If it's OK, the new model can be retrieved via get_event()"""
        self.window.set_title(self.title)

        self._init_drawer()
        self._init_all_the_stores()
        self._update_scales()

        response = self.window.run()
        self.window.hide()
        return response

    def on_ssa_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            self._bg_draw_is_clicked__drag_active = False
            self._bg_draw_is_clicked__location = (int(button.x), int(button.y))
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            # Select.
            self.drawer.end_drag()
            self._currently_selected_mark = self.drawer.get_pos_mark_under_mouse()
            self.drawer.set_selected(self._currently_selected_mark)

        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_button_release_event(self, box, button: Gdk.EventButton):
        if button.button == 1 and self.drawer is not None:
            # SELECT / DRAG
            if self._currently_selected_mark is not None:
                if self._bg_draw_is_clicked__drag_active:
                    # END DRAG / UPDATE POSITION
                    tile_x, tile_y = self.drawer.get_current_drag_entity_pos()
                    tile_x /= BPC_TILE_DIM
                    tile_y /= BPC_TILE_DIM
                    # Out of bounds failsafe:
                    if tile_x < 0:
                        tile_x = 0
                    if tile_y < 0:
                        tile_y = 0
                    self.drawer.end_drag()
                    self._currently_selected_mark.x_relative = math.floor(tile_x)
                    self._currently_selected_mark.y_relative = math.floor(tile_y)
                    if tile_x % 1 != 0:
                        self._currently_selected_mark.x_offset = 2
                    else:
                        self._currently_selected_mark.x_offset = 0
                    if tile_y % 1 != 0:
                        self._currently_selected_mark.y_offset = 2
                    else:
                        self._currently_selected_mark.y_offset = 0
        self._bg_draw_is_clicked__location = None
        self._bg_draw_is_clicked__drag_active = False
        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            if self._currently_selected_mark is not None:
                this_x, this_y = motion.get_coords()
                if self._bg_draw_is_clicked__location is not None:
                    start_x, start_y = self._bg_draw_is_clicked__location
                    # Start drag & drop if mouse moved at least one tile.
                    if not self._bg_draw_is_clicked__drag_active and (
                            abs(start_x - this_x) > BPC_TILE_DIM / 2 * self._scale_factor
                            or abs(start_y - this_y) > BPC_TILE_DIM / 2 * self._scale_factor
                    ):
                        self._bg_draw_is_clicked__drag_active = True
                        self.drawer.set_drag_position(
                            int((start_x - 4) / self._scale_factor) - (self._currently_selected_mark.x_with_offset * BPC_TILE_DIM),
                            int((start_y - 4) / self._scale_factor) - (self._currently_selected_mark.y_with_offset * BPC_TILE_DIM)
                        )

            self._w_ssa_draw.queue_draw()

    # SCENE TOOLBAR #
    def on_tool_scene_zoom_in_clicked(self, *args):
        self._scale_factor *= 2
        self._update_scales()

    def on_tool_scene_zoom_out_clicked(self, *args):
        self._scale_factor /= 2
        self._update_scales()

    def on_tool_scene_grid_toggled(self, w, *args):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())
            self._w_ssa_draw.queue_draw()

    def on_tool_choose_map_bg_cb_changed(self, w: Gtk.ComboBox):
        model, cbiter = w.get_model(), w.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            item_id = model[cbiter][0]
            self.mapbg_id = item_id
            bma = self.map_bg_module.get_bma(item_id)
            bpl = self.map_bg_module.get_bpl(item_id)
            bpc = self.map_bg_module.get_bpc(item_id)
            bpas = self.map_bg_module.get_bpas(item_id)
            self._map_bg_surface = pil_to_cairo_surface(
                bma.to_pil(bpc, bpl, bpas, False, False, single_frame=True)[0].convert('RGBA')
            )
            bma_width = bma.map_width_camera * BPC_TILE_DIM
            bma_height = bma.map_height_camera * BPC_TILE_DIM
            if self.drawer:
                self._set_drawer_bg(self._map_bg_surface, bma_width, bma_height)

    def _init_all_the_stores(self):
        # MAP BGS
        map_bg_list: BgList = self.map_bg_module.bgs
        tool_choose_map_bg_cb: Gtk.ComboBox = self.builder.get_object('tool_choose_map_bg_cb')
        map_bg_store = Gtk.ListStore(int, str)  # ID, BMA name
        default_bg = map_bg_store.append([-1, _("None")])
        for i, entry in enumerate(map_bg_list.level):
            bg_iter = map_bg_store.append([i, entry.bma_name])
            if i == self.mapbg_id:
                default_bg = bg_iter
        self._fast_set_comboxbox_store(tool_choose_map_bg_cb, map_bg_store, 1)
        tool_choose_map_bg_cb.set_active_iter(default_bg)

    def _init_drawer(self):
        self.drawer = Drawer(self._w_ssa_draw, self.ssa,
                             lambda *args: '', self.sprite_provider)
        self.drawer.add_position_marks(self.pos_marks)
        self.drawer.edit_position_marks()
        self.drawer.set_selected(self.pos_marks[self.pos_mark_to_edit])
        self.drawer.start()

        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tool_scene_grid').get_active())

    def _set_drawer_bg(self, surface: cairo.Surface, w: int, h: int):
        self._map_bg_width = w
        self._map_bg_height = h
        self._w_ssa_draw.set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        self.drawer.map_bg = surface
        self._w_ssa_draw.queue_draw()

    def _update_scales(self):
        self._w_ssa_draw.set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self._scale_factor)

        self._w_ssa_draw.queue_draw()

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)
