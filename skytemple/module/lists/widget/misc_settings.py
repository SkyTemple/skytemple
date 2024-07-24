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
import logging
import re
from typing import TYPE_CHECKING, cast
from gi.repository import Gtk
from range_typed_integers import u8, u8_checked, u16, u16_checked
from skytemple.core.rom_project import BinaryName
from skytemple.core.ui_utils import catch_overflow, data_dir
from skytemple_files.hardcoded.dungeon_misc import HardcodedDungeonMisc
from skytemple_files.hardcoded.hp_items import HardcodedHpItems
from skytemple_files.hardcoded.main_menu_music import HardcodedMainMenuMusic
from skytemple_files.hardcoded.spawn_rate import HardcodedSpawnRate
from skytemple_files.hardcoded.text_speed import HardcodedTextSpeed

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
PATTERN_ITEM_ENTRY = re.compile(".*\\(#(\\d+)\\).*")
logger = logging.getLogger(__name__)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "lists", "misc_settings.ui"))
class StListsMiscSettingsPage(Gtk.Box):
    __gtype_name__ = "StListsMiscSettingsPage"
    module: ListsModule
    item_data: None
    store_main_menu_music: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    entry_normal_spawn_delay: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_stolen_spawn_delay: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    cb_main_menu_music: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    entry_belly_lost_wtw: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_burn_damage_delay: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_poison_damage_delay: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_bad_poison_damage_delay: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_belly_lost: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_belly_lost_wtw_1000: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_text_speed: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_ginseng_3_chance: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_life_seed: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_oran_berry: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    entry_sitrus_berry: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())

    def __init__(self, module: ListsModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self._string_provider = module.project.get_string_provider()
        self._init_combos()
        self._init_values()
        self._suppress_signals = False

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_entry_text_speed_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u8_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.ARM9,
            lambda bin: HardcodedTextSpeed.set_text_speed(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    def on_cb_main_menu_music_changed(self, widget: Gtk.ComboBox, *args):
        if self._suppress_signals:
            return
        model, cbiter = (widget.get_model(), widget.get_active_iter())
        if model is not None and cbiter is not None and (cbiter != []):
            static_data = self.module.project.get_rom_module().get_static_data()
            mus = model[cbiter][0]
            self.module.project.modify_binary(
                BinaryName.OVERLAY_00,
                lambda bin: self.module.project.modify_binary(
                    BinaryName.OVERLAY_09,
                    lambda bin2: HardcodedMainMenuMusic.set_main_menu_music(mus, bin, static_data, bin2),
                ),
            )
            self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_normal_spawn_delay_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedSpawnRate.set_normal_spawn_rate(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_stolen_spawn_delay_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedSpawnRate.set_stolen_spawn_rate(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    def on_entry_belly_lost_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = float(widget.get_text())
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_29,
            lambda bin: HardcodedDungeonMisc.set_belly_loss_turn(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_belly_lost_wtw_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_29,
            lambda bin: HardcodedDungeonMisc.set_belly_loss_walk_through_walls(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_belly_lost_wtw_1000_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_29,
            lambda bin: HardcodedDungeonMisc.set_belly_loss_1000ile_walk_through_walls(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_ginseng_3_chance_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedDungeonMisc.set_ginseng_increase_by_3_chance(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_life_seed_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedHpItems.set_life_seed_hp(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_oran_berry_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedHpItems.set_oran_berry_hp(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_sitrus_berry_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedHpItems.set_sitrus_berry_hp(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_burn_damage_delay_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedDungeonMisc.set_burn_damage_delay(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_poison_damage_delay_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedDungeonMisc.set_poison_damage_delay(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    @Gtk.Template.Callback()
    @catch_overflow(u16)
    def on_entry_bad_poison_damage_delay_changed(self, widget, *args):
        if self._suppress_signals:
            return
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(
            BinaryName.OVERLAY_10,
            lambda bin: HardcodedDungeonMisc.set_bad_poison_damage_delay(val, bin, static_data),
        )
        self.module.mark_misc_settings_as_modified()

    def _init_combos(self):
        # Init music tracks
        cb_store = self.store_main_menu_music
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
        self.entry_text_speed.set_text(str(HardcodedTextSpeed.get_text_speed(arm9, static_data)))
        self.cb_main_menu_music.set_active(HardcodedMainMenuMusic.get_main_menu_music(ov00, static_data))
        self.entry_normal_spawn_delay.set_text(str(HardcodedSpawnRate.get_normal_spawn_rate(ov10, static_data)))
        self.entry_stolen_spawn_delay.set_text(str(HardcodedSpawnRate.get_stolen_spawn_rate(ov10, static_data)))
        self.entry_belly_lost.set_text(str(HardcodedDungeonMisc.get_belly_loss_turn(ov29, static_data)))
        self.entry_belly_lost_wtw.set_text(
            str(HardcodedDungeonMisc.get_belly_loss_walk_through_walls(ov29, static_data))
        )
        self.entry_belly_lost_wtw_1000.set_text(
            str(HardcodedDungeonMisc.get_belly_loss_1000ile_walk_through_walls(ov29, static_data))
        )
        self.entry_ginseng_3_chance.set_text(
            str(HardcodedDungeonMisc.get_ginseng_increase_by_3_chance(ov10, static_data))
        )
        self.entry_life_seed.set_text(str(HardcodedHpItems.get_life_seed_hp(ov10, static_data)))
        self.entry_oran_berry.set_text(str(HardcodedHpItems.get_oran_berry_hp(ov10, static_data)))
        self.entry_sitrus_berry.set_text(str(HardcodedHpItems.get_sitrus_berry_hp(ov10, static_data)))
        self.entry_burn_damage_delay.set_text(str(HardcodedDungeonMisc.get_burn_damage_delay(ov10, static_data)))
        self.entry_poison_damage_delay.set_text(str(HardcodedDungeonMisc.get_poison_damage_delay(ov10, static_data)))
        self.entry_bad_poison_damage_delay.set_text(
            str(HardcodedDungeonMisc.get_bad_poison_damage_delay(ov10, static_data))
        )
