"""Manages the state and files of the currently open ROM"""
#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
import os
import shutil
import sys
from enum import Enum, auto
from typing import Union, Iterator, TYPE_CHECKING, Optional, Dict, Callable, Type, Tuple, Any, List, overload, Literal, \
    cast
from datetime import datetime

from gi.repository import GLib, Gtk
from ndspy.rom import NintendoDSRom
from pmdsky_debug_py.protocol import SectionProtocol

from skytemple.core.item_tree import ItemTreeEntryRef
from skytemple.core.ui_utils import assert_not_none
from skytemple_files.data.sprconf.handler import SPRCONF_FILENAME

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.modules import Modules
from skytemple.core.open_request import OpenRequest
from skytemple.core.model_context import ModelContext
from skytemple.core.sprite_provider import SpriteProvider
from skytemple.core.string_provider import StringProvider, StringType
from skytemple_files.common.project_file_manager import ProjectFileManager
from skytemple.core.async_tasks.delegator import AsyncTaskDelegator
from skytemple_files.common.types.data_handler import DataHandler, T
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.i18n_util import _
from skytemple_files.common.util import get_files_from_rom_with_extension, get_rom_folder, create_file_in_rom, \
    get_ppmdu_config_for_rom, get_files_from_folder_with_extension, \
    folder_in_rom_exists, create_folder_in_rom, get_binary_from_rom, set_binary_in_rom
from skytemple_files.container.sir0.sir0_serializable import Sir0Serializable
from skytemple_files.patch.patches import Patcher
from skytemple_files.compression_container.common_at.handler import CommonAtType
from skytemple_files.hardcoded.icon_banner import IconBanner

logger = logging.getLogger(__name__)
BACKUP_NAME = '.~backup.bin'

if TYPE_CHECKING:
    from skytemple.controller.main import MainController
    from skytemple.module.rom.module import RomModule


from contextlib import nullcontext, AbstractContextManager


class BinaryName(Enum):
    """This enum maps to binary names of SymbolsProtocol."""
    ARM9 = auto(), 'arm9'
    OVERLAY_00 = auto(), 'overlay0'
    OVERLAY_09 = auto(), 'overlay9'
    OVERLAY_10 = auto(), 'overlay10'
    OVERLAY_11 = auto(), 'overlay11'
    OVERLAY_13 = auto(), 'overlay13'
    OVERLAY_29 = auto(), 'overlay29'

    def __new__(cls, *args, **kwargs):
        obj = object.__new__(cls)
        obj._value_ = args[0]
        return obj

    # ignore the first param since it's already set by __new__
    def __init__(self, _: str, xml_name: Optional[str] = None):
        self._xml_name_ = xml_name

    def __str__(self):
        return self._xml_name_

    def __repr__(self):
        return f'BinaryName.{self.name}'

    @property
    def xml_name(self):
        return self._xml_name_


