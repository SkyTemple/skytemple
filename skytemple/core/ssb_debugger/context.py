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
from threading import Lock
from typing import TYPE_CHECKING, Optional, List, Iterable

from gi.repository import Gtk

from explorerscript.source_map import SourceMapPositionMark
from skytemple.core.error_handler import display_error
from skytemple.core.events.events import EVT_DEBUGGER_SCRIPT_OPEN, EVT_DEBUGGER_SELECTED_STRING_CHANGED
from skytemple.core.events.manager import EventManager
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_SCENE, REQUEST_TYPE_SCENE_SSA, REQUEST_TYPE_SCENE_SSS, \
    REQUEST_TYPE_SCENE_SSE
from skytemple.core.rom_project import RomProject
from skytemple.core.ssb_debugger.ssb_loaded_file_handler import SsbLoadedFileHandler
from skytemple.core.string_provider import StringType
from skytemple.module.script.controller.dialog.pos_mark_editor import PosMarkEditorController
from skytemple_files.common.ppmdu_config.data import Pmd2Data
from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple_files.common.script_util import ScriptFiles, load_script_files, SCRIPT_DIR, SSA_EXT, SSS_EXT, SSB_EXT
from skytemple_files.script.ssb.constants import SsbConstant
from skytemple_ssb_debugger.context.abstract import AbstractDebuggerControlContext, EXPS_KEYWORDS
from skytemple_ssb_debugger.threadsafe import synchronized_now
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple_ssb_debugger.model.ssb_files.file_manager import SsbFileManager
    from skytemple.core.ssb_debugger.manager import DebuggerManager
    from skytemple_ssb_debugger.model.ssb_files.file import SsbLoadedFile
file_load_lock = Lock()
save_lock = Lock()


class SkyTempleMainDebuggerControlContext(AbstractDebuggerControlContext):

    def __init__(self, manager: 'DebuggerManager'):
        self._manager = manager
        self._special_words_cache = None

    def allows_interactive_file_management(self) -> bool:
        return False

    def before_quit(self) -> bool:
        return True

    def on_quit(self):
        self._manager.on_close()

    def on_focus(self):
        EventManager.instance().debugger_window_has_focus()

    def on_blur(self):
        EventManager.instance().debugger_window_lost_focus()

    def on_selected_string_changed(self, string: str):
        EventManager.instance().trigger(EVT_DEBUGGER_SELECTED_STRING_CHANGED, string)

    def show_ssb_script_editor(self) -> bool:
        return False

    def open_rom(self, filename: str):
        return NotImplementedError()

    def get_project_dir(self) -> str:
        return self._project_fm.dir()

    def load_script_files(self) -> ScriptFiles:
        return load_script_files(RomProject.get_current().get_rom_folder(SCRIPT_DIR))

    def is_project_loaded(self) -> bool:
        return RomProject.get_current() is not None

    def get_rom_filename(self) -> str:
        return RomProject.get_current().filename

    def save_rom(self):
        # We only save the current ROM contents!
        RomProject.get_current().save_as_is()

    def get_static_data(self) -> Pmd2Data:
        return RomProject.get_current().get_rom_module().get_static_data()

    def get_project_filemanager(self) -> ProjectFileManager:
        return self._project_fm

    @synchronized_now(file_load_lock)
    def get_ssb(self, filename, ssb_file_manager: 'SsbFileManager') -> 'SsbLoadedFile':
        f: 'SsbLoadedFile' = RomProject.get_current().open_file_in_rom(filename, SsbLoadedFileHandler,
                                                                       filename=filename,
                                                                       static_data=self.get_static_data(),
                                                                       project_fm=self._project_fm)
        f.file_manager = ssb_file_manager
        return f

    def on_script_edit(self, filename):
        EventManager.instance().trigger(EVT_DEBUGGER_SCRIPT_OPEN, filename)

    @synchronized_now(save_lock)
    def save_ssb(self, filename, ssb_model, ssb_file_manager: 'SsbFileManager'):
        project = RomProject.get_current()
        ssb_loaded_file = self.get_ssb(filename, ssb_file_manager)
        ssb_loaded_file.ssb_model = ssb_model
        project.prepare_save_model(filename, assert_that=ssb_loaded_file)
        project.save_as_is()

    def open_scene_editor(self, type_of_scene, path):
        try:
            map_name, filename = path.split('/')[-2:]
            if type_of_scene == 'ssa':
                RomProject.get_current().request_open(OpenRequest(
                    REQUEST_TYPE_SCENE_SSA, (map_name, filename.replace(SSB_EXT, SSA_EXT))
                ), True)
            elif type_of_scene == 'sss':
                RomProject.get_current().request_open(OpenRequest(
                    REQUEST_TYPE_SCENE_SSS, (map_name, filename.replace(SSB_EXT, SSS_EXT))
                ), True)
            elif type_of_scene == 'sse':
                RomProject.get_current().request_open(OpenRequest(
                    REQUEST_TYPE_SCENE_SSE, map_name
                ), True)
            else:
                raise ValueError()
            self._manager.main_window.present()
        except ValueError:
            md = SkyTempleMessageDialog(self._manager.get_window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("A scene for this script was not found."),
                                        title=_("No Scenes Found"))
            md.run()
            md.destroy()

    def open_scene_editor_for_map(self, map_name):
        try:
            RomProject.get_current().request_open(OpenRequest(
                REQUEST_TYPE_SCENE, map_name
            ), True)
            self._manager.main_window.present()
        except ValueError:
            md = SkyTempleMessageDialog(self._manager.get_window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("A scene for this script was not found."),
                                        title=_("No Scenes Found"))
            md.run()
            md.destroy()

    def edit_position_mark(self, mapname: str, scene_name: str, scene_type: str, pos_marks: List[SourceMapPositionMark],
                           pos_mark_to_edit: int) -> bool:
        try:
            cntrl: PosMarkEditorController = RomProject.get_current().get_module('script').get_pos_mark_editor_controller(
                self._manager.get_window(), mapname, scene_name.split('/')[-1], scene_type, pos_marks, pos_mark_to_edit
            )
            return cntrl.run() == Gtk.ResponseType.OK
        except IndexError:
            md = SkyTempleMessageDialog(self._manager.get_window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, f"SkyTemple is missing the 'script' "
                                                            f"module to handle this request.")
            md.run()
            md.destroy()
        except ValueError as err:
            md = SkyTempleMessageDialog(self._manager.get_window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, str(err))
            md.run()
            md.destroy()

    @property
    def _project_fm(self):
        return RomProject.get_current().get_project_file_manager()

    def display_error(self, exc_info, error_message, error_title=None):
        if error_title is None:
            error_title = _('SkyTemple Script Engine Debugger - Error!')
        display_error(exc_info, error_message, error_title, self._manager.get_window())

    def get_special_words(self) -> Iterable[str]:
        def q():
            for x in self._get_special_words_uncached():
                yield from x.split('_')

        if self._special_words_cache is None:
            self._special_words_cache = set(q())
        return self._special_words_cache

    def _get_special_words_uncached(self):
        pro = RomProject.get_current()
        yield from self.get_static_data().script_data.op_codes__by_name.keys()
        yield from (x.name.replace('$', '') for x in SsbConstant.collect_all(self.get_static_data().script_data))
        yield from EXPS_KEYWORDS
        yield from pro.get_string_provider().get_all(StringType.POKEMON_NAMES)

    @staticmethod
    def message_dialog_cls():
        return SkyTempleMessageDialog
