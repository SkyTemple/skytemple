"""Manages the state and files of the currently open ROM"""
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
import logging
from typing import Union, Iterator, TYPE_CHECKING, Optional, Dict, Callable

from gi.repository import GLib, Gtk
from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple.core.open_request import OpenRequest
from skytemple.core.model_context import ModelContext
from skytemple.core.sprite_provider import SpriteProvider
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.common.types.data_handler import DataHandler, T
from skytemple_files.common.util import get_files_from_rom_with_extension, get_rom_folder, create_file_in_rom, \
    get_ppmdu_config_for_rom

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skytemple.controller.main import MainController
    from skytemple.module.rom.module import RomModule


try:
    from contextlib import nullcontext
except ImportError:  # < Python 3.7
    from contextlib import contextmanager
    @contextmanager
    def nullcontext(enter_result=None):
        yield enter_result


class RomProject:
    _current: 'RomProject' = None

    @classmethod
    def get_current(cls) -> Union['RomProject', None]:
        """Returns the currently open RomProject or None"""
        return cls._current

    @classmethod
    def open(cls, filename, main_controller: Optional['MainController'] = None):
        """
        Open a file (in a new thread).
        If the main controller is set, it will be informed about this.
        """
        AsyncTaskRunner().instance().run_task(cls._open_impl(filename, main_controller))

    @classmethod
    async def _open_impl(cls, filename, main_controller: Optional['MainController']):
        cls._current = RomProject(filename, main_controller.load_view_main_list)
        try:
            cls._current.load()
            if main_controller:
                GLib.idle_add(lambda: main_controller.on_file_opened())
        except BaseException as ex:
            cls._current = None
            if main_controller:
                GLib.idle_add(lambda ex=ex: main_controller.on_file_opened_error(ex))

    def __init__(self, filename: str, cb_open_view: Callable[[Gtk.TreeIter], None]):
        self.filename = filename
        self._rom: NintendoDSRom = None
        self._rom_module: Optional['RomModule'] = None
        self._loaded_modules: Dict[str, AbstractModule] = {}
        self._sprite_renderer: Optional[SpriteProvider] = None
        # Dict of filenames -> models
        self._opened_files = {}
        self._opened_files_contexts = {}
        # List of filenames that were requested to be opened threadsafe.
        self._files_threadsafe = []
        self._files_unsafe = []
        # Dict of filenames -> file handler object
        self._file_handlers = {}
        # List of modified filenames
        self._modified_files = []
        # Callback for opening views using iterators from the main view list.
        self._cb_open_view: Callable[[Gtk.TreeIter], None] = cb_open_view

    def load(self):
        """Load the ROM into memory and initialize all modules"""
        self._rom = NintendoDSRom.fromFile(self.filename)
        self._loaded_modules = {}
        for name, module in Modules.all().items():
            if name == 'rom':
                self._rom_module = module(self)
            else:
                self._loaded_modules[name] = module(self)

        self._sprite_renderer = SpriteProvider(self)

    def get_rom_module(self) -> 'RomModule':
        return self._rom_module

    def get_modules(self, include_rom_module=True) -> Iterator[AbstractModule]:
        """Iterate over loaded modules"""
        if include_rom_module:
            return iter(list(self._loaded_modules.values()) + [self._rom_module])
        return iter(self._loaded_modules.values())

    def get_module(self, name):
        return self._loaded_modules[name]

    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: DataHandler[T],
                         threadsafe=False) -> Union[T, ModelContext[T]]:
        """
        Open a file. If already open, the opened object is returned.
        The second parameter is a file handler to use. Please note, that the file handler is only
        used if the file is not already open.

        The value of ``threadsafe`` must be the same for all requests to the file. If one request to open a
        file used the value False but another True or vice-versa, this will raise a ValueError.

        If ``threadsafe`` is True, instead of returning the model, a ModelContext[T] is returned.
        """
        if file_path_in_rom not in self._opened_files:
            bin = self._rom.getFileByName(file_path_in_rom)
            self._opened_files[file_path_in_rom] = file_handler_class.deserialize(bin)
            self._file_handlers[file_path_in_rom] = file_handler_class
        if threadsafe:
            if file_path_in_rom in self._files_unsafe:
                raise ValueError(
                    f"Tried to open {file_path_in_rom} threadsafe, but it was requested unsafe somewhere else."
                )
            if file_path_in_rom not in self._opened_files_contexts:
                self._opened_files_contexts[file_path_in_rom] = ModelContext(self._opened_files[file_path_in_rom])
            return self._opened_files_contexts[file_path_in_rom]
        elif file_path_in_rom in self._files_threadsafe:
            raise ValueError(f"Tried to open {file_path_in_rom} unsafe, but it was requested threadsafe somewhere else.")
        return self._opened_files[file_path_in_rom]

    def mark_as_modified(self, file: Union[str, object]):
        """Mark a file as modified, either by filename or model. TODO: Input checking"""
        if isinstance(file, str):
            assert file in self._opened_files
            if file not in self._modified_files:
                self._modified_files.append(file)
        else:
            filename = list(self._opened_files.keys())[list(self._opened_files.values()).index(file)]
            self._modified_files.append(filename)
            if file not in self._modified_files:
                self._modified_files.append(file)

    def has_modifications(self):
        return len(self._modified_files) > 0

    def save(self, main_controller: Optional['MainController']):
        """Save the rom. The main controller will be informed about this, if given."""
        AsyncTaskRunner().instance().run_task(self._save_impl(main_controller))

    async def _save_impl(self, main_controller: Optional['MainController']):
        try:
            for name in self._modified_files:
                context = self._opened_files_contexts[name] \
                    if name in self._opened_files_contexts \
                    else nullcontext(self._opened_files[name])
                with context as model:
                    handler = self._file_handlers[name]
                    logger.debug(f"Saving {name} in ROM. Model: {model}, Handler: {handler}")
                    binary_data = handler.serialize(model)
                    self._rom.setFileByName(name, binary_data)
            self._modified_files = []
            logger.debug(f"Saving ROM to {self.filename}")
            self._rom.saveToFile(self.filename)
            if main_controller:
                GLib.idle_add(lambda: main_controller.on_file_saved())

        except Exception as err:
            if main_controller:
                GLib.idle_add(lambda err=err: main_controller.on_file_saved_error(err))

    def get_files_with_ext(self, ext):
        return get_files_from_rom_with_extension(self._rom, ext)

    def get_rom_folder(self, path):
        return get_rom_folder(self._rom, path)

    def create_new_file(self, filename, model, file_handler_class: DataHandler[T]):
        """Creates a new file in the ROM and fills it with the model content provided and
        writes the serialized model data there"""
        copy_bin = file_handler_class.serialize(model)
        create_file_in_rom(self._rom, filename, copy_bin)
        self._opened_files[filename] = file_handler_class.deserialize(copy_bin)
        self._file_handlers[filename] = file_handler_class
        return copy_bin

    def file_exists(self, filename):
        return self._rom.filenames.idOf(filename) is not None

    def load_rom_data(self):
        return get_ppmdu_config_for_rom(self._rom)

    def request_open(self, request: OpenRequest, raise_exception=False):
        """
        Handle a request to open a resource in the editor. If the resource was not found, nothing happens,
        unless raise_exception is true, in which case a ValueError is raised.
        """
        for module in self._loaded_modules.values():
            result = module.handle_request(request)
            if result is not None:
                self._cb_open_view(result)
                return
        if raise_exception:
            raise ValueError("No handler for request.")

    def get_sprite_provider(self) -> SpriteProvider:
        return self._sprite_renderer
