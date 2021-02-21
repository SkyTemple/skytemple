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

from gi.repository import Gtk

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.module_controller import SimpleController
from skytemple_files.common.i18n_util import _


class EntityController(SimpleController):
    def __init__(self, module: AbstractModule, name):
        self.name = name

    def get_title(self) -> str:
        return self.name

    def get_content(self) -> Gtk.Widget:
        return self.generate_content_label(
            _("Each Pokémon has two gender forms (even if it only has one gender).\n"
              "This entry contains both of these forms. The first form is the main form, it is used "
              "as a fallback in some cases, when the data for the second form doesn't exist.")
        )

    def get_icon(self) -> str:
        return None

    def get_back_illust(self) -> str:
        return 'monsters'
