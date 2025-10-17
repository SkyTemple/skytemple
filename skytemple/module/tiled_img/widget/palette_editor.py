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

import os
from typing import TYPE_CHECKING, cast

from gi.repository import Gtk, Gdk
from gi.repository.Gtk import ResponseType
from skytemple_files.common.i18n_util import _
from skytemple_files.common.util import make_palette_colors_unique

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import data_dir
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.tiled_img.module import TiledImgModule


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "tiled_img", "palette_editor.ui"))
class StPaletteEditorDialog(Gtk.Dialog):
    __gtype_name__ = "StPaletteEditorDialog"
    module: TiledImgModule
    notebook: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    make_unique_box: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    add_remove_btns: Gtk.ButtonBox = cast(Gtk.ButtonBox, Gtk.Template.Child())

    def __init__(
        self,
        parent_window,
        palettes: dict[str, list[int]],
        disable_color0=True,
        allow_adding_removing=False,
        show_make_unique_button=True,
    ):
        super().__init__()

        # Deprecated, this option doesn't do anything anymore. color0 is always editable.
        self.disable_color0 = False
        self.allow_adding_removing = allow_adding_removing
        self.show_make_unique_button = show_make_unique_button

        self.set_attached_to(parent_window)
        self.set_transient_for(parent_window)

        self.notebook.add_events(Gdk.EventMask.SCROLL_MASK | Gdk.EventMask.SMOOTH_SCROLL_MASK)

        self.page_boxes: list[Gtk.Box] = []

        self.tab_keys = list(palettes.keys())
        self.palettes = list(palettes.values())

    def show_dialog(self):
        self.set_size_request(690, 280)
        self._init_notebook_pages()
        self._init_page(0)
        if not self.show_make_unique_button:
            self.make_unique_box.set_visible(False)
        if not self.allow_adding_removing:
            self.add_remove_btns.set_visible(False)

        resp = self.run()
        self.destroy()

        if resp == ResponseType.OK:
            return self.palettes
        return None

    @Gtk.Template.Callback()
    def on_notebook_switch_page(self, ntb, wdg, page_num):
        if page_num is None:
            return
        self._init_page(page_num)

    @Gtk.Template.Callback()
    def on_notebook_scroll_event(self, widget, event):
        if event.get_scroll_deltas()[2] < 0:
            self.notebook.prev_page()
        else:
            self.notebook.next_page()

    def on_color_button_color_set(self, cb: Gtk.ColorButton, color_index):
        page_num = self.notebook.get_current_page()
        color: Gdk.Color = cb.get_color()
        self.palettes[page_num][color_index * 3 : color_index * 3 + 3] = [
            int(color.red_float * 255),  # type: ignore
            int(color.green_float * 255),  # type: ignore
            int(color.blue_float * 255),  # type: ignore
        ]

    @Gtk.Template.Callback()
    def on_make_unique_info_button_clicked(self, *args):
        md = SkyTempleMessageDialog(
            self,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Some images editors have problems when editing indexed images that contain\n"
                "the same color multiple times (they mis-match the actual color index).\n"
                "Since the import expects all 8x8 tiles to only use one 16-color palette, this\n"
                "can lead to issues.\n\n"
                "To solve this, you can make all colors in the palettes unique. This is done by\n"
                "slightly shifting the color values of duplicate colors (not visible for the\n"
                "human eye)."
            ),
            title=_("Make Colors Unique"),
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_make_unique_button_clicked(self, *args):
        self.palettes = make_palette_colors_unique(self.palettes)
        self._init_page(self.notebook.get_current_page())
        md = SkyTempleMessageDialog(
            self,
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Made colors unique."),
            title=_("Palette Editor"),
            is_success=True,
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_palette_add_button_release_event(self, wdg, event):
        tab_label = Gtk.Label.new("*")
        tab_label.show()
        current_page_idx = self.notebook.get_current_page()
        if event.get_state() & Gdk.ModifierType.CONTROL_MASK:
            idx = current_page_idx
        else:
            idx = current_page_idx + 1
        bx = self._create_notebook_page()

        self.notebook.insert_page(bx, tab_label, idx)
        self.page_boxes.insert(idx, bx)
        self.palettes.insert(idx, self.palettes[current_page_idx].copy())

        self.notebook.set_current_page(idx)

    @Gtk.Template.Callback()
    def on_palette_remove_clicked(self, wdg):
        if self.notebook.get_n_pages() < 2:
            md = SkyTempleMessageDialog(
                self,
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("You can not remove the last palette."),
                title=_("Error!"),
            )
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
            return
        current_page_idx = self.notebook.get_current_page()
        self.notebook.remove_page(current_page_idx)
        del self.page_boxes[current_page_idx]
        del self.palettes[current_page_idx]
        self._init_page(current_page_idx)

    def _init_notebook_pages(self):
        """Create a notebook page for each palette editable"""
        for name in self.tab_keys:
            tab_label = Gtk.Label.new(name)
            tab_label.show()
            bx = self._create_notebook_page()
            self.notebook.append_page(bx, tab_label)
            self.page_boxes.append(bx)

    def _init_page(self, page_number):
        if len(self.page_boxes) < 1:
            return
        bx = self.page_boxes[page_number]

        sw: Gtk.ScrolledWindow = Gtk.ScrolledWindow.new()
        vp: Gtk.Viewport = Gtk.Viewport.new()

        grid: Gtk.Grid = Gtk.Grid.new()
        grid.set_column_spacing(5)
        grid.set_row_spacing(10)
        grid.set_margin_right(15)
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)
        grid.show()
        for child in bx:
            bx.remove(child)
        vp.add(grid)
        vp.show()
        sw.add(vp)
        sw.set_min_content_height(160)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.show()
        bx.pack_start(sw, True, True, 0)

        palette = self.palettes[page_number]
        len_palette = len(palette)

        grid_w = 8

        previous_row_start_elem = None
        previous_col_start_elem = None
        for i, color_idx in enumerate(range(0, len_palette, 3)):
            cbx = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
            lb = Gtk.Label.new(_("Color ") + str(i))
            cb: Gtk.ColorButton = Gtk.ColorButton.new()
            if hasattr(cb.props, "show_editor"):
                cb.set_property("show_editor", True)
            cb.set_color(
                Gdk.Color.from_floats(
                    palette[color_idx] / 255,
                    palette[color_idx + 1] / 255,
                    palette[color_idx + 2] / 255,
                )
            )

            if i == 0 and self.disable_color0:
                cb.set_sensitive(False)

            cb.show()
            lb.show()
            cbx.pack_start(lb, True, True, 0)
            cbx.pack_start(cb, False, True, 0)
            cbx.show()

            # Connect signal
            cb.connect("color-set", self.on_color_button_color_set, i)

            if i % grid_w == 0:
                if previous_row_start_elem:
                    # New row
                    grid.attach_next_to(cbx, previous_row_start_elem, Gtk.PositionType.BOTTOM, 1, 1)
                else:
                    # First row
                    grid.add(cbx)
                previous_row_start_elem = cbx
            else:
                # New cell in next column
                grid.attach_next_to(cbx, previous_col_start_elem, Gtk.PositionType.RIGHT, 1, 1)

            previous_col_start_elem = cbx

    def _create_notebook_page(self):
        bx: Gtk.Box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 0)
        bx.set_margin_bottom(5)
        bx.set_margin_left(5)
        bx.set_margin_top(5)
        bx.set_margin_right(5)
        bx.show()
        return bx
