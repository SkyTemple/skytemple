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
import os
from typing import Optional, Dict, List, Tuple

from gi.repository import Gtk
from gi.repository.Gtk import TreeStore

from explorerscript.source_map import SourceMapPositionMark
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.model_context import ModelContext
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_SCENE, REQUEST_TYPE_SCENE_SSE, REQUEST_TYPE_SCENE_SSA, \
    REQUEST_TYPE_SCENE_SSS
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.core.ssb_debugger.ssb_loaded_file_handler import SsbLoadedFileHandler
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import recursive_generate_item_store_row_label, recursive_up_item_store_mark_as_modified, \
    data_dir
from skytemple.module.script.controller.folder import FolderController
from skytemple.module.script.controller.map import MapController
from skytemple.module.script.controller.dialog.pos_mark_editor import PosMarkEditorController
from skytemple.module.script.controller.ssa import SsaController
from skytemple.module.script.controller.ssb import SsbController, SCRIPT_SCRIPTS
from skytemple.module.script.controller.lsd import LsdController
from skytemple.module.script.controller.main import MainController, SCRIPT_SCENES
from skytemple.module.script.controller.sub import SubController
from skytemple_files.common.script_util import load_script_files, SCRIPT_DIR, SSA_EXT, SSS_EXT, LSD_EXT
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.i18n_util import f, _
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.dungeon_data.fixed_bin.model import FixedBin
from skytemple_files.dungeon_data.mappa_bin.model import MappaBin
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.hardcoded.dungeons import DungeonDefinition, HardcodedDungeons
from skytemple_files.hardcoded.ground_dungeon_tilesets import HardcodedGroundDungeonTilesets, GroundTilesetMapping
from skytemple_files.list.level.model import LevelListBin
from skytemple_files.script.lsd.model import Lsd
from skytemple_files.script.ssa_sse_sss.model import Ssa
from skytemple.controller.main import MainController as SkyTempleMainController

LEVEL_LIST = 'BALANCE/level_list.bin'


class ScriptModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['map_bg']

    @classmethod
    def sort_order(cls):
        return 50

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project

        # Load all scripts
        self.script_engine_file_tree = load_script_files(self.project.get_rom_folder(SCRIPT_DIR), self.get_level_list() if self.has_level_list() else None)

        # Tree iters for handle_request:
        self._map_scene_root: Dict[str, Gtk.TreeIter] = {}
        self._acting_roots: Dict[str, Gtk.TreeIter] = {}
        self._sub_roots: Dict[str, Gtk.TreeIter] = {}
        self._map_ssas: Dict[str, Dict[str, Gtk.TreeIter]] = {}
        self._map_sse: Dict[str, Gtk.TreeIter] = {}
        self._map_ssss: Dict[str, Dict[str, Gtk.TreeIter]] = {}

        self._tree_model: Optional[TreeStore] = None
        self._root = None
        self._other_node = None
        self._sub_nodes = None

    def load_tree_items(self, item_store: TreeStore, root_node):
        # -> Script [main]
        root = item_store.append(root_node, [
            'skytemple-e-ground-symbolic', SCRIPT_SCENES, self, MainController, 0, False, '', True
        ])
        self._root = root

        self._tree_model = item_store

        #    -> Common [common]
        item_store.append(root, [
            'skytemple-e-script-symbolic', SCRIPT_SCRIPTS, self,  SsbController, 0, False, '', True
        ])

        sub_nodes = {
            'S': item_store.append(root, [
                'skytemple-folder-symbolic', _('S - System'), self, FolderController, _('S - System'), False, '', True
            ]),
            'T': item_store.append(root, [
                'skytemple-folder-symbolic', _('T - Town'), self, FolderController, _('T - Town'), False, '', True
            ]),
            'D': item_store.append(root, [
                'skytemple-folder-symbolic', _('D - Dungeon'), self, FolderController, _('D - Dungeon'), False, '', True
            ]),
            'G': item_store.append(root, [
                'skytemple-folder-symbolic', _('G - Guild'), self, FolderController, _('G - Guild'), False, '', True
            ]),
            'H': item_store.append(root, [
                'skytemple-folder-symbolic', _('H - Habitat'), self, FolderController, _('H - Habitat'), False, '', True
            ]),
            'P': item_store.append(root, [
                'skytemple-folder-symbolic', _('P - Places'), self, FolderController, _('P - Places'), False, '', True
            ]),
            'V': item_store.append(root, [
                'skytemple-folder-symbolic', _('V - Visual'), self, FolderController, _('V - Visual'), False, '', True
            ])
        }
        # Other
        other = item_store.append(root, [
            'skytemple-folder-symbolic', _('Others'), self, FolderController, None, False, '', True
        ])
        self._other_node = other
        self._sub_nodes = sub_nodes

        for i, map_obj in enumerate(self.script_engine_file_tree['maps'].values()):
            parent = other
            if map_obj['name'][0] in sub_nodes.keys():
                parent = sub_nodes[map_obj['name'][0]]
            self._map_ssas[map_obj['name']] = {}
            self._map_ssss[map_obj['name']] = {}
            #    -> (Map Name) [map]
            map_root = item_store.append(parent, [
                'skytemple-folder-symbolic', map_obj['name'], self,  MapController, map_obj['name'], False, '', True
            ])
            self._map_scene_root[map_obj['name']] = map_root

            if map_obj['enter_sse'] is not None:
                #          -> Enter [sse]
                self._map_sse[map_obj['name']] = item_store.append(map_root, [
                    'skytemple-e-ground-symbolic', _('Enter (sse)'), self,  SsaController, {
                        'map': map_obj['name'],
                        'file': f"{SCRIPT_DIR}/{map_obj['name']}/{map_obj['enter_sse']}",
                        'type': 'sse',
                        'scripts': map_obj['enter_ssbs'].copy()
                    }, False, '', True
                ])

            #       -> Acting Scripts [lsd]
            acting_root = item_store.append(map_root, [
                'skytemple-folder-open-symbolic', _('Acting (ssa)'), self,  LsdController, map_obj['name'], False, '', True
            ])
            self._acting_roots[map_obj['name']] = acting_root
            for ssa, ssb in map_obj['ssas']:
                stem = ssa[:-len(SSA_EXT)]
                #             -> Scene [ssa]
                filename = f"{SCRIPT_DIR}/{map_obj['name']}/{ssa}"
                self._map_ssas[map_obj['name']][filename] = item_store.append(acting_root, [
                    'skytemple-e-ground-symbolic', stem,
                    self, SsaController, {
                        'map': map_obj['name'],
                        'file': filename,
                        'type': 'ssa',
                        'scripts': [ssb]
                    }, False, '', True
                ])

            #       -> Sub Scripts [sub]
            sub_root = item_store.append(map_root, [
                'skytemple-folder-open-symbolic', _('Sub (sss)'), self,  SubController, map_obj['name'], False, '', True
            ])
            self._sub_roots[map_obj['name']] = sub_root
            for sss, ssbs in map_obj['subscripts'].items():
                stem = sss[:-len(SSS_EXT)]
                #             -> Scene [sss]
                filename = f"{SCRIPT_DIR}/{map_obj['name']}/{sss}"
                self._map_ssss[map_obj['name']][filename] = item_store.append(sub_root, [
                    'skytemple-e-ground-symbolic', stem,
                    self, SsaController, {
                        'map': map_obj['name'],
                        'file': filename,
                        'type': 'sss',
                        'scripts': ssbs.copy()
                    }, False, '', True
                ])

        recursive_generate_item_store_row_label(self._tree_model[root])

    def handle_request(self, request: OpenRequest) -> Optional[Gtk.TreeIter]:
        if request.type == REQUEST_TYPE_SCENE:
            # if we have an enter scene, open it directly.
            if request.identifier in self._map_sse:
                return self._map_sse[request.identifier]
            # otherwise show scene landing page
            if request.identifier in self._map_scene_root.keys():
                return self._map_scene_root[request.identifier]
        if request.type == REQUEST_TYPE_SCENE_SSE:
            if request.identifier in self._map_sse:
                return self._map_sse[request.identifier]
        if request.type == REQUEST_TYPE_SCENE_SSA:
            if request.identifier[0] in self._map_ssas:
                for it in self._map_ssas[request.identifier[0]].values():
                    # Check if the filename of the tree iter entry (see load_tree_items) matches the request filename.
                    file_name = self._tree_model[it][4]['file'].split('/')[-1]
                    if file_name == request.identifier[1]:
                        return it
        if request.type == REQUEST_TYPE_SCENE_SSS:
            if request.identifier[0] in self._map_ssss:
                for it in self._map_ssss[request.identifier[0]].values():
                    # Check if the filename of the tree iter entry (see load_tree_items) matches the request filename.
                    file_name = self._tree_model[it][4]['file'].split('/')[-1]
                    if file_name == request.identifier[1]:
                        return it
        return None

    def get_ssa(self, filename):
        return self.project.open_file_in_rom(filename, FileType.SSA,
                                             scriptdata=self.project.get_rom_module().get_static_data().script_data)

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

    def mark_as_modified(self, mapname, type, filename):
        """Mark a specific scene as modified"""
        self.project.mark_as_modified(filename)

        treeiter = None
        if type == 'ssa':
            if mapname in self._map_ssas and filename in self._map_ssas[mapname]:
                treeiter = self._map_ssas[mapname][filename]
        elif type == 'sss':
            if mapname in self._map_ssss and filename in self._map_ssss[mapname]:
                treeiter = self._map_ssss[mapname][filename]
        elif type == 'sse':
            if mapname in self._map_sse:
                treeiter = self._map_sse[mapname]

        # Mark as modified in tree
        if treeiter is not None:
            row = self._tree_model[treeiter]
            if row is not None:
                recursive_up_item_store_mark_as_modified(row)

    def get_sprite_provider(self) -> SpriteProvider:
        return self.project.get_sprite_provider()

    def get_pos_mark_editor_controller(self, parent_window: Gtk.Window, mapname: str,
                                       scene_name: str, scene_type: str,
                                       pos_marks: List[SourceMapPositionMark],
                                       pos_mark_to_edit: int) -> PosMarkEditorController:
        if mapname not in self.project.get_rom_module().get_static_data().script_data.level_list__by_name:
            raise ValueError(_("Map not found."))
        return PosMarkEditorController(
            self.get_ssa(f'{SCRIPT_DIR}/{mapname}/{scene_name[:-4]}.{scene_type}'), parent_window,
            self.get_sprite_provider(),
            self.project.get_rom_module().get_static_data().script_data.level_list__by_name[mapname],
            self.project.get_module('map_bg'),
            self,
            pos_marks, pos_mark_to_edit
        )

    def has_level_list(self):
        return self.project.file_exists(LEVEL_LIST)

    def get_level_list(self) -> LevelListBin:
        return self.project.open_sir0_file_in_rom(LEVEL_LIST, LevelListBin)

    def mark_level_list_as_modified(self):
        self.project.mark_as_modified(LEVEL_LIST)
        recursive_up_item_store_mark_as_modified(self._tree_model[self._root])

    def get_bg_level_list(self) -> BgList:
        return self.project.open_file_in_rom('MAP_BG/bg_list.dat', FileType.BG_LIST_DAT)

    def get_map_display_name(self, nameid):
        sp = self.project.get_string_provider()
        if nameid == 0:
            return sp.get_value(StringType.GROUND_MAP_NAMES, 0), sp.get_index(StringType.GROUND_MAP_NAMES, 0)
        if nameid < 181:
            return sp.get_value(StringType.DUNGEON_NAMES_SELECTION, nameid - 1), sp.get_index(StringType.DUNGEON_NAMES_SELECTION, nameid - 1)
        return sp.get_value(StringType.GROUND_MAP_NAMES, nameid - 182), sp.get_index(StringType.GROUND_MAP_NAMES, nameid - 182)

    def get_dungeon_tilesets(self) -> List[GroundTilesetMapping]:
        config = self.project.get_rom_module().get_static_data()
        ov11 = self.project.get_binary(BinaryName.OVERLAY_11)
        return HardcodedGroundDungeonTilesets.get_ground_dungeon_tilesets(ov11, config)

    def save_dungeon_tilesets(self, value: List[GroundTilesetMapping]):
        config = self.project.get_rom_module().get_static_data()
        self.project.modify_binary(
            BinaryName.OVERLAY_11, lambda binary: HardcodedGroundDungeonTilesets.set_ground_dungeon_tilesets(
                value, binary, config
            )
        )
        recursive_up_item_store_mark_as_modified(self._tree_model[self._root])

    def create_new_level(self, new_name):
        parent = self._other_node
        if new_name[0] in self._sub_nodes.keys():
            parent = self._sub_nodes[new_name[0]]
        self._map_ssas[new_name] = {}
        self._map_ssss[new_name] = {}
        map_root = self._tree_model.append(parent, [
            'skytemple-folder-symbolic', new_name, self,  MapController, new_name, False, '', True
        ])
        self._map_scene_root[new_name] = map_root
        ar = self._tree_model.append(map_root, [
            'skytemple-folder-open-symbolic', _('Acting (ssa)'), self,  LsdController, new_name, False, '', True
        ])
        self._acting_roots[new_name] = ar
        sr = self._tree_model.append(map_root, [
            'skytemple-folder-open-symbolic', _('Sub (sss)'), self,  SubController, new_name, False, '', True
        ])
        self._sub_roots[new_name] = sr
        recursive_generate_item_store_row_label(self._tree_model[parent])

    def get_subnodes(self, name):
        enter = None
        acting = None
        sub = None
        child = self._tree_model.iter_children(self._map_scene_root[name])
        while child is not None:
            controller = self._tree_model[child][3]
            data = self._tree_model[child][4]
            if controller == SsaController and isinstance(data, dict) and 'type' in data and data['type'] == 'sse':
                enter = child
            elif controller == LsdController:
                acting = child
            elif controller == SubController:
                sub = child

            nxt = self._tree_model.iter_next(child)
            child = nxt

        return enter, acting, sub

    def add_scene_enter(self, level_name):
        scene_name = 'enter'
        file_name, ssb_file_name = self._create_scene_file(level_name, scene_name, 'sse', matching_ssb='00')
        self._map_sse[level_name] = self._tree_model.append(self._map_scene_root[level_name], [
            'skytemple-e-ground-symbolic', _('Enter (sse)'), self, SsaController, {
                'map': level_name,
                'file': file_name,
                'type': 'sse',
                'scripts': [ssb_file_name.split('/')[-1]]
            }, False, '', True
        ])
        recursive_generate_item_store_row_label(self._tree_model[self._map_sse[level_name]])
        self.mark_as_modified(level_name, 'sse', file_name)

    def add_scene_acting(self, level_name, scene_name):
        file_name, ssb_file_name = self._create_scene_file(level_name, scene_name, 'ssa', matching_ssb='')
        lsd_path = f'{SCRIPT_DIR}/{level_name}/{level_name.lower()}{LSD_EXT}'
        if not self.project.file_exists(lsd_path):
            self.project.create_new_file(lsd_path, FileType.LSD.new(), FileType.LSD)
        lsd: Lsd = self.project.open_file_in_rom(lsd_path, FileType.LSD)
        lsd.entries.append(scene_name)
        self._map_ssas[level_name][file_name] = self._tree_model.append(self._acting_roots[level_name], [
            'skytemple-e-ground-symbolic', scene_name,
            self, SsaController, {
                'map': level_name,
                'file': file_name,
                'type': 'ssa',
                'scripts': [ssb_file_name.split('/')[-1]]
            }, False, '', True
        ])
        recursive_generate_item_store_row_label(self._tree_model[self._map_ssas[level_name][file_name]])
        self.mark_as_modified(level_name, 'ssa', file_name)

    def add_scene_sub(self, level_name, scene_name):
        file_name, ssb_file_name = self._create_scene_file(level_name, scene_name, 'sss', matching_ssb='00')
        self._map_ssss[level_name][file_name] = self._tree_model.append(self._sub_roots[level_name], [
            'skytemple-e-ground-symbolic', scene_name,
            self, SsaController, {
                'map': level_name,
                'file': file_name,
                'type': 'sss',
                'scripts': [ssb_file_name.split('/')[-1]]
            }, False, '', True
        ])
        recursive_generate_item_store_row_label(self._tree_model[self._map_ssss[level_name][file_name]])
        self.mark_as_modified(level_name, 'sss', file_name)

    def _get_empty_scene(self) -> Ssa:
        with open(os.path.join(data_dir(), 'empty.ssx'), 'rb') as f:
            return FileType.SSA.deserialize(f.read())

    def _create_scene_file(self, level_name, scene_name, ext, matching_ssb=None):
        dir_name = f"{SCRIPT_DIR}/{level_name}"
        if '.' in scene_name:
            raise ValueError(_("The file name provided must not have a file extension."))
        if len(scene_name) > 8:
            raise ValueError(_("The file name provided is too long (max 8 characters)."))
        ssx_name = f"{dir_name}/{scene_name}.{ext}"

        self.project.ensure_dir(dir_name)
        self.project.create_new_file(ssx_name, self._get_empty_scene(), FileType.SSA)

        if matching_ssb is not None:
            ssb_name = f"{dir_name}/{scene_name}{matching_ssb}.ssb"

            save_kwargs = {
                'filename': ssb_name,
                'static_data': self.project.get_rom_module().get_static_data(),
                'project_fm': self.project.get_project_file_manager()
            }
            self.project.create_new_file(
                ssb_name, SsbLoadedFileHandler.create(**save_kwargs), SsbLoadedFileHandler, **save_kwargs
            )
            # Update debugger
            SkyTempleMainController.debugger_manager().on_script_added(
                ssb_name, level_name, ext, f'{scene_name}.{ext}'
            )
            return ssx_name, ssb_name
        else:
            return ssx_name, None

    def get_mapping_dungeon_assets(
            self
    ) -> Tuple[List[GroundTilesetMapping], MappaBin, FixedBin, ModelContext[DungeonBinPack], List[DungeonDefinition]]:
        static_data = self.project.get_rom_module().get_static_data()
        mappings = self.get_dungeon_tilesets()

        mappa = self.project.open_file_in_rom('BALANCE/mappa_s.bin', FileType.MAPPA_BIN)
        fixed = self.project.open_file_in_rom(
            'BALANCE/fixed.bin', FileType.FIXED_BIN,
            static_data=static_data
        )

        dungeon_bin_context: ModelContext[DungeonBinPack] = self.project.open_file_in_rom(
            'DUNGEON/dungeon.bin', FileType.DUNGEON_BIN, static_data=static_data, threadsafe=True
        )

        dungeon_list = HardcodedDungeons.get_dungeon_list(
            self.project.get_binary(BinaryName.ARM9), static_data
        )

        return mappings, mappa, fixed, dungeon_bin_context, dungeon_list
