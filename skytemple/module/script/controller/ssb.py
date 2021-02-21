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

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.module_controller import SimpleController
from skytemple_files.common.i18n_util import f, _

SCRIPT_SCRIPTS = _('Scripts')


class SsbController(SimpleController):
    def __init__(self, module: AbstractModule, item_id: int):
        pass

    def get_title(self) -> str:
        return SCRIPT_SCRIPTS

    def get_content(self) -> Gtk.Widget:
        box: Gtk.Box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 20)
        label = self.generate_content_label(
            _('Each of the scenes has at least one script assigned to them, which is run when the scene is loaded.\n'
              'In addition to that, there is also "COMMON/unionall.ssb", which contains the game\'s coroutines '
              '(main scripts).\n\n'
              'To edit the game\'s scripts, open the Script Engine Debugger. You can also do this by clicking the bug '
              'icon in the top right.\n')
        )
        button_box = Gtk.ButtonBox.new(Gtk.Orientation.VERTICAL)
        button: Gtk.Button = Gtk.Button.new_with_label(_('Open Script Engine Debugger'))
        button.connect('clicked', lambda *args: MainController.debugger_manager().open(MainController.window()))
        button_box.pack_start(button, False, False, 0)

        box.pack_start(label, False, False, 0)
        box.pack_start(button_box, False, False, 0)
        return box

    def get_icon(self) -> str:
        return 'skytemple-illust-script'
