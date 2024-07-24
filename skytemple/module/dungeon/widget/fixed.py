#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
from __future__ import annotations
import sys
from typing import TYPE_CHECKING, Callable, cast
from gi.repository import Gtk, Gdk
from range_typed_integers import u32_checked, u32, u8
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.md.protocol import Gender
from skytemple.controller.main import MainController
from skytemple.core.canvas_scale import CanvasScale
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.open_request import (
    OpenRequest,
    REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY,
    REQUEST_TYPE_DUNGEON_TILESET,
)
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate
from skytemple.module.dungeon import (
    COUNT_VALID_TILESETS,
    TILESET_FIRST_BG,
    SPECIAL_MONSTERS,
)
from skytemple.module.dungeon.entity_rule_container import EntityRuleContainer
from skytemple.module.dungeon.fixed_room_drawer import (
    FixedRoomDrawer,
    InfoLayer,
    InteractionMode,
)
from skytemple.module.dungeon.fixed_room_entity_renderer.full_map import (
    FullMapEntityRenderer,
)
from skytemple.module.dungeon.fixed_room_entity_renderer.minimap import (
    MinimapEntityRenderer,
)
from skytemple.module.dungeon.fixed_room_tileset_renderer.bg import (
    FixedFloorDrawerBackground,
)
from skytemple.module.dungeon.fixed_room_tileset_renderer.minimap import (
    FixedFloorDrawerMinimap,
)
from skytemple.module.dungeon.fixed_room_tileset_renderer.tileset import (
    FixedFloorDrawerTileset,
)
from skytemple.module.dungeon.minimap_provider import MinimapProvider
from skytemple_files.dungeon_data.fixed_bin.model import (
    FixedFloor,
    TileRuleType,
    TileRule,
    EntityRule,
)
from skytemple_files.graphics.dpc import DPC_TILING_DIM
from skytemple_files.graphics.dpci import DPCI_TILE_DIM
from skytemple_files.hardcoded.fixed_floor import MonsterSpawnType
from skytemple_files.common.i18n_util import _, f

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon", "fixed.ui"))
class StDungeonFixedPage(Gtk.Notebook):
    __gtype_name__ = "StDungeonFixedPage"
    module: DungeonModule
    item_data: int
    dialog_map_import_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_collision_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_layers_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    ovl_add_entity: Gtk.Overlay = cast(Gtk.Overlay, Gtk.Template.Child())
    ovl_add_tile: Gtk.Overlay = cast(Gtk.Overlay, Gtk.Template.Child())
    tab_scene: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    tool_scene_zoom_in: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tool_scene_zoom_out: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tool_scene_grid: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tool_scene_move: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tool_scene_add_tile: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tool_scene_add_entity: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tool_scene_copy: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tool_choose_tileset: Gtk.ToolItem = cast(Gtk.ToolItem, Gtk.Template.Child())
    tool_choose_tileset_cb: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    tool_scene_goto_tileset: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tb_info_layer: Gtk.ToolItem = cast(Gtk.ToolItem, Gtk.Template.Child())
    tb_info_layer_none: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tb_info_layer_tiles: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tb_info_layer_items: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tb_info_layer_monsters: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tb_info_layer_traps: Gtk.RadioToolButton = cast(Gtk.RadioToolButton, Gtk.Template.Child())
    tool_fullmap: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    utility_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    utility_default: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    utility_tile_frame: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    utility_tile_frame_desc_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    utility_tile_type: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    utility_tile_direction: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    utility_tile_frame_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    utility_entity_frame: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    utility_entity_frame_desc_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    btn_goto_entity_editor: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    utility_entity_type: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    utility_entity_direction: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    utility_entity_frame_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    legend_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    info_none: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    info_tiles: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    info_items: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    info_monsters: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    info_traps: Gtk.Frame = cast(Gtk.Frame, Gtk.Template.Child())
    fixed_draw_event: Gtk.EventBox = cast(Gtk.EventBox, Gtk.Template.Child())
    fixed_draw: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    tab_triggers: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    settings_grid: Gtk.Grid = cast(Gtk.Grid, Gtk.Template.Child())
    btn_help_music: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_moves: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_moves: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_orbs: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    btn_help_orbs: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_override: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    btn_help_override: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_music: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    settings_height: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    settings_width: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    settings_unk9: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_unk8: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_unk5: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_unk4: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    btn_help_unk9: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_defeat_enemies: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    btn_help_unk8: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_defeat_enemies: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_apply_size: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_complete: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_boss: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    settings_free: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    btn_help_complete: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_boss: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_free: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_help_unk5: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    _last_scale_factor: CanvasScale | None = None
    _last_show_full_map = True

    def __init__(self, module: DungeonModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self.tileset_id = 0
        if self.__class__._last_scale_factor is not None:
            self._scale_factor = self.__class__._last_scale_factor
        else:
            self._scale_factor = CanvasScale(1.0)
        self.drawer: FixedRoomDrawer | None = None
        self.entity_rule_container: EntityRuleContainer = EntityRuleContainer(
            *self.module.get_fixed_floor_entity_lists()
        )
        self.properties = self.module.get_fixed_floor_properties()[self.item_data]
        self.override_id = self.module.get_fixed_floor_overrides()[self.item_data]
        # TODO: Duplicated code
        self.enemy_settings_name = [f"{i}" for i in range(0, 256)]
        self.long_enemy_settings_name = [f"{i}: ???" for i in range(0, 256)]
        for spawn_type in MonsterSpawnType:
            self.enemy_settings_name[spawn_type.value] = f"{spawn_type.description}"
            self.long_enemy_settings_name[spawn_type.value] = f"{spawn_type.value}: {spawn_type.description}"
        self.monster_names = {}
        self.long_monster_names = {}
        length = len(self.module.get_monster_md().entries)
        num_entities = FileType.MD.properties().num_entities
        for i, entry in enumerate(self.module.get_monster_md().entries):
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, i % num_entities)
            self.monster_names[i] = f"{name}"
            self.long_monster_names[i] = f"{name} ({Gender(entry.gender).name.capitalize()}) (${i:04})"
        for i in range(length, length + SPECIAL_MONSTERS):
            self.monster_names[i] = _("(Special?)")
            self.long_monster_names[i] = _("(Special?)") + f" (${i:04})"
        self.floor: FixedFloor | None = None
        self._draw: Gtk.DrawingArea | None = None
        self._bg_draw_is_clicked__press_active = False
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location: tuple[int, int] | None = None
        self._currently_selected = None
        self.script_data = self.module.project.get_rom_module().get_static_data().script_data
        self._draw = self.fixed_draw
        self._init_comboboxes()
        self._auto_select_tileset()
        self._init_fixed_floor()
        self._load_settings()
        self._init_drawer()
        tool_fullmap = self.tool_fullmap
        tool_fullmap.set_active(self._last_show_full_map)
        self.on_tool_fullmap_toggled(tool_fullmap, ignore_scaling=True)
        self._update_scales()
        self._suppress_signals = False

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.ovl_add_entity)
        safe_destroy(self.ovl_add_tile)

    @Gtk.Template.Callback()
    def on_fixed_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        if not self.drawer:
            return
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            assert self.floor
            self._bg_draw_is_clicked__press_active = True
            self._bg_draw_is_clicked__drag_active = False
            self._bg_draw_is_clicked__location = (int(button.x), int(button.y))
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)
            self.drawer.end_drag()
            # PLACE
            self._place()
            # COPY
            if self.drawer.interaction_mode == InteractionMode.COPY:
                if self.drawer.get_cursor_is_in_bounds(self.floor.width, self.floor.height, True):
                    x, y = self.drawer.get_cursor_pos_in_grid(True)
                    action_to_copy = self.floor.actions[y * self.floor.width + x]
                    if isinstance(action_to_copy, TileRule):
                        self.tool_scene_add_tile.set_active(True)
                        self._select_combobox(
                            "utility_tile_type",
                            lambda row: row[0] == action_to_copy.tr_type.value,
                        )
                        self._select_combobox(
                            "utility_tile_direction",
                            lambda row: row[0] == action_to_copy.direction.ssa_id
                            if action_to_copy.direction is not None
                            else 0,
                        )
                    else:
                        self.tool_scene_add_entity.set_active(True)
                        self._select_combobox(
                            "utility_entity_type",
                            lambda row: row[0] == action_to_copy.entity_rule_id,
                        )
                        self._select_combobox(
                            "utility_entity_direction",
                            lambda row: row[0] == action_to_copy.direction.ssa_id
                            if action_to_copy.direction is not None
                            else 0,
                        )
            # SELECT
            elif self.drawer.interaction_mode == InteractionMode.SELECT:
                if self.drawer.get_cursor_is_in_bounds(self.floor.width, self.floor.height, True):
                    self._currently_selected = self.drawer.get_cursor_pos_in_grid(True)
        if self._draw:
            self._draw.queue_draw()

    @Gtk.Template.Callback()
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
                        self.floor.actions[tile_y * self.floor.width + tile_x] = self.floor.actions[
                            old_y * self.floor.width + old_x
                        ]
                        # Insert floor at old position
                        self.floor.actions[old_y * self.floor.width + old_x] = TileRule(TileRuleType.FLOOR_ROOM, None)
                        self.module.mark_fixed_floor_as_modified(self.item_data)
        self._currently_selected = None
        self._bg_draw_is_clicked__location = None
        self._bg_draw_is_clicked__drag_active = False
        if self.drawer:
            self.drawer.end_drag()
        if self._draw:
            self._draw.queue_draw()

    @Gtk.Template.Callback()
    def on_fixed_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)
            # PLACE
            self._place()
            if self._currently_selected is not None:
                this_x = motion.x
                this_y = motion.y
                if self._bg_draw_is_clicked__location is not None:
                    start_x, start_y = self._bg_draw_is_clicked__location
                    # Start drag & drop if mouse moved at least one tile.
                    if not self._bg_draw_is_clicked__drag_active and (
                        abs(start_x - this_x) > DPC_TILING_DIM * DPCI_TILE_DIM * 0.7 * self._scale_factor
                        or abs(start_y - this_y) > DPC_TILING_DIM * DPCI_TILE_DIM * 0.7 * self._scale_factor
                    ):
                        start_x /= self._scale_factor
                        start_y /= self._scale_factor
                        if self.drawer.get_pos_is_in_bounds(
                            start_x, start_y, self.floor.width, self.floor.height, True
                        ):
                            self.drawer.set_selected(self.drawer.get_pos_in_grid(start_x, start_y, True))
                            self._bg_draw_is_clicked__drag_active = True
                            self.drawer.set_drag_position(
                                int((start_x - 4) / self._scale_factor) - self._currently_selected[0],
                                int((start_y - 4) / self._scale_factor) - self._currently_selected[1],
                            )
            if self._draw:
                self._draw.queue_draw()

    @Gtk.Template.Callback()
    def on_utility_entity_direction_changed(self, *args):
        if not self._suppress_signals:
            self._reapply_selected_entity()

    @Gtk.Template.Callback()
    def on_utility_entity_type_changed(self, *args):
        if not self._suppress_signals:
            self._reapply_selected_entity()

    @Gtk.Template.Callback()
    def on_btn_goto_entity_editor_clicked(self, *args):
        idx = self.utility_entity_type.get_active()
        self.module.project.request_open(OpenRequest(REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY, idx))

    @Gtk.Template.Callback()
    def on_utility_tile_direction_changed(self, *args):
        if not self._suppress_signals:
            self._reapply_selected_tile()

    @Gtk.Template.Callback()
    def on_utility_tile_type_changed(self, *args):
        if not self._suppress_signals:
            self._reapply_selected_tile()

    @Gtk.Template.Callback()
    def on_tool_scene_goto_tileset_clicked(self, *args):
        self.module.project.request_open(OpenRequest(REQUEST_TYPE_DUNGEON_TILESET, self.tileset_id))

    @Gtk.Template.Callback()
    def on_tool_choose_tileset_cb_changed(self, w: Gtk.ComboBox):
        if not self._suppress_signals:
            idx = w.get_active()
            self.tileset_id = idx
            self.on_tool_fullmap_toggled(self.tool_fullmap, ignore_scaling=True)

    @Gtk.Template.Callback()
    def on_tool_scene_copy_toggled(self, *args):
        self._enable_copy_or_move_mode()
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.COPY

    @Gtk.Template.Callback()
    def on_tool_scene_add_entity_toggled(self, *args):
        self._enable_entity_editing()
        self._reapply_selected_entity()

    @Gtk.Template.Callback()
    def on_tool_scene_add_tile_toggled(self, *args):
        self._enable_tile_editing()
        self._reapply_selected_tile()

    @Gtk.Template.Callback()
    def on_tool_scene_move_toggled(self, *args):
        self._enable_copy_or_move_mode()
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.SELECT

    @Gtk.Template.Callback()
    def on_tool_scene_grid_toggled(self, w: Gtk.ToggleButton):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())

    @Gtk.Template.Callback()
    def on_tb_info_layer_none_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(None)
        info = self.info_none
        self.legend_stack.set_visible_child(info)

    @Gtk.Template.Callback()
    def on_tb_info_layer_tiles_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.TILE)
        info = self.info_tiles
        self.legend_stack.set_visible_child(info)

    @Gtk.Template.Callback()
    def on_tb_info_layer_items_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.ITEM)
        info = self.info_items
        self.legend_stack.set_visible_child(info)

    @Gtk.Template.Callback()
    def on_tb_info_layer_monsters_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.MONSTER)
        info = self.info_monsters
        self.legend_stack.set_visible_child(info)

    @Gtk.Template.Callback()
    def on_tb_info_layer_traps_toggled(self, *args):
        if self.drawer:
            self.drawer.set_info_layer(InfoLayer.TRAP)
        info = self.info_traps
        self.legend_stack.set_visible_child(info)

    @Gtk.Template.Callback()
    def on_tool_scene_zoom_in_clicked(self, *args):
        self._scale_factor *= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tool_scene_zoom_out_clicked(self, *args):
        self._scale_factor /= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tool_fullmap_toggled(self, w: Gtk.ToggleToolButton, *args, ignore_scaling=False):
        self.__class__._last_show_full_map = w.get_active()
        if w.get_active():
            if not ignore_scaling:
                self._scale_factor //= 10
                self.__class__._last_scale_factor = self._scale_factor
            if self.drawer:
                self.drawer.set_entity_renderer(FullMapEntityRenderer(self.drawer))
            self._init_tileset()
        else:
            if not ignore_scaling:
                self._scale_factor *= 10
                self.__class__._last_scale_factor = self._scale_factor
            minimap_provider = MinimapProvider(self.module.get_zmappa())
            if self.drawer:
                self.drawer.set_entity_renderer(MinimapEntityRenderer(self.drawer, minimap_provider))
                self.drawer.set_tileset_renderer(FixedFloorDrawerMinimap(minimap_provider))
        self._update_scales()
        if self._draw:
            self._draw.queue_draw()

    # EDIT SETTINGS

    @Gtk.Template.Callback()
    @catch_overflow(u32)
    def on_settings_music_changed(self, w):
        if not self._suppress_signals:
            try:
                self.properties.music_track = u32_checked(int(w.get_text()))
            except ValueError:
                return
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_complete_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            if state:
                self.properties.null |= 1  # type: ignore
            else:
                self.properties.null &= ~1  # type: ignore
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_boss_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            if state:
                self.properties.null |= 2  # type: ignore
            else:
                self.properties.null &= ~2  # type: ignore
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_free_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            if state:
                self.properties.null |= 4  # type: ignore
            else:
                self.properties.null &= ~4  # type: ignore
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_moves_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.moves_enabled = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_orbs_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.orbs_enabled = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_defeat_enemies_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.exit_floor_when_defeating_enemies = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_unk4_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.unk4 = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_unk5_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.unk5 = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_unk8_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.unk8 = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_unk9_state_set(self, w: Gtk.Switch, state: bool, *args):
        if not self._suppress_signals:
            self.properties.unk9 = state
            self.module.save_fixed_floor_properties(self.item_data, self.properties)

    @Gtk.Template.Callback()
    def on_settings_override_changed(self, w: Gtk.ComboBox, *args):
        if not self._suppress_signals:
            self.override_id = u8(w.get_active())
            self.module.save_fixed_floor_override(self.item_data, self.override_id)

    @Gtk.Template.Callback()
    def on_btn_apply_size_clicked(self, *args):
        try:
            width = int(self.settings_width.get_text())
            height = int(self.settings_height.get_text())
            if width == 0 or height == 0:  # 0x0 rooms are allowed to be consistent with the fact that they exist
                width = height = 0
            assert width >= 0 and height >= 0
        except (ValueError, AssertionError):
            display_error(
                sys.exc_info(),
                _("Width and height must be numbers >= 0."),
                _("Invalid values."),
            )
            return
        confirm = True
        assert self.floor is not None
        if width < self.floor.width or height < self.floor.height:
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.WARNING,
                Gtk.ButtonsType.YES_NO,
                _("You are about to reduce the size of the room. This will delete tiles. Do you want to continue?"),
                title=_("Warning!"),
            )
            response = md.run()
            md.destroy()
            confirm = response == Gtk.ResponseType.YES
        if confirm:
            self.floor.resize(width, height)
            self.module.mark_fixed_floor_as_modified(self.item_data)
            MainController.reload_view()

    @Gtk.Template.Callback()
    def on_btn_help_music_clicked(self, *args):
        self._help(
            _("If not set, the track ID specified on the floor this fixed floor is assigned to will be used instead.")
        )

    @Gtk.Template.Callback()
    def on_btn_help_moves_clicked(self, *args):
        self._help(
            _(
                "Whether or not moves can be used. Does not affect the regular attack. If 0, other Pokémon will not attack (they won't even use the regular attack, not even if Exclusive Move-User is disabled)"
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_orbs_clicked(self, *args):
        self._help(
            _(
                "If ChangeFixedFloorProperties is not applied and the fixed floor ID is 0 or >= 165 this setting is ignored. Orbs are always allowed."
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_defeat_enemies_clicked(self, *args):
        self._help(_("If enabled, the floor is exited after all the enemies have been defeated"))

    @Gtk.Template.Callback()
    def on_btn_help_unk5_clicked(self, *args):
        self._help(
            _(
                "If disabled, certain traps (Summon, Pitfall and Pokémon) will be disabled.\nIf ChangeFixedFloorProperties is not applied and the fixed floor ID is 0 or >= 165 this setting is ignored. It is always enabled."
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_unk8_clicked(self, *args):
        self._help(
            _(
                "If disabled, warping, being blown away and leaping effects will be disabled.\nIf ChangeFixedFloorProperties is not applied and the fixed floor ID is 0 or >= 165 this setting is ignored. It is always enabled."
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_unk9_clicked(self, *args):
        self._help(
            _(
                "If disabled, prevents any kind of item pulling (such as with the Trawl Orb).\nIf ChangeFixedFloorProperties is not applied and the fixed floor ID is 0 or >= 165 this setting is ignored. It is always enabled."
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_complete_clicked(self, *args):
        self._help(
            _(
                "If enabled, the game will treat this fixed room as an entire floor, not a single room in a floor layout.\nIf ChangeFixedFloorProperties is not applied, this will only be enabled when the fixed floor ID is between 1 and 164. "
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_boss_clicked(self, *args):
        self._help(
            _(
                "Enables boss fight conditions.\nIf ChangeFixedFloorProperties is not applied, this will only be enabled when the fixed floor ID is between 1 and 80. "
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_free_clicked(self, *args):
        self._help(
            _(
                "Allows free layouts. For example, fixed rooms with this setting can omit stairs.\nIf ChangeFixedFloorProperties is not applied, this will only be enabled when the fixed floor ID is between 1 and 110. "
            )
        )

    @Gtk.Template.Callback()
    def on_btn_help_override_clicked(self, *args):
        self._help(
            _(
                "If the dungeon mode is REQUEST (= the dungeon is marked as cleared once), this fixed floor will be used instead.\nThis is used in dungeons where the content of a fixed floor varies depending on the story progress, such as in most of the dungeons with a legendary Pokémon at the end (first visit vs rematch)."
            )
        )

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
        self._fast_set_comboxbox_store(self.tool_choose_tileset_cb, store, 1)

    def _init_override_dropdown(self):
        store = Gtk.ListStore(int, str)  # id, name
        store.append([0, _("No override")])
        for i in range(1, 256):
            store.append([i, f(_("No. {i}"))])  # TRANSLATORS: Number {i}
        self._fast_set_comboxbox_store(self.settings_override, store, 1)

    def _init_entity_combobox(self):
        store = Gtk.ListStore(int, str)  # id, name
        reserved_ids = [x.value for x in TileRuleType]
        for i, (item_spawn, monster_spawn, tile_spawn, stats) in enumerate(self.entity_rule_container):
            # Make sure we are not allowing entities which would turn into tile rules upon saving!
            if i + 16 in reserved_ids:
                continue
            store.append([i, self._desc(i, item_spawn, monster_spawn, tile_spawn)])
        w = self.utility_entity_type
        self._fast_set_comboxbox_store(w, store, 1)
        w.set_active(0)

    def _init_tile_combobox(self):
        store = Gtk.ListStore(int, str)  # id, name
        for rule in TileRuleType:
            store.append([rule.value, f"{rule.value}: " + rule.explanation])
        w = self.utility_tile_type
        self._fast_set_comboxbox_store(w, store, 1)
        w.set_active(0)

    def _init_direction_combobox(self):
        store_tile = Gtk.ListStore(int, str)  # id, name
        store_entity = Gtk.ListStore(int, str)  # id, name
        store_tile.append([0, _("None")])
        store_entity.append([0, _("None")])
        for idx, dir in self.script_data.directions__by_ssa_id.items():
            store_tile.append([idx, dir.name])
            store_entity.append([idx, dir.name])
        w1 = self.utility_tile_direction
        w2 = self.utility_entity_direction
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
                monster_spawn.md_idx,
                monster_spawn.enemy_settings.value,
                self.monster_names,
                self.enemy_settings_name,
                short=True,
            )
        return desc

    def _place(self):
        assert self.floor is not None and self.drawer is not None
        if self._bg_draw_is_clicked__press_active and self.drawer.get_cursor_is_in_bounds(
            self.floor.width, self.floor.height, True
        ):
            x, y = self.drawer.get_cursor_pos_in_grid(True)
            if (
                self.drawer.interaction_mode == InteractionMode.PLACE_TILE
                or self.drawer.interaction_mode == InteractionMode.PLACE_ENTITY
            ):
                self.floor.actions[y * self.floor.width + x] = self.drawer.get_selected()
                self.module.mark_fixed_floor_as_modified(self.item_data)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _auto_select_tileset(self):
        cb: Gtk.ComboBox = self.tool_choose_tileset_cb
        self.tileset_id = self.module.get_default_tileset_for_fixed_floor(self.item_data)
        cb.set_active(self.tileset_id)

    def _load_settings(self):
        assert self.floor is not None
        self.settings_music.set_text(str(self.properties.music_track))
        self.settings_moves.set_active(self.properties.moves_enabled)
        self.settings_orbs.set_active(self.properties.orbs_enabled)
        self.settings_defeat_enemies.set_active(self.properties.exit_floor_when_defeating_enemies)
        self.settings_unk4.set_active(self.properties.unk4)
        self.settings_unk5.set_active(self.properties.unk5)
        self.settings_unk8.set_active(self.properties.unk8)
        self.settings_unk9.set_active(self.properties.unk9)
        self.settings_override.set_active(self.override_id)
        self.settings_width.set_text(str(self.floor.width))
        self.settings_height.set_text(str(self.floor.height))
        if not self.module.project.is_patch_applied("ChangeFixedFloorProperties"):
            self.settings_complete.set_sensitive(False)
            self.settings_boss.set_sensitive(False)
            self.settings_free.set_sensitive(False)
            self.settings_complete.set_active(bool(1 <= self.item_data < 165))
            self.settings_boss.set_active(bool(1 <= self.item_data <= 80))
            self.settings_free.set_active(bool(1 <= self.item_data <= 110))
        else:
            self.settings_complete.set_active(bool(self.properties.null & 1))
            self.settings_boss.set_active(bool(self.properties.null & 2))
            self.settings_free.set_active(bool(self.properties.null & 4))

    def _init_fixed_floor(self):
        # Fixed floor data
        self.floor = self.module.get_fixed_floor(self.item_data)

    def _init_tileset(self):
        assert self.drawer is not None
        if self.tileset_id < TILESET_FIRST_BG:
            # Real tileset
            self.drawer.set_tileset_renderer(FixedFloorDrawerTileset(*self.module.get_dungeon_tileset(self.tileset_id)))
        else:
            # Background to render using dummy tileset
            self.drawer.set_tileset_renderer(
                FixedFloorDrawerBackground(
                    *self.module.get_dungeon_background(self.tileset_id - TILESET_FIRST_BG),
                    *self.module.get_dummy_tileset(),
                )
            )

    def _init_drawer(self):
        if self._draw:
            self.drawer = FixedRoomDrawer(
                self._draw,
                self.floor,
                self.module.project.get_sprite_provider(),
                self.entity_rule_container,
                self.module.project.get_string_provider(),
                self.module,
            )
            self.drawer.start()
            self.drawer.set_draw_tile_grid(self.tool_scene_grid.get_active())

    def _update_scales(self):
        assert self.drawer is not None and self._draw is not None and (self.drawer.tileset_renderer is not None)
        assert self.floor is not None
        self._draw.set_size_request(
            (self.floor.width + 10) * self.drawer.tileset_renderer.chunk_dim() * self._scale_factor,
            (self.floor.height + 10) * self.drawer.tileset_renderer.chunk_dim() * self._scale_factor,
        )
        self.drawer.set_scale(self._scale_factor)
        self._draw.queue_draw()

    def _enable_entity_editing(self):
        stack: Gtk.Stack = self.utility_stack
        stack.set_visible_child(self.utility_entity_frame)
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_ENTITY

    def _enable_tile_editing(self):
        stack: Gtk.Stack = self.utility_stack
        stack.set_visible_child(self.utility_tile_frame)
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_TILE

    def _enable_copy_or_move_mode(self):
        stack: Gtk.Stack = self.utility_stack
        stack.set_visible_child(self.utility_default)

    def _reapply_selected_entity(self):
        dir = None
        dir_id = self.utility_entity_direction.get_active()
        if dir_id > 0:
            dir = self.script_data.directions__by_ssa_id[dir_id]
        w = self.utility_entity_type
        active_iter = w.get_active_iter()
        assert active_iter is not None
        entity_id = w.get_model()[active_iter][0]
        assert self.drawer is not None
        self.drawer.set_selected(EntityRule(entity_id, dir))
        entity = self.entity_rule_container.entities[entity_id]
        item_spawn, monster_spawn, tile_spawn, stats = self.entity_rule_container.get(entity_id)
        self.utility_entity_frame_desc_label.set_markup(
            f"<b>Pokémon ({entity.monster_id})</b>:\n{self.module.desc_fixed_floor_monster(monster_spawn.md_idx, monster_spawn.enemy_settings.value, self.long_monster_names, self.long_enemy_settings_name)}\n\n<b>{_('Stats')} ({monster_spawn.stats_entry})</b>:\n{self.module.desc_fixed_floor_stats(monster_spawn.stats_entry, stats)}\n\n<b>{_('Item')} ({entity.item_id})</b>:\n{self.module.desc_fixed_floor_item(item_spawn.item_id)}\n\n<b>{_('Tile Properties')} ({entity.tile_id})</b>:\n{self.module.desc_fixed_floor_tile(tile_spawn)}"
        )

    def _reapply_selected_tile(self):
        dir = None
        dir_id = self.utility_tile_direction.get_active()
        if dir_id > 0:
            dir = self.script_data.directions__by_ssa_id[dir_id]
        w = self.utility_tile_type
        active_iter = w.get_active_iter()
        assert active_iter is not None
        tile_rule = TileRuleType(w.get_model()[active_iter][0])  # type: ignore
        assert self.drawer is not None
        self.drawer.set_selected(TileRule(tile_rule, dir))
        self.utility_tile_frame_desc_label.set_markup(
            f"<b>{tile_rule.explanation}</b>\n{_('Type')}: {tile_rule.floor_type.name.capitalize()}\n{tile_rule.room_type.name.capitalize()}\n{_('Impassable')}: {(_('Yes') if tile_rule.impassable else _('No'))}\nAffected by Absolute Mover: {(_('Yes') if tile_rule.absolute_mover else _('No'))}\n\n{tile_rule.notes}"
        )

    def _select_combobox(self, cb_name: str, callback: Callable[[Gtk.TreeModelRow], bool]):
        cb = getattr(self, cb_name)
        l_iter = cb.get_model().get_iter_first()
        while l_iter is not None:
            if callback(cb.get_model()[l_iter]):
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)

    def _help(self, msg):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            msg,
        )
        md.run()
        md.destroy()
