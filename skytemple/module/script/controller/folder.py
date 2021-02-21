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
from skytemple_files.common.i18n_util import f, _


class FolderController(SimpleController):
    def __init__(self, module: AbstractModule, name):
        self.name = name

    def get_title(self) -> str:
        if self.name is not None:
            return f(_('Script Scenes for maps in category "{self.name}"'))
        return _('Script Scenes for other maps')

    def get_content(self) -> Gtk.Widget:
        if self.name is not None:
            return self.generate_content_label(
                f(_("This section contains all the script scenes of maps, that start with the letter {self.name[0]}."))
            )
        return self.generate_content_label(
            _("This section contains all the script scenes of maps, that don't fit in any of the other categories.")
        )

    def get_icon(self) -> str:
        return None

    def get_back_illust(self) -> str:
        return 'map'
