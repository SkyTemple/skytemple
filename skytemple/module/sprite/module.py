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
import sys
import webbrowser
from typing import TYPE_CHECKING, Union, Optional

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.model_context import ModelContext
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.sprite.controller.monster_sprite import MonsterSpriteController
from skytemple.module.sprite.controller.object import ObjectController
from skytemple.module.sprite.controller.object_main import OBJECT_SPRTIES, ObjectMainController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import MONSTER_BIN
from skytemple_files.container.bin_pack.model import BinPack
from skytemple_files.graphics.chara_wan.model import WanFile
from skytemple_files.common.i18n_util import f, _
if TYPE_CHECKING:
    from skytemple.module.gfxcrunch.module import GfxcrunchModule


GROUND_DIR = 'GROUND'
WAN_FILE_EXT = 'wan'
GROUND_BIN = 'MONSTER/m_ground.bin'
ATTACK_BIN = 'MONSTER/m_attack.bin'


class SpriteModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['gfxcrunch']

    @classmethod
    def sort_order(cls):
        return 130

    def __init__(self, rom_project: RomProject):
        """Object and actor sprites."""
        self.project = rom_project
        self.list_of_obj_sprites = self.project.get_files_with_ext(WAN_FILE_EXT, GROUND_DIR)

        self._tree_model = None
        self._tree_level_iter = {}

    def load_tree_items(self, item_store: TreeStore, root_node):
        root = item_store.append(root_node, [
            'skytemple-e-object-symbolic', OBJECT_SPRTIES, self, ObjectMainController, 0, False, '', True
        ])
        self._tree_model = item_store
        self._tree_level_iter = {}

        for name in self.list_of_obj_sprites:
            self._tree_level_iter[name] = item_store.append(root, [
                'skytemple-e-object-symbolic', name, self,  ObjectController, name, False, '', True
            ])

        recursive_generate_item_store_row_label(self._tree_model[root])

    def get_monster_sprite_editor(self, sprite_id: int,
                                  modified_callback, assign_new_sprite_id_cb,
                                  get_shadow_size_cb, set_shadow_size_cb) -> Gtk.Widget:
        """Returns the view for one portrait slots"""
        controller = MonsterSpriteController(self, sprite_id,
                                             modified_callback, assign_new_sprite_id_cb,
                                             get_shadow_size_cb, set_shadow_size_cb)
        return controller.get_view()

    def get_object_sprite_raw(self, filename):
        assert filename in self.list_of_obj_sprites
        return self.project.open_file_manually(GROUND_DIR + '/' + filename)

    def save_object_sprite(self, filename, data: bytes):
        assert filename in self.list_of_obj_sprites
        self.project.save_file_manually(GROUND_DIR + '/' + filename, data)
        row = self._tree_model[self._tree_level_iter[filename]]
        recursive_up_item_store_mark_as_modified(row)

    def get_sprite_provider(self):
        return self.project.get_sprite_provider()

    def get_gfxcrunch(self) -> 'GfxcrunchModule':
        return self.project.get_module('gfxcrunch')

    def import_a_sprite(self) -> Optional[bytes]:
        if self.get_gfxcrunch().is_available():
            return self.import_a_sprite__gfxcrunch()
        return self.import_a_sprite__wan()

    def export_a_sprite(self, sprite: bytes):
        if self.get_gfxcrunch().is_available():
            return self.export_a_sprite__gfxcrunch(sprite)
        return self.export_a_sprite__wan(sprite)

    def import_a_sprite__wan(self) -> bytes:
        dialog = Gtk.FileChooserNative.new(
            _("Import WAN sprite..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.wan'
            with open(fn, 'rb') as f:
                return f.read()

    def export_a_sprite__wan(self, sprite: bytes):
        dialog = Gtk.FileChooserNative.new(
            _("Export WAN sprite..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )
        filter = Gtk.FileFilter()
        filter.set_name(_("WAN sprite (*.wan)"))
        filter.add_pattern("*.wan")
        dialog.add_filter(filter)

        response = dialog.run()
        fn = dialog.get_filename()

        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.wan'
            with open(fn, 'wb') as f:
                f.write(sprite)

    def import_a_sprite__gfxcrunch(self) -> Optional[bytes]:
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, _("To import select the directory of the sprite export. If it "
                                                          "is still zipped, unzip it first."))
        md.run()
        md.destroy()

        dialog = Gtk.FileChooserNative.new(
            _("Import gfxcrunch sprite..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                return self.get_gfxcrunch().import_sprite(fn)
            except BaseException as e:
                display_error(
                    sys.exc_info(),
                    str(e),
                    _("Error importing the sprite.")
                )
                return None

    def export_a_sprite__gfxcrunch(self, sprite: bytes):
        dialog = Gtk.FileChooserNative.new(
            "Export gfxcrunch sprite...",
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _('_Save'), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                self.get_gfxcrunch().export_sprite(sprite, fn)
            except BaseException as e:
                display_error(
                    sys.exc_info(),
                    str(e),
                    _("Error exporting the sprite.")
                )

    def open_spritebot_explanation(self):
        webbrowser.open_new_tab('https://docs.google.com/document/d/1EceEEjyeoFwoKXdNj4vpXdoYRWp8CID64e-ZqY954_Q/edit')

    def open_gfxcrunch_page(self):
        self.get_gfxcrunch().open_gfxcrunch_page()

    def get_monster_bin_ctx(self) -> ModelContext[BinPack]:
        return self.project.open_file_in_rom(MONSTER_BIN, FileType.BIN_PACK, threadsafe=True)

    def get_ground_bin_ctx(self) -> ModelContext[BinPack]:
        return self.project.open_file_in_rom(GROUND_BIN, FileType.BIN_PACK, threadsafe=True)

    def get_attack_bin_ctx(self) -> ModelContext[BinPack]:
        return self.project.open_file_in_rom(ATTACK_BIN, FileType.BIN_PACK, threadsafe=True)

    def get_monster_monster_sprite_chara(self, id, raw=False) -> Union[bytes, WanFile]:
        with self.get_monster_bin_ctx() as bin_pack:
            decompressed = FileType.PKDPX.deserialize(bin_pack[id]).decompress()
            if raw:
                return decompressed
            return FileType.WAN.CHARA.deserialize(decompressed)

    def get_monster_ground_sprite_chara(self, id, raw=False) -> Union[bytes, WanFile]:
        with self.get_ground_bin_ctx() as bin_pack:
            if raw:
                return bin_pack[id]
            return FileType.WAN.CHARA.deserialize(bin_pack[id])

    def get_monster_attack_sprite_chara(self, id, raw=False) -> Union[bytes, WanFile]:
        with self.get_attack_bin_ctx() as bin_pack:
            decompressed = FileType.PKDPX.deserialize(bin_pack[id]).decompress()
            if raw:
                return decompressed
            return FileType.WAN.CHARA.deserialize(decompressed)

    def get_monster_sprite_count(self):
        with self.get_monster_bin_ctx() as monster_bin, \
                self.get_attack_bin_ctx() as attack_bin, \
                self.get_ground_bin_ctx() as ground_bin:
            if len(monster_bin) != len(attack_bin) or len(attack_bin) != len(ground_bin):
                display_error(None, _("Error with sprite files: They don't have the same length!"))
                return -1
            return len(monster_bin)


    def save_monster_monster_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        with self.get_monster_bin_ctx() as bin_pack:
            if not raw:
                data = FileType.WAN.CHARA.serialize(data)
            data = FileType.PKDPX.serialize(FileType.PKDPX.compress(data))
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(MONSTER_BIN)

    def save_monster_ground_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        with self.get_ground_bin_ctx() as bin_pack:
            if not raw:
                data = FileType.WAN.CHARA.serialize(data)
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(GROUND_BIN)

    def save_monster_attack_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        with self.get_attack_bin_ctx() as bin_pack:
            if not raw:
                data = FileType.WAN.CHARA.serialize(data)
            data = FileType.PKDPX.serialize(FileType.PKDPX.compress(data))
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(ATTACK_BIN)
