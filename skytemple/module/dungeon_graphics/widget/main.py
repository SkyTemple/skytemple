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
from enum import Enum
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, iter_tree_model, data_dir
from skytemple_files.common.i18n_util import _
from skytemple_files.data.md.protocol import PokeType
from skytemple_files.hardcoded.dungeons import (
    TilesetMapColor,
    TilesetStirringEffect,
    TilesetSecretPowerEffect,
    TilesetNaturePowerMoveEntry,
    TilesetWeatherEffect,
    TilesetProperties,
)

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule
DUNGEON_GRAPHICS_NAME = _("Dungeon Graphics")
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon_graphics", "main.ui"))
class StDungeonGraphicsMainPage(Gtk.Box):
    __gtype_name__ = "StDungeonGraphicsMainPage"
    module: DungeonGraphicsModule
    item_data: None
    box_edit: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    level_list_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_name: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_map_color: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_stirring_effect: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_secret_power_effect: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_camouflage_type: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_nature_power_move_entry: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_weather_effect: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_full_water_floor: Gtk.CellRendererToggle = cast(Gtk.CellRendererToggle, Gtk.Template.Child())
    list_tree_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())

    def __init__(self, module: DungeonGraphicsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.lst = self.module.get_tileset_properties()
        self._init_combo_stores()
        self._init_values()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_map_color_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][2] = cb_store[new_iter][0]
        store[path][9] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_stirring_effect_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][3] = cb_store[new_iter][0]
        store[path][10] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_secret_power_effect_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][4] = cb_store[new_iter][0]
        store[path][11] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_camouflage_type_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][5] = cb_store[new_iter][0]
        store[path][12] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_nature_power_move_entry_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][6] = cb_store[new_iter][0]
        store[path][13] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_weather_effect_changed(self, widget: Gtk.CellRendererCombo, path, new_iter, *args):
        store = self.list_tree_store
        cb_store = widget.props.model
        store[path][7] = cb_store[new_iter][0]
        store[path][14] = cb_store[new_iter][1]
        self._save_list()

    @Gtk.Template.Callback()
    def on_cr_full_water_floor_toggled(self, widget: Gtk.CellRendererToggle, path):
        store = self.list_tree_store
        store[path][8] = not widget.get_active()
        self._save_list()

    def _init_combo_stores(self):
        # cr_map_color
        self._create_for_enum(self.cr_map_color, TilesetMapColor)
        # cr_stirring_effect
        self._create_for_enum(self.cr_stirring_effect, TilesetStirringEffect)
        # cr_secret_power_effect
        self._create_for_enum(self.cr_secret_power_effect, TilesetSecretPowerEffect)
        # cr_camouflage_type
        self._create_for_enum_with_strings(self.cr_camouflage_type, PokeType, StringType.TYPE_NAMES)
        # cr_nature_power_move_entry
        self._create_for_enum(self.cr_nature_power_move_entry, TilesetNaturePowerMoveEntry)
        # cr_weather_effect
        self._create_for_enum(self.cr_weather_effect, TilesetWeatherEffect)

    def _create_for_enum(self, cr: Gtk.CellRendererCombo, en: type[Enum]):
        store = Gtk.ListStore(int, str)  # id, name
        cr.props.model = store
        for e in en:
            store.append([e.value, e.print_name])  # type: ignore

    def _create_for_enum_with_strings(self, cr: Gtk.CellRendererCombo, en: type[Enum], string_type: StringType):
        store = Gtk.ListStore(int, str)  # id, name
        cr.props.model = store
        for e in en:
            store.append(
                [
                    e.value,
                    self.module.project.get_string_provider().get_value(string_type, e.value),
                ]
            )

    def _init_values(self):
        from skytemple.module.dungeon_graphics.module import NUMBER_OF_TILESETS

        store = self.list_tree_store
        for i, v in enumerate(self.lst):
            store.append(
                [
                    str(i),
                    f"{_('Tileset')} {i}" if i < NUMBER_OF_TILESETS else f"{_('Background')} {i}",
                    v.map_color.value,
                    v.stirring_effect.value,
                    v.secret_power_effect.value,
                    v.camouflage_type.value,
                    v.nature_power_move_entry.value,
                    v.weather_effect.value,
                    v.full_water_floor,
                    v.map_color.print_name,
                    v.stirring_effect.print_name,
                    v.secret_power_effect.print_name,
                    self.module.project.get_string_provider().get_value(StringType.TYPE_NAMES, v.camouflage_type.value),
                    v.nature_power_move_entry.print_name,
                    v.weather_effect.print_name,
                ]
            )

    def _save_list(self):
        self.lst = []
        for row in iter_tree_model(self.list_tree_store):
            self.lst.append(
                TilesetProperties(
                    TilesetMapColor(row[2]),  # type: ignore
                    TilesetStirringEffect(row[3]),  # type: ignore
                    TilesetSecretPowerEffect(row[4]),  # type: ignore
                    PokeType(row[5]),
                    TilesetNaturePowerMoveEntry(row[6]),  # type: ignore
                    TilesetWeatherEffect(row[7]),  # type: ignore
                    bool(row[8]),
                )
            )
        self.module.set_tileset_properties(self.lst)
