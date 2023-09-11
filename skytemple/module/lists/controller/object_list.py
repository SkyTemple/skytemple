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
import sys
import logging
from typing import TYPE_CHECKING, Optional, cast

from gi.repository import Gtk
from range_typed_integers import u16, u8, u16_checked

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import glib_async, catch_overflow, builder_get_assert, assert_not_none
from skytemple.module.lists.controller.base import ListBaseController
from skytemple_files.list.object.model import ObjectListBin
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptObject
from skytemple_files.common.i18n_util import _
if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

logger = logging.getLogger(__name__)


class ObjectListController(ListBaseController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self._list: ObjectListBin
        self._list_store: Gtk.ListStore

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'object_list.glade')
        stack = builder_get_assert(self.builder, Gtk.Stack, 'list_stack')

        if not self.module.has_object_list():
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_na'))
            return stack
        self._list = self.module.get_object_list()

        # ON LOAD ASSIGN PPMDU ENTITY LIST TO ACTOR LIST MODEL
        # This will also reflect changes to the list in other parts of the UI.
        self.module.project.get_rom_module().get_static_data().script_data.objects = self._list.list

        stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_list'))
        self.load()
        return stack

    def on_btn_remove_clicked(self, *args):
        # TODO
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            _("Not implemented.")
        )
        md.run()
        md.destroy()

    def on_btn_add_clicked(self, *args):
        self._list_store.append([len(self._list.list), "NULL", 0, 0, 0, False])
        self._list.list.append(Pmd2ScriptObject(
            id=u16(len(self._list.list)),
            unk1=u16(0),
            unk2=u16(0),
            unk3=u8(0),
            name="NULL"
        ))
        self.module.mark_objects_as_modified()

    def on_cr_name_edited(self, widget, path, text):
        try:
            if len(text) > 10:
                raise ValueError("Object name has more than 10 characters.")
            if max([ord(c) for c in text])>=256:
                raise ValueError("Object name has non-ASCII characters.")
            self._list_store[path][1] = text
        except ValueError as err:
            display_error(
                sys.exc_info(),
                str(err),
                _("Invalid object name")
            )

    @catch_overflow(u16)
    def on_cr_type_edited(self, widget, path, text):
        try:
            self._list_store[path][2] = u16_checked(int(text))
        except ValueError:
            return

    @catch_overflow(u16)
    def on_cr_unk21_edited(self, widget, path, text):
        try:
            self._list_store[path][3] = u16_checked(int(text))
        except ValueError:
            return

    @catch_overflow(u16)
    def on_cr_unk22_edited(self, widget, path, text):
        try:
            self._list_store[path][4] = u16_checked(int(text))
        except ValueError:
            return

    def on_cr_flag_toggled(self, widget, path, **args):
        self._list_store[path][5] = not self._list_store[path][5]

    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the model."""
        if self._loading:
            return
        o_id, name, o_type, unk21, unk22, flag = store[path][:]
        obj = self._list.list[o_id]
        obj.name = name
        obj.unk1 = o_type
        obj.unk2 = unk21+(unk22 << 8)
        obj.unk3 = int(flag)
        logger.debug(f"Updated object {o_id}: {obj}")

        self.module.mark_objects_as_modified()

    def refresh_list(self):
        tree = builder_get_assert(self.builder, Gtk.TreeView, 'object_tree')
        self._list_store = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        self._list_store.clear()
        # Iterate list
        for idx, entry in enumerate(self._list.list):
            self._list_store.append([
                idx, entry.name, entry.unk1, entry.unk2 & 0xFF, entry.unk2 >> 8, bool(entry.unk3)
            ])

    def get_tree(self):
        return builder_get_assert(self.builder, Gtk.TreeView, 'objet_tree')

    def can_be_placeholder(self):
        return True
