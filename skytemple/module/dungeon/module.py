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
import logging
from typing import Optional, List, Union, Iterable, Tuple
from xml.etree.ElementTree import Element

from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label
from skytemple.module.dungeon.controller.dojos import DOJOS_NAME, DojosController
from skytemple.module.dungeon.controller.dungeon import DungeonController
from skytemple.module.dungeon.controller.fixed_rooms import FIXED_ROOMS_NAME, FixedRoomsController
from skytemple.module.dungeon.controller.floor import FloorController
from skytemple.module.dungeon.controller.group import GroupController
from skytemple.module.dungeon.controller.main import MainController, DUNGEONS_NAME
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.md.model import Md
from skytemple_files.dungeon_data.mappa_bin.floor import MappaFloor
from skytemple_files.dungeon_data.mappa_bin.mappa_xml import mappa_floor_xml_import
from skytemple_files.dungeon_data.mappa_bin.model import MappaBin
from skytemple_files.dungeon_data.mappa_g_bin.mappa_converter import convert_mappa_to_mappag
from skytemple_files.hardcoded.dungeons import HardcodedDungeons, DungeonDefinition, DungeonRestriction

# TODO: Add this to dungeondata.xml?
DOJO_DUNGEONS_FIRST = 0xB4
DOJO_DUNGEONS_LAST = 0xBF
DOJO_MAPPA_ENTRY = 0x35
# Those are not actual dungeons and share mappa floor data with Temporal Tower future.
INVALID_DUNGEON_IDS = [175, 176, 177, 178]
ICON_ROOT = 'skytemple-e-dungeon-symbolic'
ICON_DUNGEONS = 'skytemple-folder-symbolic'  # TODO: Remove.
ICON_FIXED_ROOMS = 'skytemple-e-dungeon-fixed-floor-symbolic'
ICON_GROUP = 'skytemple-folder-open-symbolic'
ICON_DUNGEON = 'skytemple-e-dungeon-symbolic'
ICON_FLOOR = 'skytemple-e-dungeon-floor-symbolic'
MAPPA_PATH = 'BALANCE/mappa_s.bin'
MAPPAG_PATH = 'BALANCE/mappa_gs.bin'
logger = logging.getLogger(__name__)


class DungeonViewInfo:
    def __init__(self, dungeon_id: int, length_can_be_edited: bool):
        self.dungeon_id = dungeon_id
        self.length_can_be_edited = length_can_be_edited


class FloorViewInfo:
    def __init__(self, floor_id: int, dungeon: DungeonViewInfo):
        self.floor_id = floor_id
        self.dungeon = dungeon


class DungeonGroup:
    def __init__(self, base_dungeon_id: int, dungeon_ids: List[int], start_ids: List[int]):
        self.base_dungeon_id = base_dungeon_id
        self.dungeon_ids = dungeon_ids
        self.start_ids = start_ids

    def __int__(self):
        return self.base_dungeon_id


class DungeonModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 210

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self._tree_model = None
        self._root_iter = None
        self._dungeon_iters = {}
        self._dungeon_floor_iters = {}

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            ICON_ROOT, DUNGEONS_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._root_iter = root

        # Regular dungeons
        for dungeon_or_group in self.load_dungeons():
            if isinstance(dungeon_or_group, DungeonGroup):
                # Group
                group = item_store.append(root, [
                    ICON_GROUP, self.generate_group_label(dungeon_or_group.base_dungeon_id), self, GroupController,
                    dungeon_or_group.base_dungeon_id, False, '', True
                ])
                for dungeon, start_id in zip(dungeon_or_group.dungeon_ids, dungeon_or_group.start_ids):
                    self._dungeon_iters[dungeon] = self._add_dungeon_to_tree(group, item_store, dungeon, start_id)
            else:
                # Dungeon
                self._dungeon_iters[dungeon_or_group] = self._add_dungeon_to_tree(root, item_store, dungeon_or_group, 0)

        # Dojo dungeons
        dojo_root = item_store.append(root, [
            ICON_DUNGEONS, DOJOS_NAME, self, DojosController, 0, False, '', True
        ])
        for i in range(DOJO_DUNGEONS_FIRST, DOJO_DUNGEONS_LAST + 1):
            self._dungeon_iters[i] = self._add_dungeon_to_tree(dojo_root, item_store, i, 0)

        # Fixed rooms
        fixed_rooms = item_store.append(root_node, [
            ICON_FIXED_ROOMS, FIXED_ROOMS_NAME, self, FixedRoomsController, 0, False, '', True
        ])
        # TODO Fixed rooms

        recursive_generate_item_store_row_label(self._tree_model[root])
        recursive_generate_item_store_row_label(self._tree_model[fixed_rooms])

    def get_mappa(self) -> MappaBin:
        return self.project.open_file_in_rom(MAPPA_PATH, FileType.MAPPA_BIN)

    def get_mappa_floor(self, item: FloorViewInfo) -> MappaFloor:
        """Returns the correct mappa floor based on the given dungeon ID and floor number"""
        did = item.dungeon.dungeon_id
        # if ID >= 0xB4 && ID <= 0xBD {
        if DOJO_DUNGEONS_FIRST <= did <= DOJO_DUNGEONS_FIRST + 9:
            return self.get_mappa().floor_lists[DOJO_MAPPA_ENTRY][item.floor_id + (did - DOJO_DUNGEONS_FIRST) * 5]
        elif did == DOJO_DUNGEONS_FIRST + 10:
            return self.get_mappa().floor_lists[DOJO_MAPPA_ENTRY][item.floor_id + 0x32]
        elif DOJO_DUNGEONS_FIRST + 11 <= did <= 0xD3:
            return self.get_mappa().floor_lists[DOJO_MAPPA_ENTRY][item.floor_id + 0x33]
        else:
            dungeon = self.get_dungeon_list()[item.dungeon.dungeon_id]
            return self.get_mappa().floor_lists[dungeon.mappa_index][item.floor_id]

    def mark_floor_as_modified(self, item: FloorViewInfo):
        # TODO: Regenerate mappa_g.
        self.project.mark_as_modified(MAPPA_PATH)
        # Mark as modified in tree
        row = self._tree_model[self._dungeon_floor_iters[item.dungeon.dungeon_id][item.floor_id]]
        recursive_up_item_store_mark_as_modified(row)

    def get_dungeon_list(self) -> List[DungeonDefinition]:
        # TODO: Cache?
        return HardcodedDungeons.get_dungeon_list(
            self.project.get_binary(BinaryName.ARM9), self.project.get_rom_module().get_static_data()
        )

    def get_dungeon_restrictions(self) -> List[DungeonRestriction]:
        # TODO: Cache?
        return HardcodedDungeons.get_dungeon_restrictions(
            self.project.get_binary(BinaryName.ARM9), self.project.get_rom_module().get_static_data()
        )

    def mark_dungeon_as_modified(self, dungeon_id, modified_mappa=True):
        self.project.get_string_provider().mark_as_modified()
        if modified_mappa:
            self._save_mappa()

        # Mark as modified in tree
        row = self._tree_model[self._dungeon_iters[dungeon_id]]
        recursive_up_item_store_mark_as_modified(row)

    def save_dungeon_list(self, dungeons: List[DungeonDefinition]):
        self.project.modify_binary(BinaryName.ARM9, lambda binary: HardcodedDungeons.set_dungeon_list(
            dungeons, binary, self.project.get_rom_module().get_static_data()
        ))

    def update_dungeon_restrictions(self, dungeon_id: int, restrictions: DungeonRestriction):
        all_restrictions = self.get_dungeon_restrictions()
        all_restrictions[dungeon_id] = restrictions
        self.save_dungeon_restrictions(all_restrictions)

    def save_dungeon_restrictions(self, restrictions: List[DungeonRestriction]):
        self.project.modify_binary(BinaryName.ARM9, lambda binary: HardcodedDungeons.set_dungeon_restrictions(
            restrictions, binary, self.project.get_rom_module().get_static_data()
        ))

    def _save_mappa(self):
        self.project.mark_as_modified(MAPPA_PATH)
        self.project.save_file_manually(MAPPAG_PATH, FileType.MAPPA_G_BIN.serialize(
            convert_mappa_to_mappag(self.get_mappa())
        ))

    def _add_dungeon_to_tree(self, root_node, item_store, idx, previous_floor_id):
        dungeon_info = DungeonViewInfo(idx, idx < DOJO_DUNGEONS_FIRST)
        dungeon = item_store.append(root_node, [
            ICON_DUNGEON, self.generate_dungeon_label(idx), self, DungeonController,
            dungeon_info, False, '', True
        ])
        if idx not in self._dungeon_floor_iters:
            self._dungeon_floor_iters[idx] = {}
        for floor_i in range(0, self.get_number_floors(idx)):
            self._dungeon_floor_iters[idx][previous_floor_id + floor_i] = item_store.append(dungeon, [
                ICON_FLOOR, self.generate_floor_label(floor_i + previous_floor_id), self, FloorController,
                FloorViewInfo(previous_floor_id + floor_i, dungeon_info), False, '', True
            ])
        return dungeon

    def load_dungeons(self) -> Iterable[Union[DungeonGroup, int]]:
        """
        Returns the dungeons, grouped by the same mappa_index. The dungeons and groups are overall sorted
        by their IDs.
        """
        lst = self.get_dungeon_list()
        groups = {}
        yielded = set()
        for idx, dungeon in enumerate(lst):
            if idx in INVALID_DUNGEON_IDS:
                continue
            if dungeon.mappa_index not in groups:
                groups[dungeon.mappa_index] = []
            groups[dungeon.mappa_index].append(idx)
        for idx, dungeon in enumerate(lst):
            if idx in INVALID_DUNGEON_IDS:
                continue
            if dungeon.mappa_index not in yielded:
                yielded.add(dungeon.mappa_index)
                if len(groups[dungeon.mappa_index]) < 2:
                    idx = groups[dungeon.mappa_index][0]
                    # This should be the only dungeon then.
                    # TODO: For 136 this somehow isn't true...
                    assert idx == 136 or lst[idx].number_floors == lst[idx].number_floors_in_group
                    assert lst[idx].start_after == 0
                    yield idx
                else:
                    yield DungeonGroup(groups[dungeon.mappa_index][0], groups[dungeon.mappa_index], [
                        lst[idx].start_after for idx in groups[dungeon.mappa_index]
                    ])

    def regroup_dungeons(self, new_groups: Iterable[Union[DungeonGroup, int]]):
        """
        Apply new dungeon groups.
        This updates the dungeon list file, the mappa files and the UI tree.
        start_ids of the DungeonGroups may be empty, it is ignored and calculated from the current dungeons instead.
        INVALID_DUNGEON_IDS will not be modified. Otherwise the list MUST contain all other regular dungeons
        (before DOJO_DUNGEONS_FIRST), just like self.load_dungeons would return it.
        """
        # DONT'T FORGET ABOUT INVALID_DUNGEON_IDS AND DOJO_DUNGEONS_FIRST
        raise NotImplementedError()

    def generate_group_label(self, base_dungeon_id) -> str:
        dname = self.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, base_dungeon_id)
        return f'"{dname}" Group'

    def generate_dungeon_label(self, idx) -> str:
        return f'{idx}: {self.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, idx)}'

    def generate_floor_label(self, floor_i) -> str:
        return f'Floor {floor_i + 1}'

    def get_number_floors(self, idx) -> int:
        # End:
        # Function that returns the number of floors in a dungeon:
        # if ID >= 0xB4 && ID <= 0xBD {
        #     return 5
        # } else if ID == 0xBE {
        #     return 1
        # } else if ID >= 0xBF {
        #     return 0x30
        # } else {
        #     Read the value from arm9.bin
        # }
        if DOJO_DUNGEONS_FIRST <= idx <= DOJO_DUNGEONS_LAST - 2:
            return 5
        if idx == DOJO_DUNGEONS_LAST - 1:
            return 1
        if idx == DOJO_DUNGEONS_LAST:
            return 0x30
        return self.get_dungeon_list()[idx].number_floors

    def get_monster_md(self) -> Md:
        return self.project.get_module('monster').monster_md

    def import_from_xml(self, selected_floors: List[Tuple[int, int]], xml: Element):
        for dungeon_id, floor_id in selected_floors:
            floor_info = FloorViewInfo(floor_id, DungeonViewInfo(dungeon_id, False))
            floor = self.get_mappa_floor(floor_info)
            mappa_floor_xml_import(xml, floor)
            self.mark_floor_as_modified(floor_info)
