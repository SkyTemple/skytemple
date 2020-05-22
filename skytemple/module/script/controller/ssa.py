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
from typing import TYPE_CHECKING, Optional

import cairo
from gi.repository import Gtk, Gdk

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.module.script.drawer import Drawer
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.model import Ssa

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule
    from skytemple.module.map_bg.module import MapBgModule


SIZE_REQUEST_NONE = 500

class SsaController(AbstractController):
    _last_open_tab = None
    _paned_pos = None

    def __init__(self, module: 'ScriptModule', item: dict):
        self.module = module
        self.map_bg_module: 'MapBgModule' = module.project.get_module('map_bg')
        self.mapname = item['map']
        self.filename = item['file']

        self.builder = None

        self._scale_factor = 1
        self._bg_draw_is_clicked = False
        self._map_bg_width = SIZE_REQUEST_NONE
        self._map_bg_height = SIZE_REQUEST_NONE
        self._map_bg_surface = None

        self.ssa: Optional[Ssa] = None

        self.drawer: Optional[Drawer] = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'ssa.glade')
        paned: Gtk.Paned = self.builder.get_object('ssa_paned')
        if self.__class__._paned_pos is not None:
            paned.set_position(self._paned_pos)
        else:
            paned.set_position(800)
        util_notebook: Gtk.Notebook = self.builder.get_object('ssa_utility')
        if self.__class__._last_open_tab is not None:
            util_notebook.set_current_page(self._last_open_tab)
        self.builder.connect_signals(self)

        self._init_ssa()
        self._init_drawer()
        self._init_all_the_combos()
        self._update_scales()

        return self.builder.get_object('editor_ssa')

    def on_ssa_utility_switch_page(self, util_notebook: Gtk.Notebook, p, pnum, *args):
        self.__class__._last_open_tab = pnum

    def on_ssa_paned_position_notify(self, paned: Gtk.Paned, *args):
        self.__class__._paned_pos = paned.get_position()

    def on_ssa_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            self._bg_draw_is_clicked = True
            # Snap to 0,5 tiles
            snap_x = correct_mouse_x - correct_mouse_x % (BPC_TILE_DIM / 2)
            snap_y = correct_mouse_y - correct_mouse_y % (BPC_TILE_DIM / 2)
            self.drawer.set_mouse_position(snap_x, snap_y)
        self.builder.get_object('ssa_draw').queue_draw()

    def on_ssa_draw_event_button_release_event(self, box, button: Gdk.EventButton):
        if button.button == 1:
            self._bg_draw_is_clicked = False
        self.builder.get_object('ssa_draw').queue_draw()

    def on_ssa_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            # Snap to 0,5 tiles
            snap_x = correct_mouse_x - correct_mouse_x % (BPC_TILE_DIM / 2)
            snap_y = correct_mouse_y - correct_mouse_y % (BPC_TILE_DIM / 2)
            self.drawer.set_mouse_position(snap_x, snap_y)
            # TODO:
            #if self.bg_draw_is_clicked:
            #    self._set_col_at_pos(snap_x, snap_y)
            self.builder.get_object('ssa_draw').queue_draw()

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
            self.builder.get_object('ssa_draw').queue_draw()

    def on_tool_scene_move_toggled(self, *args):
        pass

    def on_tool_scene_add_actor_toggled(self, *args):
        pass

    def on_tool_scene_add_object_toggled(self, *args):
        pass

    def on_tool_scene_add_performer_toggled(self, *args):
        pass

    def on_tool_scene_add_trigger_toggled(self, *args):
        pass

    def on_tool_choose_map_bg_cb_changed(self, w: Gtk.ComboBox):
        model, cbiter = w.get_model(), w.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            item_id = model[cbiter][0]
            bma = self.map_bg_module.get_bma(item_id)
            bpl = self.map_bg_module.get_bpl(item_id)
            bpc = self.map_bg_module.get_bpc(item_id)
            bpas = self.map_bg_module.get_bpas(item_id)
            self._map_bg_surface = pil_to_cairo_surface(
                bma.to_pil(bpc, bpl.palettes, bpas, False, False)[0].convert('RGBA')
            )
            if self.drawer:
                self._set_drawer_bg(self._map_bg_surface,
                                    bma.map_width_camera * BPC_TILE_DIM,
                                    bma.map_height_camera * BPC_TILE_DIM)

    def on_tool_scene_goto_bg_clicked(self, *args):
        pass  # TODO: GOTO BUTTONS

    # EVENTS TOOLBAR #
    def on_tool_events_add_clicked(self, *args):
        pass

    def on_tool_events_remove_clicked(self, *args):
        pass

    def on_tool_events_edit_clicked(self, *args):
        pass

    # SECTOR TOOLBAR #
    def on_tool_sector_add_clicked(self, *args):
        pass

    def on_tool_sector_remove_clicked(self, *args):
        pass

    # SCRIPT TOOLBAR #
    def on_tool_script_edit_clicked(self, *args):
        pass

    def on_tool_script_add_clicked(self, *args):
        pass

    def on_tool_script_remove_clicked(self, *args):
        pass

    # ACTOR TOOLBAR #
    def on_tool_actors_add_clicked(self, *args):
        pass

    def on_tool_actors_remove_clicked(self, *args):
        pass

    # OBJECT TOOLBAR #
    def on_tool_objects_add_clicked(self, *args):
        pass

    def on_tool_objects_remove_clicked(self, *args):
        pass

    # PERFORMER TOOLBAR #
    def on_tool_performers_add_clicked(self, *args):
        pass

    def on_tool_performers_remove_clicked(self, *args):
        pass

    # TRIGGER TOOLBAR #
    def on_tool_triggers_add_clicked(self, *args):
        pass

    def on_tool_triggers_remove_clicked(self, *args):
        pass

    # ACTOR OVERLAY #
    def on_po_actor_x_changed(self, *args):
        pass

    def on_po_actor_y_changed(self, *args):
        pass

    def on_po_actor_sector_changed(self, *args):
        pass

    def on_po_actor_kind_changed(self, *args):
        pass

    def on_po_actor_script_changed(self, *args):
        pass

    # OBJECT OVERLAY #
    def on_po_object_x_changed(self, *args):
        pass

    def on_po_object_y_changed(self, *args):
        pass

    def on_po_object_sector_changed(self, *args):
        pass

    def on_po_object_kind_changed(self, *args):
        pass

    def on_po_object_script_changed(self, *args):
        pass

    def on_po_object_width_changed(self, *args):
        pass

    def on_po_object_height_changed(self, *args):
        pass

    # PERFORMER OVERLAY #
    def on_po_performer_x_changed(self, *args):
        pass

    def on_po_performer_y_changed(self, *args):
        pass

    def on_po_performer_sector_changed(self, *args):
        pass

    def on_po_performer_kind_changed(self, *args):
        pass

    def on_po_performer_width_changed(self, *args):
        pass

    def on_po_performer_height_changed(self, *args):
        pass

    # TRIGGER OVERLAY #
    def on_po_trigger_x_changed(self, *args):
        pass

    def on_po_trigger_y_changed(self, *args):
        pass

    def on_po_trigger_sector_changed(self, *args):
        pass

    def on_po_trigger_id_changed(self, *args):
        pass

    def on_po_trigger_width_changed(self, *args):
        pass

    def on_po_trigger_height_changed(self, *args):
        pass

    def _init_ssa(self):
        self.ssa = self.module.get_ssa(self.filename)

    def _init_all_the_combos(self):
        # MAP BGS
        map_bg_list: BgList = self.map_bg_module.bgs
        tool_choose_map_bg_cb: Gtk.ComboBox = self.builder.get_object('tool_choose_map_bg_cb')
        map_bg_store = Gtk.ListStore(int, str)  # ID, BPL name
        default_bg = map_bg_store.append([-1, "None"])
        for i, entry in enumerate(map_bg_list.level):
            bg_iter = map_bg_store.append([i, entry.bpl_name])
            if entry.bpl_name == self.mapname:
                default_bg = bg_iter
        tool_choose_map_bg_cb.set_model(map_bg_store)
        renderer_text = Gtk.CellRendererText()
        tool_choose_map_bg_cb.pack_start(renderer_text, True)
        tool_choose_map_bg_cb.add_attribute(renderer_text, "text", 1)
        tool_choose_map_bg_cb.set_active_iter(default_bg)

    def _init_drawer(self):
        self.drawer = Drawer(self.builder.get_object('ssa_draw'), self.ssa)
        self.drawer.start()

        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tool_scene_grid').get_active())

    def _set_drawer_bg(self, surface: cairo.Surface, w: int, h: int):
        self._map_bg_width = w
        self._map_bg_height = h
        self.builder.get_object('ssa_draw').set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        self.drawer.map_bg = surface
        self.builder.get_object('ssa_draw').queue_draw()

    def _update_scales(self):
        self.builder.get_object('ssa_draw').set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self._scale_factor)

        self.builder.get_object('ssa_draw').queue_draw()
