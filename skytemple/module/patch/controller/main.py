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
from typing import Optional

from gi.repository import Gtk

from skytemple.core.module_controller import SimpleController
from skytemple_files.common.i18n_util import _

PATCHES = _('Patches')


class MainController(SimpleController):
    def __init__(self, _module, _item_id):
        pass

    def get_title(self) -> str:
        return _('Patches')

    def get_content(self) -> Gtk.Widget:
        return self.generate_content_label(
            _("In this section you can apply built-in ASM patches, your own ASM patches and custom\nitem-, move- and "
              "special process effects written in Assembler.\n\nYou will also find information on how to write our own\n"
              "patches and effects in the C and Rust programming languages.\n\nAdditionally you can browse all symbols "
              "and functions\nin the game known to SkyTemple.")
        )

    def get_icon(self) -> Optional[str]:
        return 'skytemple-illust-patch'
