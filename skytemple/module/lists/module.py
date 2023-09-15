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
from typing import List, Tuple, Optional, Union

from range_typed_integers import i16, u16, u8

from gi.repository import Gtk
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.item_tree import ItemTree, ItemTreeEntry, ItemTreeEntryRef, RecursionType
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_DUNGEON_MUSIC
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.module.lists.controller.dungeon_music import DungeonMusicController
from skytemple.module.lists.controller.guest_pokemon import GuestPokemonController
from skytemple.module.lists.controller.iq import IqController
from skytemple.module.lists.controller.main import MainController, GROUND_LISTS
from skytemple.module.lists.controller.actor_list import ActorListController
from skytemple.module.lists.controller.object_list import ObjectListController
from skytemple.module.lists.controller.misc_settings import MiscSettingsController
from skytemple.module.lists.controller.rank_list import RankListController
from skytemple.module.lists.controller.menu_list import MenuListController
from skytemple.module.lists.controller.special_pcs import SpecialPcsController
from skytemple.module.lists.controller.starters_list import StartersListController
from skytemple.module.lists.controller.recruitment_list import RecruitmentListController
from skytemple.module.lists.controller.tactics import TacticsController
from skytemple.module.lists.controller.world_map import WorldMapController
from skytemple.module.lists.controller.dungeon_interrupt import DungeonInterruptController
from skytemple.module.lists.controller.animations import AnimationsController
from skytemple.module.monster.module import WAZA_P_BIN
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.inter_d.handler import InterDHandler
from skytemple_files.data.anim.handler import AnimHandler
from skytemple_files.data.md.protocol import MdProtocol
from skytemple_files.data.waza_p.protocol import WazaPProtocol
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
from skytemple_files.list.object.model import ObjectListBin
from skytemple_files.common.i18n_util import _

