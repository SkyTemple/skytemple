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
import re
from typing import TYPE_CHECKING, Optional

from gi.repository import Gtk
from range_typed_integers import u16, u16_checked

from skytemple.controller.main import MainController
from skytemple.core.list_icon_renderer import ORANGE
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import glib_async, catch_overflow
from skytemple.module.lists.controller.base import ListBaseController, PATTERN_MD_ENTRY
from skytemple_files.list.actor.model import ActorListBin
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptEntity
from skytemple_files.common.i18n_util import _
from skytemple_files.user_error import UserValueError

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

logger = logging.getLogger(__name__)


class ActorListController(ListBaseController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self._list: ActorListBin

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'actor_list.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_actor_list():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack
        self._list = self.module.get_actor_list()

        # ON LOAD ASSIGN PPMDU ENTITY LIST TO ACTOR LIST MODEL
        # This will also reflect changes to the list in other parts of the UI.
        self.module.project.get_rom_module().get_static_data().script_data.level_entities = self._list.list

        stack.set_visible_child(self.builder.get_object('box_list'))
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
        idx = len(self._list.list)
        self._list_store.append([
            str(idx), "NEW", str(0), self._get_icon(1, idx, False),
            1, str(0), str(0), self._ent_names[1],
            None
        ])
        self._list.list.append(Pmd2ScriptEntity(
            id=u16(idx),
            type=u16(0),
            entid=u16(1),
            name="NEW",
            unk3=u16(0),
            unk4=u16(0)
        ))
        self.module.mark_actors_as_modified()

    def on_cr_name_edited(self, widget, path, text):
        self._list_store[path][1] = text

    @catch_overflow(u16)
    def on_cr_type_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][2] = text

    @catch_overflow(u16)
    def on_cr_entity_edited(self, widget, path, text):
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        try:
            entid = u16_checked(int(match.group(1)))
        except ValueError:
            return
        idx = int(self._list_store[path][0])

        # Check, if this is a special entry,
        # in this case we update the standin entry!
        # TODO: it's a bit weird doing this over the color
        if self._list_store[path][8] == ORANGE:
            logger.debug(f"Updated standin for actor {idx}: {entid}")
            standins = self._sprite_provider.get_standin_entities()
            standins[idx] = entid
            self._sprite_provider.set_standin_entities(standins)

        # ent_name:
        try:
            self._list_store[path][7] = self._ent_names[entid]
        except KeyError as e:
            raise UserValueError(_("No Pokémon with this ID found."))

        # entid:
        self._list_store[path][4] = entid
        # ent_icon:
        # If color is orange it's special.
        # TODO: it's a bit weird doing this over the color
        self._list_store[path][3] = self._get_icon(entid, idx, self._list_store[path][8] == ORANGE)

    @catch_overflow(u16)
    def on_cr_unk3_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][5] = text

    @catch_overflow(u16)
    def on_cr_unk4_edited(self, widget, path, text):
        try:
            u16_checked(int(text))  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][6] = text

    @glib_async
    def on_list_store_row_changed(self, store, path, l_iter):
        """Propagate changes to list store entries to the model."""
        if self._loading:
            return
        a_id, name, a_type, ent_icon, entid, unk3, unk4, ent_name, color = store[path][:]
        a_id = int(a_id)
        actor = self._list.list[a_id]
        actor.name = name
        # If the color is orange, this is a spcial actor and we update the standin entries instead.
        # TODO: it's a bit weird doing this over the color
        if color != ORANGE:
            actor.entid = entid
        actor.type = int(a_type)
        actor.unk3 = int(unk3)
        actor.unk4 = int(unk4)
        logger.debug(f"Updated actor {a_id}: {actor}")

        self.module.mark_actors_as_modified()

    def refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('actor_tree')
        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()
        # Iterate list
        for idx, entry in enumerate(self._list.list):
            # If the entid is NOT 0 we will edit the value of entid
            entid_to_edit = entry.entid
            force_placeholder = False
            if entid_to_edit <= 0:
                force_placeholder = True
                # Otherwise we will edit the placeholder for this entry in the table.
                entid_to_edit = u16(1)
                standins = self._sprite_provider.get_standin_entities()
                if idx in standins:
                    entid_to_edit = standins[idx]
            self._list_store.append([
                str(idx), entry.name, str(entry.type), self._get_icon(entid_to_edit, idx, force_placeholder),
                entid_to_edit, str(entry.unk3), str(entry.unk4), self._ent_names[entid_to_edit],
                ORANGE if force_placeholder else None
            ])

    def get_tree(self):
        return self.builder.get_object('actor_tree')

    def can_be_placeholder(self):
        return True
