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

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.module_controller import AbstractController
from skytemple.module.dungeon import COUNT_VALID_TILESETS, TILESET_FIRST_BG
from skytemple.module.dungeon.fixed_room_drawer import FixedRoomDrawer
from skytemple.module.dungeon.fixed_room_tileset_renderer.bg import FixedFloorDrawerBackground
from skytemple.module.dungeon.fixed_room_tileset_renderer.tileset import FixedFloorDrawerTileset
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule


class FixedController(AbstractController):
    _last_scale_factor = None

    def __init__(self, module: 'DungeonModule', item_id: int):
        self.floor_id = item_id
        self.module = module
        self.tileset_id = 0

        self.builder = None

        if self.__class__._last_scale_factor is not None:
            self._scale_factor = self.__class__._last_scale_factor
        else:
            self._scale_factor = 1

        self.drawer: Optional[FixedRoomDrawer] = None

        self.floor: Optional[FixedFloor] = None
        self._draw = None

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'fixed.glade')
        self._draw = self.builder.get_object('fixed_draw')

        self._init_comboboxes()
        self._auto_select_tileset()
        self._init_fixed_floor()
        self._init_drawer()
        self._init_tileset()
        self._update_scales()

        self.builder.connect_signals(self)

        return self.builder.get_object('editor')

    def on_fixed_draw_event_button_press_event(self, *args):
        """ TODO """

    def on_fixed_draw_event_button_release_event(self, *args):
        """ TODO """

    def on_fixed_draw_event_motion_notify_event(self, *args):
        """ TODO """

    def on_utility_entity_direction_changed(self, *args):
        """ TODO """

    def on_utility_entity_type_changed(self, *args):
        """ TODO """

    def on_btn_goto_entity_editor_clicked(self, *args):
        """ TODO """

    def on_utility_tile_direction_changed(self, *args):
        """ TODO """

    def on_utility_tile_type_changed(self, *args):
        """ TODO """

    def on_tool_scene_goto_tileset_clicked(self, *args):
        """ TODO """

    def on_tool_choose_tileset_cb_changed(self, w: Gtk.ComboBox):
        idx = w.get_active()
        self.tileset_id = idx
        self._init_tileset()

    def on_tool_scene_copy_toggled(self, *args):
        """ TODO """

    def on_tool_scene_add_entity_toggled(self, *args):
        """ TODO """

    def on_tool_scene_add_tile_toggled(self, *args):
        """ TODO """

    def on_tool_scene_move_toggled(self, *args):
        """ TODO """

    def on_tool_scene_grid_toggled(self, *args):
        """ TODO """

    def on_tool_scene_zoom_out_clicked(self, *args):
        """ TODO """

    def on_tool_scene_zoom_in_clicked(self, *args):
        """ TODO """

    def _init_comboboxes(self):
        self._init_tileset_chooser()

    def _init_tileset_chooser(self):
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_TILESETS):
            if i >= TILESET_FIRST_BG:
                store.append([i, f"Background {i}"])
            else:
                store.append([i, f"Tileset {i}"])
        self._fast_set_comboxbox_store(self.builder.get_object('tool_choose_tileset_cb'), store, 1)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _auto_select_tileset(self):
        # TODO. We just use a fixed value for now
        cb: Gtk.ComboBox = self.builder.get_object('tool_choose_tileset_cb')
        cb.set_active(0)
        self.tileset_id = 0

    def _init_fixed_floor(self):
        # Fixed floor data
        self.floor = self.module.get_fixed_floor(self.floor_id)
        # TODO: Settings
        # TODO: Overrides

    def _init_tileset(self):
        if self.tileset_id < TILESET_FIRST_BG:
            # Real tileset
            self.drawer.set_tileset_renderer(FixedFloorDrawerTileset(*self.module.get_dungeon_tileset(self.tileset_id)))
        else:
            # Background to render using dummy tileset
            self.drawer.set_tileset_renderer(FixedFloorDrawerBackground(
                *self.module.get_dungeon_background(self.tileset_id - TILESET_FIRST_BG),
                *self.module.get_dummy_tileset())
            )
        self._draw.queue_draw()

    def _init_drawer(self):
        self.drawer = FixedRoomDrawer(self._draw, self.floor, self.module.project.get_sprite_provider())
        self.drawer.start()

        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tool_scene_grid').get_active())

    def _update_scales(self):
        self._draw.set_size_request(
            (self.floor.width + 10) * DPCI_TILE_DIM * DPC_TILING_DIM * self._scale_factor,
            (self.floor.height + 10) * DPCI_TILE_DIM * DPC_TILING_DIM * self._scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self._scale_factor)

        self._draw.queue_draw()