class RomProject:
    _current: Optional['RomProject'] = None

    @classmethod
    def get_current(cls) -> Optional['RomProject']:
        """Returns the currently open RomProject or None"""
        return cls._current

    @classmethod
    def open(cls, filename, main_controller: 'MainController'):
        """
        Open a file (in a new thread).
        If the main controller is set, it will be informed about this.
        """
        # First check for a backup file from last save.
        backup_fn = os.path.join(ProjectFileManager(filename).dir(), BACKUP_NAME)
        if os.path.exists(backup_fn):
            cls.handle_backup_restore(filename, backup_fn, main_controller)

        AsyncTaskDelegator.run_task(cls._open_impl(filename, main_controller))

    @classmethod
    async def _open_impl(cls, filename, main_controller: 'MainController'):
        cls._current = RomProject(filename, main_controller.load_view_main_list)
        try:
            await cls._current.load()
            if main_controller:
                GLib.idle_add(lambda: main_controller.on_file_opened())
        except BaseException as ex:
            exc_info = sys.exc_info()
            cls._current = None
            if main_controller:
                GLib.idle_add(lambda ex=ex: main_controller.on_file_opened_error(exc_info, ex))

    @classmethod
    def handle_backup_restore(cls, rom_fn: str, backup_fn: str, main_controller: 'MainController'):
        dialog: Gtk.MessageDialog = SkyTempleMessageDialog(
            main_controller.window(),
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.WARNING,
            Gtk.ButtonsType.NONE, _("There was a backup file for this ROM found. This indicates that the ROM was corrupted when SkyTemple tried to save it last.")
        )
        as_is: Gtk.Widget = dialog.add_button(_("No, load ROM as-is"), 0)
        as_is.get_style_context().add_class('destructive-action')
        dialog.add_button(_("Yes, load backup"), 1)

        original_rom_text = _("Last modified: {} - Size: {}").format(datetime.fromtimestamp(os.path.getmtime(rom_fn)).isoformat(), os.path.getsize(rom_fn))
        backup_rom_text = _("Last modified: {} - Size: {}").format(datetime.fromtimestamp(os.path.getmtime(backup_fn)).isoformat(), os.path.getsize(backup_fn))

        dialog.format_secondary_text(_(
            "Do you want to restore the backup?\n"
            "If you select 'Yes, load backup', the backup will replace the ROM file and will then be loaded.\n"
            "If you select 'No, load ROM as-is', the backup will be deleted and SkyTemple will attempt to load the (potentially) corrupted ROM file.\n\n"
            "Original ROM: {}\n"
            "Backup ROM: {}").format(original_rom_text, backup_rom_text))
        response = dialog.run()
        dialog.destroy()
        if response == 1:
            os.replace(backup_fn, rom_fn)
        else:
            os.unlink(backup_fn)

    def __init__(self, filename: str, cb_open_view: Callable[[ItemTreeEntryRef], None]):
        self.filename = filename
        self._rom: Optional[NintendoDSRom] = None
        self._rom_module: Optional['RomModule'] = None
        self._loaded_modules: Dict[str, AbstractModule] = {}
        self._sprite_renderer: Optional[SpriteProvider] = None
        self._string_provider: Optional[StringProvider] = None
        # Dict of filenames -> models
        self._opened_files: Dict[str, Any] = {}
        self._opened_files_contexts: Dict[str, ModelContext] = {}
        # List of filenames that were requested to be opened threadsafe.
        self._files_threadsafe: List[str] = []
        self._files_unsafe: List[str] = []
        # Dict of filenames -> file handler object
        self._file_handlers: Dict[str, Type[DataHandler]] = {}
        self._file_handler_kwargs: Dict[str, Dict[str, Any]] = {}
        # List of modified filenames
        self._modified_files: List[str] = []
        self._forced_modified = False
        # Callback for opening views using iterators from the main view list.
        self._cb_open_view: Callable[[ItemTreeEntryRef], None] = cb_open_view
        self._project_fm = ProjectFileManager(filename)

        self._icon_banner: Optional[IconBanner] = None
        
        # Lazy
        self._patcher: Optional[Patcher] = None

    async def load(self):
        """Load the ROM into memory and initialize all modules"""
        self._rom = NintendoDSRom.fromFile(self.filename)
        await AsyncTaskDelegator.buffer()
        self._loaded_modules = {}

        self._rom_module = Modules.get_rom_module()(self)
        self._rom_module.load_rom_data()
        for name, module in Modules.all().items():
            logger.debug(f"Loading module {name} for ROM...")
            if name == 'rom':
                continue
            else:
                self._loaded_modules[name] = module(self)
            await AsyncTaskDelegator.buffer()

        self._sprite_renderer = SpriteProvider(self)
        await AsyncTaskDelegator.buffer()
        self._string_provider = StringProvider(self)
        await AsyncTaskDelegator.buffer()
        self._icon_banner = IconBanner(self._rom)

    def get_rom_module(self) -> 'RomModule':
        assert self._rom_module is not None
        return self._rom_module

    def get_project_file_manager(self):
        return self._project_fm

    def get_modules(self, include_rom_module=True) -> Iterator[AbstractModule]:
        """Iterate over loaded modules"""
        if include_rom_module:
            assert self._rom_module is not None
            return iter(list(self._loaded_modules.values()) + [self._rom_module])
        return iter(self._loaded_modules.values())

    if TYPE_CHECKING:
        from skytemple.module.rom.module import RomModule
        from skytemple.module.bgp.module import BgpModule
        from skytemple.module.tiled_img.module import TiledImgModule
        from skytemple.module.map_bg.module import MapBgModule
        from skytemple.module.script.module import ScriptModule
        from skytemple.module.monster.module import MonsterModule
        from skytemple.module.portrait.module import PortraitModule
        from skytemple.module.patch.module import PatchModule
        from skytemple.module.lists.module import ListsModule
        from skytemple.module.misc_graphics.module import MiscGraphicsModule
        from skytemple.module.dungeon.module import DungeonModule
        from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule
        from skytemple.module.strings.module import StringsModule
        from skytemple.module.gfxcrunch.module import GfxcrunchModule
        from skytemple.module.sprite.module import SpriteModule
        from skytemple.module.moves_items.module import MovesItemsModule
        from skytemple.module.spritecollab.module import SpritecollabModule

    @overload
    def get_module(self, name: Literal['rom']) -> 'RomModule': ...
    @overload
    def get_module(self, name: Literal['bgp']) -> 'BgpModule': ...
    @overload
    def get_module(self, name: Literal['tiled_img']) -> 'TiledImgModule': ...
    @overload
    def get_module(self, name: Literal['map_bg']) -> 'MapBgModule': ...
    @overload
    def get_module(self, name: Literal['script']) -> 'ScriptModule': ...
    @overload
    def get_module(self, name: Literal['gfxcrunch']) -> 'GfxcrunchModule': ...
    @overload
    def get_module(self, name: Literal['sprite']) -> 'SpriteModule': ...
    @overload
    def get_module(self, name: Literal['monster']) -> 'MonsterModule': ...
    @overload
    def get_module(self, name: Literal['portrait']) -> 'PortraitModule': ...
    @overload
    def get_module(self, name: Literal['patch']) -> 'PatchModule': ...
    @overload
    def get_module(self, name: Literal['lists']) -> 'ListsModule': ...
    @overload
    def get_module(self, name: Literal['moves_items']) -> 'MovesItemsModule': ...
    @overload
    def get_module(self, name: Literal['misc_graphics']) -> 'MiscGraphicsModule': ...
    @overload
    def get_module(self, name: Literal['dungeon']) -> 'DungeonModule': ...
    @overload
    def get_module(self, name: Literal['dungeon_graphics']) -> 'DungeonGraphicsModule': ...
    @overload
    def get_module(self, name: Literal['strings']) -> 'StringsModule': ...
    @overload
    def get_module(self, name: Literal['spritecollab']) -> 'SpritecollabModule': ...

    def get_module(self, name: str) -> AbstractModule:
        return self._loaded_modules[name]

    def get_icon_banner(self) -> IconBanner:
        assert self._icon_banner
        return self._icon_banner

    def get_rom_name(self) -> str:
        assert self._rom is not None
        return self._rom.name.decode('ascii')

    def set_rom_name(self, name: str):
        assert self._rom is not None
        self._rom.name = name.encode('ascii')

    def get_id_code(self) -> str:
        assert self._rom is not None
        return self._rom.idCode.decode('ascii')

    def set_id_code(self, id_code: str):
        assert self._rom is not None
        self._rom.idCode = id_code.encode('ascii')

    @overload
    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: Type[DataHandler[T]],
                         threadsafe: Literal[False] = False, **kwargs) -> T:
        ...

    @overload
    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: Type[DataHandler[T]],
                         threadsafe: Literal[True], **kwargs) -> ModelContext[T]:
        ...

    def open_file_in_rom(self, file_path_in_rom: str, file_handler_class: Type[DataHandler[T]],
                         threadsafe=False, **kwargs):
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
            assert self._rom is not None
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
            assert self._rom is not None
            bin = self._rom.getFileByName(file_path_in_rom)
            sir0 = FileType.SIR0.deserialize(bin)
            self._opened_files[file_path_in_rom] = FileType.SIR0.unwrap_obj(sir0, sir0_serializable_type)
            self._file_handlers[file_path_in_rom] = FileType.SIR0
            self._file_handler_kwargs[file_path_in_rom] = {}
        return self._open_common(file_path_in_rom, threadsafe)

    def open_sprconf(self, threadsafe=False):
        """Opens the MONSTER/sprconf.json if it exists, if not it creates it first."""
        if SPRCONF_FILENAME not in self._opened_files:
            assert self._rom is not None
            self._opened_files[SPRCONF_FILENAME] = FileType.SPRCONF.load(self._rom)
            self._file_handlers[SPRCONF_FILENAME] = FileType.SPRCONF
            self._file_handler_kwargs[SPRCONF_FILENAME] = {}
        return self._open_common(SPRCONF_FILENAME, threadsafe)

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
            if filename not in self._modified_files:
                self._modified_files.append(filename)

    def force_mark_as_modified(self):
        self._forced_modified = True

    def has_modifications(self):
        return len(self._modified_files) > 0 or self._forced_modified

    def save(self, main_controller: Optional['MainController']):
        """Save the rom. The main controller will be informed about this, if given."""
        AsyncTaskDelegator.run_task(self._save_impl(main_controller))

    def open_file_manually(self, filename: str):
        """Returns the raw bytes of a file. GENERALLY NOT RECOMMENDED."""
        return assert_not_none(self._rom).getFileByName(filename)

    def save_file_manually(self, filename: str, data: bytes):
        """
        Manually save a file in the ROM. This should generally not be used,
        please use a combination of open_file_in_rom and mark_as_modified instead. This should only be used
        for re-generated files which are otherwise not read by SkyTemple (only saved), such as the mappa_gs.bin file.
        THIS INVALIDATES THE CURRENTLY LOADED FILE (via open_file_in_rom; it will return a new model now).
        """
        assert self._rom is not None
        if filename in self._opened_files:
            del self._opened_files[filename]
        if filename in self._opened_files_contexts:
            del self._opened_files_contexts[filename]
        self._rom.setFileByName(filename, data)
        self.force_mark_as_modified()
        
    def create_file_manually(self, filename: str, data: bytes):
        """
        Manually create a file in the ROM. 
        """
        assert self._rom is not None
        create_file_in_rom(self._rom, filename, data)
        self.force_mark_as_modified()

    async def _save_impl(self, main_controller: Optional['MainController']):
        try:
            for name in self._modified_files:
                self.prepare_save_model(name)
                await AsyncTaskDelegator.buffer()
            self._modified_files = []
            if self._icon_banner:
                self._icon_banner.save_to_rom()
            self._forced_modified = False
            logger.debug(f"Saving ROM to {self.filename}")
            await AsyncTaskDelegator.buffer()
            self.save_as_is()
            await AsyncTaskDelegator.buffer()
            if main_controller:
                GLib.idle_add(lambda: assert_not_none(main_controller).on_file_saved())

        except Exception as err:
            if main_controller:
                exc_info = sys.exc_info()
                GLib.idle_add(lambda err=err: assert_not_none(main_controller).on_file_saved_error(exc_info, err))

    def prepare_save_model(self, name, assert_that=None):
        """
        Write the binary model for this type to the ROM object in memory.
        If assert_that is given, it is asserted, that the model matches the one on record.
        """
        assert self._rom is not None
        context: AbstractContextManager = (
            self._opened_files_contexts[name]
            if name in self._opened_files_contexts
            else nullcontext(self._opened_files[name])
        )
        with context as model:
            handler = self._file_handlers[name]
            logger.debug(f"Saving {name} in ROM. Model: {model}, Handler: {handler}")
            if handler == FileType.SIR0:
                logger.debug(f"> Saving as Sir0 wrapped data.")
                model = FileType.SIR0.wrap_obj(model)
            if assert_that is not None:
                assert assert_that is model, "The model that is being saved must match!"
            binary_data = handler.serialize(model, **self._file_handler_kwargs[name])
            self._rom.setFileByName(name, binary_data)

    def save_as_is(self):
        """Simply save the current ROM to disk."""
        assert self._rom is not None
        # First copy current ROM to a temp file.
        backup_fn = os.path.join(self.get_project_file_manager().dir(), BACKUP_NAME)
        # When doing "Save As..." the file may not exist yet.
        if os.path.exists(self.filename):
            shutil.copyfile(self.filename, backup_fn)
        # Now save
        self._rom.saveToFile(self.filename, updateDeviceCapacity=True)
        # Delete the backup
        if os.path.exists(backup_fn):
            os.unlink(backup_fn)

    def get_files_with_ext(self, ext, folder_name: Optional[str] = None):
        assert self._rom is not None
        if folder_name is None:
            return get_files_from_rom_with_extension(self._rom, ext)
        else:
            folder = self._rom.filenames.subfolder(folder_name)
            if folder is None:
                return []
            return get_files_from_folder_with_extension(folder, ext)

    def get_rom_folder(self, path):
        assert self._rom is not None
        return get_rom_folder(self._rom, path)

    def file_exists(self, path):
        """Check if a file exists"""
        assert self._rom is not None
        return path in self._rom.filenames

    def create_new_file(self, new_filename, model, file_handler_class: Type[DataHandler[T]], **kwargs):
        """Creates a new file in the ROM and fills it with the model content provided and
        writes the serialized model data there"""
        assert self._rom is not None
        copy_bin = file_handler_class.serialize(model, **kwargs)
        create_file_in_rom(self._rom, new_filename, copy_bin)
        self._opened_files[new_filename] = file_handler_class.deserialize(copy_bin, **kwargs)
        self._file_handlers[new_filename] = file_handler_class
        self._file_handler_kwargs[new_filename] = kwargs
        return copy_bin

    def ensure_dir(self, dir_name):
        """Makes sure the specified directory exists in the ROM-FS. If not, it is created."""
        assert self._rom is not None
        if not folder_in_rom_exists(self._rom, dir_name):
            create_folder_in_rom(self._rom, dir_name)

    def load_rom_data(self):
        assert self._rom is not None
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
        assert self._sprite_renderer is not None
        return self._sprite_renderer

    def get_string_provider(self) -> StringProvider:
        assert self._string_provider is not None
        return self._string_provider

    def create_patcher(self):
        if self._patcher is None:
            assert self._rom is not None
            self._patcher = Patcher(self._rom, self.get_rom_module().get_static_data())
        return self._patcher

    def get_binary(self, binary: Union[SectionProtocol, BinaryName, str]) -> bytes:
        assert self._rom is not None
        if isinstance(binary, str) or isinstance(binary, BinaryName):
            the_binary = getattr(self.get_rom_module().get_static_data().bin_sections, str(binary))
        else:
            the_binary = binary
        return get_binary_from_rom(self._rom, the_binary)

    def modify_binary(self, binary: Union[SectionProtocol, BinaryName, str], modify_cb: Callable[[bytearray], None]):
        """Modify one of the binaries (such as arm9 or overlay) and save it to the ROM"""
        assert self._rom is not None
        if isinstance(binary, str) or isinstance(binary, BinaryName):
            the_binary = getattr(self.get_rom_module().get_static_data().bin_sections, str(binary))
        else:
            the_binary = binary
        data = bytearray(self.get_binary(the_binary))
        modify_cb(data)
        set_binary_in_rom(self._rom, the_binary, data)
        self.force_mark_as_modified()

    def is_patch_applied(self, patch_name):
        patcher = self.create_patcher()
        try:
            if patcher.is_applied(patch_name):
                return True
            else:
                return False
        except NotImplementedError:
            return False
        
    def init_patch_properties(self):
        """ Initialize patch-specific properties of the rom. """
        
        # Allow ATUPX files if the ProvideATUPXSupport patch is applied
        if self.is_patch_applied("ProvideATUPXSupport"):
            FileType.COMMON_AT.allow(CommonAtType.ATUPX)
        else:
            FileType.COMMON_AT.disallow(CommonAtType.ATUPX)
            
        # Change Pokemon Names and Categories strings if ExpandPokeList
        md_properties = FileType.MD.properties()
        if self.is_patch_applied("ExpandPokeList"):
            StringType.POKEMON_NAMES.replace_xml_name('New Pokemon Names')
            StringType.POKEMON_CATEGORIES.replace_xml_name('New Pokemon Categories')
            md_properties.num_entities = 2048
            md_properties.max_possible = 2048
        else:
            StringType.POKEMON_NAMES.replace_xml_name('Pokemon Names')
            StringType.POKEMON_CATEGORIES.replace_xml_name('Pokemon Categories')
            md_properties.num_entities = 600
            md_properties.max_possible = 554
