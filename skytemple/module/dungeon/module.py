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
import logging
import os
from typing import Optional, List, Union, Iterable, Tuple
from xml.etree.ElementTree import Element

from PIL import Image
from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_FIXED_FLOOR, \
    REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY, REQUEST_TYPE_DUNGEONS
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, \
    recursive_generate_item_store_row_label, data_dir
from skytemple.module.dungeon import MAX_ITEMS
from skytemple.module.dungeon.controller.dojos import DOJOS_NAME, DojosController
from skytemple.module.dungeon.controller.dungeon import DungeonController
from skytemple.module.dungeon.controller.fixed import FixedController
from skytemple.module.dungeon.controller.fixed_rooms import FIXED_ROOMS_NAME, FixedRoomsController
from skytemple.module.dungeon.controller.floor import FloorController
from skytemple.module.dungeon.controller.group import GroupController
from skytemple.module.dungeon.controller.invalid import InvalidDungeonController
from skytemple.module.dungeon.controller.main import MainController, DUNGEONS_NAME
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.data.md.model import Md
from skytemple_files.dungeon_data.fixed_bin.model import FixedBin
from skytemple_files.dungeon_data.mappa_bin.floor import MappaFloor
from skytemple_files.dungeon_data.mappa_bin.mappa_xml import mappa_floor_xml_import
from skytemple_files.dungeon_data.mappa_bin.model import MappaBin
from skytemple_files.dungeon_data.mappa_bin.trap_list import MappaTrapType
from skytemple_files.dungeon_data.mappa_bin.validator.validator import DungeonValidator
from skytemple_files.dungeon_data.mappa_g_bin.mappa_converter import convert_mappa_to_mappag
from skytemple_files.graphics.dbg.model import Dbg
from skytemple_files.graphics.dma.model import Dma
from skytemple_files.graphics.dpc.model import Dpc
from skytemple_files.graphics.dpci.model import Dpci
from skytemple_files.graphics.dpl.model import Dpl
from skytemple_files.hardcoded.dungeons import HardcodedDungeons, DungeonDefinition, DungeonRestriction
from skytemple_files.dungeon_data.floor_attribute.handler import FloorAttributeHandler

# TODO: Add this to dungeondata.xml?
from skytemple_files.hardcoded.fixed_floor import EntitySpawnEntry, ItemSpawn, MonsterSpawn, TileSpawn, \
    MonsterSpawnStats, HardcodedFixedFloorTables, FixedFloorProperties
from skytemple_files.common.i18n_util import _, f

