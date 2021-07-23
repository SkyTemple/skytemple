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
from typing import TYPE_CHECKING

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import BinaryName
from skytemple_files.common.i18n_util import f, _
from skytemple_files.hardcoded.guest_pokemon import ExtraDungeonDataList, GuestPokemonList, GuestPokemon, \
    ExtraDungeonDataEntry

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule


class GuestPokemonController(AbstractController):

    def __init__(self, module: 'ListsModule', item_id: int):
        self.module = module
        self.builder = None
        self.arm9 = module.project.get_binary(BinaryName.ARM9)
        self.static_data = module.project.get_rom_module().get_static_data()

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'guest_pokemon.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_edit_extra_pokemon():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack

        self._fill_extra_dungeon_data()
        self._fill_guest_pokemon_data()
        self._update_free_entries_left()

        stack.set_visible_child(self.builder.get_object('box_list'))
        self.builder.connect_signals(self)

        return stack

    def on_nb_sl_switch_page(self, n: Gtk.Notebook, p, pnum, *args):
        if pnum == 0:
            self._fill_extra_dungeon_data()
        elif pnum == 1:
            self._fill_guest_pokemon_data()

    def on_btn_help_extra_dungeon_data_clicked(self, *args):
        self._help(_("- HLR (uncleared): Whether Hidden Land restrictions should be active in the dungeon when you "
                     "enter it without having cleared it yet.\n"
                     "Hidden Land restrictions prevent sending pokémon home or changing leaders. In addition, "
                     "if a team member faints you will get kicked out of the dungeon.\n"
                     "- Disable recruiting: Only applies when the dungeon is uncleared. If enabled, recruiting will "
                     "be disabled.\n"
                     "- SIDE01 check: If enabled, guest pokémon will only be added to the team if the ground variable "
                     "SIDE01_BOSS2ND is 0.\n"
                     "- HLR (cleared): Whether Hidden Land restrictions should be enabled in the dungeon when you "
                     "enter it after it's cleared."))
    
    def on_guest_pokemon_add_clicked(self, *args):
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        store.append([
            str(len(store)), "0", "1", "0", "0", "0", "0", "0", "1", "1", "1", "0", "0", "0", "0", "0", "0"
        ])
        self._update_free_entries_left()
        self._save_guest_pokemon_data()

    def on_guest_pokemon_remove_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('tree_guest_pokemon_data')
        model, treeiter = tree.get_selection().get_selected()
        # There has to be a better way of getting this value
        selected_row_index = tree.get_selection().get_selected_rows()[1][0][0]
        if model is not None and treeiter is not None:
            model.remove(treeiter)
        self._update_free_entries_left()
        self._guest_pokemon_entry_deleted(selected_row_index)
        self._save_guest_pokemon_data()

    # <editor-fold desc="HANDLERS: Guest pokémon" defaultstate="collapsed">
    def on_guest_pokemon_unk1_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 1)

    def on_guest_pokemon_poke_id_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 2)

    def on_guest_pokemon_unk2_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 3)

    def on_guest_pokemon_move1_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 4)

    def on_guest_pokemon_move2_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 5)

    def on_guest_pokemon_move3_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 6)

    def on_guest_pokemon_move4_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 7)

    def on_guest_pokemon_hp_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 8)

    def on_guest_pokemon_level_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 9)

    def on_guest_pokemon_iq_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 10)

    def on_guest_pokemon_attack_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 11)

    def on_guest_pokemon_special_attack_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 12)

    def on_guest_pokemon_defense_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 13)

    def on_guest_pokemon_special_defense_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 14)

    def on_guest_pokemon_unk3_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 15)

    def on_guest_pokemon_exp_edited(self, widget, path, text):
        self._update_guest_pokemon_data_value(path, text, 16)
    # </editor-fold>

    # <editor-fold desc="HANDLERS: Guest pokémon" defaultstate="collapsed">
    def on_extra_dungeon_data_guest_pokemon_1_edited(self, widget, path, text):
        # TOFIX: This never runs for some reason
        print("TEST")
        store: Gtk.ListStore = self.builder.get_object('store_tree_extra_dungeon_data')
        store[path][1] = int(text)
        self._save_extra_dungeon_data()

    # TODO: Rest of extra dungeon data handlers
    # </editor-fold>

    def _fill_extra_dungeon_data(self):
        # Init extra dungeon data store
        store: Gtk.ListStore = self.builder.get_object('store_tree_extra_dungeon_data')
        store.clear()
        for idx, item in enumerate(ExtraDungeonDataList.read(self.arm9, self.static_data)):
            store.append([
                str(idx), str(item.guest1_index), str(item.guest2_index), item.hlr_uncleared, item.disable_recruit,
                item.side01_check, item.hlr_cleared
            ])

    def _fill_guest_pokemon_data(self):
        # Init guest pokémon data store
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        store.clear()
        for i, item in enumerate(GuestPokemonList.read(self.arm9, self.static_data)):
            store.append([
                str(i), str(item.unk1), str(item.poke_id), str(item.unk2), str(item.moves[0]), str(item.moves[1]),
                str(item.moves[2]), str(item.moves[3]), str(item.hp), str(item.level), str(item.iq), str(item.atk),
                str(item.sp_atk), str(item.def_), str(item.sp_def), str(item.unk3), str(item.exp)
            ])

    def _save_extra_dungeon_data(self):
        store: Gtk.ListStore = self.builder.get_object('store_tree_extra_dungeon_data')
        extra_dungeon_data_list = []
        for i, row in enumerate(store):
            extra_dungeon_data_list.append(ExtraDungeonDataEntry(int(row[1]), int(row[2]),
                                                                 row[3], row[4], row[5], row[6]))
        self.module.set_extra_dungeon_data(extra_dungeon_data_list)
        # Update our copy of the binary
        self.arm9 = self.module.project.get_binary(BinaryName.ARM9)

    def _save_guest_pokemon_data(self):
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        guest_pokemon_list = []
        for i, row in enumerate(store):
            guest_pokemon_list.append(GuestPokemon(int(row[1]), int(row[2]), int(row[3]),
                                                   [int(row[4]), int(row[5]), int(row[6]), int(row[7])],
                                                   int(row[8]), int(row[9]), int(row[10]), int(row[11]),
                                                   int(row[12]), int(row[13]), int(row[14]), int(row[15]),
                                                   int(row[16])))
        self.module.set_guest_pokemon_data(guest_pokemon_list)
        # Update our copy of the binary
        self.arm9 = self.module.project.get_binary(BinaryName.ARM9)

    def _update_free_entries_left(self):
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        entries_left = GuestPokemonList.get_max_entries(self.arm9, self.static_data) - len(store)

        entries_left_text: Gtk.Label = self.builder.get_object('label_free_entries_left')
        entries_left_text.set_text(f"Free entries left: {entries_left}")

        add_button: Gtk.Button = self.builder.get_object('btn_guest_pokemon_add')
        if entries_left <= 0:
            add_button.set_sensitive(False)
        else:
            add_button.set_sensitive(True)

    def _guest_pokemon_entry_deleted(self, pos: int):
        """
        Updates IDs and references to entries from the extra dungeon data list.
        Must be called after removing a guest pokémon entry from the list.
        """
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        for i, row in enumerate(store):
            row[0] = str(i)

        # Update references
        store: Gtk.ListStore = self.builder.get_object('store_tree_extra_dungeon_data')
        for row in enumerate(store):
            if int(row[1][1]) == pos:
                row[1][1] = "-1"
            elif int(row[1][1]) > pos:
                row[1][1] = str(int(row[1][1]) - 1)

            if int(row[1][2]) == pos:
                row[1][2] = "-1"
            elif int(row[1][2]) > pos:
                row[1][2] = str(int(row[1][2]) - 1)
        self._save_extra_dungeon_data()

    def _update_guest_pokemon_data_value(self, path, text, value_pos: int):
        try:
            v = int(text)
        except ValueError:
            return
        store: Gtk.ListStore = self.builder.get_object('store_tree_guest_pokemon_data')
        store[path][value_pos] = text
        self._save_guest_pokemon_data()

    def _help(self, msg):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, msg)
        md.run()
        md.destroy()