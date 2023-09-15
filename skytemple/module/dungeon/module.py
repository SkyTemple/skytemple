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
import os
import sys
from functools import reduce
from math import gcd
from typing import Optional, List, Union, Iterable, Tuple, Dict, Literal, Sequence
from xml.etree.ElementTree import Element

from PIL import Image
from range_typed_integers import u8_checked, u8, u16

from gi.repository import Gtk
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.error_handler import display_error
from skytemple.core.item_tree import ItemTree, ItemTreeEntryRef, ItemTreeEntry, RecursionType
from skytemple.core.model_context import ModelContext
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_FIXED_FLOOR, \
    REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY, REQUEST_TYPE_DUNGEONS, REQUEST_TYPE_DUNGEON_FLOOR
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import data_dir
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
from skytemple_files.data.md.protocol import MdProtocol
from skytemple_files.dungeon_data.fixed_bin.model import FixedBin
from skytemple_files.dungeon_data.mappa_bin.protocol import MappaBinProtocol, MappaFloorProtocol, MappaTrapType
from skytemple_files.dungeon_data.mappa_bin.mappa_xml import mappa_floor_xml_import, mappa_floor_from_xml, \
    mappa_floor_to_xml
from skytemple_files.dungeon_data.mappa_bin.validator.validator import DungeonValidator
from skytemple_files.dungeon_data.mappa_g_bin.mappa_converter import convert_mappa_to_mappag
from skytemple_files.graphics.dbg.protocol import DbgProtocol
from skytemple_files.graphics.dma.protocol import DmaProtocol
from skytemple_files.graphics.dpc.protocol import DpcProtocol
from skytemple_files.graphics.dpci.protocol import DpciProtocol
from skytemple_files.graphics.dpl.protocol import DplProtocol
from skytemple_files.hardcoded.dungeon_music import HardcodedDungeonMusic, DungeonMusicEntry
from skytemple_files.hardcoded.dungeons import HardcodedDungeons, DungeonDefinition, DungeonRestriction
from skytemple_files.dungeon_data.floor_attribute.handler import FloorAttributeHandler

from skytemple_files.hardcoded.fixed_floor import EntitySpawnEntry, ItemSpawn, MonsterSpawn, TileSpawn, \
    MonsterSpawnStats, HardcodedFixedFloorTables, FixedFloorProperties
from skytemple_files.common.i18n_util import _, f

