#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
from enum import Enum
from typing import Dict, Union

from skytemple_files.common.i18n_util import _
from skytemple_files.common.ppmdu_config.data import Pmd2PatchParameter, Pmd2PatchParameterType

from gi.repository import Gtk

from skytemple_files.patch.errors import PatchNotConfiguredError

logger = logging.getLogger(__name__)


class PatchCanceledError(Exception):
    pass


class ParamDialogController:
    """A dialog controller as an UI for asking for patch parameters."""

    def __init__(self, parent_window: Gtk.Window):
        self.window: Gtk.Dialog = Gtk.Dialog.new()
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        self.window.set_modal(True)
        self.window.add_buttons(_("Cancel"), Gtk.ResponseType.CLOSE, _("Apply"), Gtk.ResponseType.APPLY)
        self.window.get_action_area().show_all()

    def run(self, name: str, parameters: Dict[str, Pmd2PatchParameter]) -> Dict[str, Union[str, int]]:
        content: Gtk.Box = self.window.get_content_area()
        self.window.set_title(_('Settings for the "{}" Patch').format(name))

        content.pack_start(
            Gtk.Label.new(_('The patch "{}" requires additional configuration:').format(name)),
            False, False, 10
        )

        grid: Gtk.Grid = Gtk.Grid.new()
        grid.set_column_spacing(5)
        grid.set_row_spacing(5)
        controls = {}

        for i, param in enumerate(parameters.values()):
            grid.attach(Gtk.Label.new(_(param.label) + ':'), 0, i, 1, 1)
            controls[param.name] = self._generate_control(param)
            grid.attach(controls[param.name], 1, i, 1, 1)

        content.pack_start(
            grid,
            True, True, 10
        )

        content.show_all()
        response = self.window.run()
        self.window.hide()

        if response != Gtk.ResponseType.APPLY:
            raise PatchCanceledError()

        config = {}
        for param_name, control in controls.items():
            config[param_name] = self._process_control(control, parameters[param_name])
        return config

    def _generate_control(self, param: Pmd2PatchParameter):
        if param.type == Pmd2PatchParameterType.INTEGER or param.type == Pmd2PatchParameterType.STRING:
            entry = Gtk.Entry()
            if param.default:
                entry.set_text(str(param.default))
            return entry
        elif param.type == Pmd2PatchParameterType.SELECT:
            combobox_text: Gtk.ComboBoxText = Gtk.ComboBoxText()
            for option in param.options:
                combobox_text.append(str(option.value), option.label)
            combobox_text.set_active(0)
            return combobox_text
        raise TypeError("Unknown parameter type " + param.type)

    def _process_control(self, control: Gtk.Widget, param: Pmd2PatchParameter) -> Union[int, str]:
        try:
            if param.type == Pmd2PatchParameterType.INTEGER or param.type == Pmd2PatchParameterType.STRING:
                assert isinstance(control, Gtk.Entry)
                control: Gtk.Entry
                value = control.get_text()
                if param.type == Pmd2PatchParameterType.INTEGER:
                    return int(value)
                return value
            elif param.type == Pmd2PatchParameterType.SELECT:
                assert isinstance(control, Gtk.ComboBoxText)
                control: Gtk.ComboBoxText
                selected_id = control.get_active_id()
                for option in param.options:
                    # We do it like this, because option.value has the correct type,
                    # selected_id is always a string.
                    if option.value == selected_id:
                        return option.value
                raise TypeError("Unknown option " + selected_id)
            raise TypeError("Unknown parameter type " + param.type)
        except ValueError:
            raise PatchNotConfiguredError(_("Invalid values for some settings provided. Please try again."), "*",
                                          _("Invalid values for some settings provided. Please try again."))
