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
import os
from typing import TYPE_CHECKING

from gi.repository import Gtk
from gi.repository.Gtk import Widget

from skytemple.core.module_controller import SimpleController
from skytemple_files.common.i18n_util import f, _
if TYPE_CHECKING:
    from skytemple.module.rom.module import RomModule


class MainController(SimpleController):
    def __init__(self, module: 'RomModule', item_id: int):
        self.module = module
        self.rom = module.controller_get_rom()

    def get_title(self) -> str:
        return os.path.basename(self.module.project.filename)

    def get_content(self) -> Widget:
        # TODO: Might want to show some more ROM info here later and make it editable.
        return self.generate_content_label(_("Select something to edit in the ROM from the tree on the left \n"
                                             "or start the debugger by clicking the bug icon on the top right."))

    def get_icon(self) -> str:
        return 'skytemple-illust-rom'
