"""Signal handlers for the map width / height dialog boxes"""

#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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

from gi.repository import Gtk


def on_map_width_chunks_changed(map_wh_link: Gtk.Switch, map_width_tiles: Gtk.Entry, map_width_chunks: Gtk.Entry):
    """If the chunk width is changed and the values are linked, also update linked fields"""
    if map_wh_link.get_active():
        try:
            map_width_tiles.set_text(str(int(map_width_chunks.get_text()) * 3))
        except ValueError:
            pass


def on_map_height_chunks_changed(map_wh_link: Gtk.Switch, map_height_tiles: Gtk.Entry, map_height_chunks: Gtk.Entry):
    """If the chunk height is changed and the values are linked, also update linked fields"""
    if map_wh_link.get_active():
        try:
            map_height_tiles.set_text(str(int(map_height_chunks.get_text()) * 3))
        except ValueError:
            pass


def on_map_wh_link_state_set(
    map_wh_link_target: Gtk.Widget,
    map_width_tiles: Gtk.Entry,
    map_height_tiles: Gtk.Entry,
    map_width_chunks: Gtk.Entry,
    map_height_chunks: Gtk.Entry,
    map_wh_link: Gtk.Switch,
    state,
):
    """If the switch state changes, disable or enable some ui elements"""
    map_wh_link_target.set_sensitive(not state)
    if state:
        on_map_width_chunks_changed(map_wh_link, map_width_tiles, map_width_chunks)
        on_map_height_chunks_changed(map_wh_link, map_height_tiles, map_height_chunks)
