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
import re
from typing import TYPE_CHECKING, List, Union, Optional, cast

from gi.repository import Gtk
from gi.repository.Gtk import Widget
from range_typed_integers import u8, u32, u16
from skytemple_files.common.types.file_types import FileType
from skytemple_files.data.md.protocol import Gender

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import catch_overflow, builder_get_assert, iter_tree_model
from skytemple.module.lists.controller.base import ListBaseController
from skytemple_files.common.i18n_util import f, _
from skytemple_files.common.ppmdu_config.dungeon_data import Pmd2DungeonDungeon
from skytemple_files.hardcoded.guest_pokemon import ExtraDungeonDataList, GuestPokemonList, GuestPokemon, \
    ExtraDungeonDataEntry

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

MONSTER_NAME_PATTERN = re.compile(r'.*\([#$](\d+)\).*')
MOVE_NAME_PATTERN = re.compile(r'.*\((\d+)\).*')


class GuestPokemonController(ListBaseController):

    def __init__(self, module: 'ListsModule', item_id: int):
        super().__init__(module)
        self.module = module
        self.builder: Gtk.Builder = None  # type: ignore
        self.arm9 = module.project.get_binary(BinaryName.ARM9)
        self.static_data = module.project.get_rom_module().get_static_data()
        self.monster_md_entries = self.module.get_monster_md().entries
        self.move_entries = self.module.get_waza_p().moves
        self._list_store: Gtk.ListStore

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'guest_pokemon.glade')
        assert self.builder
        self._list_store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        stack = builder_get_assert(self.builder, Gtk.Stack, 'list_stack')

        if not self.module.has_edit_extra_pokemon():
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_na'))
            return stack

        self._loading = True
        self._fill_extra_dungeon_data()
        self._fill_guest_pokemon_data()
        self._init_completion()
        self._update_free_entries_left()
        self._loading = False

        stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_list'))
        self.builder.connect_signals(self)

        return stack

    def on_nb_sl_switch_page(self, n: Gtk.Notebook, p, pnum, *args):
        if pnum == 0:
            self._fill_extra_dungeon_data()
        elif pnum == 1:
            self._fill_guest_pokemon_data()

    def on_btn_help_extra_dungeon_data_clicked(self, *args):
        self._help(_("Guest pokémon IDs refer to the entries in the guest pokémon tab. A value of -1 represents "
                     "an empty entry (no guest pokémon).\n"
                     "- HLR (uncleared): Whether Hidden Land restrictions should be active when the dungeon is "
                     "uncleared.\n"
                     "Hidden Land restrictions prevent sending pokémon home or changing leaders. In addition, "
                     "if a team member faints you will get kicked out of the dungeon.\n"
                     "- Disable recruiting: Only applies when the dungeon is uncleared. If enabled, recruiting will "
                     "be disabled. This flag overrides the \"recruiting enabled\" flag in the dungeon restrictions.\n"
                     "- SIDE01 check: If enabled, guest pokémon will only be added to the team if the ground variable "
                     "SIDE01_BOSS2ND is 0.\n"
                     "- HLR (cleared): Whether Hidden Land restrictions should be active when the dungeon has been "
                     "cleared."))

    def on_guest_pokemon_add_clicked(self, *args):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        store.append([
            str(store.iter_n_children()), "0", self._get_monster_display_name(0), "0", self._get_move_display_name(0),
            self._get_move_display_name(0), self._get_move_display_name(0), self._get_move_display_name(0),
            "1", "1", "1", "0", "0", "0", "0", "0", "0", None
        ])
        self._update_free_entries_left()
        self._save_guest_pokemon_data()

    def on_guest_pokemon_remove_clicked(self, *args):
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'tree_guest_pokemon_data')
        model, treeiter = tree.get_selection().get_selected()
        # There has to be a better way of getting this value
        selected_row_index = tree.get_selection().get_selected_rows()[1][0][0]  # type: ignore
        if model is not None and treeiter is not None:
            cast(Gtk.ListStore, model).remove(treeiter)
        self._update_free_entries_left()
        self._guest_pokemon_entry_deleted(selected_row_index)
        self._save_guest_pokemon_data()

    # <editor-fold desc="HANDLERS: Guest pokémon" defaultstate="collapsed">
    @catch_overflow(u32)
    def on_guest_pokemon_unk1_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 1, 0, 0xFFFFFFFF)

    def on_guest_pokemon_poke_id_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_monsters'))

    def on_guest_pokemon_poke_id_edited(self, widget, path, text):
        try:
            entid = self._get_monster_id_from_display_name(text)
        except ValueError:
            return
        store: Gtk.ListStore = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        store[path][2] = text
        idx = int(store[path][0])
        store[path][17] = self._get_icon(entid, idx, False)
        self._save_guest_pokemon_data()

    @catch_overflow(u8)
    def on_guest_pokemon_joined_at_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 3, 0, 255)

    def on_guest_pokemon_move_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.ListStore, 'completion_moves'))

    def on_guest_pokemon_move1_edited(self, widget, path, text):
        self._update_guest_pokemon_move(path, text, 4)

    def on_guest_pokemon_move2_edited(self, widget, path, text):
        self._update_guest_pokemon_move(path, text, 5)

    def on_guest_pokemon_move3_edited(self, widget, path, text):
        self._update_guest_pokemon_move(path, text, 6)

    def on_guest_pokemon_move4_edited(self, widget, path, text):
        self._update_guest_pokemon_move(path, text, 7)

    @catch_overflow(0, 999)
    def on_guest_pokemon_hp_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 8, 0, 999)

    @catch_overflow(0, 100)
    def on_guest_pokemon_level_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 9, 0, 100)

    @catch_overflow(0, 999)
    def on_guest_pokemon_iq_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 10, 0, 999)

    @catch_overflow(u8)
    def on_guest_pokemon_attack_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 11, 0, 255)

    @catch_overflow(u8)
    def on_guest_pokemon_special_attack_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 12, 0, 255)

    @catch_overflow(u8)
    def on_guest_pokemon_defense_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 13, 0, 255)

    @catch_overflow(u8)
    def on_guest_pokemon_special_defense_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 14, 0, 255)

    @catch_overflow(u16)
    def on_guest_pokemon_unk3_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 15, 0, 0xFFFF)

    @catch_overflow(u32)
    def on_guest_pokemon_exp_edited(self, widget, path, text):
        self._update_guest_pokemon_int(path, text, 16, 0, 0xFFFFFFFF)
    # </editor-fold>

    # <editor-fold desc="HANDLERS: Extra dungeon data" defaultstate="collapsed">
    def on_extra_dungeon_data_guest_pokemon_1_edited(self, widget, path, text):
        try:
            v = int(text)
            if v < -1 or v >= builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data').iter_n_children():
                return
        except ValueError:
            return
        store: Gtk.ListStore = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        store[path][1] = text
        self._save_extra_dungeon_data()

    def on_extra_dungeon_data_guest_pokemon_2_edited(self, widget, path, text):
        try:
            v = int(text)
            if v < -1 or v >= builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data').iter_n_children():
                return
        except ValueError:
            return
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        store[path][2] = text
        self._save_extra_dungeon_data()

    def on_extra_dungeon_data_hlr_uncleared_toggled(self, widget, path):
        self._update_extra_dungeon_data_boolean(widget, path, 3)

    def on_extra_dungeon_data_disable_recruiting_toggled(self, widget, path):
        self._update_extra_dungeon_data_boolean(widget, path, 4)

    def on_extra_dungeon_data_side01_check_toggled(self, widget, path):
        self._update_extra_dungeon_data_boolean(widget, path, 5)

    def on_extra_dungeon_data_hlr_cleared_toggled(self, widget, path):
        self._update_extra_dungeon_data_boolean(widget, path, 6)
    # </editor-fold>

    def refresh_list(self):
        self._fill_guest_pokemon_data()

    def _get_store_icon_id(self):
        return 17

    def _get_store_entid_id(self):
        return 2

    def _fill_extra_dungeon_data(self):
        # Init extra dungeon data store
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        store.clear()
        dungeons : List[Pmd2DungeonDungeon] = self.static_data.dungeon_data.dungeons
        for idx, item in enumerate(ExtraDungeonDataList.read(self.arm9, self.static_data)):
            name = self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, idx)
            store.append([
                str(idx) + ": " + name, str(item.guest1_index), str(item.guest2_index),
                item.hlr_uncleared, item.disable_recruit, item.side01_check, item.hlr_cleared
            ])

    def _fill_guest_pokemon_data(self):
        # Init guest pokémon data store
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        store.clear()
        for i, item in enumerate(GuestPokemonList.read(self.arm9, self.static_data)):
            store.append([
                str(i), str(item.unk1), self._get_monster_display_name(item.poke_id), str(item.joined_at),
                self._get_move_display_name(item.moves[0]), self._get_move_display_name(item.moves[1]),
                self._get_move_display_name(item.moves[2]), self._get_move_display_name(item.moves[3]), str(item.hp),
                str(item.level), str(item.iq), str(item.atk), str(item.sp_atk), str(item.def_), str(item.sp_def),
                str(item.unk3), str(item.exp), self._get_icon(item.poke_id, i)
            ])

    def _save_extra_dungeon_data(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        extra_dungeon_data_list = []
        for i, row in enumerate(iter_tree_model(store)):
            extra_dungeon_data_list.append(ExtraDungeonDataEntry(int(row[1]), int(row[2]),
                                                                 row[3], row[4], row[5], row[6]))
        self.module.set_extra_dungeon_data(extra_dungeon_data_list)
        # Update our copy of the binary
        self.arm9 = self.module.project.get_binary(BinaryName.ARM9)

    def _save_guest_pokemon_data(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        guest_pokemon_list = []
        for i, row in enumerate(iter_tree_model(store)):
            guest_pokemon_list.append(GuestPokemon(
                u32(int(row[1])), u16(self._get_monster_id_from_display_name(row[2])), u16(int(row[3])),
                [
                    u16(self._get_move_id_from_display_name(row[4])),
                    u16(self._get_move_id_from_display_name(row[5])),
                    u16(self._get_move_id_from_display_name(row[6])),
                    u16(self._get_move_id_from_display_name(row[7]))
                ],
                u16(int(row[8])), u16(int(row[9])), u16(int(row[10])), u16(int(row[11])),
                u16(int(row[12])), u16(int(row[13])), u16(int(row[14])), u16(int(row[15])),
                u32(int(row[16])))
            )
        self.module.set_guest_pokemon_data(guest_pokemon_list)
        # Update our copy of the binary
        self.arm9 = self.module.project.get_binary(BinaryName.ARM9)

    def _init_completion(self):
        # Init monsters Completion
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_completion_monsters')
        for i in range(len(self.monster_md_entries)):
            store.append([self._get_monster_display_name(i)])

        # Init moves Completion
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_completion_moves')
        for i in range(len(self.move_entries)):
            store.append([self._get_move_display_name(i)])

    def _update_free_entries_left(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        entries_left = GuestPokemonList.get_max_entries(self.static_data) - store.iter_n_children()

        entries_left_text = builder_get_assert(self.builder, Gtk.Label, 'label_free_entries_left')
        entries_left_text.set_text(f"Free entries left: {entries_left}")

        add_button = builder_get_assert(self.builder, Gtk.Button, 'btn_guest_pokemon_add')
        if entries_left <= 0:
            add_button.set_sensitive(False)
        else:
            add_button.set_sensitive(True)

    def _guest_pokemon_entry_deleted(self, pos: int):
        """
        Updates IDs and references to entries from the extra dungeon data list.
        Must be called after removing a guest pokémon entry from the list.
        """
        assert self.builder
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        for i, row in enumerate(iter_tree_model(store)):
            row[0] = str(i)

        # Update references
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        for row in enumerate(iter_tree_model(store)):
            if int(row[1][1]) == pos:
                row[1][1] = "-1"
            elif int(row[1][1]) > pos:
                row[1][1] = str(int(row[1][1]) - 1)

            if int(row[1][2]) == pos:
                row[1][2] = "-1"
            elif int(row[1][2]) > pos:
                row[1][2] = str(int(row[1][2]) - 1)
        self._save_extra_dungeon_data()

    def _update_extra_dungeon_data_boolean(self, widget, path, value_pos: int):
        assert self.builder
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_extra_dungeon_data')
        store[path][value_pos] = not widget.get_active()
        self._save_extra_dungeon_data()

    def _update_guest_pokemon_int(self, path, text, value_pos: int, min_val: int, max_val: int):
        assert self.builder
        try:
            v = int(text)
            if v < min_val or v > max_val:
                raise OverflowError()
        except ValueError:
            return
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        store[path][value_pos] = text
        self._save_guest_pokemon_data()

    def _update_guest_pokemon_move(self, path, text, value_pos: int):
        assert self.builder
        try:
            self._get_move_id_from_display_name(text)
        except ValueError:
            return
        store = builder_get_assert(self.builder, Gtk.ListStore, 'store_tree_guest_pokemon_data')
        store[path][value_pos] = text
        self._save_guest_pokemon_data()

    def _help(self, msg):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, msg)
        md.run()
        md.destroy()

    def _get_monster_display_name(self, i: int):
        entry = self.monster_md_entries[i]
        name = self.module.project.get_string_provider().get_value(
            StringType.POKEMON_NAMES, i % FileType.MD.properties().num_entities)
        return f'{name} ({Gender(entry.gender).print_name}) (${i:04})'

    def _get_move_display_name(self, i: int):
        entry = self.move_entries[i]
        name = self.module.project.get_string_provider().get_value(StringType.MOVE_NAMES, i)
        return f'{name} ({i:03})'

    def _get_monster_id_from_display_name(self, display_name):
        match = MONSTER_NAME_PATTERN.match(display_name)
        if match is None:
            raise ValueError
        return int(match.group(1))

    def _get_move_id_from_display_name(self, display_name):
        match = MOVE_NAME_PATTERN.match(display_name)
        if match is None:
            raise ValueError
        return int(match.group(1))
