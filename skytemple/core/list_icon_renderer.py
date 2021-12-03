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
from functools import partial
from itertools import zip_longest
from typing import Dict

import cairo
from gi.repository import GdkPixbuf, GLib

from skytemple.core.ui_utils import get_list_store_iter_by_idx

ORANGE = 'orange'
ORANGE_RGB = (1, 0.65, 0)


class ListIconRenderer:
    def __init__(self, column_id, can_be_placeholder=False):
        self._icon_pixbufs: Dict[any, GdkPixbuf.Pixbuf] = {}
        self._refresh_timer = None
        self.column_id = column_id
        self.can_be_placeholder = can_be_placeholder
        self._registered_for_reload = []
        self._loading = True

    def load_icon(self, store, load_fn, target_name, idx, parameters, is_placeholder=False):
        self._registered_for_reload.append((store, idx, (store, load_fn, target_name, idx, parameters, is_placeholder)))
        return self._get_icon(store, load_fn, target_name, idx, parameters, is_placeholder)

    def unload(self):
        self._icon_pixbufs = None
        self._refresh_timer = None
        self.column_id = None
        self.can_be_placeholder = None
        self._registered_for_reload = None
        self._loading = True

    def _get_icon(self, store, load_fn, target_name, idx, parameters, is_placeholder=False):
        was_loading = self._loading
        sprite, x, y, w, h = load_fn(*parameters,
                                     lambda: GLib.idle_add(
                                         partial(self._reload_icon, parameters, idx, store, load_fn, target_name, was_loading)
                                     ))

        if is_placeholder:
            ctx = cairo.Context(sprite)
            ctx.set_source_rgb(*ORANGE_RGB)
            ctx.rectangle(0, 0, w, h)
            ctx.set_operator(cairo.OPERATOR_IN)
            ctx.fill()

        data = bytes(sprite.get_data())
        # this is painful.
        new_data = bytearray()
        for b, g, r, a in grouper(data, 4):
            new_data += bytes([r, g, b, a])
        self._icon_pixbufs[target_name] = GdkPixbuf.Pixbuf.new_from_data(
            new_data, GdkPixbuf.Colorspace.RGB, True, 8, w, h, sprite.get_stride()
        )
        return self._icon_pixbufs[target_name]

    def _reload_icon(self, parameters, idx, store, load_fn, target_name, was_loading):
        if store == None:
            return
        if not self._loading and not was_loading:
            row = store[get_list_store_iter_by_idx(store, idx)]
            row[self.column_id] = self._get_icon(store, load_fn, target_name, idx, parameters, row[8] == ORANGE if self.can_be_placeholder else False)
            return
        if self._refresh_timer is not None:
            GLib.source_remove(self._refresh_timer)
        self._refresh_timer = GLib.timeout_add_seconds(0.5, self._reload_icons_in_tree)

    def _reload_icons_in_tree(self):
        try:
            for model, idx, params in self._registered_for_reload:
                model[get_list_store_iter_by_idx(model, idx)][self.column_id] = self._get_icon(*params)
            self._loading = False
            self._refresh_timer = None
        except (AttributeError, TypeError):
            pass  # This happens when the view was unloaded in the meantime.


def grouper(iterable, n, fillvalue=None):
    args = [iter(iterable)] * n
    return ((bytes(bytearray(x))) for x in zip_longest(fillvalue=fillvalue, *args))
