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
from typing import List, Dict, Optional, Tuple
from xml.etree.ElementTree import Element

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
from skytemple_files.data.tbl_talk.model import TblTalk, TalkType
from skytemple_files.data.md.model import Md, MdEntry, NUM_ENTITIES, ShadowSize
from skytemple_files.data.monster_xml import monster_xml_import
from skytemple_files.data.waza_p.model import WazaP
from skytemple_files.graphics.kao.model import KaoImage, SUBENTRIES, Kao
from skytemple_files.hardcoded.monster_sprite_data_table import HardcodedMonsterSpriteDataTable
from skytemple_files.common.i18n_util import _

MONSTER_MD_FILE = 'BALANCE/monster.md'
M_LEVEL_BIN = 'BALANCE/m_level.bin'
WAZA_P_BIN = 'BALANCE/waza_p.bin'
WAZA_P2_BIN = 'BALANCE/waza_p2.bin'
PORTRAIT_FILE = 'FONT/kaomado.kao'
TBL_TALK_FILE = 'MESSAGE/tbl_talk.tlk'
logger = logging.getLogger(__name__)


class MonsterModule(AbstractModule):
    """Module to edit the monster.md and other Pokémon related data."""
    @classmethod
    def depends_on(cls):
        return ['portrait', 'sprite']

    @classmethod
    def sort_order(cls):
        return 70

    def __init__(self, rom_project: RomProject):
        self.project = rom_project
        self.monster_md: Md = self.project.open_file_in_rom(MONSTER_MD_FILE, FileType.MD)
        self.m_level_bin: BinPack = self.project.open_file_in_rom(M_LEVEL_BIN, FileType.BIN_PACK)
        self.waza_p_bin: WazaP = self.project.open_file_in_rom(WAZA_P_BIN, FileType.WAZA_P)
        self.waza_p2_bin: WazaP = self.project.open_file_in_rom(WAZA_P2_BIN, FileType.WAZA_P)
        self.tbl_talk: TblTalk = self.project.open_file_in_rom(TBL_TALK_FILE, FileType.TBL_TALK)

        self._tree_model = None
        self._tree_iter__entity_roots = {}
        self._tree_iter__entries = []

    def load_tree_items(self, item_store: TreeStore, root_node):
        self._root = item_store.append(root_node, [
            'skytemple-e-monster-symbolic', MONSTER_NAME, self, MainController, 0, False, '', True
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
            ent_root = item_store.append(self._root, self.generate_entry__entity_root(baseid, name))
            self._tree_iter__entity_roots[baseid] = ent_root

            for entry in entry_list:
                self._tree_iter__entries[entry.md_index] = item_store.append(
                    ent_root, self.generate_entry__entry(entry.md_index, entry.gender)
                )

        recursive_generate_item_store_row_label(self._tree_model[self._root])

    def refresh(self, item_id):
        entry = self.monster_md.entries[item_id]
        name = self.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
        self._tree_model[self._tree_iter__entity_roots[entry.md_index_base]][:] = self.generate_entry__entity_root(
            entry.md_index_base, name
        )
        self._tree_model[self._tree_iter__entries[item_id]][:] = self.generate_entry__entry(
            entry.md_index, entry.gender
        )

    def generate_entry__entity_root(self, entid, name):
        return [
            'skytemple-e-monster-base-symbolic', f'#{entid:03}: {name}',
            self, EntityController, f'#{entid:03}: {name}', False, '', True
        ]

    def generate_entry__entry(self, i, gender):
        return [
            'skytemple-e-monster-symbolic', f'${i:04}: {gender.print_name}',
            self, MonsterController, i, False, '', True
        ]

    def get_entry_both(self, item_id) -> Tuple[MdEntry, Optional[MdEntry]]:
        if item_id + NUM_ENTITIES < len(self.monster_md):
            return self.monster_md[item_id], self.monster_md[item_id + NUM_ENTITIES]
        return self.monster_md[item_id], None

    def get_entry(self, item_id):
        return self.monster_md[item_id]

    def get_pokemon_names_and_categories(self, item_id):
        sp = self.project.get_string_provider()
        names = {}
        for lang in sp.get_languages():
            names[lang.name] = (
                sp.get_value(StringType.POKEMON_NAMES, item_id, lang),
                sp.get_value(StringType.POKEMON_CATEGORIES, item_id, lang)
            )
        return names

    def get_m_level_bin_entry(self, idx) -> Optional[LevelBinEntry]:
        if idx > -1 and idx < len(self.m_level_bin):
            raw = self.m_level_bin[idx]
            return FileType.LEVEL_BIN_ENTRY.deserialize(
                FileType.PKDPX.deserialize(FileType.SIR0.deserialize(raw).content).decompress()
            )
        return None

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

    def get_waza_p2(self) -> WazaP:
        return self.waza_p2_bin

    def get_portrait_view(self, item_id):
        if item_id == 0:
            return Gtk.Label.new(_("This entry has no portraits."))
        return self.project.get_module('portrait').get_editor(item_id - 1, lambda: self.mark_md_as_modified(item_id))

    def get_sprite_view(self, sprite_id, item_id):
        def set_new_sprite_id(new_sprite_id):
            self.get_entry(item_id).sprite_index = new_sprite_id

        def set_shadow_size(shadow_size_id):
            try:
                self.get_entry(item_id).shadow_size = ShadowSize(shadow_size_id)
            except BaseException as ex:
                logger.warning("Failed to set shadow size", exc_info=ex)

        v = self.project.get_module('sprite').get_monster_sprite_editor(
            sprite_id,
            lambda: self.mark_md_as_modified(item_id),
            set_new_sprite_id,
            lambda: self.get_entry(item_id).shadow_size.value,
            set_shadow_size
        )
        v.show_all()
        return v

    def get_portraits_for_export(self, item_id) -> Tuple[Optional[List[KaoImage]], Optional[List[KaoImage]]]:
        portraits = None
        portraits2 = None
        portrait_module = self.project.get_module('portrait')
        kao = portrait_module.kao
        if item_id > -1 and item_id < kao.toc_len:
            portraits = []
            for kao_i in range(0, SUBENTRIES):
                portraits.append(kao.get(item_id, kao_i))

        if item_id > -1 and NUM_ENTITIES + item_id < kao.toc_len:
            portraits2 = []
            for kao_i in range(0, SUBENTRIES):
                portraits2.append(kao.get(NUM_ENTITIES + item_id, kao_i))

        return portraits, portraits2

    def get_level_up_view(self, item_id):
        if item_id >= NUM_ENTITIES:
            return Gtk.Label.new(_("Stats and moves are only editable for base forms.")), None
        controller = LevelUpController(self, item_id)
        return controller.get_view(), controller

    def set_personality(self, item_id, value):
        """Set personality value of the monster"""
        self.tbl_talk.set_monster_personality(item_id, value)
        self.project.mark_as_modified(TBL_TALK_FILE)
        self._mark_as_modified_in_tree(item_id)

    def get_special_personality(self, spec_id):
        """Get special personality value"""
        return self.tbl_talk.get_special_personality(spec_id)
    
    def set_special_personality(self, spec_id, value):
        """Set special personality value"""
        self.tbl_talk.set_special_personality(spec_id, value)
        self.mark_tbl_talk_as_modified()
    
    def get_personality(self, item_id):
        """Get personality value of the monster"""
        return self.tbl_talk.get_monster_personality(item_id)
    
    def get_nb_personality_groups(self):
        return self.tbl_talk.get_nb_groups()
    
    def add_personality_group(self):
        return self.tbl_talk.add_group()
    
    def remove_personality_group(self, group: int):
        return self.tbl_talk.remove_group(group)
    
    def get_personality_dialogues(self, group: int, dialogue_types: TalkType):
        return self.tbl_talk.get_dialogues(group, dialogue_types)
    
    def set_personality_dialogues(self, group: int, dialogue_types: TalkType, dialogues: List[int]):
        return self.tbl_talk.set_dialogues(group, dialogue_types, dialogues)

    def mark_string_as_modified(self):
        """Mark as modified"""
        self.project.get_string_provider().mark_as_modified()
        recursive_up_item_store_mark_as_modified(self._tree_model[self._root])
        
    def mark_tbl_talk_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(TBL_TALK_FILE)
        recursive_up_item_store_mark_as_modified(self._tree_model[self._root])
        
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

    def get_export_data(self, entry):
        waza_p = self.get_waza_p()
        waza_p2 = self.get_waza_p2()
        md_gender1, md_gender2 = self.get_entry_both(entry.md_index_base)
        names = self.get_pokemon_names_and_categories(entry.md_index_base)
        moveset = None
        if entry.md_index_base < len(waza_p.learnsets):
            moveset = waza_p.learnsets[entry.md_index_base]
        moveset2 = None
        if entry.md_index_base < len(waza_p2.learnsets):
            moveset2 = waza_p2.learnsets[entry.md_index_base]
        stats_and_portraits_id = entry.md_index_base - 1
        stats = self.get_m_level_bin_entry(stats_and_portraits_id)
        portraits, portraits2 = self.get_portraits_for_export(stats_and_portraits_id)
        return names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2

    def import_from_xml(self, selected_monsters: List[int], xml: Element):
        for monster_id in selected_monsters:
            entry = self.get_entry(monster_id)
            names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2 = self.get_export_data(entry)
            we_are_gender1 = monster_id < NUM_ENTITIES

            md_gender1_imp = md_gender1
            portraits1_imp = portraits
            md_gender2_imp = md_gender2
            portraits2_imp = portraits2
            if md_gender2:
                if we_are_gender1:
                    md_gender2_imp = None
                    portraits2_imp = None
                else:
                    md_gender1_imp = None
                    portraits1_imp = None

            monster_xml_import(
                xml, md_gender1_imp, md_gender2_imp,
                names, moveset, moveset2, stats,
                portraits1_imp, portraits2_imp
            )
            if stats:
                self.set_m_level_bin_entry(entry.md_index_base - 1, stats)
            if names:
                sp = self.project.get_string_provider()
                for lang_name, (name, category) in names.items():
                    model = sp.get_model(lang_name)
                    model.strings[sp.get_index(StringType.POKEMON_NAMES, entry.md_index_base)] = name
                    model.strings[sp.get_index(StringType.POKEMON_CATEGORIES, entry.md_index_base)] = category
                sp.mark_as_modified()

            portrait_module = self.project.get_module('portrait')
            kao: Kao = portrait_module.kao
            portraits = portraits if we_are_gender1 else portraits2
            if portraits:
                for i, portrait in enumerate(portraits):
                    existing = kao.get(monster_id - 1, i)
                    if portrait:
                        if existing:
                            existing.compressed_img_data = portrait.compressed_img_data
                            existing.pal_data = portrait.pal_data
                            existing.modified = True
                            existing.as_pil = None
                        else:
                            kao.set(monster_id - 1, i, portrait)
                    else:
                        # TODO: Support removing portraits
                        pass
            self.refresh(monster_id)
            self.mark_md_as_modified(monster_id)
            self.project.mark_as_modified(WAZA_P_BIN)
            self.project.mark_as_modified(WAZA_P2_BIN)
            self.project.get_string_provider().mark_as_modified()
            self.project.mark_as_modified(PORTRAIT_FILE)
