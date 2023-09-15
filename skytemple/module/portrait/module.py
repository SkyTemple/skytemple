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
import math
import sys

from gi.repository import Gtk
from skytemple_files.common.i18n_util import _, f
from skytemple_files.graphics.kao import SUBENTRIES
from skytemple_files.graphics.kao.sprite_bot_sheet import SpriteBotSheet

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.error_handler import display_error
from skytemple.core.item_tree import ItemTree
from skytemple.core.rom_project import RomProject
from skytemple.module.portrait.portrait_provider import PortraitProvider
from skytemple.module.portrait.controller.portrait import PortraitController
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.kao.protocol import KaoProtocol

logger = logging.getLogger(__name__)
PORTRAIT_FILE = 'FONT/kaomado.kao'


class PortraitModule(AbstractModule):
    """Provides editing and displaying functionality for portraits."""
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 0  # n/a

    def __init__(self, rom_project: RomProject):
        """Loads the list of backgrounds for the ROM."""
        self.project = rom_project
        self.kao: KaoProtocol = self.project.open_file_in_rom(PORTRAIT_FILE, FileType.KAO)
        self._portrait_provider = PortraitProvider(self.kao)
        self._portrait_provider__was_init = False

    def load_tree_items(self, item_tree: ItemTree):
        """This module does not have main views."""
        pass

    def get_editor(self, item_id: int, modified_callback) -> Gtk.Widget:
        """Returns the view for one portrait slots"""
        controller = PortraitController(self, item_id, modified_callback)
        return controller.get_view()

    def get_portrait_provider(self) -> PortraitProvider:
        if not self._portrait_provider__was_init:
            self._portrait_provider.init_loader(MainController.window().get_screen())
            self._portrait_provider__was_init = True
        return self._portrait_provider

    def is_idx_supported(self, idx: int) -> bool:
        """Check if the portrait ID is valid."""
        return idx >= 0

    def import_sheet(self, idx: int, fn: str, clear_other_slots=True):
        try:
            if clear_other_slots:
                for i in range(0, SUBENTRIES):
                    self.kao.delete(idx, i)
            for subindex, image in SpriteBotSheet.load(fn, self.get_portrait_name):
                try:
                    self.kao.set_from_img(idx, subindex, image)
                except Exception as err:
                    name = self.get_portrait_name(subindex)
                    logger.error(f"Failed importing image '{name}'.", exc_info=err)
                    display_error(
                        sys.exc_info(),
                        f(_('Failed importing image "{name}":\n{err}')),
                        f(_("Error for '{name}'."))
                    )
        except Exception as err:
            logger.error(f"Failed importing portraits sheet: {err}", exc_info=err)
            display_error(
                sys.exc_info(),
                f(_('Failed importing portraits sheet:\n{err}')),
                _("Could not import.")
            )
        # Mark as modified
        self.mark_as_modified()

    def get_portrait_name(self, subindex):
        portrait_name = self.project.get_rom_module().get_static_data().script_data.face_names__by_id[
            math.floor(subindex / 2)
        ].name.replace('-', '_')
        portrait_name = f'{subindex}: {portrait_name}'
        if subindex % 2 != 0:
            portrait_name += _(' (flip)')  # TRANSLATORS: Suffix for flipped portraits
        return portrait_name

    def mark_as_modified(self):
        self.project.mark_as_modified(PORTRAIT_FILE)
