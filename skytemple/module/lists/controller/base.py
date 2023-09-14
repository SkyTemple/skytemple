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
import re
import typing
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Optional, Dict, List, Union

import cairo
from gi.repository import Gtk, GLib

from skytemple_files.data.md.protocol import Gender
from skytemple.core.list_icon_renderer import ListIconRenderer
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import builder_get_assert

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
PATTERN_MD_ENTRY = re.compile(r'.*\(\$(\d+)\).*')


class ListBaseController(AbstractController, ABC):
    def __init__(self, module: 'ListsModule', *args):
        self.module = module

        self.builder: Gtk.Builder = None  # type: ignore
        self._sprite_provider = self.module.project.get_sprite_provider()
        self._ent_names: Dict[int, str] = {}
        self._list_store: Optional[Gtk.ListStore] = None
        self.icon_renderer: Optional[ListIconRenderer] = None
        self._loading = False

    def load(self):
        self._loading = True

        self._init_monster_store()
        self.refresh_list()

        self.builder.connect_signals(self)
        self._loading = False

    @typing.no_type_check
    def unload(self):
        super().unload()
        self.builder = None
        self._sprite_provider = None
        self._ent_names = None
        self._list_store = None
        if self.icon_renderer is not None:
            self.icon_renderer.unload()
        self.icon_renderer = None
        self._loading = False

    def _init_monster_store(self):
        monster_md = self.module.get_monster_md()
        monster_store = builder_get_assert(self.builder, Gtk.ListStore, 'monster_store')
        for idx, entry in enumerate(monster_md.entries):
            if idx == 0:
                continue
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            self._ent_names[idx] = f'{name} ({Gender(entry.gender).print_name}) (${idx:04})'
            monster_store.append([self._ent_names[idx]])

    def on_draw_example_placeholder_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        sprite, x, y, w, h = self._sprite_provider.get_actor_placeholder(
            9999, 0, lambda: GLib.idle_add(lambda: builder_get_assert(self.builder, Gtk.DrawingArea, 'draw_example_placeholder').queue_draw())
        )
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if widget.get_size_request() != (w, h):
            widget.set_size_request(w, h)

    def on_completion_entities_match_selected(self, completion, model, tree_iter):
        pass

    def on_cr_entity_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_entities'))

    @abstractmethod
    def refresh_list(self):
        pass

    def can_be_placeholder(self):
        return False

    def _get_icon(self, entid, idx, force_placeholder=False, store=None, store_iters=None):
        # store_iters is deprecated and unused
        if self.icon_renderer is None:
            self.icon_renderer = ListIconRenderer(self._get_store_icon_id(), self.can_be_placeholder())
        if store is None:
            store = self._list_store
        if entid <= 0 or force_placeholder:
            load_fn: typing.Callable = self._sprite_provider.get_actor_placeholder
            target_name = f'pl{idx}'
            parameters = idx, 0
            is_placeholder = True
        else:
            load_fn = self._sprite_provider.get_monster
            target_name = entid
            parameters = entid, 0
            is_placeholder = False
        return self.icon_renderer.load_icon(store, load_fn, target_name, idx, parameters, is_placeholder)

    def _get_store_icon_id(self):
        return 3

    def _get_store_entid_id(self):
        return 4
