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
from typing import List, Tuple, Optional

from gi.repository.Gtk import TreeStore, TreeIter

from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_MUSIC
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.ui_utils import recursive_up_item_store_mark_as_modified, generate_item_store_row_label
from skytemple.module.lists.controller.dungeon_music import DungeonMusicController
from skytemple.module.lists.controller.guest_pokemon import GuestPokemonController
from skytemple.module.lists.controller.iq import IqController
from skytemple.module.lists.controller.main import MainController, GROUND_LISTS
from skytemple.module.lists.controller.actor_list import ActorListController
from skytemple.module.lists.controller.misc_settings import MiscSettingsController
from skytemple.module.lists.controller.rank_list import RankListController
from skytemple.module.lists.controller.menu_list import MenuListController
from skytemple.module.lists.controller.special_pcs import SpecialPcsController
from skytemple.module.lists.controller.starters_list import StartersListController
from skytemple.module.lists.controller.recruitment_list import RecruitmentListController
from skytemple.module.lists.controller.tactics import TacticsController
from skytemple.module.lists.controller.world_map import WorldMapController
from skytemple.module.lists.controller.sp_effects import SPEffectsController
from skytemple.module.lists.controller.dungeon_interrupt import DungeonInterruptController
from skytemple.module.lists.controller.animations import AnimationsController
from skytemple.module.monster.module import WAZA_P_BIN
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.data_cd.handler import DataCDHandler
from skytemple_files.data.inter_d.handler import InterDHandler
from skytemple_files.data.anim.handler import AnimHandler
from skytemple_files.data.md.model import Md
from skytemple_files.data.waza_p.model import WazaP
from skytemple_files.hardcoded.dungeon_music import HardcodedDungeonMusic, DungeonMusicEntry
from skytemple_files.hardcoded.dungeons import MapMarkerPlacement, HardcodedDungeons
from skytemple_files.hardcoded.guest_pokemon import ExtraDungeonDataList, ExtraDungeonDataEntry, GuestPokemon, \
    GuestPokemonList
from skytemple_files.hardcoded.personality_test_starters import HardcodedPersonalityTestStarters
from skytemple_files.hardcoded.default_starters import HardcodedDefaultStarters, SpecialEpisodePc
from skytemple_files.hardcoded.rank_up_table import Rank, HardcodedRankUpTable
from skytemple_files.hardcoded.recruitment_tables import HardcodedRecruitmentTables
from skytemple_files.hardcoded.menus import HardcodedMenus, MenuEntry, MenuType
from skytemple_files.hardcoded.tactics import HardcodedTactics
from skytemple_files.list.actor.model import ActorListBin
from skytemple_files.common.i18n_util import _

ACTOR_LIST = 'BALANCE/actor_list.bin'
SP_EFFECTS = 'BALANCE/process.bin'
DUNGEON_INTERRUPT = "BALANCE/inter_d.bin"
ANIMATIONS = "BALANCE/anim.bin"

