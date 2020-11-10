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
from skytemple.module.dungeon.entity_rule_container import EntityRuleContainer
from skytemple.module.dungeon.fixed_room_drawer import FixedRoomDrawer, InfoLayer
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
        self.entity_rule_container: EntityRuleContainer = EntityRuleContainer(
            *self.module.get_fixed_floor_entity_lists()
        )

        self.properties = self.module.get_fixed_floor_properties()[self.floor_id]
        self.override_id = self.module.get_fixed_floor_overrides()[self.floor_id]

        self.floor: Optional[FixedFloor] = None
        self._draw = None

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'fixed.glade')
        self._draw = self.builder.get_object('fixed_draw')

        self._init_comboboxes()
        self._auto_select_tileset()
        self._load_settings()
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

    def on_tool_scene_grid_toggled(self, w: Gtk.ToggleButton):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())

    def on_tb_info_layer_none_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(None)
        self.builder.get_object('legend_stack').set_visible_child(self.builder.get_object('info_none'))

    def on_tb_info_layer_tiles_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.TILE)
        self.builder.get_object('legend_stack').set_visible_child(self.builder.get_object('info_tiles'))

    def on_tb_info_layer_items_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.ITEM)
        self.builder.get_object('legend_stack').set_visible_child(self.builder.get_object('info_items'))

    def on_tb_info_layer_monsters_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.MONSTER)
        self.builder.get_object('legend_stack').set_visible_child(self.builder.get_object('info_monsters'))

    def on_tb_info_layer_traps_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.TRAP)
        self.builder.get_object('legend_stack').set_visible_child(self.builder.get_object('info_traps'))

    def on_tool_scene_zoom_in_clicked(self, *args):
        self._scale_factor *= 2
        self._update_scales()

    def on_tool_scene_zoom_out_clicked(self, *args):
        self._scale_factor /= 2
        self._update_scales()

    # EDIT SETTINGS

    def on_settings_music_changed(self, w):
        try:
            self.properties.music_track = int(w.get_text())
        except ValueError:
            return
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_moves_active_notify(self, w, *args):
        self.properties.moves_enabled = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_orbs_active_notify(self, w, *args):
        self.properties.orbs_enabled = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk4_active_notify(self, w, *args):
        self.properties.unk4 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk5_active_notify(self, w, *args):
        self.properties.unk5 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk8_active_notify(self, w, *args):
        self.properties.unk6 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk9_active_notify(self, w, *args):
        self.properties.unk9 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk10_active_notify(self, w, *args):
        self.properties.unk10 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_override_changed(self, w: Gtk.ComboBox, *args):
        self.override_id = w.get_active()
        self.module.save_fixed_floor_override(self.floor_id, self.override_id)

    def on_settings_width_changed(self, w, *args):
        pass  # todo

    def on_settings_height_changed(self, w, *args):
        pass  # todo

    # END EDIT SETTINGS

    def _init_comboboxes(self):
        self._init_tileset_chooser()
        self._init_override_dropdown()

    def _init_tileset_chooser(self):
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_TILESETS):
            if i >= TILESET_FIRST_BG:
                store.append([i, f"Background {i}"])
            else:
                store.append([i, f"Tileset {i}"])
        self._fast_set_comboxbox_store(self.builder.get_object('tool_choose_tileset_cb'), store, 1)

    def _init_override_dropdown(self):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, "No override"])
        for i in range(1, 256):
            store.append([i, f"No. {i}"])
        self._fast_set_comboxbox_store(self.builder.get_object('settings_override'), store, 1)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _auto_select_tileset(self):
        cb: Gtk.ComboBox = self.builder.get_object('tool_choose_tileset_cb')
        self.tileset_id = self.module.get_default_tileset_for_fixed_floor(self.floor_id)
        cb.set_active(self.tileset_id)

    def _load_settings(self):
        self.builder.get_object('settings_music').set_text(str(self.properties.music_track))
        self.builder.get_object('settings_moves').set_active(self.properties.moves_enabled)
        self.builder.get_object('settings_orbs').set_active(self.properties.orbs_enabled)
        self.builder.get_object('settings_unk4').set_active(self.properties.unk4)
        self.builder.get_object('settings_unk5').set_active(self.properties.unk5)
        self.builder.get_object('settings_unk8').set_active(self.properties.unk8)
        self.builder.get_object('settings_unk9').set_active(self.properties.unk9)
        self.builder.get_object('settings_unk10').set_active(self.properties.unk10)
        self.builder.get_object('settings_override').set_active(self.override_id)

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
        self.drawer = FixedRoomDrawer(self._draw, self.floor, self.module.project.get_sprite_provider(),
                                      self.entity_rule_container,
                                      self.module.project.get_string_provider())
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
