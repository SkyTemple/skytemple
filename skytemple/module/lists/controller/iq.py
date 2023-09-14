#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
from enum import Enum, auto
from functools import partial
from typing import TYPE_CHECKING, cast, Optional

from gi.repository import Gtk
from range_typed_integers import u16, u16_checked, u8, u8_checked, i32, i32_checked, i16, i16_checked

from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, builder_get_assert, create_tree_view_column, assert_not_none
from skytemple_files.common.i18n_util import _
from skytemple_files.data.md.protocol import IQGroup
from skytemple_files.hardcoded.iq import HardcodedIq, IqGroupsSkills

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

PATTERN_ITEM_ENTRY = re.compile(r'.*\(#(\d+)\).*')
logger = logging.getLogger(__name__)
FIRST_GUMMI_ITEM_ID = 119
WONDER_GUMMI_ITEM_ID = 136
FAIRY_GUMMI_ITEM_ID = 138
NECTAR_ITEM_ID = 103
PATCH_IQ_SKILL_GROUPS = 'CompressIQData'


class IqGainOtherItem(Enum):
    WONDER_GUMMI = auto()
    NECTAR = auto()
    JUICE_BAR_NECTAR = auto()


class IqController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self._string_provider = module.project.get_string_provider()
        self.builder: Gtk.Builder = None  # type: ignore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'iq.glade')
        box = builder_get_assert(self.builder, Gtk.Box, 'box_list')

        self._init_iq_gains()
        self._init_iq_skills()
        self._init_misc_settings()

        self.builder.connect_signals(self)
        return box

    @catch_overflow(u16)
    def on_entry_min_iq_exclusive_move_user_changed(self, widget, *args):
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.ARM9, lambda bin: HardcodedIq.set_min_iq_for_exclusive_move_user(val, bin, static_data))
        self.module.mark_iq_as_modified()

    @catch_overflow(u16)
    def on_entry_min_iq_item_master_changed(self, widget, *args):
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.ARM9, lambda bin: HardcodedIq.set_min_iq_for_item_master(val, bin, static_data))
        self.module.mark_iq_as_modified()

    @catch_overflow(u16)
    def on_intimidator_activation_chance_changed(self, widget, *args):
        try:
            val = u16_checked(int(widget.get_text()))
        except ValueError:
            return
        static_data = self.module.project.get_rom_module().get_static_data()
        self.module.project.modify_binary(BinaryName.OVERLAY_10, lambda bin: HardcodedIq.set_intimidator_chance(val, bin, static_data))
        self.module.mark_iq_as_modified()

    @catch_overflow(u8)
    def on_cr_other_iq_gain_edited(self, widget, path, text):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'iq_gain_other_items')
        static_data = self.module.project.get_rom_module().get_static_data()
        try:
            val = u8_checked(int(text))
        except ValueError:
            return
        typ: IqGainOtherItem = store[path][0]
        store[path][2] = text

        if typ == IqGainOtherItem.NECTAR:
            self.module.project.modify_binary(
                BinaryName.OVERLAY_29, lambda bin: HardcodedIq.set_nectar_gain(val, bin, static_data)
            )
            self.module.mark_iq_as_modified()
        elif typ == IqGainOtherItem.WONDER_GUMMI:
            self.module.project.modify_binary(
                BinaryName.ARM9, lambda bin: HardcodedIq.set_wonder_gummi_gain(val, bin, static_data)
            )
            self.module.mark_iq_as_modified()
        elif typ == IqGainOtherItem.JUICE_BAR_NECTAR:
            self.module.project.modify_binary(
                BinaryName.ARM9, lambda bin: HardcodedIq.set_juice_bar_nectar_gain(val, bin, static_data)
            )
            self.module.mark_iq_as_modified()

    @catch_overflow(i32)
    def on_cr_iq_pnts_edited(self, widget, path, text):
        store = assert_not_none(cast(Optional[Gtk.ListStore], builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_skills').get_model()))
        try:
            val = i32_checked(int(text))
        except ValueError:
            return
        store[path][2] = text

        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        static_data = self.module.project.get_rom_module().get_static_data()
        iq_skills = HardcodedIq.get_iq_skills(arm9, static_data)
        iq_skills[int(store[path][0])].iq_required = val
        self.module.project.modify_binary(
            BinaryName.ARM9, lambda bin: HardcodedIq.set_iq_skills(iq_skills, bin, static_data)
        )

        self.module.mark_iq_as_modified()

    @catch_overflow(i16)
    def on_cr_iq_restrictions_edited(self, widget, path, text):
        store = assert_not_none(cast(Optional[Gtk.ListStore], builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_skills').get_model()))
        try:
            val = i16_checked(int(text))
        except ValueError:
            return
        store[path][3] = text

        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        static_data = self.module.project.get_rom_module().get_static_data()
        iq_skills = HardcodedIq.get_iq_skills(arm9, static_data)
        iq_skills[int(store[path][0])].restriction_group = val
        self.module.project.modify_binary(
            BinaryName.ARM9, lambda bin: HardcodedIq.set_iq_skills(iq_skills, bin, static_data)
        )

        self.module.mark_iq_as_modified()

    @catch_overflow(u8)
    def on_cr_iq_gain_edited(self, widget, path, text, *, type_id):
        store = assert_not_none(cast(Optional[Gtk.ListStore], builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_gain').get_model()))
        try:
            val = u8_checked(int(text))
        except ValueError:
            return
        store[path][type_id + 2] = text
        gummi_id = store[path][0]

        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        patch_applied = self.module.project.is_patch_applied("AddTypes")
        static_data = self.module.project.get_rom_module().get_static_data()
        gains = HardcodedIq.get_gummi_iq_gains(arm9, static_data, patch_applied)
        gains[type_id][gummi_id] = val
        self.module.project.modify_binary(
            BinaryName.ARM9, lambda bin: HardcodedIq.set_gummi_iq_gains(gains, bin, static_data, patch_applied)
        )

        self.module.mark_iq_as_modified()

    @catch_overflow(u8)
    def on_cr_belly_heal_edited(self, widget, path, text, *, type_id):
        store = assert_not_none(cast(Optional[Gtk.ListStore], builder_get_assert(self.builder, Gtk.TreeView, 'tree_belly_gain').get_model()))
        try:
            val = u8_checked(int(text))
        except ValueError:
            return
        store[path][type_id + 2] = text
        gummi_id = store[path][0]

        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        patch_applied = self.module.project.is_patch_applied("AddTypes")
        static_data = self.module.project.get_rom_module().get_static_data()
        gains = HardcodedIq.get_gummi_belly_heal(arm9, static_data, patch_applied)
        gains[type_id][gummi_id] = val
        self.module.project.modify_binary(
            BinaryName.ARM9, lambda bin: HardcodedIq.set_gummi_belly_heal(gains, bin, static_data, patch_applied)
        )

        self.module.mark_iq_as_modified()

    @catch_overflow(u8)
    def on_cr_skill_to_group(self, widget, path, *, group_id):
        selected = not widget.get_active()
        store = assert_not_none(cast(Optional[Gtk.ListStore], builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_skills').get_model()))
        store[path][group_id + 4] = selected
        skill_id = u8_checked(int(store[path][0]))

        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        static_data = self.module.project.get_rom_module().get_static_data()
        assert self.module.project.is_patch_applied(PATCH_IQ_SKILL_GROUPS)
        groups = IqGroupsSkills.read_compressed(arm9, static_data)
        if selected:
            if skill_id not in groups[group_id]:
                groups[group_id].append(skill_id)
                groups[group_id].sort()
        else:
            if skill_id in groups[group_id]:
                groups[group_id].remove(skill_id)
        self.module.project.modify_binary(
            BinaryName.ARM9, lambda bin: IqGroupsSkills.write_compressed(bin, groups, static_data)
        )

        self.module.mark_iq_as_modified()

    def _init_misc_settings(self):
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        ov10 = self.module.project.get_binary(BinaryName.OVERLAY_10)
        static_data = self.module.project.get_rom_module().get_static_data()

        builder_get_assert(self.builder, Gtk.Entry, 'entry_min_iq_exclusive_move_user').set_text(str(HardcodedIq.get_min_iq_for_exclusive_move_user(arm9, static_data)))
        builder_get_assert(self.builder, Gtk.Entry, 'entry_min_iq_item_master').set_text(str(HardcodedIq.get_min_iq_for_item_master(arm9, static_data)))
        builder_get_assert(self.builder, Gtk.Entry, 'intimidator_activation_chance').set_text(str(HardcodedIq.get_intimidator_chance(ov10, static_data)))

    def _init_iq_gains(self):
        """
        Store format:
        - int: id
        - str: gummi name
        For each gummi:
        - str: (type name)
        Tree is the same layout. Name column already exists.
        """
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        ov29 = self.module.project.get_binary(BinaryName.OVERLAY_29)
        static_data = self.module.project.get_rom_module().get_static_data()
        patch_applied = self.module.project.is_patch_applied("AddTypes")
        type_strings = self._string_provider.get_all(StringType.TYPE_NAMES)
        gummi_iq_gain_table = HardcodedIq.get_gummi_iq_gains(arm9, static_data, patch_applied)
        gummi_belly_gain_table = HardcodedIq.get_gummi_belly_heal(arm9, static_data, patch_applied)
        num_types = min(len(gummi_iq_gain_table), len(type_strings))

        # Normal Gummis
        store: Gtk.ListStore = Gtk.ListStore(*([int, str] + [str] * num_types))
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_gain')
        store_belly: Gtk.ListStore = Gtk.ListStore(*([int, str] + [str] * num_types))
        tree_belly = builder_get_assert(self.builder, Gtk.TreeView, 'tree_belly_gain')
        tree.set_model(store)
        tree_belly.set_model(store_belly)
        for i in range(0, num_types):
            if i == 0:
                continue
            gummi_item_id = FIRST_GUMMI_ITEM_ID + i - 1
            if i == 18:
                gummi_item_id = FAIRY_GUMMI_ITEM_ID
            gummi_name = self._string_provider.get_value(StringType.ITEM_NAMES, gummi_item_id)
            data = [i, gummi_name]
            data_belly = [i, gummi_name]
            for j in range(0, num_types):
                data.append(str(gummi_iq_gain_table[j][i]))
                data_belly.append(str(gummi_belly_gain_table[j][i]))
            store.append(data)
            store_belly.append(data_belly)

            # column and cell renderer
            renderer: Gtk.CellRendererText = Gtk.CellRendererText(editable=True)
            renderer.connect('edited', partial(self.on_cr_iq_gain_edited, type_id=i))
            column = create_tree_view_column(type_strings[i], renderer, text=i + 2)
            tree.append_column(column)
            renderer = Gtk.CellRendererText(editable=True)
            renderer.connect('edited', partial(self.on_cr_belly_heal_edited, type_id=i))
            column = create_tree_view_column(type_strings[i], renderer, text=i + 2)
            tree_belly.append_column(column)

        # Other items
        store_other_items = builder_get_assert(self.builder, Gtk.ListStore, 'iq_gain_other_items')
        store_other_items.append([
            IqGainOtherItem.WONDER_GUMMI,
            self._string_provider.get_value(StringType.ITEM_NAMES, WONDER_GUMMI_ITEM_ID),
            str(HardcodedIq.get_wonder_gummi_gain(arm9, static_data))
        ])
        store_other_items.append([
            IqGainOtherItem.NECTAR,
            self._string_provider.get_value(StringType.ITEM_NAMES, NECTAR_ITEM_ID),
            str(HardcodedIq.get_nectar_gain(ov29, static_data))
        ])
        store_other_items.append([
            IqGainOtherItem.JUICE_BAR_NECTAR,
            _("Juice Bar Nectar"),
            str(HardcodedIq.get_juice_bar_nectar_gain(arm9, static_data))
        ])

    def _init_iq_skills(self):
        arm9 = self.module.project.get_binary(BinaryName.ARM9)
        static_data = self.module.project.get_rom_module().get_static_data()
        iq_skills = HardcodedIq.get_iq_skills(arm9, static_data)
        if self.module.project.is_patch_applied(PATCH_IQ_SKILL_GROUPS):
            restrictions = IqGroupsSkills.read_compressed(arm9, static_data)
        else:
            restrictions = IqGroupsSkills.read_uncompressed(arm9, static_data)
        assert len(restrictions) == len(IQGroup)
        # Ignore invalid
        restrictions.pop()

        # noinspection PyTypeChecker
        store: Gtk.ListStore = Gtk.ListStore(*([str, str, str, str] + [bool] * (len(IQGroup) - 1)))
        tree: Gtk.TreeView = builder_get_assert(self.builder, Gtk.TreeView, 'tree_iq_skills')
        tree.set_model(store)

        for i, skill in enumerate(iq_skills):
            if i == 0:
                # Add columns and cell renderers for IQ groups
                for entry_i, entry in enumerate(IQGroup):
                    if entry == IQGroup.INVALID:
                        continue
                    renderer: Gtk.CellRendererToggle = Gtk.CellRendererToggle(activatable=self.module.project.is_patch_applied(PATCH_IQ_SKILL_GROUPS))
                    renderer.connect('toggled', partial(self.on_cr_skill_to_group, group_id=entry_i))
                    column = create_tree_view_column(entry.print_name, renderer, active=entry_i + 4)
                    tree.append_column(column)
                continue

            iq_group_assignments = []
            for group in restrictions:
                iq_group_assignments.append(i in group)

            # noinspection PyTypeChecker
            store.append([
                str(i), self._string_provider.get_value(
                    StringType.IQ_SKILL_NAMES, i - 1
                ), str(skill.iq_required), str(skill.restriction_group)
            ] + iq_group_assignments)