class ListsModule(AbstractModule):
    """Module to modify lists."""
    @classmethod
    def depends_on(cls):
        return ['monster', 'map_bg']

    @classmethod
    def sort_order(cls):
        return 20

    def __init__(self, rom_project: RomProject):
        self.project = rom_project

        self._tree_model = None
        self._actor_tree_iter = None
        self._starters_tree_iter = None
        self._recruitment_tree_iter = None
        self._world_map_tree_iter = None
        self._rank_list_tree_iter = None
        self._menu_list_tree_iter = None
        self._dungeon_music_tree_iter = None
        self._misc_settings_tree_iter = None
        self._guest_pokemon_root_iter = None
        self._special_episodes_root_iter = None
        self._tactics_root_iter = None
        self._iq_tree_iter = None

        self.waza_p_bin: WazaP = self.project.open_file_in_rom(WAZA_P_BIN, FileType.WAZA_P)

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'skytemple-view-list-symbolic', GROUND_LISTS, self, MainController, 0, False, '', True
        ])
        self._actor_tree_iter = item_store.append(root, [
            'skytemple-e-actor-symbolic', _('Actors'), self, ActorListController, 0, False, '', True
        ])
        self._starters_tree_iter = item_store.append(root, [
            'skytemple-e-monster-symbolic', _('Starters'), self, StartersListController, 0, False, '', True
        ])
        self._recruitment_tree_iter = item_store.append(root, [
            'skytemple-e-monster-symbolic', _('Recruitment List'), self, RecruitmentListController, 0, False, '', True
        ])
        self._world_map_tree_iter = item_store.append(root, [
            'skytemple-e-worldmap-symbolic', _('World Map Markers'), self, WorldMapController, 0, False, '', True
        ])
        self._rank_list_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Rank List'), self, RankListController, 0, False, '', True
        ])
        self._menu_list_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Menu List'), self, MenuListController, 0, False, '', True
        ])
        self._sp_effects_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Special Process Effects'), self, SPEffectsController, 0, False, '', True
        ])
        self._dun_inter_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Dungeon Interruptions'), self, DungeonInterruptController, 0, False, '', True
        ])
        self._animations_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Animations'), self, AnimationsController, 0, False, '', True
        ])
        self._dungeon_music_tree_iter = item_store.append(root, [
            'skytemple-e-music-symbolic', _('Dungeon Music'), self, DungeonMusicController, 0, False, '', True
        ])
        self._guest_pokemon_root_iter = item_store.append(root, [
            'skytemple-e-monster-symbolic', _('Guest Pokémon'), self, GuestPokemonController, 0, False, '', True
        ])
        self._special_episodes_root_iter = item_store.append(root, [
            'skytemple-e-monster-symbolic', _('Special Episode PCs'), self, SpecialPcsController, 0, False, '', True
        ])
        self._tactics_root_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Tactics'), self, TacticsController, 0, False, '', True
        ])
        self._iq_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('IQ'), self, IqController, 0, False, '', True
        ])
        self._misc_settings_tree_iter = item_store.append(root, [
            'skytemple-view-list-symbolic', _('Misc. Settings'), self, MiscSettingsController, 0, False, '', True
        ])
        generate_item_store_row_label(item_store[root])
        generate_item_store_row_label(item_store[self._actor_tree_iter])
        generate_item_store_row_label(item_store[self._starters_tree_iter])
        generate_item_store_row_label(item_store[self._recruitment_tree_iter])
        generate_item_store_row_label(item_store[self._world_map_tree_iter])
        generate_item_store_row_label(item_store[self._rank_list_tree_iter])
        generate_item_store_row_label(item_store[self._menu_list_tree_iter])
        generate_item_store_row_label(item_store[self._sp_effects_tree_iter])
        generate_item_store_row_label(item_store[self._dun_inter_tree_iter])
        generate_item_store_row_label(item_store[self._animations_tree_iter])
        generate_item_store_row_label(item_store[self._dungeon_music_tree_iter])
        generate_item_store_row_label(item_store[self._misc_settings_tree_iter])
        generate_item_store_row_label(item_store[self._guest_pokemon_root_iter])
        generate_item_store_row_label(item_store[self._special_episodes_root_iter])
        generate_item_store_row_label(item_store[self._tactics_root_iter])
        generate_item_store_row_label(item_store[self._iq_tree_iter])
        self._tree_model = item_store

    def handle_request(self, request: OpenRequest) -> Optional[TreeIter]:
        if request.type == REQUEST_TYPE_DUNGEON_MUSIC:
            return self._dungeon_music_tree_iter

    def has_sp_effects(self):
        return self.project.file_exists(SP_EFFECTS)

    def get_sp_effects(self):
        return self.project.open_file_in_rom(SP_EFFECTS, DataCDHandler)
    
    def mark_sp_effects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(SP_EFFECTS)
        # Mark as modified in tree
        row = self._tree_model[self._sp_effects_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def has_dungeon_interrupts(self):
        return self.project.file_exists(DUNGEON_INTERRUPT)

    def get_dungeon_interrupts(self):
        return self.project.open_file_in_rom(DUNGEON_INTERRUPT, InterDHandler)

    def mark_dungeon_interrupts_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(DUNGEON_INTERRUPT)
        # Mark as modified in tree
        row = self._tree_model[self._dun_inter_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def has_animations(self):
        return self.project.file_exists(ANIMATIONS)

    def get_animations(self):
        return self.project.open_file_in_rom(ANIMATIONS, AnimHandler)

    def mark_animations_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ANIMATIONS)
        # Mark as modified in tree
        row = self._tree_model[self._animations_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def has_actor_list(self):
        return self.project.file_exists(ACTOR_LIST)

    def get_actor_list(self) -> ActorListBin:
        return self.project.open_sir0_file_in_rom(ACTOR_LIST, ActorListBin)
    
    def mark_actors_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ACTOR_LIST)
        # Mark as modified in tree
        row = self._tree_model[self._actor_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def has_edit_extra_pokemon(self):
        return self.project.is_patch_applied("EditExtraPokemon")

    def mark_str_as_modified(self):
        self.project.get_string_provider().mark_as_modified()
        # Mark as modified in tree
        row = self._tree_model[self._starters_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def mark_misc_settings_as_modified(self):
        # Mark as modified in tree
        row = self._tree_model[self._misc_settings_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def mark_iq_as_modified(self):
        # Mark as modified in tree
        row = self._tree_model[self._iq_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_monster_md(self) -> Md:
        return self.project.get_module('monster').monster_md

    def get_waza_p(self) -> WazaP:
        return self.waza_p_bin

    def get_starter_default_ids(self) -> Tuple[int, int]:
        """Returns players & partner default starters"""
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        player = HardcodedDefaultStarters.get_player_md_id(arm9, static_data)
        partner = HardcodedDefaultStarters.get_partner_md_id(arm9, static_data)
        return player, partner

    def set_starter_default_ids(self, player, partner):
        """Sets players & partner default starters"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_player_md_id(player, arm9, static_data)
            HardcodedDefaultStarters.set_partner_md_id(partner, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._starters_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_special_pcs(self) -> List[SpecialEpisodePc]:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_special_episode_pcs(arm9, static_data)

    def set_special_pcs(self, lst: List[SpecialEpisodePc]):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_special_episode_pcs(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._special_episodes_root_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_tactics(self) -> List[int]:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedTactics.get_unlock_levels(arm9, static_data)

    def set_tactics(self, lst: List[int]):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedTactics.set_unlock_levels(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._tactics_root_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def get_starter_ids(self) -> Tuple[List[int], List[int]]:
        """Returns players & partner starters"""
        ov13 = self.project.get_binary(BinaryName.OVERLAY_13)
        static_data = self.project.get_rom_module().get_static_data()
        player = HardcodedPersonalityTestStarters.get_player_md_ids(ov13, static_data)
        partner = HardcodedPersonalityTestStarters.get_partner_md_ids(ov13, static_data)
        return player, partner

    def set_starter_ids(self, player, partner):
        def update(ov13):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedPersonalityTestStarters.set_player_md_ids(player, ov13, static_data)
            HardcodedPersonalityTestStarters.set_partner_md_ids(partner, ov13, static_data)
        self.project.modify_binary(BinaryName.OVERLAY_13, update)

        row = self._tree_model[self._starters_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def get_starter_level_player(self) -> int:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_player_level(arm9, static_data)

    def set_starter_level_player(self, level: int):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_player_level(level, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._starters_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def get_starter_level_partner(self) -> int:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_partner_level(arm9, static_data)

    def set_starter_level_partner(self, level: int):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_partner_level(level, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._starters_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_recruitment_list(self) -> Tuple[List[int], List[int], List[int]]:
        """Returns the recruitment lists: species, levels, locations"""
        ov11 = self.project.get_binary(BinaryName.OVERLAY_11)
        static_data = self.project.get_rom_module().get_static_data()
        species = HardcodedRecruitmentTables.get_monster_species_list(ov11, static_data)
        level = HardcodedRecruitmentTables.get_monster_levels_list(ov11, static_data)
        location = HardcodedRecruitmentTables.get_monster_locations_list(ov11, static_data)
        return species, level, location

    def set_recruitment_list(self, species, level, location):
        """Sets the recruitment lists: species, levels, locations"""
        def update(ov11):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedRecruitmentTables.set_monster_species_list(species, ov11, static_data)
            HardcodedRecruitmentTables.set_monster_levels_list(level, ov11, static_data)
            HardcodedRecruitmentTables.set_monster_locations_list(location, ov11, static_data)
        self.project.modify_binary(BinaryName.OVERLAY_11, update)

        row = self._tree_model[self._recruitment_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_world_map_markers(self) -> List[MapMarkerPlacement]:
        """Returns the world map markers"""
        arm9bin = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        markers = HardcodedDungeons.get_marker_placements(arm9bin, static_data)
        return markers

    def set_world_map_markers(self, markers: List[MapMarkerPlacement]):
        """Sets the world map markers"""
        def update(arm9bin):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDungeons.set_marker_placements(markers, arm9bin, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._world_map_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def get_rank_list(self) -> List[Rank]:
        """Returns the rank up table."""
        arm9bin = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedRankUpTable.get_rank_up_table(arm9bin, static_data)

    def set_rank_list(self, values: List[Rank]):
        """Sets the rank up table."""
        def update(arm9bin):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedRankUpTable.set_rank_up_table(values, arm9bin, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._rank_list_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def get_menu(self, menu_id) -> List[MenuEntry]:
        """Returns the rank up table."""
        binary = self.project.get_binary(MenuType(menu_id).binary)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedMenus.get_menu(MenuType(menu_id), binary, static_data)

    def set_menu(self, menu_id, values: List[MenuEntry]):
        """Sets the rank up table."""
        def update(binary):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedMenus.set_menu(MenuType(menu_id), values, binary, static_data)
        
        self.project.modify_binary(MenuType(menu_id).binary, update)

        row = self._tree_model[self._menu_list_tree_iter]
        recursive_up_item_store_mark_as_modified(row)
    
    def mark_string_as_modified(self):
        """Mark as modified"""
        self.project.get_string_provider().mark_as_modified()

    def get_dungeon_music_spec(self) -> Tuple[List[DungeonMusicEntry], List[Tuple[int, int, int, int]]]:
        config = self.project.get_rom_module().get_static_data()
        ov10 = self.project.get_binary(BinaryName.OVERLAY_10)
        return (
            HardcodedDungeonMusic.get_music_list(ov10, config),
            HardcodedDungeonMusic.get_random_music_list(ov10, config)
        )

    def set_dungeon_music(self, lst, random):
        config = self.project.get_rom_module().get_static_data()
        self.project.modify_binary(BinaryName.OVERLAY_10, lambda ov10: HardcodedDungeonMusic.set_music_list(lst, ov10, config))
        self.project.modify_binary(BinaryName.OVERLAY_10, lambda ov10: HardcodedDungeonMusic.set_random_music_list(random, ov10, config))

        row = self._tree_model[self._dungeon_music_tree_iter]
        recursive_up_item_store_mark_as_modified(row)

    def set_extra_dungeon_data(self, lst: List[ExtraDungeonDataEntry]):
        """Updates the extra dungeon data list"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            ExtraDungeonDataList.write(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._guest_pokemon_root_iter]
        recursive_up_item_store_mark_as_modified(row)

    def set_guest_pokemon_data(self, lst: List[GuestPokemon]):
        """Updates the guest pokémon data list"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            GuestPokemonList.write(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        row = self._tree_model[self._guest_pokemon_root_iter]
        recursive_up_item_store_mark_as_modified(row)

    def collect_debugging_info(self, open_controller: AbstractController) -> Optional[DebuggingInfo]:
        if isinstance(open_controller, ActorListController):
            pass  # todo
        if isinstance(open_controller, StartersListController):
            pass  # todo
        if isinstance(open_controller, RecruitmentListController):
            pass  # todo
        if isinstance(open_controller, WorldMapController):
            pass  # todo
        if isinstance(open_controller, RankListController):
            pass  # todo
        if isinstance(open_controller, MenuListController):
            pass  # todo
        if isinstance(open_controller, SPEffectsController):
            pass  # todo
        if isinstance(open_controller, DungeonInterruptController):
            pass  # todo
        if isinstance(open_controller, AnimationsController):
            pass  # todo
        if isinstance(open_controller, DungeonMusicController):
            pass  # todo
        if isinstance(open_controller, GuestPokemonController):
            pass  # todo
        if isinstance(open_controller, SpecialPcsController):
            pass  # todo
        if isinstance(open_controller, TacticsController):
            pass  # todo
        if isinstance(open_controller, IqController):
            pass  # todo
        if isinstance(open_controller, MiscSettingsController):
            pass  # todo
        return None