DOJO_DUNGEONS_FIRST = 0xB4
DOJO_DUNGEONS_LAST = 0xBF
DOJO_MAPPA_ENTRY = 0x35
ICON_ROOT = 'skytemple-e-dungeon-symbolic'
ICON_DUNGEONS = 'skytemple-folder-symbolic'  # TODO: Remove.
ICON_FIXED_ROOMS = 'skytemple-e-dungeon-fixed-floor-symbolic'
ICON_GROUP = 'skytemple-folder-symbolic'
ICON_DUNGEON = 'skytemple-e-dungeon-symbolic'
ICON_FLOOR = 'skytemple-e-dungeon-floor-symbolic'
MAPPA_PATH = 'BALANCE/mappa_s.bin'
MAPPAG_PATH = 'BALANCE/mappa_gs.bin'
FIXED_PATH = 'BALANCE/fixed.bin'
DUNGEON_BIN = 'DUNGEON/dungeon.bin'
logger = logging.getLogger(__name__)
FLOOR_RANKS = "BALANCE/f_ranks.bin"
FLOOR_MISSION_FORBIDDEN = "BALANCE/fforbid.bin"

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

        self._tree_model: Optional[Gtk.TreeModel] = None
        self._root_iter = None
        self._dungeon_iters = {}
        self._dungeon_floor_iters = {}
        self._fixed_floor_iters = []
        self._fixed_floor_root_iter = None
        self._fixed_floor_data: Optional[FixedBin] = None
        self._dungeon_bin: Optional[DungeonBinPack] = None
        self._cached_dungeon_list = None

        # Preload mappa
        self.get_mappa()
        self._validator = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        self._validator = DungeonValidator(self.get_mappa().floor_lists)
        root = item_store.append(root_node, [
            ICON_ROOT, DUNGEONS_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._root_iter = root

        static_data = self.project.get_rom_module().get_static_data()
        self._fixed_floor_data = self.project.open_file_in_rom(
            FIXED_PATH, FileType.FIXED_BIN,
            static_data=static_data
        )
        self._dungeon_bin: DungeonBinPack = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN,
            static_data=static_data
        )

        self._validator.validate(self.get_dungeon_list())

        self._fill_dungeon_tree()

        # Fixed rooms
        self._fixed_floor_root_iter = item_store.append(root_node, [
            ICON_FIXED_ROOMS, FIXED_ROOMS_NAME, self, FixedRoomsController, 0, False, '', True
        ])
        for i in range(0, len(self._fixed_floor_data.fixed_floors)):
            self._fixed_floor_iters.append(item_store.append(self._fixed_floor_root_iter, [
                ICON_FIXED_ROOMS, f(_('Fixed Room {i}')), self, FixedController,
                i, False, '', True
            ]))

        recursive_generate_item_store_row_label(self._tree_model[root])
        recursive_generate_item_store_row_label(self._tree_model[self._fixed_floor_root_iter])

    def rebuild_dungeon_tree(self):
        # Collect modified of _dungeon_iters and _dungeon_floor_iters
        modified_dungeons = {x: self._tree_model[y][5] for x, y in self._dungeon_iters.items()}
        modified_floors = {}
        for dungeon, floors in self._dungeon_floor_iters.items():
            modified_floors[dungeon] = {x: self._tree_model[y][5] for x, y in floors.items()}
        # Delete everything under _root_iter
        child = self._tree_model.iter_children(self._root_iter)
        while child is not None:
            nxt = self._tree_model.iter_next(child)
            self._tree_model.remove(child)
            child = nxt
        self._dungeon_iters = {}
        self._dungeon_floor_iters = {}
        # _fill_dungeon_tree
        self._fill_dungeon_tree()
        # Apply modified of _dungeon_iters and _dungeon_floor_iters
        for dungeon, modified in modified_dungeons.items():
            if dungeon in self._dungeon_iters:
                self._tree_model[self._dungeon_iters[dungeon]][5] = modified
        for dungeon, floors in modified_floors.items():
            if dungeon in self._dungeon_floor_iters:
                for floor, modified in floors.items():
                    if floor in self._dungeon_floor_iters[dungeon]:
                        self._tree_model[self._dungeon_floor_iters[dungeon][floor]][5] = modified
        # Re-generate label
        recursive_generate_item_store_row_label(self._tree_model[self._root_iter])

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        if request.type == REQUEST_TYPE_DUNGEONS:
            return self._root_iter
        if request.type == REQUEST_TYPE_DUNGEON_FIXED_FLOOR:
            return self._fixed_floor_iters[request.identifier]
        if request.type == REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY:
            FixedRoomsController.focus_entity_on_open = request.identifier
            return self._fixed_floor_root_iter

    def get_validator(self) -> DungeonValidator:
        return self._validator

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

    def get_fixed_floor(self, floor_id):
        return self._fixed_floor_data.fixed_floors[floor_id]

    def mark_floor_as_modified(self, item: FloorViewInfo, modified_mappag = False):
        if modified_mappag:
            # This is slow, since it builds the entire mappa_g file from scratch. 
            # It would be better to only modify the floor attributes changed
            self.save_mappa()
        else:
            self.project.mark_as_modified(MAPPA_PATH)
        # Mark as modified in tree
        row = self._tree_model[self._dungeon_floor_iters[item.dungeon.dungeon_id][item.floor_id]]
        recursive_up_item_store_mark_as_modified(row)

    def get_dungeon_list(self) -> List[DungeonDefinition]:
        if self._cached_dungeon_list==None:
            self._cached_dungeon_list = HardcodedDungeons.get_dungeon_list(
                self.project.get_binary(BinaryName.ARM9), self.project.get_rom_module().get_static_data()
            )
        return self._cached_dungeon_list

    def get_dungeon_restrictions(self) -> List[DungeonRestriction]:
        # TODO: Cache?
        return HardcodedDungeons.get_dungeon_restrictions(
            self.project.get_binary(BinaryName.ARM9), self.project.get_rom_module().get_static_data()
        )

    def mark_dungeon_as_modified(self, dungeon_id, modified_mappa=True):
        self.project.get_string_provider().mark_as_modified()
        if modified_mappa:
            self.save_mappa()

        # Mark as modified in tree
        row = self._tree_model[self._dungeon_iters[dungeon_id]]
        recursive_up_item_store_mark_as_modified(row)

    def mark_root_as_modified(self):
        # Mark as modified in tree
        row = self._tree_model[self._root_iter]
        recursive_up_item_store_mark_as_modified(row)

    def save_dungeon_list(self, dungeons: List[DungeonDefinition]):
        self.project.modify_binary(BinaryName.ARM9, lambda binary: HardcodedDungeons.set_dungeon_list(
            dungeons, binary, self.project.get_rom_module().get_static_data()
        ))
        self._cached_dungeon_list = None

    def update_dungeon_restrictions(self, dungeon_id: int, restrictions: DungeonRestriction):
        all_restrictions = self.get_dungeon_restrictions()
        all_restrictions[dungeon_id] = restrictions
        self.save_dungeon_restrictions(all_restrictions)

    def save_dungeon_restrictions(self, restrictions: List[DungeonRestriction]):
        self.project.modify_binary(BinaryName.ARM9, lambda binary: HardcodedDungeons.set_dungeon_restrictions(
            restrictions, binary, self.project.get_rom_module().get_static_data()
        ))

    def save_mappa(self):
        self.project.mark_as_modified(MAPPA_PATH)
        self.project.save_file_manually(MAPPAG_PATH, FileType.MAPPA_G_BIN.serialize(
            convert_mappa_to_mappag(self.get_mappa())
        ))

    def _fill_dungeon_tree(self):
        item_store = self._tree_model
        root = self._root_iter

        # Regular dungeons
        for group_id, dungeon_or_group in enumerate(self.load_dungeons()):
            if isinstance(dungeon_or_group, DungeonGroup):
                # Group
                group = item_store.append(root, [
                    ICON_GROUP, self.generate_group_label(dungeon_or_group.base_dungeon_id), self, GroupController,
                    dungeon_or_group.base_dungeon_id, False, '', True
                ])
                for dungeon, start_id in zip(dungeon_or_group.dungeon_ids, dungeon_or_group.start_ids):
                    self._add_dungeon_to_tree(group, item_store, dungeon, start_id)
            else:
                # Dungeon
                self._add_dungeon_to_tree(root, item_store, dungeon_or_group, 0)

        # Dojo dungeons
        dojo_root = item_store.append(root, [
            ICON_DUNGEONS, DOJOS_NAME, self, DojosController, 0, False, '', True
        ])
        for i in range(DOJO_DUNGEONS_FIRST, DOJO_DUNGEONS_LAST + 1):
            self._add_dungeon_to_tree(dojo_root, item_store, i, 0)

    def _add_dungeon_to_tree(self, root_node, item_store, idx, previous_floor_id):
        clazz = DungeonController if idx not in self._validator.invalid_dungeons else InvalidDungeonController
        dungeon_info = DungeonViewInfo(idx, idx < DOJO_DUNGEONS_FIRST)
        self._dungeon_iters[idx] = item_store.append(root_node, [
            ICON_DUNGEON, self.generate_dungeon_label(idx), self, clazz,
            dungeon_info, False, '', True
        ])
        if clazz == DungeonController:
            self._regenerate_dungeon_floors(idx, previous_floor_id)

    def _regenerate_dungeon_floors(self, idx, previous_floor_id):
        dungeon = self._dungeon_iters[idx]
        item_store: Gtk.TreeStore = self._tree_model
        dungeon_info = self._tree_model[dungeon][4]
        self._dungeon_floor_iters[idx] = {}
        iter = item_store.iter_children(dungeon)
        while iter is not None:
            nxt = item_store.iter_next(iter)
            item_store.remove(iter)
            iter = nxt
        for floor_i in range(0, self.get_number_floors(idx)):
            self._dungeon_floor_iters[idx][previous_floor_id + floor_i] = item_store.append(dungeon, [
                ICON_FLOOR, self.generate_floor_label(floor_i + previous_floor_id), self, FloorController,
                FloorViewInfo(previous_floor_id + floor_i, dungeon_info), False, '', True
            ])

    def load_dungeons(self) -> Iterable[Union[DungeonGroup, int]]:
        """
        Returns the dungeons, grouped by the same mappa_index. The dungeons and groups are overall sorted
        by their IDs.
        """
        lst = self.get_dungeon_list()
        groups = {}
        yielded = set()
        for idx, dungeon in enumerate(lst):
            if dungeon.mappa_index not in groups:
                groups[dungeon.mappa_index] = []
            groups[dungeon.mappa_index].append(idx)
            self.adjust_nb_floors_mf(dungeon.mappa_index, dungeon.number_floors_in_group)
            self.adjust_nb_floors_ranks(dungeon.mappa_index, dungeon.number_floors_in_group)
        groups_sorted = {}
        for idx, entries in groups.items():
            groups_sorted[idx] = sorted(entries, key=lambda dun_idx: lst[dun_idx].start_after)
        groups = groups_sorted
        
        for idx, dungeon in enumerate(lst):
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
        The the list MUST contain all regular dungeons (before DOJO_DUNGEONS_FIRST), just like self.load_dungeons
        would return it.
        """
        mappa = self.get_mappa()
        old_floor_lists = mappa.floor_lists
        reorder_list = []
        dojo_floors = old_floor_lists[DOJO_MAPPA_ENTRY]
        new_floor_lists = []
        dungeons = self.get_dungeon_list()
        # Sanity check list.
        dungeons_not_visited = set((i for i in range(0, len(dungeons))))

        # TODO Build new floor lists and update dungeon entries. Insert dojo dungeons at DOJO_MAPPA_ENTRY
        for group_or_dungeon in new_groups:
            # At DOJO_MAPPA_ENTRY insert the dojo:
            if len(new_floor_lists) == DOJO_MAPPA_ENTRY:
                new_floor_lists.append(dojo_floors)
                reorder_list.append([(DOJO_MAPPA_ENTRY, None, None)])
            reorder_list.append([])
            # Process this entry
            next_index = len(new_floor_lists)
            new_floor_list = []
            if isinstance(group_or_dungeon, DungeonGroup):
                group = group_or_dungeon.dungeon_ids
            else:
                group = [group_or_dungeon]
            floor_count_in_group = sum(dungeons[i].number_floors for i in group)
            for i in group:
                dungeons_not_visited.remove(i)
                old_first = dungeons[i].start_after
                old_last = old_first + dungeons[i].number_floors
                new_floors = old_floor_lists[dungeons[i].mappa_index][old_first:old_last]
                reorder_list[-1].append((dungeons[i].mappa_index, old_first, old_last))
                floor_i = len(new_floor_list)
                for floor in new_floors:
                    floor.layout.floor_number = floor_i
                    floor_i += 1
                dungeons[i].number_floors_in_group = floor_count_in_group
                dungeons[i].mappa_index = next_index
                dungeons[i].start_after = len(new_floor_list)
                new_floor_list += new_floors
            new_floor_lists.append(new_floor_list)

        assert len(dungeons_not_visited) == 0, _("Some dungeons were missing in the new group list. "
                                                 "This is a bug.")

        # If we haven't inserted the dojo dungeon floor list yet, do it now and pad with empty lists.
        if len(new_floor_lists) < DOJO_MAPPA_ENTRY:
            for i in range(len(new_floor_lists), DOJO_MAPPA_ENTRY + 1):
                if i == DOJO_MAPPA_ENTRY:
                    new_floor_lists.append(dojo_floors)
                    reorder_list.append([(DOJO_MAPPA_ENTRY, None, None)])
                else:
                    new_floor_lists.append([])
                    reorder_list.append([])
        
        mappa.floor_lists = new_floor_lists
        self._validator.floors = new_floor_lists
        self.mark_root_as_modified()
        self.save_mappa()
        self.save_dungeon_list(dungeons)

        # Update floor attributes
        self.reorder_floors_ranks(reorder_list)
        self.reorder_floors_mf(reorder_list)
        if self.has_floor_ranks():
            self.project.mark_as_modified(FLOOR_RANKS)
        if self.has_mission_forbidden():
            self.project.mark_as_modified(FLOOR_MISSION_FORBIDDEN)

        self.rebuild_dungeon_tree()

    def generate_group_label(self, base_dungeon_id) -> str:
        # noinspection PyUnusedLocal
        dname = self.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, base_dungeon_id)
        return f(_('"{dname}" Group'))

    def generate_dungeon_label(self, idx) -> str:
        return f'{idx}: {self.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, idx)}'

    # noinspection PyUnusedLocal
    def generate_floor_label(self, floor_i) -> str:
        return f(_('Floor {floor_i + 1}'))

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

    def change_floor_count(self, dungeon_id, number_floors_new): #TODO: Unchanged
        """
        This will update the floor count for the given dungeon:
        - Will add or remove floors from the dungeon's mappa entry, starting at the end of this dungeon's floor
          based on the current floor count for this dungeon
        - Update the dungeon's data entry (floor count + total floor count in group)
        - For all other dungeons in the same group: Update data entries (total floor count + start offset)
        - Regenerate the UI in SkyTemple (dungeon tree)
        """

        dungeon_definitions = self.get_dungeon_list()

        is_group: Union[False, DungeonGroup] = False
        for dungeon_or_group in self.load_dungeons():
            if dungeon_or_group == dungeon_id:
                break
            elif isinstance(dungeon_or_group, DungeonGroup):
                if dungeon_id in dungeon_or_group.dungeon_ids:
                    is_group = dungeon_or_group
                    break

        mappa_index = dungeon_definitions[dungeon_id].mappa_index
        floor_offset = dungeon_definitions[dungeon_id].start_after
        number_floors_old = dungeon_definitions[dungeon_id].number_floors
        floor_list = self.get_mappa().floor_lists[mappa_index]
        floors_added = number_floors_new - number_floors_old

        # Update Mappa
        if floors_added == 0:
            return  # nothing to do
        if floors_added < 0:
            # We removed floors
            for _ in range(0, -floors_added):
                del floor_list[floor_offset + number_floors_new]
        else:
            # We added floors
            last_floor_xml = floor_list[floor_offset + number_floors_old - 1].to_xml()
            for i in range(0, floors_added):
                floor_list.insert(floor_offset + number_floors_old + i, MappaFloor.from_xml(last_floor_xml))

        # Update floor ranks
        self.extend_nb_floors_ranks(dungeon_id, floor_offset+number_floors_old, floors_added, self.get_floor_rank(dungeon_id, floor_offset+number_floors_old-1))
        if self.has_floor_ranks():
            self.project.mark_as_modified(FLOOR_RANKS)
        # Update mission forbidden
        self.extend_nb_floors_mf(dungeon_id, floor_offset+number_floors_old, floors_added, self.get_floor_mf(dungeon_id, floor_offset+number_floors_old-1))
        if self.has_mission_forbidden():
            self.project.mark_as_modified(FLOOR_MISSION_FORBIDDEN)

        # Update dungeon data
        dungeon_definitions[dungeon_id].number_floors = number_floors_new
        if is_group:
            new_total_floor_count = sum([dungeon_definitions[x].number_floors for x in is_group.dungeon_ids])
            dungeon_definitions[dungeon_id].number_floors_in_group = new_total_floor_count

            for dungeon_in_group in (x for x in is_group.dungeon_ids if x != dungeon_id):
                # Update dungeon data of group floors
                if dungeon_definitions[dungeon_in_group].start_after > dungeon_definitions[dungeon_id].start_after:
                    dungeon_definitions[dungeon_in_group].start_after += floors_added
                dungeon_definitions[dungeon_in_group].number_floors_in_group = new_total_floor_count
        else:
            dungeon_definitions[dungeon_id].number_floors_in_group = number_floors_new

        # Re-count floors
        for i, floor in enumerate(floor_list):
            floor.layout.floor_number = i + 1

        # Mark as changed
        self.mark_dungeon_as_modified(dungeon_id, True)
        self.save_dungeon_list(dungeon_definitions)
        if is_group:
            for dungeon_in_group in is_group.dungeon_ids:
                self._regenerate_dungeon_floors(dungeon_in_group, dungeon_definitions[dungeon_in_group].start_after)
        else:
            self._regenerate_dungeon_floors(dungeon_id, floor_offset)
        recursive_generate_item_store_row_label(self._tree_model[self._root_iter])

    def get_monster_md(self) -> Md:
        return self.project.get_module('monster').monster_md

    def import_from_xml(self, selected_floors: List[Tuple[int, int]], xml: Element):
        for dungeon_id, floor_id in selected_floors:
            floor_info = FloorViewInfo(floor_id, DungeonViewInfo(dungeon_id, False))
            floor = self.get_mappa_floor(floor_info)
            mappa_floor_xml_import(xml, floor)
            self.mark_floor_as_modified(floor_info, modified_mappag=True)

    def get_dungeon_tileset(self, tileset_id) -> Tuple[Dma, Dpci, Dpc, Dpl]:
        return (
            self._dungeon_bin.get(f'dungeon{tileset_id}.dma'),
            self._dungeon_bin.get(f'dungeon{tileset_id}.dpci'),
            self._dungeon_bin.get(f'dungeon{tileset_id}.dpc'),
            self._dungeon_bin.get(f'dungeon{tileset_id}.dpl'),
        )

    def get_dungeon_background(self, background_id) -> Tuple[Dbg, Dpci, Dpc, Dpl]:
        return (
            self._dungeon_bin.get(f'dungeon_bg{background_id}.dbg'),
            self._dungeon_bin.get(f'dungeon_bg{background_id}.dpci'),
            self._dungeon_bin.get(f'dungeon_bg{background_id}.dpc'),
            self._dungeon_bin.get(f'dungeon_bg{background_id}.dpl'),
        )

    def _get_dungeon_group(self, dungeon_id: int) -> int:
        return self.get_dungeon_list()[dungeon_id].mappa_index
    
    def has_mission_forbidden(self):
        return self.project.file_exists(FLOOR_MISSION_FORBIDDEN)
    
    def has_floor_ranks(self):
        return self.project.file_exists(FLOOR_RANKS)

    def extend_nb_floors_ranks(self, dungeon_id: int, start_floor: int, nb_floors: int, rank: int = 0):
        if self.has_floor_ranks():
            group_id = self._get_dungeon_group(dungeon_id)
            f_ranks = self.project.open_file_in_rom(FLOOR_RANKS, FloorAttributeHandler)
            f_ranks.extend_nb_floors(group_id, start_floor+1, nb_floors, rank)
        
    def reorder_floors_ranks(self, reorder_list: List[List[Tuple[int,Optional[int],Optional[int]]]]): # (old_group_id, start_floor, end_floor)
        if self.has_floor_ranks():
            f_ranks = self.project.open_file_in_rom(FLOOR_RANKS, FloorAttributeHandler)
            f_ranks.reorder_floors(reorder_list)
        
    def adjust_nb_floors_ranks(self, group_id: int, nb_floors: int):
        if self.has_floor_ranks():
            f_ranks = self.project.open_file_in_rom(FLOOR_RANKS, FloorAttributeHandler)
            f_ranks.adjust_nb_floors(group_id, nb_floors+1)
        
    def get_floor_rank(self, dungeon_id: int, floor_id: int) -> Optional[int]:
        if self.has_floor_ranks():
            group_id = self._get_dungeon_group(dungeon_id)
            f_ranks = self.project.open_file_in_rom(FLOOR_RANKS, FloorAttributeHandler)
            return f_ranks.get_floor_attr(group_id, floor_id+1)
        else:
            return None

    def set_floor_rank(self, dungeon_id: int, floor_id: int, rank: int):
        if self.has_floor_ranks():
            group_id = self._get_dungeon_group(dungeon_id)
            f_ranks = self.project.open_file_in_rom(FLOOR_RANKS, FloorAttributeHandler)
            f_ranks.set_floor_attr(group_id, floor_id+1, rank)
            self.project.mark_as_modified(FLOOR_RANKS)
    
    def extend_nb_floors_mf(self, dungeon_id: int, start_floor: int, nb_floors: int, forbidden: int):
        if self.has_mission_forbidden():
            group_id = self._get_dungeon_group(dungeon_id)
            f_mission = self.project.open_file_in_rom(FLOOR_MISSION_FORBIDDEN, FloorAttributeHandler)
            f_mission.extend_nb_floors(group_id, start_floor+1, nb_floors, forbidden)
        
    def reorder_floors_mf(self, reorder_list: List[List[Tuple[int,Optional[int],Optional[int]]]]): # (old_group_id, start_floor, end_floor)
        if self.has_floor_ranks():
            f_mission = self.project.open_file_in_rom(FLOOR_MISSION_FORBIDDEN, FloorAttributeHandler)
            f_mission.reorder_floors(reorder_list)
            
    def adjust_nb_floors_mf(self, group_id: int, nb_floors: int):
        if self.has_mission_forbidden():
            f_mission = self.project.open_file_in_rom(FLOOR_MISSION_FORBIDDEN, FloorAttributeHandler)
            f_mission.adjust_nb_floors(group_id, nb_floors+1)
        
    def get_floor_mf(self, dungeon_id: int, floor_id: int) -> Optional[int]:
        if self.has_mission_forbidden():
            group_id = self._get_dungeon_group(dungeon_id)
            f_mission = self.project.open_file_in_rom(FLOOR_MISSION_FORBIDDEN, FloorAttributeHandler)
            return f_mission.get_floor_attr(group_id, floor_id+1)
        else:
            return None

    def set_floor_mf(self, dungeon_id: int, floor_id: int, forbidden: int):
        if self.has_mission_forbidden():
            group_id = self._get_dungeon_group(dungeon_id)
            f_mission = self.project.open_file_in_rom(FLOOR_MISSION_FORBIDDEN, FloorAttributeHandler)
            f_mission.set_floor_attr(group_id, floor_id+1, forbidden)
            self.project.mark_as_modified(FLOOR_MISSION_FORBIDDEN)
    
    def get_fixed_floor_entity_lists(self) -> Tuple[List[EntitySpawnEntry], List[ItemSpawn], List[MonsterSpawn], List[TileSpawn], List[MonsterSpawnStats]]:
        config = self.project.get_rom_module().get_static_data()
        ov29 = self.project.get_binary(BinaryName.OVERLAY_29)
        ov10 = self.project.get_binary(BinaryName.OVERLAY_10)
        return (
            HardcodedFixedFloorTables.get_entity_spawn_table(ov29, config),
            HardcodedFixedFloorTables.get_item_spawn_list(ov29, config),
            HardcodedFixedFloorTables.get_monster_spawn_list(ov29, config),
            HardcodedFixedFloorTables.get_tile_spawn_list(ov29, config),
            HardcodedFixedFloorTables.get_monster_spawn_stats_table(ov10, config),
        )

    def save_fixed_floor_entity_lists(self, entities, items, monsters, tiles, stats):

        config = self.project.get_rom_module().get_static_data()

        def update_ov29(binary):
            HardcodedFixedFloorTables.set_entity_spawn_table(binary, entities, config)
            HardcodedFixedFloorTables.set_item_spawn_list(binary, items, config)
            HardcodedFixedFloorTables.set_monster_spawn_list(binary, monsters, config)
            HardcodedFixedFloorTables.set_tile_spawn_list(binary, tiles, config)

        self.project.modify_binary(
            BinaryName.OVERLAY_29, update_ov29
        )
        self.project.modify_binary(
            BinaryName.OVERLAY_10, lambda binary: HardcodedFixedFloorTables.set_monster_spawn_stats_table(
                binary, stats, config
            )
        )
        row = self._tree_model[self._fixed_floor_root_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_dummy_tileset(self) -> [Dma, Image.Image]:
        with open(os.path.join(data_dir(), 'fixed_floor', 'dummy.dma'), 'rb') as f:
            dma = FileType.DMA.deserialize(f.read())
        return (
            dma,
            Image.open(os.path.join(data_dir(), 'fixed_floor', 'dummy.png'))
        )

    def get_default_tileset_for_fixed_floor(self, floor_id):
        for floor_list in self.get_mappa().floor_lists:
            for floor in floor_list:
                if floor.layout.fixed_floor_id == floor_id:
                    return floor.layout.tileset_id
        return 0

    def get_fixed_floor_properties(self) -> List[FixedFloorProperties]:
        ov10 = self.project.get_binary(BinaryName.OVERLAY_10)
        config = self.project.get_rom_module().get_static_data()
        return HardcodedFixedFloorTables.get_fixed_floor_properties(ov10, config)

    def get_fixed_floor_overrides(self) -> List[int]:
        ov29 = self.project.get_binary(BinaryName.OVERLAY_29)
        config = self.project.get_rom_module().get_static_data()
        return HardcodedFixedFloorTables.get_fixed_floor_overrides(ov29, config)

    def save_fixed_floor_properties(self, floor_id, new_properties):
        properties = self.get_fixed_floor_properties()
        properties[floor_id] = new_properties
        self.project.modify_binary(
            BinaryName.OVERLAY_10, lambda binary: HardcodedFixedFloorTables.set_fixed_floor_properties(
                binary, properties, self.project.get_rom_module().get_static_data()
        ))
        self.mark_fixed_floor_as_modified(floor_id)

    def save_fixed_floor_override(self, floor_id, override_id):
        overrides = self.get_fixed_floor_overrides()
        overrides[floor_id] = override_id
        self.project.modify_binary(
            BinaryName.OVERLAY_29, lambda binary: HardcodedFixedFloorTables.set_fixed_floor_overrides(
                binary, overrides, self.project.get_rom_module().get_static_data()
        ))
        self.mark_fixed_floor_as_modified(floor_id)

    def mark_fixed_floor_as_modified(self, floor_id):
        self.project.mark_as_modified(FIXED_PATH)
        row = self._tree_model[self._fixed_floor_iters[floor_id]]
        recursive_up_item_store_mark_as_modified(row)

    @staticmethod
    def desc_fixed_floor_tile(tile):
        attrs = []
        attrs.append(_("Floor") if not tile.is_secondary_terrain() else _("Secondary"))
        if tile.trap_id < 25:
            trap = MappaTrapType(tile.trap_id)
            attrs.append(' '.join([x.capitalize() for x in trap.name.split('_')]))
        if tile.trap_is_visible():
            attrs.append(_("Vis."))  # TRANSLATORS: Visible (trap)
        if not tile.can_be_broken():
            attrs.append(_("Unb."))  # TRANSLATORS: Unbreakable (trap)
        return ", ".join(attrs)

    def desc_fixed_floor_item(self, item_id):
        return self.project.get_string_provider().get_value(
            StringType.ITEM_NAMES, item_id
        ) if item_id < MAX_ITEMS else _("(Special?)")

    @staticmethod
    def desc_fixed_floor_monster(monster_id, enemy_settings, monster_names, enemy_settings_names, short=False):
        if monster_id == 0:
            return _("Nothing")
        if short:
            return monster_names[monster_id]
        return monster_names[monster_id] + " (" + enemy_settings_names[enemy_settings] + ")"

    def desc_fixed_floor_stats(self, i, entry):
        return f(_("{i} - Lvl: {entry.level}, Atk: {entry.attack}, Def: {entry.defense}, "
                   "Sp. Atk: {entry.special_attack}, Sp. Def: {entry.special_defense}, HP: {entry.hp}"))

    def mappa_generate_and_insert_new_floor_list(self):
        mappa = self.get_mappa()
        index = len(mappa.floor_lists)
        mappa.floor_lists.append([self.mappa_generate_new_floor()])
        return index

    def mappa_generate_new_floor(self) -> MappaFloor:
        """Copies the first floor of test dungeon and returns it"""
        return MappaFloor.from_xml(self.get_mappa().floor_lists[0][0].to_xml())


