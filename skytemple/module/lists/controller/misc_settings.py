#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import logging
import re
from typing import TYPE_CHECKING

from gi.repository import Gtk

from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import BinaryName
from skytemple_files.hardcoded.dungeon_misc import HardcodedDungeonMisc
from skytemple_files.hardcoded.hp_items import HardcodedHpItems
from skytemple_files.hardcoded.main_menu_music import HardcodedMainMenuMusic
from skytemple_files.hardcoded.spawn_rate import HardcodedSpawnRate
from skytemple_files.hardcoded.text_speed import HardcodedTextSpeed

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)


class MiscSettingsController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'misc_settings.glade')
        box: Gtk.Box = self.builder.get_object('box')

        self._init_combos()
        self._init_values()

        self.builder.connect_signals(self)
        return box

    def on_entry_text_speed_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return

        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.ARM9, lambda bin: HardcodedTextSpeed.set_text_speed(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_cb_main_menu_music_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            static_data = self.module.project.get_rom_module().get_static_data()
            self.module.project.modify_binary(BinaryName.OVERLAY_00, lambda bin: (
                self.module.project.modify_binary(BinaryName.OVERLAY_09, lambda bin2: (
                    HardcodedMainMenuMusic.set_main_menu_music(model[cbiter][0], bin, static_data, bin2)
                ))
            ))
            self.module.mark_misc_settings_as_modified()

    def on_entry_normal_spawn_delay_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedSpawnRate.set_normal_spawn_rate(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_stolen_spawn_delay_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedSpawnRate.set_stolen_spawn_rate(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_belly_lost_changed(self, widget, *args):
        try:
            val = float(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_29, lambda bin: HardcodedDungeonMisc.set_belly_loss_turn(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_belly_lost_wtw_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_29, lambda bin: HardcodedDungeonMisc.set_belly_loss_walk_through_walls(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_belly_lost_wtw_1000_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_29, lambda bin: HardcodedDungeonMisc.set_belly_loss_1000ile_walk_through_walls(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_ginseng_3_chance_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedDungeonMisc.set_ginseng_increase_by_3_chance(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_life_seed_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedHpItems.set_life_seed_hp(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_oran_berry_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedHpItems.set_oran_berry_hp(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_sitrus_berry_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedHpItems.set_sitrus_berry_hp(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_burn_damage_delay_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedDungeonMisc.set_burn_damage_delay(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_poison_damage_delay_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedDungeonMisc.set_poison_damage_delay(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def on_entry_bad_poison_damage_delay_changed(self, widget, *args):
        try:
            val = int(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedDungeonMisc.set_bad_poison_damage_delay(val, bin, static_data))
        self.module.mark_misc_settings_as_modified()

    def _init_combos(self):
        # Init music tracks
        cb_store: Gtk.ListStore = self.builder.get_object('store_main_menu_music')
        # Init combobox
        cb_store.clear()
        for idx, track in self.module.project.get_rom_module().get_static_data().script_data.bgms__by_id.items():
            cb_store.append([idx, track.name])

    def _init_values(self):
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        ov00 = self.module.project.get_binary(BinaryName.OVERLAY_00)
        ov10 = self.module.project.get_binary(BinaryName.OVERLAY_10)
        ov29 = self.module.project.get_binary(BinaryName.OVERLAY_29)
        static_data = self.module.project.get_rom_module().get_static_data()

        self.builder.get_object('entry_text_speed').set_text(str(HardcodedTextSpeed.get_text_speed(arm9, static_data)))
        self.builder.get_object('cb_main_menu_music').set_active(HardcodedMainMenuMusic.get_main_menu_music(ov00, static_data))
        self.builder.get_object('entry_normal_spawn_delay').set_text(str(HardcodedSpawnRate.get_normal_spawn_rate(ov10, static_data)))
        self.builder.get_object('entry_stolen_spawn_delay').set_text(str(HardcodedSpawnRate.get_stolen_spawn_rate(ov10, static_data)))
        self.builder.get_object('entry_belly_lost').set_text(str(HardcodedDungeonMisc.get_belly_loss_turn(ov29, static_data)))
        self.builder.get_object('entry_belly_lost_wtw').set_text(str(HardcodedDungeonMisc.get_belly_loss_walk_through_walls(ov29, static_data)))
        self.builder.get_object('entry_belly_lost_wtw_1000').set_text(str(HardcodedDungeonMisc.get_belly_loss_1000ile_walk_through_walls(ov29, static_data)))
        self.builder.get_object('entry_ginseng_3_chance').set_text(str(HardcodedDungeonMisc.get_ginseng_increase_by_3_chance(ov10, static_data)))
        self.builder.get_object('entry_life_seed').set_text(str(HardcodedHpItems.get_life_seed_hp(ov10, static_data)))
        self.builder.get_object('entry_oran_berry').set_text(str(HardcodedHpItems.get_oran_berry_hp(ov10, static_data)))
        self.builder.get_object('entry_sitrus_berry').set_text(str(HardcodedHpItems.get_sitrus_berry_hp(ov10, static_data)))
        self.builder.get_object('entry_burn_damage_delay').set_text(str(HardcodedDungeonMisc.get_burn_damage_delay(ov10, static_data)))
        self.builder.get_object('entry_poison_damage_delay').set_text(str(HardcodedDungeonMisc.get_poison_damage_delay(ov10, static_data)))
        self.builder.get_object('entry_bad_poison_damage_delay').set_text(str(HardcodedDungeonMisc.get_bad_poison_damage_delay(ov10, static_data)))
