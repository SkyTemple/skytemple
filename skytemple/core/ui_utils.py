"""UI utilities."""
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
import os
import pathlib
import sys
from io import BytesIO
from xml.etree import ElementTree

import gi

gi.require_version('Gtk', '3.0')

import pkg_resources
from gi.repository import Gtk
from gi.repository.Gio import AppInfo
from gi.repository.Gtk import TreeModelRow
from skytemple_files.common.i18n_util import _

APP = 'skytemple'


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


def version():
    if os.path.exists(os.path.abspath(os.path.join(data_dir(), '..', '..', '.git'))):
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
        temp_file = BytesIO()
        tree.write(temp_file, encoding='utf-8', xml_declaration=True)
        xml_text = temp_file.getvalue().decode()
        return Gtk.Builder.new_from_string(xml_text, len(xml_text))
    else:
        builder = Gtk.Builder()
        builder.set_translation_domain(APP)
        builder.add_from_file(gui_file)
        return builder
