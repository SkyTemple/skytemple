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
import sys
from typing import TYPE_CHECKING, Optional, Callable, Mapping

from gi.repository import Gtk, Gdk
from gi.repository.Gtk import Widget

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY, \
    REQUEST_TYPE_DUNGEON_TILESET
from skytemple.core.string_provider import StringType
from skytemple.module.dungeon import COUNT_VALID_TILESETS, TILESET_FIRST_BG, SPECIAL_MONSTERS
from skytemple.module.dungeon.entity_rule_container import EntityRuleContainer
from skytemple.module.dungeon.fixed_room_drawer import FixedRoomDrawer, InfoLayer, InteractionMode
from skytemple.module.dungeon.fixed_room_tileset_renderer.bg import FixedFloorDrawerBackground
from skytemple.module.dungeon.fixed_room_tileset_renderer.tileset import FixedFloorDrawerTileset
from skytemple_files.data.md.model import NUM_ENTITIES
from skytemple_files.dungeon_data.fixed_bin.model import FixedFloor, TileRuleType, TileRule, EntityRule
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import DPCI_TILE_DIM
from skytemple_files.hardcoded.fixed_floor import MonsterSpawnType
from skytemple_files.common.i18n_util import _, f

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

        # TODO: Duplicated code
        self.enemy_settings_name = [f"{i}" for i in range(0, 256)]
        self.long_enemy_settings_name = [f"{i}: ???" for i in range(0, 256)]
        for spawn_type in MonsterSpawnType:
            self.enemy_settings_name[spawn_type.value] = f"{spawn_type.description}"
            self.long_enemy_settings_name[spawn_type.value] = f"{spawn_type.value}: {spawn_type.description}"

        self.monster_names = {}
        self.long_monster_names = {}
        length = len(self.module.get_monster_md().entries)
        for i, entry in enumerate(self.module.get_monster_md().entries):
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, i % NUM_ENTITIES)
            self.monster_names[i] = f'{name}'
            self.long_monster_names[i] = f'{name} ({entry.gender.name.capitalize()}) (${i:04})'
        for i in range(length, length + SPECIAL_MONSTERS):
            self.monster_names[i] = _('(Special?)')
            self.long_monster_names[i] = _('(Special?)') + f' (${i:04})'

        self.floor: Optional[FixedFloor] = None
        self._draw = None

        self._bg_draw_is_clicked__press_active = False
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location = None
        self._currently_selected = None

        self.script_data = self.module.project.get_rom_module().get_static_data().script_data

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'fixed.glade')
        self._draw = self.builder.get_object('fixed_draw')

        self._init_comboboxes()
        self._auto_select_tileset()
        self._init_fixed_floor()
        self._load_settings()
        self._init_drawer()
        self._init_tileset()
        self._update_scales()

        self.builder.connect_signals(self)

        return self.builder.get_object('editor')

    def on_fixed_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        if not self.drawer:
            return
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            self._bg_draw_is_clicked__press_active = True
            self._bg_draw_is_clicked__drag_active = False
            self._bg_draw_is_clicked__location = (int(button.x), int(button.y))
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            self.drawer.end_drag()
            # PLACE
            self._place()

            # COPY
            if self.drawer.interaction_mode == InteractionMode.COPY:
                if self.drawer.get_cursor_is_in_bounds(
                        self.floor.width, self.floor.height, True
                ):
                    x, y = self.drawer.get_cursor_pos_in_grid(True)
                    action_to_copy = self.floor.actions[y * self.floor.width + x]
                    if isinstance(action_to_copy, TileRule):
                        self.builder.get_object('tool_scene_add_tile').set_active(True)
                        self._select_combobox('utility_tile_type',
                                              lambda row: row[0] == action_to_copy.tr_type.value)
                        self._select_combobox('utility_tile_direction',
                                              lambda row: row[0] == action_to_copy.direction.ssa_id
                                              if action_to_copy.direction is not None else 0)
                    else:
                        self.builder.get_object('tool_scene_add_entity').set_active(True)
                        self._select_combobox('utility_entity_type',
                                              lambda row: row[0] == action_to_copy.entity_rule_id)
                        self._select_combobox('utility_entity_direction',
                                              lambda row: row[0] == action_to_copy.direction.ssa_id
                                              if action_to_copy.direction is not None else 0)

            # SELECT
            elif self.drawer.interaction_mode == InteractionMode.SELECT:
                if self.drawer.get_cursor_is_in_bounds(
                        self.floor.width, self.floor.height, True
                ):
                    self._currently_selected = self.drawer.get_cursor_pos_in_grid(True)

        self._draw.queue_draw()

    def on_fixed_draw_event_button_release_event(self, box, button: Gdk.EventButton):
        if button.button == 1 and self.drawer is not None:
            self._bg_draw_is_clicked__press_active = False
            # SELECT / DRAG
            if self._currently_selected is not None:
                if self._bg_draw_is_clicked__drag_active:
                    # END DRAG / UPDATE POSITION
                    tile_x, tile_y = self.drawer.get_cursor_pos_in_grid(True)
                    # Out of bounds failsafe:
                    if tile_x < 0:
                        tile_x = 0
                    if tile_y < 0:
                        tile_y = 0
                    if tile_x >= self.floor.width:
                        tile_x = self.floor.width - 1
                    if tile_y >= self.floor.height:
                        tile_y = self.floor.height - 1
                    # Place at new position
                    old_x, old_y = self.drawer.get_selected()
                    # abort if dragging onto same tile
                    if old_x != tile_x or old_y != tile_y:
                        self.floor.actions[tile_y * self.floor.width + tile_x] = self.floor.actions[old_y * self.floor.width + old_x]
                        # Insert floor at old position
                        self.floor.actions[old_y * self.floor.width + old_x] = TileRule(TileRuleType.FLOOR_ROOM, None)
                        self.module.mark_fixed_floor_as_modified(self.floor_id)
        self._currently_selected = None
        self._bg_draw_is_clicked__location = None
        self._bg_draw_is_clicked__drag_active = False
        self.drawer.end_drag()
        self._draw.queue_draw()

    def on_fixed_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            # PLACE
            self._place()

            if self._currently_selected is not None:
                this_x, this_y = motion.get_coords()
                if self._bg_draw_is_clicked__location is not None:
                    start_x, start_y = self._bg_draw_is_clicked__location
                    # Start drag & drop if mouse moved at least one tile.
                    if not self._bg_draw_is_clicked__drag_active and (
                            abs(start_x - this_x) > (DPC_TILING_DIM * DPCI_TILE_DIM * 0.7) * self._scale_factor
                            or abs(start_y - this_y) >  (DPC_TILING_DIM * DPCI_TILE_DIM * 0.7) * self._scale_factor
                    ):
                        start_x /= self._scale_factor
                        start_y /= self._scale_factor
                        if self.drawer.get_pos_is_in_bounds(start_x, start_y, self.floor.width, self.floor.height, True):
                            self.drawer.set_selected(self.drawer.get_pos_in_grid(start_x, start_y, True))
                            self._bg_draw_is_clicked__drag_active = True
                            self.drawer.set_drag_position(
                                int((start_x - 4) / self._scale_factor) - self._currently_selected[0],
                                int((start_y - 4) / self._scale_factor) - self._currently_selected[1]
                            )

            self._draw.queue_draw()

    def on_utility_entity_direction_changed(self, *args):
        self._reapply_selected_entity()

    def on_utility_entity_type_changed(self, *args):
        self._reapply_selected_entity()

    def on_btn_goto_entity_editor_clicked(self, *args):
        idx = self.builder.get_object('utility_entity_type').get_active()
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY, idx
        ))

    def on_utility_tile_direction_changed(self, *args):
        self._reapply_selected_tile()

    def on_utility_tile_type_changed(self, *args):
        self._reapply_selected_tile()

    def on_tool_scene_goto_tileset_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_DUNGEON_TILESET, self.tileset_id
        ))

    def on_tool_choose_tileset_cb_changed(self, w: Gtk.ComboBox):
        idx = w.get_active()
        self.tileset_id = idx
        self._init_tileset()

    def on_tool_scene_copy_toggled(self, *args):
        self._enable_copy_or_move_mode()
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.COPY

    def on_tool_scene_add_entity_toggled(self, *args):
        self._enable_entity_editing()
        self._reapply_selected_entity()

    def on_tool_scene_add_tile_toggled(self, *args):
        self._enable_tile_editing()
        self._reapply_selected_tile()

    def on_tool_scene_move_toggled(self, *args):
        self._enable_copy_or_move_mode()
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.SELECT

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

    def on_settings_defeat_enemies_active_notify(self, w, *args):
        self.properties.exit_floor_when_defeating_enemies = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk4_active_notify(self, w, *args):
        self.properties.unk4 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk5_active_notify(self, w, *args):
        self.properties.unk5 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk8_active_notify(self, w, *args):
        self.properties.unk8 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_unk9_active_notify(self, w, *args):
        self.properties.unk9 = w.get_active()
        self.module.save_fixed_floor_properties(self.floor_id, self.properties)

    def on_settings_override_changed(self, w: Gtk.ComboBox, *args):
        self.override_id = w.get_active()
        self.module.save_fixed_floor_override(self.floor_id, self.override_id)

    def on_btn_apply_size_clicked(self, *args):
        try:
            width = int(self.builder.get_object('settings_width').get_text())
            height = int(self.builder.get_object('settings_height').get_text())
            if width == 0 or height == 0: # 0x0 rooms are allowed to be consistent with the fact that they exist
                width = height = 0
            assert width >= 0 and height >= 0
        except (ValueError, AssertionError):
            display_error(
                sys.exc_info(),
                _("Width and height must be numbers >= 0."),
                _("Invalid values.")
            )
            return

        confirm = True
        if width < self.floor.width or height < self.floor.height:
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.YES_NO,
                _("You are about to reduce the size of the room. This will delete tiles. Do you want to continue?"),
                title=_("Warning!")
            )
            response = md.run()
            md.destroy()
            confirm = response == Gtk.ResponseType.YES
        if confirm:
            self.floor.resize(width, height)
            self.module.mark_fixed_floor_as_modified(self.floor_id)
            MainController.reload_view()

    def on_btn_help_music_clicked(self, *args):
        self._help(_("If not set, the track ID specified on the floor this fixed floor is assigned to will be used "
                     "instead."))

    def on_btn_help_moves_clicked(self, *args):
        self._help(_("Whether or not moves can be used. Does not affect the regular attack. If 0, other Pokémon will "
                     "not attack (they won't even use the regular attack, not even if Exclusive Move-User is disabled"
                     ")"))

    def on_btn_help_orbs_clicked(self, *args):
        self._help(_("If the fixed floor ID is 0 or >= 165 this setting is ignored. Orbs are always allowed."))

    def on_btn_help_defeat_enemies_clicked(self, *args):
        self._help(_("If enabled, the floor is exited after all the enemies have been defeated"))

    def on_btn_help_unk8_clicked(self, *args):
        self._help(_("If the fixed floor ID is 0 or >= 165 this setting is ignored. It is always enabled."))

    def on_btn_help_unk9_clicked(self, *args):
        self._help(_("Prevents any kind of item pulling (such as with the Trawl Orb)."
                     "\nIf the fixed floor ID is 0 or >= 165 this setting is ignored. It is always enabled."))

    def on_btn_help_override_clicked(self, *args):
        self._help(_("If the dungeon mode is REQUEST (= the dungeon is marked as cleared once), this fixed floor will "
                     "be used instead.\nThis is used in dungeons where the content of a fixed floor varies depending "
                     "on the story progress, such as in most of the dungeons with a legendary Pokémon at the end "
                     "(first visit vs rematch)."))

    # END EDIT SETTINGS

    def _init_comboboxes(self):
        self._init_tileset_chooser()
        self._init_override_dropdown()
        self._init_entity_combobox()
        self._init_tile_combobox()
        self._init_direction_combobox()

    def _init_tileset_chooser(self):
        store = Gtk.ListStore(int, str)  # id, name
        for i in range(0, COUNT_VALID_TILESETS):
            if i >= TILESET_FIRST_BG:
                store.append([i, f(_("Background {i}"))])
            else:
                store.append([i, f(_("Tileset {i}"))])
        self._fast_set_comboxbox_store(self.builder.get_object('tool_choose_tileset_cb'), store, 1)

    def _init_override_dropdown(self):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, _("No override")])
        for i in range(1, 256):
            store.append([i, f(_("No. {i}"))])  # TRANSLATORS: Number {i}
        self._fast_set_comboxbox_store(self.builder.get_object('settings_override'), store, 1)

    def _init_entity_combobox(self):
        store = Gtk.ListStore(int, str)  # id, name
        reserved_ids = [x.value for x in TileRuleType]
        for i, (item_spawn, monster_spawn, tile_spawn, stats) in enumerate(self.entity_rule_container):
            # Make sure we are not allowing entities which would turn into tile rules upon saving!
            if i + 16 in reserved_ids:
                continue
            store.append([i, self._desc(i, item_spawn, monster_spawn, tile_spawn)])
        w = self.builder.get_object('utility_entity_type')
        self._fast_set_comboxbox_store(w, store, 1)
        w.set_active(0)

    def _init_tile_combobox(self):
        store = Gtk.ListStore(int, str)  # id, name
        for rule in TileRuleType:
            store.append([rule.value, f"{rule.value}: " + rule.explanation])
        w = self.builder.get_object('utility_tile_type')
        self._fast_set_comboxbox_store(w, store, 1)
        w.set_active(0)

    def _init_direction_combobox(self):
        store_tile = Gtk.ListStore(int, str)  # id, name
        store_entity = Gtk.ListStore(int, str)  # id, name
        store_tile.append([0, _('None')])
        store_entity.append([0, _('None')])
        for idx, dir in self.script_data.directions__by_ssa_id.items():
            store_tile.append([idx, dir.name])
            store_entity.append([idx, dir.name])
        w1 = self.builder.get_object('utility_tile_direction')
        w2 = self.builder.get_object('utility_entity_direction')
        self._fast_set_comboxbox_store(w1, store_tile, 1)
        self._fast_set_comboxbox_store(w2, store_entity, 1)
        w1.set_active(0)
        w2.set_active(0)

    def _desc(self, i, item_spawn, monster_spawn, tile_spawn):
        desc = f"{i}: " + self.module.desc_fixed_floor_tile(tile_spawn)
        if item_spawn.item_id > 0:
            desc += ", " + self.module.desc_fixed_floor_item(item_spawn.item_id)
        if monster_spawn.md_idx > 0:
            desc += ", " + self.module.desc_fixed_floor_monster(
                monster_spawn.md_idx, monster_spawn.enemy_settings.value, self.monster_names, self.enemy_settings_name,
                short=True
            )
        return desc

    def _place(self):
        if self._bg_draw_is_clicked__press_active and self.drawer.get_cursor_is_in_bounds(
                self.floor.width, self.floor.height, True
        ):
            x, y = self.drawer.get_cursor_pos_in_grid(True)
            if self.drawer.interaction_mode == InteractionMode.PLACE_TILE \
                    or self.drawer.interaction_mode == InteractionMode.PLACE_ENTITY:
                self.floor.actions[y * self.floor.width + x] = self.drawer.get_selected()
                self.module.mark_fixed_floor_as_modified(self.floor_id)

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
        self.builder.get_object('settings_defeat_enemies').set_active(self.properties.exit_floor_when_defeating_enemies)
        self.builder.get_object('settings_unk4').set_active(self.properties.unk4)
        self.builder.get_object('settings_unk5').set_active(self.properties.unk5)
        self.builder.get_object('settings_unk8').set_active(self.properties.unk8)
        self.builder.get_object('settings_unk9').set_active(self.properties.unk9)
        self.builder.get_object('settings_override').set_active(self.override_id)
        self.builder.get_object('settings_width').set_text(str(self.floor.width))
        self.builder.get_object('settings_height').set_text(str(self.floor.height))

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

    def _enable_entity_editing(self):
        stack: Gtk.Stack = self.builder.get_object('utility_stack')
        stack.set_visible_child(self.builder.get_object('utility_entity_frame'))
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_ENTITY

    def _enable_tile_editing(self):
        stack: Gtk.Stack = self.builder.get_object('utility_stack')
        stack.set_visible_child(self.builder.get_object('utility_tile_frame'))
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_TILE

    def _enable_copy_or_move_mode(self):
        stack: Gtk.Stack = self.builder.get_object('utility_stack')
        stack.set_visible_child(self.builder.get_object('utility_default'))

    def _reapply_selected_entity(self):
        dir = None
        dir_id = self.builder.get_object('utility_entity_direction').get_active()
        if dir_id > 0:
            dir = self.script_data.directions__by_ssa_id[dir_id]
        w = self.builder.get_object('utility_entity_type')
        entity_id = w.get_model()[w.get_active_iter()][0]
        self.drawer.set_selected(EntityRule(
            entity_id,
            dir
        ))
        entity = self.entity_rule_container.entities[entity_id]
        item_spawn, monster_spawn, tile_spawn, stats = self.entity_rule_container.get(entity_id)
        self.builder.get_object('utility_entity_frame_desc_label').set_markup(
            f"<b>Pokémon ({entity.monster_id})</b>:\n"
            f"{self.module.desc_fixed_floor_monster(monster_spawn.md_idx, monster_spawn.enemy_settings.value, self.long_monster_names, self.long_enemy_settings_name)}\n\n"
            f"<b>{_('Stats')} ({monster_spawn.stats_entry})</b>:\n"
            f"{self.module.desc_fixed_floor_stats(monster_spawn.stats_entry, stats)}\n\n"
            f"<b>{_('Item')} ({entity.item_id})</b>:\n"
            f"{self.module.desc_fixed_floor_item(item_spawn.item_id)}\n\n"
            f"<b>{_('Tile Properties')} ({entity.tile_id})</b>:\n"
            f"{self.module.desc_fixed_floor_tile(tile_spawn)}"
        )

    def _reapply_selected_tile(self):
        dir = None
        dir_id = self.builder.get_object('utility_tile_direction').get_active()
        if dir_id > 0:
            dir = self.script_data.directions__by_ssa_id[dir_id]
        w = self.builder.get_object('utility_tile_type')
        tile_rule = TileRuleType(w.get_model()[w.get_active_iter()][0])
        self.drawer.set_selected(TileRule(
            tile_rule,
            dir
        ))
        self.builder.get_object('utility_tile_frame_desc_label').set_markup(
            f"<b>{tile_rule.explanation}</b>\n"
            f"{_('Type')}: {tile_rule.floor_type.name.capitalize()}\n"
            f"{tile_rule.room_type.name.capitalize()}\n"
            f"{_('Impassable')}: {_('Yes') if tile_rule.impassable else _('No')}\n"
            f"Affected by Absolute Mover: {_('Yes') if tile_rule.absolute_mover else _('No')}\n"
            f"\n"
            f"{tile_rule.notes}"
        )

    def _select_combobox(self, cb_name: str, callback: Callable[[Mapping], bool]):
        cb: Gtk.ComboBox = self.builder.get_object(cb_name)
        l_iter = cb.get_model().get_iter_first()
        while l_iter is not None:
            if callback(cb.get_model()[l_iter]):
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)

    def _help(self, msg):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, msg)
        md.run()
        md.destroy()
