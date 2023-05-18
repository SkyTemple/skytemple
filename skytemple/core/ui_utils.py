"""UI utilities."""
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
import functools
import os
import pathlib
import sys
from tempfile import NamedTemporaryFile
from typing import Union, Type, overload
from xml.etree import ElementTree

import gi
from range_typed_integers import u8, u16, u32, i8, i16, get_range, i32

gi.require_version('Gtk', '3.0')

import pkg_resources
from gi.repository import Gtk, GLib
from gi.repository.Gio import AppInfo
from gi.repository.Gtk import TreeModelRow
from skytemple_files.common.i18n_util import _

APP = 'skytemple'
REPO_MOVE_EFFECTS = "https://github.com/theCapypara/eos_move_effects"


def recursive_up_item_store_mark_as_modified(row: TreeModelRow, modified=True):
    """Starting at the row, move UP the tree and set column 5 (starting at 0) to modified."""
    row[5] = modified
    generate_item_store_row_label(row)
    if row.parent is not None:
        recursive_up_item_store_mark_as_modified(row.parent, modified)


def recursive_down_item_store_mark_as_modified(row: TreeModelRow, modified=True):
    """Starting at the row, move DOWN the tree and set column 5 (starting at 0) to modified."""
    row[5] = modified
    generate_item_store_row_label(row)
    for child in row.iterchildren():
        recursive_down_item_store_mark_as_modified(child, modified)


def generate_item_store_row_label(row: TreeModelRow):
    """Set column number 6 (final_label) based on the values in the other columns"""
    row[6] = f"{'*' if row[5] else ''}{row[1]}"


def recursive_generate_item_store_row_label(row: TreeModelRow):
    """Like generate_item_store_row_label but recursive DOWN the tree"""
    generate_item_store_row_label(row)
    for child in row.iterchildren():
        recursive_generate_item_store_row_label(child)


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
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'data')
    return os.path.join(os.path.dirname(__file__), '..', 'data')


def is_dark_theme(widget):
    style_ctx = widget.get_style_context()
    color = style_ctx.get_background_color(Gtk.StateFlags.NORMAL)
    return 0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue < 0.5


def open_dir(directory):
    """Cross-platform open directory"""
    if sys.platform == 'win32':
        os.startfile(directory)
    else:
        AppInfo.launch_default_for_uri(pathlib.Path(directory).as_uri())


def version(*, ignore_dev=False):
    if not ignore_dev and os.path.exists(os.path.abspath(os.path.join(data_dir(), '..', '..', '.git'))):
        return 'dev'
    try:
        return pkg_resources.get_distribution("skytemple").version
    except pkg_resources.DistributionNotFound:
        # Try reading from a VERISON file instead
        version_file = os.path.join(data_dir(), 'VERSION')
        if os.path.exists(version_file):
            with open(version_file) as f:
                return f.read()
        return 'unknown'


def make_builder(gui_file) -> Gtk.Builder:
    """GTK under Windows does not detect the locale. So we have to translate manually."""
    if sys.platform == "win32":
        tree = ElementTree.parse(gui_file)
        for node in tree.iter():
            if 'translatable' in node.attrib:
                node.text = _(node.text)
        with NamedTemporaryFile(delete=False) as temp_file:
            tree.write(temp_file.file, encoding='utf-8', xml_declaration=True)
        builder = Gtk.Builder.new_from_file(temp_file.name)
        os.unlink(temp_file.name)
    else:
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(gui_file)

    # TODO: A bit of a dirty quickfix to make all switches look better
    for object in builder.get_objects():
        if isinstance(object, Gtk.Switch):
            object.set_halign(Gtk.Align.CENTER)
            object.set_valign(Gtk.Align.CENTER)

    return builder


GDK_BACKEND_BROADWAY = 'broadway'
def gdk_backend():
    # TODO: better way to do this?
    return os.environ.get('GDK_BACKEND', 'default')


def glib_async(f):
    """Decorator to wrap a function call in Glib.idle_add."""
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        return GLib.idle_add(lambda: f(*args, **kwargs))

    return wrapper


@overload
def catch_overflow(typ: Union[Type[u8], Type[u16], Type[u32], Type[i8], Type[i16], Type[i32]]): ...
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
                    GLib.idle_add(lambda: display_error(
                        sys.exc_info(),
                        _("The value you entered is invalid.\n\nValid values must be in the range [{},{}].").format(rmin, rmax),
                        _("SkyTemple - Value out of range"), log=False
                    ))
                else:
                    raise

        return wrapper
    return catch_overflow_decorator


def get_list_store_iter_by_idx(store: Gtk.ListStore, idx, get_iter=False):
    liter = store.get_iter_first()
    for i in range(0, idx):
        liter = store.iter_next(liter)
    if get_iter:
        return liter
    return liter
