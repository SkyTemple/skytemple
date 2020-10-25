"""UI utilities."""
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
import os

from gi.repository import Gtk
from gi.repository.Gtk import TreeModelRow


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
        filter_nds.set_name("Nintendo DS ROMs (*.nds)")
        filter_nds.add_mime_type("application/x-nintendo-ds-rom")
        filter_nds.add_pattern("*.nds")
        dialog.add_filter(filter_nds)

        filter_any = Gtk.FileFilter()
        filter_any.set_name("Any files")
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)


def add_dialog_gif_filter(dialog):
        filter = Gtk.FileFilter()
        filter.set_name("GIF image (*.gif)")
        filter.add_mime_type("image/gif")
        filter.add_pattern("*.gif")
        dialog.add_filter(filter)


def add_dialog_png_filter(dialog):
        filter = Gtk.FileFilter()
        filter.set_name("PNG image (*.png)")
        filter.add_mime_type("image/png")
        filter.add_pattern("*.png")
        dialog.add_filter(filter)


def add_dialog_xml_filter(dialog):
        filter = Gtk.FileFilter()
        filter.set_name("XML document (*.xml)")
        filter.add_mime_type("application/xml")
        filter.add_pattern("*.xml")
        dialog.add_filter(filter)


def data_dir():
    return os.path.join(os.path.dirname(__file__), '..', 'data')


def is_dark_theme(widget):
    style_ctx = widget.get_style_context()
    color = style_ctx.get_background_color(Gtk.StateFlags.NORMAL)
    return 0.2126 * color.red + 0.7152 * color.green + 0.0722 * color.blue < 0.5
