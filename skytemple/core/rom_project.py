"""Manages the state and files of the currently open ROM"""
import logging
from typing import Union, Iterator

from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple.core.task import AsyncTaskRunner
from skytemple.core.ui_signals import SIGNAL_OPENED, SIGNAL_OPENED_ERROR, SIGNAL_SAVED_ERROR, SIGNAL_SAVED
from skytemple_files.common.types.data_handler import DataHandler, T
from skytemple_files.common.types.file_types import FileType

logger = logging.getLogger(__name__)


class RomProject:
    _current: 'RomProject' = None

    @classmethod
    def get_current(cls) -> Union['RomProject', None]:
        """Returns the currently open RomProject or None"""
        return cls._current

    @classmethod
    def open(cls, filename, gobject=None):
        """
        Open a file (in a new thread).
        If a gobject is passed: the signal from const SIGNAL_OPENED will be emitted on it when done.
        """
        AsyncTaskRunner().instance().run_task(cls._open_impl(filename, gobject))

    @classmethod
    async def _open_impl(cls, filename, go):
        cls._current = RomProject(filename)
        try:
            cls._current.load()
            if go:
                AsyncTaskRunner.emit(go, SIGNAL_OPENED)
        except BaseException as ex:
            cls._current = None
            if go:
                AsyncTaskRunner.emit(go, SIGNAL_OPENED_ERROR, ex)

    def __init__(self, filename: str):
        self.filename = filename
        self._rom: NintendoDSRom = None
        self._loaded_modules = {}
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
            self._loaded_modules[name] = module(self)
        # TODO: Check ROM module if ROM is actually supported!

    def modules(self) -> Iterator[AbstractModule]:
        """Iterate over loaded modules"""
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

    def save(self, go):
        """Save the rom. The signal SIGNAL_SAVED/SIGNAL_SAVED_ERROR will be emitted on go if done."""
        AsyncTaskRunner().instance().run_task(self._save_impl(go))

    async def _save_impl(self, go):
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
            if go:
                AsyncTaskRunner.emit(go, SIGNAL_SAVED)

        except Exception as err:
            if go:
                AsyncTaskRunner.emit(go, SIGNAL_SAVED_ERROR, err)
