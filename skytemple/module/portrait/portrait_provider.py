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
import threading
from typing import List, Dict, Tuple

import cairo
from gi.repository import Gdk, GdkPixbuf, Gtk

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.data.md.model import NUM_ENTITIES
from skytemple_files.graphics.kao.model import Kao, KAO_IMG_METAPIXELS_DIM, KAO_IMG_IMG_DIM

IMG_DIM = KAO_IMG_METAPIXELS_DIM * KAO_IMG_IMG_DIM
portrait_provider_lock = threading.Lock()


class PortraitProvider:
    """
    PortraitProvider. This class renders portraits using Threads. If a portrait is requested, a loading icon
    is returned instead, until it is loaded by the AsyncTaskRunner.
    """
    def __init__(self, kao: Kao):
        self._kao = kao
        self._loader_surface = None
        self._error_surface = None

        self._loaded: Dict[Tuple[int, int], cairo.Surface] = {}
        self._loaded__is_fallback: Dict[Tuple[int, int], bool] = {}

        self._requests: List[Tuple[int, int]] = []

        # init_loader MUST be called next!

    def init_loader(self, screen: Gdk.Screen):
        icon_theme: Gtk.IconTheme = Gtk.IconTheme.get_for_screen(screen)
        # Loader icon
        loader_icon: GdkPixbuf.Pixbuf = icon_theme.load_icon(
            'skytemple-image-loading-symbolic', IMG_DIM, Gtk.IconLookupFlags.FORCE_SIZE
        ).copy()
        self._loader_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, IMG_DIM, IMG_DIM)
        ctx = cairo.Context(self._loader_surface)
        Gdk.cairo_set_source_pixbuf(ctx, loader_icon, 0, 0)
        ctx.paint()
        # Error icon
        error_icon: GdkPixbuf.Pixbuf = icon_theme.load_icon(
            'skytemple-img-load-error-symbolic', IMG_DIM, Gtk.IconLookupFlags.FORCE_SIZE
        ).copy()
        self._error_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, IMG_DIM, IMG_DIM)
        ctx = cairo.Context(self._error_surface)
        Gdk.cairo_set_source_pixbuf(ctx, error_icon, 0, 0)
        ctx.paint()

    def reset(self):
        with portrait_provider_lock:
            self._loaded = {}
            self._loaded__is_fallback = {}
            self._requests = []

    def get(self, entry_id: int, sub_id: int, after_load_cb=lambda: None, allow_fallback=True) -> cairo.Surface:
        """
        Returns a portrait.
        As long as the portrait is being loaded, the loader portrait is returned instead.
        If allow_fallback is set, the base form entry is loaded (% 600), when the portrait doesn't exist.
        """
        with portrait_provider_lock:
            if (entry_id, sub_id) in self._loaded:
                if allow_fallback or (not allow_fallback and not self._loaded__is_fallback[(entry_id, sub_id)]):
                    return self._loaded[(entry_id, sub_id)]
                else:
                    return self.get_error()
            if (entry_id, sub_id) not in self._requests:
                self._requests.append((entry_id, sub_id))
                self._load(entry_id, sub_id, after_load_cb, allow_fallback)
        return self.get_loader()

    def _load(self, entry_id, sub_id, after_load_cb, allow_fallback):
        AsyncTaskRunner.instance().run_task(self._load__impl(entry_id, sub_id, after_load_cb, allow_fallback))

    async def _load__impl(self, entry_id, sub_id, after_load_cb, allow_fallback):
        is_fallback = False
        try:
            kao = self._kao.get(entry_id, sub_id)
            if kao is None or kao.empty is True:
                if allow_fallback:
                    is_fallback = True
                    kao = self._kao.get(entry_id % NUM_ENTITIES, sub_id)
                    if kao is None:
                        raise RuntimeError()
                else:
                    raise RuntimeError()
            portrait_pil = kao.get()
            surf = pil_to_cairo_surface(portrait_pil.convert('RGBA'))
            loaded = surf
        except (RuntimeError, ValueError):
            loaded = self.get_error()
        with portrait_provider_lock:
            self._loaded[(entry_id, sub_id)] = loaded
            self._loaded__is_fallback[(entry_id, sub_id)] = is_fallback
            self._requests.remove((entry_id, sub_id))
        after_load_cb()

    def get_loader(self) -> cairo.Surface:
        """
        Returns the loader sprite. A "loading" icon with the size ~24x24px.
        """
        return self._loader_surface

    def get_error(self) -> cairo.Surface:
        """
        Returns the error sprite. An "error" icon with the size ~24x24px.
        """
        return self._error_surface
