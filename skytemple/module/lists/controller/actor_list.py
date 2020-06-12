#  Copyright 2020 Parakoopa
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
from functools import partial
from itertools import zip_longest
from typing import TYPE_CHECKING, Optional, Dict

import cairo
from gi.repository import Gtk, GLib, GdkPixbuf, Gdk

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.list.actor.model import ActorListBin
if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule

ORANGE = 'orange'
ORANGE_RGB = (1, 0.65, 0)
PATTERN_MD_ENTRY = re.compile(r'.*\(\$(\d+)\).*')
logger = logging.getLogger(__name__)


class ActorListController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        self.module = module

        self.builder = None
        self._sprite_provider = self.module.project.get_sprite_provider()
        self._list: Optional[ActorListBin] = None
        self._icon_pixbufs: Dict[any, GdkPixbuf.Pixbuf] = {}
        self._refresh_timer = None
        self._ent_names: Dict[int, str] = {}
        self._tree_iters_by_idx: Dict[int, Gtk.TreeIter] = {}
        self._tmp_path = None
        self._list_store: Optional[Gtk.ListStore] = None
        self._loading = False

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'actor_list.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_actor_list():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack
        self._list = self.module.get_actor_list()

        self._loading = True
        # ON LOAD ASSIGN PPMDU ENTITY LIST TO ACTOR LIST MODEL
        # This will also reflect changes to the list in other parts of the UI.
        self.module.project.get_rom_module().get_static_data().script_data.level_entities = self._list.list

        stack.set_visible_child(self.builder.get_object('box_list'))

        self._init_monster_store()
        self.refresh_list()

        self.builder.connect_signals(self)
        self._loading = False
        return stack

    def _init_monster_store(self):
        monster_md = self.module.get_monster_md()
        monster_store: Gtk.ListStore = self.builder.get_object('monster_store')
        for idx, entry in enumerate(monster_md.entries):
            if idx == 0:
                continue
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            self._ent_names[idx] = f'{name} ({entry.gender.name.capitalize()}) (${idx:04})'
            monster_store.append([self._ent_names[idx]])

    def on_draw_example_placeholder_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        sprite, x, y, w, h = self._sprite_provider.get_actor_placeholder(
            9999, 0, lambda: GLib.idle_add(lambda: self.builder.get_object('draw_example_placeholder').queue_draw())
        )
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if widget.get_size_request() != (w, h):
            widget.set_size_request(w, h)

    def on_completion_entities_match_selected(self, completion, model, tree_iter):
        pass

    def on_cr_entity_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_entities'))
        self._tmp_path = path

    def on_btn_remove_clicked(self, *args):
        # TODO
        md = Gtk.MessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            f"Not implemented."
        )
        md.run()
        md.destroy()

    def on_btn_add_clicked(self, *args):
        # TODO
        md = Gtk.MessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            f"Not implemented."
        )
        md.run()
        md.destroy()

    def on_cr_name_edited(self, widget, path, text):
        self._list_store[path][1] = text

    def on_cr_type_edited(self, widget, path, text):
        try:
            int(text)  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][2] = text

    def on_cr_entity_edited(self, widget, path, text):
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        try:
            entid = int(match.group(1))
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

        # entid:
        self._list_store[path][4] = entid
        # ent_icon:
        # If color is orange it's special.
        # TODO: it's a bit weird doing this over the color
        self._list_store[path][3] = self._get_icon(entid, idx, self._list_store[path][8] == ORANGE)
        # ent_name:
        self._list_store[path][7] = self._ent_names[entid]

    def on_cr_unk3_edited(self, widget, path, text):
        try:
            int(text)  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][5] = text

    def on_cr_unk4_edited(self, widget, path, text):
        try:
            int(text)  # this is only for validating.
        except ValueError:
            return
        self._list_store[path][6] = text

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

        self.module.mark_as_modified()

    def refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('actor_tree')
        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()
        self._icon_pixbufs = {}
        # Iterate list
        for idx, entry in enumerate(self._list.list):
            # If the entid is NOT 0 we will edit the value of entid
            entid_to_edit = entry.entid
            force_placeholder = False
            if entid_to_edit <= 0:
                force_placeholder = True
                # Otherwise we will edit the placeholder for this entry in the table.
                entid_to_edit = 1
                standins = self._sprite_provider.get_standin_entities()
                if idx in standins:
                    entid_to_edit = standins[idx]
            l_iter = self._list_store.append([
                str(idx), entry.name, str(entry.type), self._get_icon(entid_to_edit, idx, force_placeholder),
                entid_to_edit, str(entry.unk3), str(entry.unk4), self._ent_names[entid_to_edit],
                ORANGE if force_placeholder else None
            ])
            self._tree_iters_by_idx[idx] = l_iter

    def _get_icon(self, entid, idx, force_placeholder=False):
        was_loading = self._loading
        if entid <= 0 or force_placeholder:
            sprite, x, y, w, h = self._sprite_provider.get_actor_placeholder(idx, 0,
                                                                             lambda: GLib.idle_add(
                                                                                 partial(self._reload_icon, 0, idx, was_loading)
                                                                             ))
            ctx = cairo.Context(sprite)
            ctx.set_source_rgb(*ORANGE_RGB)
            ctx.rectangle(0, 0, w, h)
            ctx.set_operator(cairo.OPERATOR_IN)
            ctx.fill()
            target = f'pl{idx}'

        else:
            sprite, x, y, w, h = self._sprite_provider.get_monster(entid, 0,
                                                                   lambda: GLib.idle_add(
                                                                       partial(self._reload_icon, entid, idx, was_loading)
                                                                   ))
            target = entid
        data = bytes(sprite.get_data())
        # this is painful.
        new_data = bytearray()
        for b, g, r, a in grouper(data, 4):
            new_data += bytes([r, g, b, a])
        self._icon_pixbufs[target] = GdkPixbuf.Pixbuf.new_from_data(
            new_data, GdkPixbuf.Colorspace.RGB, True, 8, w, h, sprite.get_stride()
        )
        return self._icon_pixbufs[target]

    def _reload_icon(self, entid, idx, was_loading):
        if not self._loading and not was_loading:
            row = self._list_store[self._tree_iters_by_idx[idx]]
            row[3] = self._get_icon(entid, idx, row[8] == ORANGE)
            return
        if self._refresh_timer is not None:
            GLib.source_remove(self._refresh_timer)
        self._refresh_timer = GLib.timeout_add_seconds(0.5, self._reload_icons_in_tree)

    def _reload_icons_in_tree(self):
        tree: Gtk.TreeView = self.builder.get_object('actor_tree')
        model: Gtk.ListStore = tree.get_model()
        self._loading = True
        for entry in model:
            # If the color is orange, this is a spcial actor and we render a placeholder instead.
            # TODO: it's a bit weird doing this over the color
            entry[3] = self._get_icon(entry[4], int(entry[0]), entry[8] == ORANGE)
        self._loading = False
        self._refresh_timer = None


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return ((bytes(bytearray(x))) for x in zip_longest(fillvalue=fillvalue, *args))
