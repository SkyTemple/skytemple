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
from skytemple.module.script.controller.common import CommonController
from skytemple.module.script.controller.enter import EnterController
from skytemple.module.script.controller.lsd_entry import LsdEntryController
from skytemple.module.script.controller.map import MapController
from skytemple.module.script.controller.ssa import SsaController
from skytemple.module.script.controller.ssb import SsbController
from skytemple.module.script.controller.lsd import LsdController
from skytemple.module.script.controller.main import MainController
from skytemple.module.script.controller.sub import SubController
from skytemple.module.script.controller.sub_entry import SubEntryController
from skytemple_files.common.script_util import load_script_files, SCRIPT_DIR, UNIONALL_SSB, SSA_EXT, SSS_EXT


class ScriptModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project

        # Load all scripts
        self.script_engine_file_tree = load_script_files(self.project.get_rom_folder(SCRIPT_DIR))

        self._tree_model = None

    def load_tree_items(self, item_store: TreeStore):
        # TODO: Add to rom root node
        # -> Script [main]
        root = item_store.append(None, [
            'folder-text', 'Scripts', self, MainController, 0, False, ''
        ])

        self._tree_model = item_store

        #    -> Common [common]
        common_root = item_store.append(root, [
            'folder', 'Common', self,  CommonController, 0, False, ''
        ])
        #       -> Master Script (unionall) [ssb]
        #       -> (others) [ssb]
        for name in self.script_engine_file_tree['common']:
            display_name = name
            if name == UNIONALL_SSB:
                display_name = f'Master Script ({name})'
            item_store.append(common_root, [
                'text-plain', display_name, self,  SsbController, 0, False, ''
            ])

        for i, map_obj in enumerate(self.script_engine_file_tree['maps'].values()):
            #    -> (Map Name) [map]
            map_root = item_store.append(root, [
                'folder', map_obj['name'], self,  MapController, map_obj['name'], False, ''
            ])

            #       -> Enter Scripts [enter]
            enter_root = item_store.append(map_root, [
                'folder', 'Enter Scripts', self,  EnterController, 0, False, ''
            ])
            if map_obj['enter_sse'] is not None:
                #          -> Map [ssa]
                item_store.append(enter_root, [
                    'image', 'Map', self,  SsaController, {'map': map_obj['name'], 'file': map_obj['enter_sse']}, False, ''
                ])
                #          -> Script X [ssb]
                for ssb in map_obj['enter_ssbs']:
                    item_store.append(enter_root, [
                        'text-plain', f'Script {self._get_fnumber_from_str("enter", ssb)}',
                        self,  SsbController, {'map': map_obj['name'], 'file': ssb}, False, ''
                    ])

            #       -> Acting Scripts [lsd]
            acting_root = item_store.append(map_root, [
                'folder', 'Acting Scripts', self,  LsdController, 0, False, ''
            ])
            for ssa, ssb in map_obj['ssas']:
                stem = ssa[:-len(SSA_EXT)]
                #          -> (name) [lsd_entry]
                acting_entry = item_store.append(acting_root, [
                    'folder', stem, self,  LsdEntryController, 0, False, ''
                ])

                #             -> Map [ssa]
                item_store.append(acting_entry, [
                    'image', f'Map',
                    self, SsaController, {'map': map_obj['name'], 'file': ssa}, False, ''
                ])
                #             -> Script [ssb]
                item_store.append(acting_entry, [
                    'text-plain', f'Script',
                    self, SsbController, {'map': map_obj['name'], 'file': ssb}, False, ''
                ])

            #       -> Sub Scripts [sub]
            sub_root = item_store.append(map_root, [
                'folder', 'Sub Scripts', self,  SubController, 0, False, ''
            ])
            for sss, ssbs in map_obj['subscripts'].items():
                stem = sss[:-len(SSS_EXT)]
                #          -> (name) [sub_entry]
                sub_entry = item_store.append(sub_root, [
                    'folder', stem, self,  SubEntryController, 0, False, ''
                ])

                #             -> Map [ssa]
                item_store.append(sub_entry, [
                    'image', f'Map',
                    self, SsaController, {'map': map_obj['name'], 'file': sss}, False, ''
                ])
                for ssb in ssbs:
                    #             -> Script X [ssb]
                    item_store.append(sub_entry, [
                        'text-plain', f'Script {self._get_fnumber_from_str(stem, ssb)}',
                        self, SsbController, {'map': map_obj['name'], 'file': ssb}, False, ''
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