# TODO: Add this to dungeondata.xml?
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
FLOOR_RANKS = "BALANCE/f_ranks.bin"
FLOOR_MISSION_FORBIDDEN = "BALANCE/fforbid.bin"
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
    def __init__(self, base_dungeon_id: int, dungeon_ids: Sequence[int], start_ids: Sequence[int]):
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
        self._errored: Union[Literal[False], Tuple] = False
        try:
            self.project = rom_project

            self._item_tree: ItemTree
            self._root_iter: Optional[ItemTreeEntryRef] = None
            self._dungeon_iters: Dict[DungeonDefinition, ItemTreeEntryRef] = {}
            self._dungeon_floor_iters: Dict[int, Dict[int, ItemTreeEntryRef]] = {}
            self._fixed_floor_iters: List[ItemTreeEntryRef] = []
            self._fixed_floor_root_iter: ItemTreeEntryRef
            self._fixed_floor_data: FixedBin
            self._dungeon_bin_context: ModelContext[DungeonBinPack]
            self._cached_dungeon_list: Optional[List[DungeonDefinition]] = None

            # Preload mappa
            logger.debug("Preloading Mappa...")
            self.get_mappa()
            logger.debug("Mappa loaded.")
            self._validator: DungeonValidator
        except Exception:
            self._errored = sys.exc_info()

    def load_tree_items(self, item_tree: ItemTree):
        if self._errored:
            display_error(
                self._errored,
                _("The dungeon floor data of this ROM is corrupt. SkyTemple will still try to open it, "
                  "but dungeon editing will not be available. Expect other bugs. Please fix your ROM."),
                _("SkyTemple")
            )
            return
        self._validator = DungeonValidator(self.get_mappa())
        root = item_tree.add_entry(None, ItemTreeEntry(
            icon=ICON_ROOT,
            name=DUNGEONS_NAME,
            module=self,
            view_class=MainController,
            item_data=0
        ))
        self._item_tree = item_tree
        self._root_iter = root

        static_data = self.project.get_rom_module().get_static_data()
        self._fixed_floor_data = self.project.open_file_in_rom(
            FIXED_PATH, FileType.FIXED_BIN,
            static_data=static_data
        )
        self._dungeon_bin_context = self.project.open_file_in_rom(
            DUNGEON_BIN, FileType.DUNGEON_BIN,
            static_data=static_data,
            threadsafe=True
        )

        self._validator.validate(self.get_dungeon_list())

        self._fill_dungeon_tree()

        # Fixed rooms
        self._fixed_floor_root_iter = item_tree.add_entry(None, ItemTreeEntry(
            icon=ICON_FIXED_ROOMS,
            name=FIXED_ROOMS_NAME,
            module=self,
            view_class=FixedRoomsController,
            item_data=0
        ))
        for i in range(0, len(self._fixed_floor_data.fixed_floors)):
            self._fixed_floor_iters.append(item_tree.add_entry(self._fixed_floor_root_iter, ItemTreeEntry(
                icon=ICON_FIXED_ROOMS,
                name=f(_('Fixed Room {i}')),
                module=self,
                view_class=FixedController,
                item_data=i
            )))

    def rebuild_dungeon_tree(self):
        assert self._root_iter is not None
        # Collect modified of _dungeon_iters and _dungeon_floor_iters
        modified_dungeons = {x: y.entry().modified for x, y in self._dungeon_iters.items()}
        modified_floors = {}
        for dungeon_entr, floors_entr in self._dungeon_floor_iters.items():
            modified_floors[dungeon_entr] = {x: y.entry().modified for x, y in floors_entr.items()}
        # Delete everything under _root_iter
        self._root_iter.delete_all_children()
        self._dungeon_iters = {}
        self._dungeon_floor_iters = {}
        # _fill_dungeon_tree
        self._fill_dungeon_tree()
        # Apply modified of _dungeon_iters and _dungeon_floor_iters
        for dungeon_m, modified in modified_dungeons.items():
            if dungeon_m in self._dungeon_iters:
                if modified:
                    self._item_tree.mark_as_modified(self._dungeon_iters[dungeon_m], RecursionType.UP)
        for dungeon_mf, floors in modified_floors.items():
            if dungeon_mf in self._dungeon_floor_iters:
                for floor, modified in floors.items():
                    if floor in self._dungeon_floor_iters[dungeon_mf]:
                        if modified:
                            self._item_tree.mark_as_modified(
                                self._dungeon_floor_iters[dungeon_mf][floor],
                                RecursionType.UP
                            )

    def handle_request(self, request: OpenRequest) -> Optional[ItemTreeEntryRef]:
        if request.type == REQUEST_TYPE_DUNGEONS:
            return self._root_iter
        if request.type == REQUEST_TYPE_DUNGEON_FIXED_FLOOR:
            return self._fixed_floor_iters[request.identifier]
        if request.type == REQUEST_TYPE_DUNGEON_FLOOR:
            try:
                dungeon_id, f_id = request.identifier
                return self._dungeon_floor_iters[dungeon_id][f_id]
            except Exception as ex:
                logger.warning(f"Could not fulfill floor open request: {ex.__class__.__name__}:{ex}")
        if request.type == REQUEST_TYPE_DUNGEON_FIXED_FLOOR_ENTITY:
            FixedRoomsController.focus_entity_on_open = request.identifier
            return self._fixed_floor_root_iter
        return None

    def get_validator(self) -> DungeonValidator:
        assert self._validator
        return self._validator

    def get_mappa(self) -> MappaBinProtocol:
        return self.project.open_file_in_rom(MAPPA_PATH, FileType.MAPPA_BIN)

    def get_mappa_floor(self, item: FloorViewInfo) -> MappaFloorProtocol:
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
        self._item_tree.mark_as_modified(self._dungeon_floor_iters[item.dungeon.dungeon_id][item.floor_id], RecursionType.UP)

    def get_dungeon_list(self) -> List[DungeonDefinition]:
        if self._cached_dungeon_list is None:
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
        self._item_tree.mark_as_modified(self._dungeon_iters[dungeon_id], RecursionType.UP)

    def mark_root_as_modified(self):
        # Mark as modified in tree
        if self._root_iter:
            self._item_tree.mark_as_modified(self._root_iter, RecursionType.UP)

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
        root = self._root_iter

        # Regular dungeons
        for group_id, dungeon_or_group in enumerate(self.load_dungeons()):
            if isinstance(dungeon_or_group, DungeonGroup):
                # Group
                group = self._item_tree.add_entry(root, ItemTreeEntry(
                    icon=ICON_GROUP,
                    name=self.generate_group_label(dungeon_or_group.base_dungeon_id),
                    module=self,
                    view_class=GroupController,
                    item_data=dungeon_or_group.base_dungeon_id
                ))
                for dungeon, start_id in zip(dungeon_or_group.dungeon_ids, dungeon_or_group.start_ids):
                    self._add_dungeon_to_tree(group, dungeon, start_id)
            else:
                # Dungeon
                self._add_dungeon_to_tree(root, dungeon_or_group, 0)

        # Dojo dungeons
        dojo_root = self._item_tree.add_entry(root, ItemTreeEntry(
            icon=ICON_DUNGEONS,
            name=DOJOS_NAME,
            module=self,
            view_class=DojosController,
            item_data=0
        ))
        for i in range(DOJO_DUNGEONS_FIRST, DOJO_DUNGEONS_LAST + 1):
            self._add_dungeon_to_tree(dojo_root, i, 0)

    def _add_dungeon_to_tree(self, root_node, idx, previous_floor_id):
        clazz = DungeonController if idx not in self._validator.invalid_dungeons else InvalidDungeonController
        dungeon_info = DungeonViewInfo(idx, idx < DOJO_DUNGEONS_FIRST)
        self._dungeon_iters[idx] = self._item_tree.add_entry(root_node, ItemTreeEntry(
            icon=ICON_DUNGEON,
            name=self.generate_dungeon_label(idx),
            module=self,
            view_class=clazz,
            item_data=dungeon_info
        ))
        if clazz == DungeonController:
            self._regenerate_dungeon_floors(idx, previous_floor_id)

    def _regenerate_dungeon_floors(self, idx, previous_floor_id):
        dungeon = self._dungeon_iters[idx]
        dungeon_info = dungeon.entry().item_data
        self._dungeon_floor_iters[idx] = {}
        dungeon.delete_all_children()
        for floor_i in range(0, self.get_number_floors(idx)):
            self._dungeon_floor_iters[idx][previous_floor_id + floor_i] = self._item_tree.add_entry(dungeon, ItemTreeEntry(
                icon=ICON_FLOOR,
                name=self.generate_floor_label(floor_i + previous_floor_id),
                module=self,
                view_class=FloorController,
                item_data=FloorViewInfo(previous_floor_id + floor_i, dungeon_info)
            ))

    def load_dungeons(self) -> Iterable[Union[DungeonGroup, int]]:
        """
        Returns the dungeons, grouped by the same mappa_index. The dungeons and groups are overall sorted
        by their IDs.
        """
        lst = self.get_dungeon_list()
        groups: Dict[int, List[int]] = {}
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
        reorder_list: List[List[Tuple[int, Optional[int], Optional[int]]]] = []
        dojo_floors = list(old_floor_lists[DOJO_MAPPA_ENTRY])
        new_floor_lists: List[List[MappaFloorProtocol]] = []
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
            new_floor_list: List[MappaFloorProtocol] = []
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
                    floor.layout.floor_number = u8_checked(floor_i)
                    floor_i += 1
                dungeons[i].number_floors_in_group = u8_checked(floor_count_in_group)
                dungeons[i].mappa_index = u8_checked(next_index)
                dungeons[i].start_after = u8_checked(len(new_floor_list))
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

        is_group: Union[Literal[False], DungeonGroup] = False
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
        mappa = self.get_mappa()
        floors_added = number_floors_new - number_floors_old

        # Update Mappa
        if floors_added == 0:
            return  # nothing to do
        if floors_added < 0:
            # We removed floors
            for _ in range(0, -floors_added):
                mappa.remove_floor_from_floor_list(mappa_index, floor_offset + number_floors_new)
        else:
            cat_ided = self.project.get_rom_module().get_static_data().dungeon_data.item_categories
            # We added floors
            last_floor_xml = mappa_floor_to_xml(
                mappa.floor_lists[mappa_index][floor_offset + number_floors_old - 1],
                cat_ided
            )
            for i in range(0, floors_added):
                mappa.insert_floor_in_floor_list(
                    mappa_index,
                    floor_offset + number_floors_old + i,
                    mappa_floor_from_xml(
                        last_floor_xml,
                        {x.name: x for x in
                         cat_ided.values()}
                    )
                )

        # Update floor ranks
        ranks = self.get_floor_rank(dungeon_id, floor_offset+number_floors_old - 1)
        if ranks:
            self.extend_nb_floors_ranks(dungeon_id, floor_offset+number_floors_old, floors_added, ranks)
        if self.has_floor_ranks():
            self.project.mark_as_modified(FLOOR_RANKS)
        # Update mission forbidden
        mf = self.get_floor_mf(dungeon_id, floor_offset+number_floors_old-1)
        if mf:
            self.extend_nb_floors_mf(dungeon_id, floor_offset+number_floors_old, floors_added, mf)
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
                dungeon_definitions[dungeon_in_group].number_floors_in_group = u8_checked(new_total_floor_count)
        else:
            dungeon_definitions[dungeon_id].number_floors_in_group = number_floors_new

        # Re-count floors
        for i, floor in enumerate(mappa.floor_lists[mappa_index]):
            floor.layout.floor_number = i + 1

        # Mark as changed
        self.mark_dungeon_as_modified(dungeon_id, True)
        self.save_dungeon_list(dungeon_definitions)
        if is_group:
            for dungeon_in_group in is_group.dungeon_ids:
                self._regenerate_dungeon_floors(dungeon_in_group, dungeon_definitions[dungeon_in_group].start_after)
        else:
            self._regenerate_dungeon_floors(dungeon_id, floor_offset)

    def get_monster_md(self) -> MdProtocol:
        return self.project.get_module('monster').monster_md

    def import_from_xml(self, selected_floors: List[Tuple[int, int]], xml: Element):
        for dungeon_id, floor_id in selected_floors:
            floor_info = FloorViewInfo(floor_id, DungeonViewInfo(dungeon_id, False))
            floor = self.get_mappa_floor(floor_info)
            mappa_floor_xml_import(
                xml,
                floor,
                {x.name: x for x in self.project.get_rom_module().get_static_data().dungeon_data.item_categories.values()}
            )
            self.mark_floor_as_modified(floor_info, modified_mappag=True)

    def get_dungeon_tileset(self, tileset_id) -> Tuple[DmaProtocol, DpciProtocol, DpcProtocol, DplProtocol]:
        with self._dungeon_bin_context as dungeon_bin:
            return (
                dungeon_bin.get(f'dungeon{tileset_id}.dma'),
                dungeon_bin.get(f'dungeon{tileset_id}.dpci'),
                dungeon_bin.get(f'dungeon{tileset_id}.dpc'),
                dungeon_bin.get(f'dungeon{tileset_id}.dpl'),
            )

    def get_dungeon_background(self, background_id) -> Tuple[DbgProtocol, DpciProtocol, DpcProtocol, DplProtocol]:
        with self._dungeon_bin_context as dungeon_bin:
            return (
                dungeon_bin.get(f'dungeon_bg{background_id}.dbg'),
                dungeon_bin.get(f'dungeon_bg{background_id}.dpci'),
                dungeon_bin.get(f'dungeon_bg{background_id}.dpc'),
                dungeon_bin.get(f'dungeon_bg{background_id}.dpl'),
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
        self._item_tree.mark_as_modified(self._fixed_floor_root_iter, RecursionType.UP)

    def get_dummy_tileset(self) -> Tuple[DmaProtocol, Image.Image]:
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

    def get_fixed_floor_overrides(self) -> List[u8]:
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
        self._item_tree.mark_as_modified(self._fixed_floor_iters[floor_id], RecursionType.UP)

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
        mappa.add_floor_list([self.mappa_generate_new_floor()])
        return index

    def mappa_generate_new_floor(self) -> MappaFloorProtocol:
        """Copies the first floor of test dungeon and returns it"""
        cats_ided = self.project.get_rom_module().get_static_data().dungeon_data.item_categories
        cats_named = {x.name: x for x in cats_ided.values()}
        return mappa_floor_from_xml(
            mappa_floor_to_xml(self.get_mappa().floor_lists[0][0], cats_ided),
            cats_named
        )

    def get_dungeon_music_spec(self) -> Tuple[List[DungeonMusicEntry], List[Tuple[u16, u16, u16, u16]]]:
        config = self.project.get_rom_module().get_static_data()
        ov10 = self.project.get_binary(BinaryName.OVERLAY_10)
        return (
            HardcodedDungeonMusic.get_music_list(ov10, config),
            HardcodedDungeonMusic.get_random_music_list(ov10, config)
        )

    def get_item(self, idx):
        return self.project.open_file_in_rom('BALANCE/item_p.bin', FileType.ITEM_P).item_list[idx]

    def item_count(self):
        return len(self.project.open_file_in_rom('BALANCE/item_p.bin', FileType.ITEM_P).item_list)

    def get_zmappa(self):
        with self._dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get('minimap.zmappat')

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, DungeonController):
            pass  # todo
        if isinstance(open_view, FloorController):
            pass  # todo
        if isinstance(open_view, FixedRoomsController):
            pass  # todo
        if isinstance(open_view, FixedController):
            pass  # todo
        return None

    @staticmethod
    def calculate_relative_weights(list_of_weights: List[int]) -> List[int]:
        """Given a list of absolute spawn weights, return the relative values."""
        weights = []
        if len(list_of_weights) < 1:
            return []
        for i in range(0, len(list_of_weights)):
            weight = list_of_weights[i]
            if weight != 0:
                last_nonzero = i - 1
                while last_nonzero >= 0 and list_of_weights[last_nonzero] == 0:
                    last_nonzero -= 1
                if last_nonzero != -1:
                    weight -= list_of_weights[last_nonzero]
            weights.append(weight)
        weights_nonzero = [w for w in weights if w != 0]
        weights_gcd = 1
        if len(weights_nonzero) > 0:
            weights_gcd = reduce(gcd, weights_nonzero)
        return [int(w / weights_gcd) for w in weights]
