"""Manages the state and files of the currently open ROM"""
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
import logging
import sys
from enum import Enum, auto
from typing import Union, Iterator, TYPE_CHECKING, Optional, Dict, Callable, Type, Tuple

from gi.repository import GLib, Gtk
from ndspy.rom import NintendoDSRom

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple.core.open_request import OpenRequest
from skytemple.core.model_context import ModelContext
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.core.string_provider import StringProvider
from skytemple_files.common.ppmdu_config.data import Pmd2Binary
from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.common.types.data_handler import DataHandler, T
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import get_files_from_rom_with_extension, get_rom_folder, create_file_in_rom, \
    get_ppmdu_config_for_rom, get_binary_from_rom_ppmdu, set_binary_in_rom_ppmdu, get_files_from_folder_with_extension
from skytemple_files.container.sir0.sir0_serializable import Sir0Serializable
from skytemple_files.patch.patches import Patcher
from skytemple_files.compression_container.common_at.handler import CommonAtType

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


class BinaryName(Enum):
    """This enum maps to binary names of the pmd2data.xml."""
    ARM9 = auto(), 'arm9.bin'
    OVERLAY_10 = auto(), 'overlay/overlay_0010.bin'
    OVERLAY_11 = auto(), 'overlay/overlay_0011.bin'
    OVERLAY_13 = auto(), 'overlay/overlay_0013.bin'
    OVERLAY_29 = auto(), 'overlay/overlay_0029.bin'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, xml_name: str = None):
        self._xml_name_ = xml_name

    def __str__(self):
        return self._xml_name_

    def __repr__(self):
        return f'BinaryName.{self.name}'

    @property
    def xml_name(self):
        return self._xml_name_


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
            exc_info = sys.exc_info()
            cls._current = None
            if main_controller:
                GLib.idle_add(lambda ex=ex: main_controller.on_file_opened_error(exc_info, ex))

    def __init__(self, filename: str, cb_open_view: Callable[[Gtk.TreeIter], None]):
        self.filename = filename
        self._rom: NintendoDSRom = None
        self._rom_module: Optional['RomModule'] = None
        self._loaded_modules: Dict[str, AbstractModule] = {}
        self._sprite_renderer: Optional[SpriteProvider] = None
        self._string_provider: Optional[StringProvider] = None
        # Dict of filenames -> models
        self._opened_files = {}
        self._opened_files_contexts = {}
        # List of filenames that were requested to be opened threadsafe.
        self._files_threadsafe = []
        self._files_unsafe = []
        # Dict of filenames -> file handler object
        self._file_handlers = {}
        self._file_handler_kwargs = {}
        # List of modified filenames
        self._modified_files = []
        self._forced_modified = False
        # Callback for opening views using iterators from the main view list.
        self._cb_open_view: Callable[[Gtk.TreeIter], None] = cb_open_view
        self._project_fm = ProjectFileManager(filename)

    def load(self):
        """Load the ROM into memory and initialize all modules"""
        self._rom = NintendoDSRom.fromFile(self.filename)
        self._loaded_modules = {}
        for name, module in Modules.all().items():
            logger.debug(f"Loading module {name} for ROM...")
            if name == 'rom':
                self._rom_module = module(self)
            else:
                self._loaded_modules[name] = module(self)

        self._sprite_renderer = SpriteProvider(self)
        self._string_provider = StringProvider(self)

    def get_rom_module(self) -> 'RomModule':
        return self._rom_module

    def get_project_file_manager(self):
        return self._project_fm

    def get_modules(self, include_rom_module=True) -> Iterator[AbstractModule]:
        """Iterate over loaded modules"""
        if include_rom_module:
            return iter(list(self._loaded_modules.values()) + [self._rom_module])
        return iter(self._loaded_modules.values())

    def get_module(self, name):
        return self._loaded_modules[name]

    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: Type[DataHandler[T]],
                         threadsafe=False, **kwargs) -> Union[T, ModelContext[T]]:
        """
        Open a file. If already open, the opened object is returned.
        The second parameter is a file handler to use. Please note, that the file handler is only
        used if the file is not already open.

        The value of ``threadsafe`` must be the same for all requests to the file. If one request to open a
        file used the value False but another True or vice-versa, this will raise a ValueError.

        If ``threadsafe`` is True, instead of returning the model, a ModelContext[T] is returned.

        Additional keyword arguments are passed to the handler (if the model isn't already loaded!!)
        The keyword arguments will also be used for serializing again.
        """
        if file_path_in_rom not in self._opened_files:
            bin = self._rom.getFileByName(file_path_in_rom)
            self._opened_files[file_path_in_rom] = file_handler_class.deserialize(bin, **kwargs)
            self._file_handlers[file_path_in_rom] = file_handler_class
            self._file_handler_kwargs[file_path_in_rom] = kwargs
        return self._open_common(file_path_in_rom, threadsafe)

    def open_sir0_file_in_rom(self, file_path_in_rom: str, sir0_serializable_type: Type[Sir0Serializable],
                              threadsafe=False):
        """
        Open a SIR0 wrapped file. If already open, the opened object is returned.
        The second parameter is the type of a Sir0Serializable to use.
        Please note, that this is only used if the file is not already open.

        The value of ``threadsafe`` must be the same for all requests to the file. If one request to open a
        file used the value False but another True or vice-versa, this will raise a ValueError.

        If ``threadsafe`` is True, instead of returning the model, a ModelContext[T] is returned.
        """
        if file_path_in_rom not in self._opened_files:
            bin = self._rom.getFileByName(file_path_in_rom)
            sir0 = FileType.SIR0.deserialize(bin)
            self._opened_files[file_path_in_rom] = FileType.SIR0.unwrap_obj(sir0, sir0_serializable_type)
            self._file_handlers[file_path_in_rom] = FileType.SIR0
            self._file_handler_kwargs[file_path_in_rom] = {}
        return self._open_common(file_path_in_rom, threadsafe)

    def _open_common(self, file_path_in_rom: str, threadsafe):
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

    def is_opened(self, filename):
        return filename in self._opened_files

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

    def force_mark_as_modified(self):
        self._forced_modified = True

    def has_modifications(self):
        return len(self._modified_files) > 0 or self._forced_modified

    def save(self, main_controller: Optional['MainController']):
        """Save the rom. The main controller will be informed about this, if given."""
        AsyncTaskRunner().instance().run_task(self._save_impl(main_controller))

    def open_file_manually(self, filename: str):
        """Returns the raw bytes of a file. GENERALLY NOT RECOMMENDED."""
        return self._rom.getFileByName(filename)

    def save_file_manually(self, filename: str, data: bytes):
        """
        Manually save a file in the ROM. This should generally not be used,
        please use a combination of open_file_in_rom and mark_as_modified instead. This should only be used
        for re-generated files which are otherwise not read by SkyTemple (only saved), such as the mappa_gs.bin file.
        THIS INVALIDATES THE CURRENTLY LOADED FILE (via open_file_in_rom; it will return a new model now).
        """
        if filename in self._opened_files:
            del self._opened_files[filename]
        if filename in self._opened_files_contexts:
            del self._opened_files_contexts[filename]
        self._rom.setFileByName(filename, data)
        self.force_mark_as_modified()

    async def _save_impl(self, main_controller: Optional['MainController']):
        try:
            for name in self._modified_files:
                self.prepare_save_model(name)
            self._modified_files = []
            self._forced_modified = False
            logger.debug(f"Saving ROM to {self.filename}")
            self.save_as_is()
            if main_controller:
                GLib.idle_add(lambda: main_controller.on_file_saved())

        except Exception as err:
            if main_controller:
                exc_info = sys.exc_info()
                GLib.idle_add(lambda err=err: main_controller.on_file_saved_error(exc_info, err))

    def prepare_save_model(self, name, assert_that=None):
        """
        Write the binary model for this type to the ROM object in memory.
        If assert_that is given, it is asserted, that the model matches the one on record.
        """
        context = self._opened_files_contexts[name] \
            if name in self._opened_files_contexts \
            else nullcontext(self._opened_files[name])
        with context as model:
            handler = self._file_handlers[name]
            logger.debug(f"Saving {name} in ROM. Model: {model}, Handler: {handler}")
            if handler == FileType.SIR0:
                logger.debug(f"> Saving as Sir0 wrapped data.")
                model = handler.wrap_obj(model)
            if assert_that is not None:
                assert assert_that is model, "The model that is being saved must match!"
            binary_data = handler.serialize(model, **self._file_handler_kwargs[name])
            self._rom.setFileByName(name, binary_data)

    def save_as_is(self):
        """Simply save the current ROM to disk."""
        self._rom.saveToFile(self.filename)

    def get_files_with_ext(self, ext, folder_name: Optional[str] = None):
        if folder_name is None:
            return get_files_from_rom_with_extension(self._rom, ext)
        else:
            return get_files_from_folder_with_extension(self._rom.filenames.subfolder(folder_name), ext)

    def get_rom_folder(self, path):
        return get_rom_folder(self._rom, path)

    def file_exists(self, path):
        """Check if a file exists"""
        return path in self._rom.filenames

    def create_new_file(self, new_filename, model, file_handler_class: Type[DataHandler[T]], **kwargs):
        """Creates a new file in the ROM and fills it with the model content provided and
        writes the serialized model data there"""
        copy_bin = file_handler_class.serialize(model, **kwargs)
        create_file_in_rom(self._rom, new_filename, copy_bin)
        self._opened_files[new_filename] = file_handler_class.deserialize(copy_bin, **kwargs)
        self._file_handlers[new_filename] = file_handler_class
        self._file_handler_kwargs[new_filename] = kwargs
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

    def get_string_provider(self) -> StringProvider:
        return self._string_provider

    def create_patcher(self):
        return Patcher(self._rom, self.get_rom_module().get_static_data())

    def get_binary(self, binary: Union[Pmd2Binary, BinaryName, str]) -> bytes:
        if not isinstance(binary, Pmd2Binary):
            binary = self.get_rom_module().get_static_data().binaries[str(binary)]
        return get_binary_from_rom_ppmdu(self._rom, binary)

    def modify_binary(self, binary: Union[Pmd2Binary, BinaryName, str], modify_cb: Callable[[bytearray], None]):
        """Modify one of the binaries (such as arm9 or overlay) and save it to the ROM"""
        if not isinstance(binary, Pmd2Binary):
            binary = self.get_rom_module().get_static_data().binaries[str(binary)]
        data = bytearray(self.get_binary(binary))
        modify_cb(data)
        set_binary_in_rom_ppmdu(self._rom, binary, data)
        self.force_mark_as_modified()

    def init_patch_properties(self):
        """ Initialize patch-specific properties of the rom. """
        patcher = self.create_patcher()
        
        # Allow ATUPX files if the ProvideATUPXSupport patch is applied
        try:
            if patcher.is_applied("ProvideATUPXSupport"):
                FileType.COMMON_AT.allow(CommonAtType.ATUPX)
            else:
                FileType.COMMON_AT.disallow(CommonAtType.ATUPX)
        except NotImplementedError:
            FileType.COMMON_AT.disallow(CommonAtType.ATUPX)
