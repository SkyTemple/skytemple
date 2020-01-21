"""Manages the state and files of the currently open ROM"""
from typing import Union, Iterator

from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple.core.task import AsyncTaskRunner
from skytemple.core.ui_signals import SIGNAL_OPENED, SIGNAL_OPENED_ERROR
from skytemple_files.common.types.data_handler import DataHandler, T


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
        self._rom = None
        self._loaded_modules = {}
        # Dict of filenames -> models
        self._opened_files = {}

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
        return self._opened_files[file_path_in_rom]
