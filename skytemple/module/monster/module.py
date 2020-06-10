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
from skytemple.core.rom_project import RomProject
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.monster.controller.entity import EntityController
from skytemple.module.monster.controller.main import MainController
from skytemple.module.monster.controller.monster import MonsterController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.md.model import Md, MdEntry

MONSTER_MD_FILE = 'BALANCE/monster.md'


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

        self._tree_model = None
        self._tree_iter__entity_roots = {}
        self._tree_iter__entries = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'system-users-symbolic', 'Pokémon', self, MainController, 0, False, ''
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
            self, EntityController, entid, False, ''
        ]

    def _generate_entry__entry(self, i, gender):
        return [
            'user-info-symbolic', f'${i:04}: {gender.name.capitalize()}',
            self, MonsterController, i, False, ''
        ]

    def get_entry(self, item_id):
        return self.monster_md[item_id]

    def get_portrait_view(self, item_id):
        if item_id == 0:
            return Gtk.Label.new("This entry has no portraits.")
        return self.project.get_module('portrait').get_editor(item_id - 1, lambda: self.mark_as_modified(item_id))

    def mark_as_modified(self, item_id):
        """Mark as modified"""
        self.project.get_string_provider().mark_as_modified()
        self.project.mark_as_modified(MONSTER_MD_FILE)
        # Mark as modified in tree
        row = self._tree_model[self._tree_iter__entries[item_id]]
        recursive_up_item_store_mark_as_modified(row)
