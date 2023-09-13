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
from typing import Dict, Optional, Callable, Mapping, List, cast

from gi.repository import Gtk
from gi.repository.Gtk import TreeModelRow
from range_typed_integers import u16_checked, u16
from skytemple.core.ui_utils import builder_get_assert, assert_not_none

from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptRoutine, Pmd2ScriptData
from skytemple_files.script.ssa_sse_sss.trigger import SsaTrigger
from skytemple_files.common.i18n_util import f, _


class SsaEventDialogController:
    def __init__(
            self, builder: Gtk.Builder, main_window: Gtk.Window,
            talk_script_names: Dict[int, str],
            scriptdata: Pmd2ScriptData,
            *, edit: Optional[SsaTrigger] = None):
        self.builder = builder
        self.edit: Optional[SsaTrigger] = edit
        self.new_model: Optional[SsaTrigger] = None
        self.talk_script_names = talk_script_names
        self.scriptdata = scriptdata
        self.window = builder_get_assert(self.builder, Gtk.Dialog, 'dialog_event')
        self.window.set_transient_for(main_window)
        self.window.set_attached_to(main_window)
        if self.edit is not None:
            try:
                # noinspection PyUnusedLocal
                script_name = self.talk_script_names[self.edit.script_id]
                self.title = f(_('Edit {script_name}')) + f' / {self.scriptdata.common_routine_info__by_id[self.edit.coroutine.id].name}'
            except KeyError:
                self.title = _('Edit Event')
        else:
            self.title = _('New Event')

    def run(self):
        """Run the dialog and return the response. If it's OK, the new model can be retrieved via get_event()"""
        self.window.set_title(self.title)
        # Fill Script IDs Combobox
        script_store = Gtk.ListStore(int, str)  # ID, name
        script_store.append([-1, _('None')])
        for sid, sname in self.talk_script_names.items():
            script_store.append([sid, sname])
        script_cb = builder_get_assert(self.builder, Gtk.ComboBox, 'event_script')
        script_cb.clear()
        self._fast_set_comboxbox_store(script_cb, script_store, 1)
        # Set Script IDs Combobox
        if self.edit:
            self._select_in_combobox_where_callback(script_cb, lambda r: assert_not_none(self.edit).script_id == r[0])
        else:
            script_cb.set_active_iter(script_store.get_iter_first())
        # Fill Coroutine Combobox
        routine_store = Gtk.ListStore(int, str)  # ID, name
        for routine in self.scriptdata.common_routine_info__by_id.values():
            routine_store.append([routine.id, routine.name])
        routine_cb = builder_get_assert(self.builder, Gtk.ComboBox, 'event_coroutine')
        routine_cb.clear()
        self._fast_set_comboxbox_store(routine_cb, routine_store, 1)
        # Set Coroutine Combobox
        if self.edit:
            self._select_in_combobox_where_callback(routine_cb, lambda r: assert_not_none(self.edit).coroutine.id == r[0])
        else:
            routine_cb.set_active_iter(routine_store.get_iter_first())
        # Clear / Set Unk2
        if self.edit:
            builder_get_assert(self.builder, Gtk.Entry, 'event_unk2').set_text(str(self.edit.unk2))
        else:
            builder_get_assert(self.builder, Gtk.Entry, 'event_unk2').set_text("")
        # Clear / Set Unk3
        if self.edit:
            builder_get_assert(self.builder, Gtk.Entry, 'event_unk3').set_text(str(self.edit.unk3))
        else:
            builder_get_assert(self.builder, Gtk.Entry, 'event_unk3').set_text("")

        response = self.window.run()

        self.window.hide()
        if response == Gtk.ResponseType.OK:
            script_id = script_store[assert_not_none(script_cb.get_active_iter())][0]
            coroutine_id = routine_store[assert_not_none(routine_cb.get_active_iter())][0]
            try:
                unk2 = u16_checked(int(builder_get_assert(self.builder, Gtk.Entry, 'event_unk2').get_text()))
            except (ValueError, OverflowError):
                unk2 = u16(0)
            try:
                unk3 = u16_checked(int(builder_get_assert(self.builder, Gtk.Entry, 'event_unk3').get_text()))
            except (ValueError, OverflowError):
                unk3 = u16(0)
            self.new_model = SsaTrigger(
                self.scriptdata, coroutine_id, unk2, unk3, script_id
            )
        return response

    def get_event(self) -> Optional[SsaTrigger]:
        """Returns the new model with the data from the dialog."""
        return self.new_model

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _select_in_combobox_where_callback(self, cb: Gtk.ComboBox, callback: Callable[[TreeModelRow], bool]):
        l_iter = cb.get_model().get_iter_first()
        while l_iter is not None:
            m = cast(Gtk.ListStore, assert_not_none(cb.get_model()))
            if callback(m[l_iter]):
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)
