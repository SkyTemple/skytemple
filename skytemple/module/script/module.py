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
import re
from typing import Union

from gi.repository.Gtk import TreeStore

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.rom_project import RomProject
from skytemple.core.ui_utils import recursive_generate_item_store_row_label
from skytemple.module.script.controller.folder import FolderController
from skytemple.module.script.controller.map import MapController
from skytemple.module.script.controller.ssa import SsaController
from skytemple.module.script.controller.ssb import SsbController
from skytemple.module.script.controller.lsd import LsdController
from skytemple.module.script.controller.main import MainController
from skytemple.module.script.controller.sub import SubController
from skytemple_files.common.script_util import load_script_files, SCRIPT_DIR, SSA_EXT, SSS_EXT
from skytemple_files.common.types.file_types import FileType


class ScriptModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['map_bg']

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project

        # Load all scripts
        self.script_engine_file_tree = load_script_files(self.project.get_rom_folder(SCRIPT_DIR))

        self._tree_model = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        # -> Script [main]
        root = item_store.append(root_node, [
            'folder-templates-symbolic', 'Script Scenes', self, MainController, 0, False, ''
        ])

        self._tree_model = item_store

        #    -> Common [common]
        item_store.append(root, [
            'text-plain', 'Scripts', self,  SsbController, 0, False, ''
        ])

        sub_nodes = {
            'S': item_store.append(root, [
                'folder-symbolic', 'S - System', self, FolderController, 0, False, ''
            ]),
            'T': item_store.append(root, [
                'folder-symbolic', 'T - Town', self, FolderController, 0, False, ''
            ]),
            'D': item_store.append(root, [
                'folder-symbolic', 'D - Dungeon', self, FolderController, 0, False, ''
            ]),
            'G': item_store.append(root, [
                'folder-symbolic', 'G - Guild', self, FolderController, 0, False, ''
            ]),
            'H': item_store.append(root, [
                'folder-symbolic', 'H - Habitat', self, FolderController, 0, False, ''
            ]),
            'P': item_store.append(root, [
                'folder-symbolic', 'P - Places', self, FolderController, 0, False, ''
            ]),
            'V': item_store.append(root, [
                'folder-symbolic', 'V - Visual', self, FolderController, 0, False, ''
            ])
        }
        # Other
        other = item_store.append(root, [
            'folder-symbolic', 'Other', self, FolderController, 0, False, ''
        ])

        for i, map_obj in enumerate(self.script_engine_file_tree['maps'].values()):
            parent = other
            if map_obj['name'][0] in sub_nodes.keys():
                parent = sub_nodes[map_obj['name'][0]]
            #    -> (Map Name) [map]
            map_root = item_store.append(parent, [
                'folder-symbolic', map_obj['name'], self,  MapController, map_obj['name'], False, ''
            ])

            if map_obj['enter_sse'] is not None:
                #          -> Scene [ssa]
                item_store.append(map_root, [
                    'folder-templates-symbolic', 'Enter (sse)', self,  SsaController, {
                        'map': map_obj['name'],
                        'file': f"{SCRIPT_DIR}/{map_obj['name']}/{map_obj['enter_sse']}",
                        'type': 'sse',
                        'scripts': map_obj['enter_ssbs'].copy()
                    }, False, ''
                ])

            #       -> Acting Scripts [lsd]
            acting_root = item_store.append(map_root, [
                'folder-symbolic', 'Acting (ssa)', self,  LsdController, 0, False, ''
            ])
            for ssa, ssb in map_obj['ssas']:
                stem = ssa[:-len(SSA_EXT)]
                #             -> Scene [ssa]
                item_store.append(acting_root, [
                    'folder-templates-symbolic', stem,
                    self, SsaController, {
                        'map': map_obj['name'],
                        'file': f"{SCRIPT_DIR}/{map_obj['name']}/{ssa}",
                        'type': 'ssa',
                        'scripts': [ssb]
                    }, False, ''
                ])

            #       -> Sub Scripts [sub]
            sub_root = item_store.append(map_root, [
                'folder-symbolic', 'Sub (sss)', self,  SubController, 0, False, ''
            ])
            for sss, ssbs in map_obj['subscripts'].items():
                stem = sss[:-len(SSS_EXT)]
                #             -> Scene [ssa]
                item_store.append(sub_root, [
                    'folder-templates-symbolic', stem,
                    self, SsaController, {
                        'map': map_obj['name'],
                        'file': f"{SCRIPT_DIR}/{map_obj['name']}/{sss}",
                        'type': 'sss',
                        'scripts': ssbs.copy()
                    }, False, ''
                ])

        recursive_generate_item_store_row_label(self._tree_model[root])

    def _get_fnumber_from_str(self, stem, string) -> str:
        """Returns the number part from a string like enter00.sse."""
        regex = re.compile('^' + stem + '(\\d{1,2})\\....$')
        match = regex.match(string)
        if not match:
            # If it doesn't match, we just return the original string in quotes.
            return f'"{string}"'
        return str(int(match.group(1)))

    def get_ssa(self, filename):
        return self.project.open_file_in_rom(filename, FileType.SSA)

    def get_scenes_for_map(self, mapname):
        """Returns the filenames (not including paths) of all SSE/SSA/SSS files for this map."""
        if mapname not in self.script_engine_file_tree['maps']:
            return []
        map_obj = self.script_engine_file_tree['maps'][mapname]

        scenes = []
        if map_obj['enter_sse'] is not None:
            scenes.append(map_obj['enter_sse'])
        for ssa, _ in map_obj['ssas']:
            scenes.append(ssa)
        for sss in map_obj['subscripts'].keys():
            scenes.append(sss)

        return scenes