ACTOR_LIST = 'BALANCE/actor_list.bin'
OBJECT_LIST = 'BALANCE/objects.bin'
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

        self._item_tree: ItemTree
        self._actor_tree_iter: ItemTreeEntryRef
        self._starters_tree_iter: ItemTreeEntryRef
        self._recruitment_tree_iter: ItemTreeEntryRef
        self._world_map_tree_iter: ItemTreeEntryRef
        self._rank_list_tree_iter: ItemTreeEntryRef
        self._menu_list_tree_iter: ItemTreeEntryRef
        self._dungeon_music_tree_iter: ItemTreeEntryRef
        self._misc_settings_tree_iter: ItemTreeEntryRef
        self._guest_pokemon_root_iter: ItemTreeEntryRef
        self._special_episodes_root_iter: ItemTreeEntryRef
        self._tactics_root_iter: ItemTreeEntryRef
        self._iq_tree_iter: ItemTreeEntryRef

        self.waza_p_bin: WazaPProtocol = self.project.open_file_in_rom(WAZA_P_BIN, FileType.WAZA_P)

    def load_tree_items(self, item_tree: ItemTree):
        root = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=GROUND_LISTS,
            module=self,
            view_class=MainController,
            item_data=0
        ))
        self._actor_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-actor-symbolic',
            name=_('Actors'),
            module=self,
            view_class=ActorListController,
            item_data=0
        ))
        self._starters_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-monster-symbolic',
            name=_('Starters'),
            module=self,
            view_class=StartersListController,
            item_data=0
        ))
        self._object_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-object-symbolic',
            name=_('Objects'),
            module=self,
            view_class=ObjectListController,
            item_data=0
        ))
        self._recruitment_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-monster-symbolic',
            name=_('Recruitment List'),
            module=self,
            view_class=RecruitmentListController,
            item_data=0
        ))
        self._world_map_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-worldmap-symbolic',
            name=_('World Map Markers'),
            module=self,
            view_class=WorldMapController,
            item_data=0
        ))
        self._rank_list_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Rank List'),
            module=self,
            view_class=RankListController,
            item_data=0
        ))
        self._menu_list_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Menu List'),
            module=self,
            view_class=MenuListController,
            item_data=0
        ))
        self._dun_inter_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Dungeon Interruptions'),
            module=self,
            view_class=DungeonInterruptController,
            item_data=0
        ))
        self._animations_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Animations'),
            module=self,
            view_class=AnimationsController,
            item_data=0
        ))
        self._dungeon_music_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-music-symbolic',
            name=_('Dungeon Music'),
            module=self,
            view_class=DungeonMusicController,
            item_data=0
        ))
        self._guest_pokemon_root_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-monster-symbolic',
            name=_('Guest Pokémon'),
            module=self,
            view_class=GuestPokemonController,
            item_data=0
        ))
        self._special_episodes_root_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-monster-symbolic',
            name=_('Special Episode PCs'),
            module=self,
            view_class=SpecialPcsController,
            item_data=0
        ))
        self._tactics_root_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Tactics'),
            module=self,
            view_class=TacticsController,
            item_data=0
        ))
        self._iq_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('IQ'),
            module=self,
            view_class=IqController,
            item_data=0
        ))
        self._misc_settings_tree_iter = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-view-list-symbolic',
            name=_('Misc. Settings'),
            module=self,
            view_class=MiscSettingsController,
            item_data=0
        ))
        self._item_tree = item_tree

    def handle_request(self, request: OpenRequest) -> Optional[ItemTreeEntryRef]:
        if request.type == REQUEST_TYPE_DUNGEON_MUSIC:
            return self._dungeon_music_tree_iter
        return None

    def has_dungeon_interrupts(self):
        return self.project.file_exists(DUNGEON_INTERRUPT)

    def get_dungeon_interrupts(self):
        return self.project.open_file_in_rom(DUNGEON_INTERRUPT, InterDHandler)

    def mark_dungeon_interrupts_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(DUNGEON_INTERRUPT)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._dun_inter_tree_iter, RecursionType.UP)
    
    def has_animations(self):
        return self.project.file_exists(ANIMATIONS)

    def get_animations(self):
        return self.project.open_file_in_rom(ANIMATIONS, AnimHandler)

    def mark_animations_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ANIMATIONS)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._animations_tree_iter, RecursionType.UP)

    def has_object_list(self):
        return self.project.file_exists(OBJECT_LIST)

    def get_object_list(self) -> ObjectListBin:
        return self.project.open_file_in_rom(OBJECT_LIST, FileType.OBJECT_LIST_BIN)
    
    def mark_objects_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(OBJECT_LIST)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._object_tree_iter, RecursionType.UP)
    
    def has_actor_list(self):
        return self.project.file_exists(ACTOR_LIST)

    def get_actor_list(self) -> ActorListBin:
        return self.project.open_sir0_file_in_rom(ACTOR_LIST, ActorListBin)
    
    def mark_actors_as_modified(self):
        """Mark as modified"""
        self.project.mark_as_modified(ACTOR_LIST)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._actor_tree_iter, RecursionType.UP)

    def has_edit_extra_pokemon(self):
        return self.project.is_patch_applied("EditExtraPokemon")

    def mark_str_as_modified(self):
        self.project.get_string_provider().mark_as_modified()
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._starters_tree_iter, RecursionType.UP)

    def mark_misc_settings_as_modified(self):
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._misc_settings_tree_iter, RecursionType.UP)

    def mark_iq_as_modified(self):
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._iq_tree_iter, RecursionType.UP)

    def get_monster_md(self) -> MdProtocol:
        return self.project.get_module('monster').monster_md

    def get_waza_p(self) -> WazaPProtocol:
        return self.waza_p_bin

    def get_starter_default_ids(self) -> Tuple[u16, u16]:
        """Returns players & partner default starters"""
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        player = HardcodedDefaultStarters.get_player_md_id(arm9, static_data)
        partner = HardcodedDefaultStarters.get_partner_md_id(arm9, static_data)
        return player, partner

    def set_starter_default_ids(self, player: u16, partner: u16):
        """Sets players & partner default starters"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_player_md_id(player, arm9, static_data)
            HardcodedDefaultStarters.set_partner_md_id(partner, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._starters_tree_iter, RecursionType.UP)

    def get_special_pcs(self) -> List[SpecialEpisodePc]:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_special_episode_pcs(arm9, static_data)

    def set_special_pcs(self, lst: List[SpecialEpisodePc]):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_special_episode_pcs(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._special_episodes_root_iter, RecursionType.UP)

    def get_tactics(self) -> List[i16]:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedTactics.get_unlock_levels(arm9, static_data)

    def set_tactics(self, lst: List[i16]):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedTactics.set_unlock_levels(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._tactics_root_iter, RecursionType.UP)
    
    def get_starter_ids(self) -> Tuple[List[u16], List[u16]]:
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

        self._item_tree.mark_as_modified(self._starters_tree_iter, RecursionType.UP)
    
    def get_starter_level_player(self) -> int:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_player_level(arm9, static_data)

    def set_starter_level_player(self, level: u8):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_player_level(level, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._starters_tree_iter, RecursionType.UP)
    
    def get_starter_level_partner(self) -> u8:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedDefaultStarters.get_partner_level(arm9, static_data)

    def set_starter_level_partner(self, level: u8):
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedDefaultStarters.set_partner_level(level, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._starters_tree_iter, RecursionType.UP)

    def get_recruitment_list(self) -> Tuple[List[u16], List[u16], List[u8]]:
        """Returns the recruitment lists: species, levels, locations"""
        ov11 = self.project.get_binary(BinaryName.OVERLAY_11)
        static_data = self.project.get_rom_module().get_static_data()
        species = HardcodedRecruitmentTables.get_monster_species_list(ov11, static_data)
        level = HardcodedRecruitmentTables.get_monster_levels_list(ov11, static_data)
        location = HardcodedRecruitmentTables.get_monster_locations_list(ov11, static_data)
        return species, level, location

    def set_recruitment_list(self, species: List[u16], level: List[u16], location: List[u8]):
        """Sets the recruitment lists: species, levels, locations"""
        def update(ov11):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedRecruitmentTables.set_monster_species_list(species, ov11, static_data)
            HardcodedRecruitmentTables.set_monster_levels_list(level, ov11, static_data)
            HardcodedRecruitmentTables.set_monster_locations_list(location, ov11, static_data)
        self.project.modify_binary(BinaryName.OVERLAY_11, update)

        self._item_tree.mark_as_modified(self._recruitment_tree_iter, RecursionType.UP)

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

        self._item_tree.mark_as_modified(self._world_map_tree_iter, RecursionType.UP)

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

        self._item_tree.mark_as_modified(self._rank_list_tree_iter, RecursionType.UP)
    
    def get_menu(self, menu_id) -> List[MenuEntry]:
        """Returns the rank up table."""
        binary = self.project.get_binary(MenuType(menu_id).binary)  # type: ignore
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedMenus.get_menu(MenuType(menu_id), binary, static_data)  # type: ignore

    def set_menu(self, menu_id, values: List[MenuEntry]):
        """Sets the rank up table."""
        def update(binary):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedMenus.set_menu(
                MenuType(menu_id),  # type: ignore
                values, binary, static_data
            )
        
        self.project.modify_binary(MenuType(menu_id).binary, update)  # type: ignore

        self._item_tree.mark_as_modified(self._menu_list_tree_iter, RecursionType.UP)
    
    def mark_string_as_modified(self):
        """Mark as modified"""
        self.project.get_string_provider().mark_as_modified()

    def get_dungeon_music_spec(self) -> Tuple[List[DungeonMusicEntry], List[Tuple[u16, u16, u16, u16]]]:
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

        self._item_tree.mark_as_modified(self._dungeon_music_tree_iter, RecursionType.UP)

    def set_extra_dungeon_data(self, lst: List[ExtraDungeonDataEntry]):
        """Updates the extra dungeon data list"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            ExtraDungeonDataList.write(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._guest_pokemon_root_iter, RecursionType.UP)

    def set_guest_pokemon_data(self, lst: List[GuestPokemon]):
        """Updates the guest pokémon data list"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            GuestPokemonList.write(lst, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._guest_pokemon_root_iter, RecursionType.UP)

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, ActorListController):
            pass  # todo
        if isinstance(open_view, StartersListController):
            pass  # todo
        if isinstance(open_view, RecruitmentListController):
            pass  # todo
        if isinstance(open_view, WorldMapController):
            pass  # todo
        if isinstance(open_view, RankListController):
            pass  # todo
        if isinstance(open_view, MenuListController):
            pass  # todo
        if isinstance(open_view, DungeonInterruptController):
            pass  # todo
        if isinstance(open_view, AnimationsController):
            pass  # todo
        if isinstance(open_view, DungeonMusicController):
            pass  # todo
        if isinstance(open_view, GuestPokemonController):
            pass  # todo
        if isinstance(open_view, SpecialPcsController):
            pass  # todo
        if isinstance(open_view, TacticsController):
            pass  # todo
        if isinstance(open_view, IqController):
            pass  # todo
        if isinstance(open_view, MiscSettingsController):
            pass  # todo
        return None
