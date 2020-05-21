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
from typing import Union, Iterator, TYPE_CHECKING, Optional, Dict

from gi.repository import GLib
from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.common.types.data_handler import DataHandler, T
from skytemple_files.common.util import get_files_from_rom_with_extension, get_rom_folder, create_file_in_rom

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skytemple.controller.main import MainController


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
        cls._current = RomProject(filename)
        try:
            cls._current.load()
            if main_controller:
                GLib.idle_add(lambda: main_controller.on_file_opened())
        except BaseException as ex:
            cls._current = None
            if main_controller:
                GLib.idle_add(lambda ex=ex: main_controller.on_file_opened_error(ex))

    def __init__(self, filename: str):
        self.filename = filename
        self._rom: NintendoDSRom = None
        self._rom_module: Optional[AbstractModule] = None
        self._loaded_modules: Dict[str, AbstractModule] = {}
        # Dict of filenames -> models
        self._opened_files = {}
        # Dict of filenames -> file handler object
        self._file_handlers = {}
        # List of modified filenames
        self._modified_files = []

    def load(self):
        """Load the ROM into memory and initialize all modules"""
        self._rom = NintendoDSRom.fromFile(self.filename)
        self._loaded_modules = {}
        for name, module in Modules.all().items():
            if name == 'rom':
                self._rom_module = module(self)
            else:
                self._loaded_modules[name] = module(self)
        # TODO: Check ROM module if ROM is actually supported!

    def get_rom_module(self):
        return self._rom_module

    def get_modules(self, include_rom_module=True) -> Iterator[AbstractModule]:
        """Iterate over loaded modules"""
        if include_rom_module:
            return iter(list(self._loaded_modules.values()) + [self._rom_module])
        return iter(self._loaded_modules.values())

    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: DataHandler[T]) -> T:
        """
        Open a file. If already open, the opened object is returned.
        The second parameter is a file handler to use. Please note, that the file handler is only
        used if the file is not already open.
        """
        if file_path_in_rom not in self._opened_files:
            bin = self._rom.getFileByName(file_path_in_rom)
            self._opened_files[file_path_in_rom] = file_handler_class.deserialize(bin)
            self._file_handlers[file_path_in_rom] = file_handler_class
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
                model = self._opened_files[name]
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
