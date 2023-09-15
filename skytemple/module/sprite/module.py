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
import sys
import webbrowser
from typing import TYPE_CHECKING, Union, Optional, Dict, overload, Literal

from gi.repository import Gtk
from PIL import Image
from skytemple_files.common.ppmdu_config.data import Pmd2Sprite

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.error_handler import display_error
from skytemple.core.item_tree import ItemTree, ItemTreeEntryRef, ItemTreeEntry, RecursionType
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.model_context import ModelContext
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from skytemple.module.sprite.controller.monster_sprite import MonsterSpriteController
from skytemple.module.sprite.controller.object import ObjectController
from skytemple.module.sprite.controller.object_main import OBJECT_SPRTIES, ObjectMainController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import MONSTER_BIN, add_extension_if_missing
from skytemple_files.container.bin_pack.model import BinPack
from skytemple_files.data.sprconf.handler import SPRCONF_FILENAME
from skytemple_files.graphics.chara_wan.model import WanFile
from skytemple_files.common.i18n_util import f, _
from skytemple_rust import pmd_wan
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

        self._item_tree: ItemTree
        self._tree_level_iter: Dict[str, ItemTreeEntryRef] = {}
        self._root: ItemTreeEntryRef

    def load_tree_items(self, item_tree: ItemTree):
        self._root = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-e-object-symbolic',
            name=OBJECT_SPRTIES,
            module=self,
            view_class=ObjectMainController,
            item_data=0
        ))
        self._item_tree = item_tree
        self._tree_level_iter = {}

        for name in self.list_of_obj_sprites:
            self._tree_level_iter[name] = item_tree.add_entry(self._root, ItemTreeEntry(
                icon='skytemple-e-object-symbolic',
                name=name,
                module=self,
                view_class=ObjectController,
                item_data=name
            ))

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
        self._item_tree.mark_as_modified(self._tree_level_iter[filename], RecursionType.UP)

    def get_sprite_provider(self):
        return self.project.get_sprite_provider()

    def get_gfxcrunch(self) -> 'GfxcrunchModule':
        return self.project.get_module('gfxcrunch')

    def add_wan(self, obj_name):
        self._tree_level_iter[obj_name] = self._item_tree.add_entry(self._root, ItemTreeEntry(
            icon='skytemple-e-object-symbolic',
            name=obj_name,
            module=self,
            view_class=ObjectController,
            item_data=obj_name
        ))

    def import_a_sprite(self) -> Optional[bytes]:
        if self.get_gfxcrunch().is_available():
            return self.import_a_sprite__gfxcrunch()
        return self.import_a_sprite__wan()

    def export_a_sprite(self, sprite: bytes):
        if self.get_gfxcrunch().is_available():
            return self.export_a_sprite__gfxcrunch(sprite)
        return self.export_a_sprite__wan(sprite)

    def import_a_sprite__wan(self) -> Optional[bytes]:
        dialog = Gtk.FileChooserNative.new(
            _("Import WAN sprite..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, 'wan')
            with open(fn, 'rb') as f:
                return f.read()
        return None

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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, 'wan')
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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                self.get_gfxcrunch().export_sprite(sprite, fn)
            except BaseException as e:
                display_error(
                    sys.exc_info(),
                    str(e),
                    _("Error exporting the sprite.")
                )
    
    def import_an_image(self) -> Optional[bytes]:
        dialog = Gtk.FileChooserNative.new(
            _("Import image file..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                img = Image.open(fn, 'r')
                return pmd_wan.encode_image_to_static_wan_file(img)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing image to object.")
                )
        return None


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

    @overload
    def get_monster_monster_sprite_chara(self, id, raw: Literal[False] = False) -> WanFile: ...
    @overload
    def get_monster_monster_sprite_chara(self, id, raw: Literal[True]) -> bytes: ...
    def get_monster_monster_sprite_chara(self, id, raw: bool = False) -> Union[bytes, WanFile]:
        with self.get_monster_bin_ctx() as bin_pack:
            decompressed = FileType.PKDPX.deserialize(bin_pack[id]).decompress()
            if raw:
                return decompressed
            return FileType.WAN.CHARA.deserialize(decompressed)

    @overload
    def get_monster_ground_sprite_chara(self, id, raw: Literal[False] = False) -> WanFile: ...
    @overload
    def get_monster_ground_sprite_chara(self, id, raw: Literal[True]) -> bytes: ...
    def get_monster_ground_sprite_chara(self, id, raw: bool = False) -> Union[bytes, WanFile]:
        with self.get_ground_bin_ctx() as bin_pack:
            if raw:
                return bin_pack[id]
            return FileType.WAN.CHARA.deserialize(bin_pack[id])

    @overload
    def get_monster_attack_sprite_chara(self, id, raw: Literal[False] = False) -> WanFile: ...
    @overload
    def get_monster_attack_sprite_chara(self, id, raw: Literal[True]) -> bytes: ...
    def get_monster_attack_sprite_chara(self, id, raw: bool = False) -> Union[bytes, WanFile]:
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
                display_error(
                    None,
                    _("Error with sprite files: They don't have the same length. This will be corrected by adding empty sprites. You should re-import the last imported sprite."),
                    should_report=False
                )
                max_size = max(len(monster_bin), max(len(attack_bin), len(ground_bin)))
                
                for missing_monster_sprite_id in range(len(monster_bin), max_size):
                    self.save_monster_monster_sprite_prepared(missing_monster_sprite_id, bytes())
                
                for missing_attack_sprite_id in range(len(attack_bin), max_size):
                    self.save_monster_attack_sprite_prepared(missing_attack_sprite_id, bytes())

                for missing_ground_sprite_id in range(len(ground_bin), max_size):
                    self.save_monster_ground_sprite_prepared(missing_ground_sprite_id, bytes())
                
                return max_size
            return len(monster_bin)

    def save_monster_sprite(self, id, wan: WanFile):
        """Import all three sprite variation of the monster"""
        monster, ground, attack = FileType.WAN.CHARA.split_wan(wan)
        # First prepare them all. This make sure we catch any conversion error and avoid partial import
        ground_prepared = self.prepare_monster_sprite(ground, False)
        monster_prepared = self.prepare_monster_sprite(monster, True)
        attack_prepared = self.prepare_monster_sprite(attack, True)
        
        self.save_monster_ground_sprite_prepared(id, ground_prepared)
        self.save_monster_monster_sprite_prepared(id, monster_prepared)
        self.save_monster_attack_sprite_prepared(id, attack_prepared)
    
    def prepare_monster_sprite(self, data: Union[bytes, WanFile], compress: bool) -> bytes:
        if isinstance(data, WanFile):
            data = FileType.WAN.CHARA.serialize(data) 
        if compress:
            data = FileType.PKDPX.serialize(FileType.PKDPX.compress(data)) 
        return data

    def save_monster_ground_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        self.save_monster_ground_sprite_prepared(id, self.prepare_monster_sprite(data, False))
    
    def save_monster_ground_sprite_prepared(self, id, data: bytes):
        with self.get_ground_bin_ctx() as bin_pack:
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(GROUND_BIN)


    def save_monster_monster_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        self.save_monster_monster_sprite_prepared(id, self.prepare_monster_sprite(data, True))
    
    def save_monster_monster_sprite_prepared(self, id, data: bytes):
        with self.get_monster_bin_ctx() as bin_pack:
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(MONSTER_BIN)

    def save_monster_attack_sprite(self, id, data: Union[bytes, WanFile], raw=False):
        self.save_monster_attack_sprite_prepared(id, self.prepare_monster_sprite(data, True))
    
    def save_monster_attack_sprite_prepared(self, id, data: bytes):
        with self.get_attack_bin_ctx() as bin_pack:
            if id == len(bin_pack):
                bin_pack.append(data)
            else:
                bin_pack[id] = data
        self.project.mark_as_modified(ATTACK_BIN)

    def update_sprconf(self, sprite: Pmd2Sprite):
        sprconf = self.project.open_sprconf()
        FileType.SPRCONF.update(sprconf, sprite)
        self.project.mark_as_modified(SPRCONF_FILENAME)
        self.project.get_rom_module().get_static_data().animation_names[sprite.id] = sprite

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, ObjectController):
            pass  # todo
        return None

    def is_idx_supported(self, idx: int) -> bool:
        """Check if the sprite ID is valid."""
        return idx >= 0
