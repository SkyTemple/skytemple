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
import webbrowser

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified
from skytemple.module.sprite.controller.monster_sprite import MonsterSpriteController
from skytemple.module.sprite.controller.object import ObjectController
from skytemple.module.sprite.controller.object_main import OBJECT_SPRTIES, ObjectMainController

GROUND_DIR = 'GROUND'
WAN_FILE_EXT = 'wan'


class SpriteModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

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

    def get_monster_sprite_editor(self, sprite_id: int, modified_callback) -> Gtk.Widget:
        """Returns the view for one portrait slots"""
        controller = MonsterSpriteController(self, sprite_id, modified_callback)
        return controller.get_view()

    def get_object_sprite_raw(self, filename):
        assert filename in self.list_of_obj_sprites
        return self.project.open_file_manually(GROUND_DIR + '/' + filename)

    def save_object_sprite(self, filename, data: bytes):
        """Mark a specific w16 as modified"""
        assert filename in self.list_of_obj_sprites
        self.project.save_file_manually(GROUND_DIR + '/' + filename, data)
        row = self._tree_model[self._tree_level_iter[filename]]
        recursive_up_item_store_mark_as_modified(row)

    def get_sprite_provider(self):
        return self.project.get_sprite_provider()

    def open_spritebot_explanation(self):
        pass  # TODO

    def open_gfxcrunch_page(self):
        webbrowser.open_new_tab('https://projectpokemon.org/home/forums/topic/31407-pokemon-mystery-dungeon-2-psy_commandos-tools-and-research-notes/')
