"""UI utilities."""

#  Copyright 2020-2025 SkyTemple Contributors
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
from __future__ import annotations

import functools
import os
import pathlib
import platform
import sys
from collections.abc import Iterable
from typing import overload, TypeVar, Any

import gi
from gi.repository import GObject
from range_typed_integers import u8, u16, u32, i8, i16, get_range, i32

gi.require_version("Gtk", "3.0")

from gi.repository import Gtk, GLib
from gi.repository.Gio import AppInfo
from skytemple_files.common.i18n_util import _

import importlib.metadata as importlib_metadata

APP = "skytemple"
REPO_MOVE_EFFECTS = "https://github.com/theCapypara/eos_move_effects"

T = TypeVar("T", bound=GObject.Object)
X = TypeVar("X")
UI_ASSERT = "SKYTEMPLE_UI_ASSERT" in os.environ


def assert_not_none(obj: X | None) -> X:
    assert obj is not None
    return obj


def builder_get_assert(builder: Gtk.Builder, typ: type[T], name: str) -> T:
    try:
        obj = builder.get_object(name)
    except AttributeError as e:
        # This can happen if called in some unload scenarios, we also treat this as an assertion failure.
        raise AssertionError("Builder was not valid") from e
    if UI_ASSERT:
        assert isinstance(obj, typ)
        return obj
    else:
        return obj  # type: ignore


def iter_maybe(x: Iterable[X] | None) -> Iterable[X]:
    if x is None:
        return ()
    return x


def iter_tree_model(model: Gtk.TreeModel) -> Any:
    # TODO: This works but isn't supported by the typestubs.
    return model  # type: ignore


def add_dialog_file_filters(dialog):
    filter_nds = Gtk.FileFilter()
    filter_nds.set_name(_("Nintendo DS ROMs (*.nds)"))
    filter_nds.add_mime_type("application/x-nintendo-ds-rom")
    filter_nds.add_pattern("*.nds")
    dialog.add_filter(filter_nds)

    filter_any = Gtk.FileFilter()
    filter_any.set_name(_("Any files"))
    filter_any.add_pattern("*")
    dialog.add_filter(filter_any)


def add_dialog_gif_filter(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("GIF image (*.gif)"))
    filter.add_mime_type("image/gif")
    filter.add_pattern("*.gif")
    dialog.add_filter(filter)


def add_dialog_png_filter(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("PNG image (*.png)"))
    filter.add_mime_type("image/png")
    filter.add_pattern("*.png")
    dialog.add_filter(filter)


def add_dialog_xml_filter(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("XML document (*.xml)"))
    filter.add_mime_type("application/xml")
    filter.add_pattern("*.xml")
    dialog.add_filter(filter)


def add_dialog_csv_filter(dialog):
    filter = Gtk.FileFilter()
    filter.set_name(_("CSV file (*.csv)"))
    filter.add_mime_type("text/csv")
    filter.add_pattern("*.csv")
    dialog.add_filter(filter)


def data_dir():
    if getattr(sys, "frozen", False):
        system = platform.system()
        if system == "Windows":
            return os.path.join(os.path.dirname(sys.executable), "_internal", "data")
        elif system == "Darwin":
            return os.path.join(os.path.dirname(sys.executable), "..", "Resources", "data")
        else:
            return os.path.join(os.path.dirname(sys.executable), "data")
    return os.path.join(os.path.dirname(__file__), "..", "data")


def is_dark_theme(widget) -> bool:
    style_ctx = widget.get_style_context()
    color = style_ctx.get_background_color(Gtk.StateFlags.NORMAL)
    return 0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue < 0.5


def open_dir(directory):
    """Cross-platform open directory"""
    if sys.platform == "win32":
        os.startfile(directory)
    else:
        AppInfo.launch_default_for_uri(pathlib.Path(directory).as_uri())


def version(*, ignore_dev=False) -> str:
    if not ignore_dev and os.path.exists(os.path.abspath(os.path.join(data_dir(), "..", "..", ".git"))):
        return "dev"
    try:
        return importlib_metadata.metadata("skytemple")["version"]
    except importlib_metadata.PackageNotFoundError:
        return "unknown"


def glib_async(f):
    """Decorator to wrap a function call in Glib.idle_add."""

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return GLib.idle_add(lambda: f(*args, **kwargs))

    return wrapper


@overload
def catch_overflow(
    typ: type[u8] | type[u16] | type[u32] | type[i8] | type[i16] | type[i32],
): ...


@overload
def catch_overflow(range_start: int, range_end: int): ...


def catch_overflow(typ_or_range_start, range_end=None):
    """
    Decorator to display a friendly error message with OverflowErrors occur
    (to inform the user of valid value ranges).

    This is only to be used for values directly input by the user.
    """

    def catch_overflow_decorator(f):
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            try:
                return f(*args, **kwargs)
            except OverflowError:
                from skytemple.core.error_handler import display_error

                rmin = None
                rmax = None
                if range_end is None:
                    rg = get_range(typ_or_range_start)
                    if rg:
                        rmin = rg.min
                        rmax = rg.max
                else:
                    rmin = typ_or_range_start
                    rmax = range_end
                if rmin is not None:
                    GLib.idle_add(
                        lambda: display_error(
                            sys.exc_info(),
                            _("The value you entered is invalid.\n\nValid values must be in the range [{},{}].").format(
                                rmin, rmax
                            ),
                            _("SkyTemple - Value out of range"),
                            log=False,
                            should_report=False,
                        )
                    )
                else:
                    raise

        return wrapper

    return catch_overflow_decorator


def get_list_store_iter_by_idx(store: Gtk.ListStore, idx, get_iter=False):
    liter = store.get_iter_first()
    for i in range(0, idx):
        assert liter is not None
        liter = store.iter_next(liter)
    if get_iter:
        return liter
    return liter


def create_tree_view_column(title: str, renderer: Gtk.CellRenderer, **kwargs: int) -> Gtk.TreeViewColumn:
    """
    Compatibility with the 'old' TreeViewColumn constructor and generally a convenient shortcut for quick TreeViewColumn
    construction.
    The kwargs name is the attribute name, the value the column ID.
    """
    column = Gtk.TreeViewColumn(title=title)
    column.pack_start(renderer, True)
    for attr, column_id in kwargs.items():
        column.add_attribute(renderer, attr, column_id)
    return column


def safe_destroy(widget: Gtk.Widget):
    """Destroys the given widget in a template destroy scenario. May skip the widget if not deemed sound."""
    widget.destroy()
