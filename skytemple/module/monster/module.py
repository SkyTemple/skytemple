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
from typing import List, Dict

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.monster.controller.entity import EntityController
from skytemple.module.monster.controller.level_up import LevelUpController
from skytemple.module.monster.controller.main import MainController, MONSTER_NAME
from skytemple.module.monster.controller.monster import MonsterController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.bin_pack.model import BinPack
from skytemple_files.data.level_bin_entry.model import LevelBinEntry
from skytemple_files.data.md.model import Md, MdEntry, NUM_ENTITIES
from skytemple_files.data.waza_p.model import WazaP
from skytemple_files.hardcoded.monster_sprite_data_table import HardcodedMonsterSpriteDataTable

MONSTER_MD_FILE = 'BALANCE/monster.md'
M_LEVEL_BIN = 'BALANCE/m_level.bin'
WAZA_P_BIN = 'BALANCE/waza_p.bin'


class MonsterModule(AbstractModule):
    """Module to edit the monster.md and other Pokémon related data."""
    @classmethod
    def depends_on(cls):
        return ['portrait']

    @classmethod
    def sort_order(cls):
        return 70

    def __init__(self, rom_project: RomProject):
        self.project = rom_project
        self.monster_md: Md = self.project.open_file_in_rom(MONSTER_MD_FILE, FileType.MD)
        self.m_level_bin: BinPack = self.project.open_file_in_rom(M_LEVEL_BIN, FileType.BIN_PACK)
        self.waza_p_bin: WazaP = self.project.open_file_in_rom(WAZA_P_BIN, FileType.WAZA_P)

        self._tree_model = None
        self._tree_iter__entity_roots = {}
        self._tree_iter__entries = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'system-users-symbolic', MONSTER_NAME, self, MainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_iter__entity_roots = {}
        self._tree_iter__entries = {}

        monster_entries_by_base_id: Dict[int, List[MdEntry]] = {}
        for entry in self.monster_md.entries:
            if entry.md_index_base not in monster_entries_by_base_id:
                monster_entries_by_base_id[entry.md_index_base] = []
            monster_entries_by_base_id[entry.md_index_base].append(entry)

        for baseid, entry_list in monster_entries_by_base_id.items():
            name = self.project.get_string_provider().get_value(StringType.POKEMON_NAMES, baseid)
            ent_root = item_store.append(root, self._generate_entry__entity_root(baseid, name))
            self._tree_iter__entity_roots[baseid] = ent_root

            for entry in entry_list:
                self._tree_iter__entries[entry.md_index] = item_store.append(
                    ent_root, self._generate_entry__entry(entry.md_index, entry.gender)
                )

        recursive_generate_item_store_row_label(self._tree_model[root])

    def refresh(self, item_id):
        entry = self.monster_md.entries[item_id]
        name = self.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
        self._tree_model[self._tree_iter__entity_roots[entry.md_index_base]][:] = self._generate_entry__entity_root(
            entry.entid, name
        )
        self._tree_model[self._tree_iter__entries[item_id]][:] = self._generate_entry__entry(
            entry.md_index, entry.gender
        )

    def _generate_entry__entity_root(self, entid, name):
        return [
            'user-info-symbolic', f'#{entid:03}: {name}',
            self, EntityController, f'#{entid:03}: {name}', False, '', True
        ]

    def _generate_entry__entry(self, i, gender):
        return [
            'user-info-symbolic', f'${i:04}: {gender.name.capitalize()}',
            self, MonsterController, i, False, '', True
        ]

    def get_entry(self, item_id):
        return self.monster_md[item_id]

    def get_m_level_bin_entry(self, idx) -> LevelBinEntry:
        raw = self.m_level_bin[idx]
        return FileType.LEVEL_BIN_ENTRY.deserialize(
            FileType.PKDPX.deserialize(FileType.SIR0.deserialize(raw).content).decompress()
        )

    def count_m_level_entries(self) -> int:
        return len(self.m_level_bin)

    def set_m_level_bin_entry(self, idx: int, entry: LevelBinEntry):
        new_bytes_unpacked = FileType.LEVEL_BIN_ENTRY.serialize(entry)
        new_bytes_pkdpx = FileType.PKDPX.serialize(FileType.PKDPX.compress(new_bytes_unpacked))
        new_bytes = FileType.SIR0.serialize(FileType.SIR0.wrap(new_bytes_pkdpx, []))
        self.m_level_bin[idx] = new_bytes
        self.project.mark_as_modified(M_LEVEL_BIN)
        self._mark_as_modified_in_tree(idx + 1)

    def get_waza_p(self) -> WazaP:
        return self.waza_p_bin

    def get_portrait_view(self, item_id):
        if item_id == 0:
            return Gtk.Label.new("This entry has no portraits.")
        return self.project.get_module('portrait').get_editor(item_id - 1, lambda: self.mark_md_as_modified(item_id))

    def get_level_up_view(self, item_id):
        if item_id >= NUM_ENTITIES:
            return Gtk.Label.new("Stats and moves are only editable for base forms."), None
        controller = LevelUpController(self, item_id)
        return controller.get_view(), controller

    def mark_md_as_modified(self, item_id):
        """Mark as modified"""
        self.project.get_string_provider().mark_as_modified()
        self.project.mark_as_modified(MONSTER_MD_FILE)
        self._mark_as_modified_in_tree(item_id)

    def mark_waza_as_modified(self, item_id):
        """Mark as modified"""
        self.project.mark_as_modified(WAZA_P_BIN)
        self._mark_as_modified_in_tree(item_id)

    def _mark_as_modified_in_tree(self, item_id):
        row = self._tree_model[self._tree_iter__entries[item_id]]
        recursive_up_item_store_mark_as_modified(row)

    def get_pokemon_sprite_data_table(self):
        """Returns the recruitment lists: species, levels, locations"""
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedMonsterSpriteDataTable.get(arm9, static_data)

    def set_pokemon_sprite_data_table(self, values):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedMonsterSpriteDataTable.set(values, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)
