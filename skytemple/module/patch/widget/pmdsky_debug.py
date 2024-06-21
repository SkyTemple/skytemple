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
from __future__ import annotations
import webbrowser
from typing import TYPE_CHECKING, Optional, cast
from gi.repository import Gtk
from pmdsky_debug_py import RELEASE
from pmdsky_debug_py.protocol import SectionProtocol, Symbol
from skytemple.core.ui_utils import assert_not_none, data_dir, safe_destroy
from skytemple_files.common.i18n_util import _, f
from skytemple.core.rom_project import RomProject

if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule
import os


@Gtk.Template(filename=os.path.join(data_dir(), "widget", "patch", "pmdsky_debug.ui"))
class StPatchPmdSkyDebugPage(Gtk.Box):
    __gtype_name__ = "StPatchPmdSkyDebugPage"
    module: PatchModule
    item_data: None
    box_normal: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    pmdsky_debug_version: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    symbol_notebook: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    repo_pmdsky_debug: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    symbol_box: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    symbol_description: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    symbol_meta: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    symbol_notebook_bin: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    symbol_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    symbol_window: Gtk.ScrolledWindow = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    symbol_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())

    def __init__(self, module: PatchModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self._selected_binary: str | None = None
        self._selected_symbol_type: str | None = None
        self._all_selected_binaries: list[str] = []
        self._all_symbol_types: list[str] = ["data", "functions"]
        self.load()
        self._suppress_signals = False

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.symbol_box)
        safe_destroy(self.symbol_window)

    @Gtk.Template.Callback()
    def on_symbol_notebook_switch_page(self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num):
        if not self._suppress_signals:
            self._selected_binary = self._all_selected_binaries[page_num]
            self.reset_all()
            self.refresh()

    @Gtk.Template.Callback()
    def on_symbol_notebook_bin_switch_page(self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num):
        if not self._suppress_signals:
            self._selected_symbol_type = self._all_symbol_types[page_num]
            self.reset_all()
            self.refresh()

    def reset_all(self):
        symbol_box = self.symbol_box
        assert_not_none(cast(Optional[Gtk.Container], symbol_box.get_parent())).remove(symbol_box)
        symbol_window = self.symbol_window
        assert_not_none(cast(Optional[Gtk.Container], symbol_window.get_parent())).remove(symbol_window)

    def load(self):
        symbol_notebook = self.symbol_notebook
        symbol_notebook_bin = self.symbol_notebook_bin
        # Fill symbol_notebook_bin
        symbol_notebook_bin.append_page(Gtk.Box.new(Gtk.Orientation.VERTICAL, 0), Gtk.Label.new(_("Data")))
        symbol_notebook_bin.append_page(Gtk.Box.new(Gtk.Orientation.VERTICAL, 0), Gtk.Label.new(_("Functions")))
        project = RomProject.get_current()
        assert project is not None
        bin_sections = project.get_rom_module().get_static_data().bin_sections
        keys = list(dict(vars(bin_sections)).keys())
        keys.sort(key=sort_bin_names)
        for bin_name in keys:
            if not bin_name.startswith("_"):
                symbol_notebook.append_page(
                    Gtk.Box.new(Gtk.Orientation.VERTICAL, 0),
                    Gtk.Label.new(readable_name(bin_name)),
                )
                self._all_selected_binaries.append(bin_name)
        self._selected_binary = self._all_selected_binaries[0]
        self._selected_symbol_type = self._all_symbol_types[0]
        self.pmdsky_debug_version.set_text(RELEASE)
        self.refresh()

    def refresh(self):
        symbol_notebook = self.symbol_notebook
        symbol_notebook_bin = self.symbol_notebook_bin
        symbol_box = self.symbol_box
        symbol_window = self.symbol_window
        tree = self.symbol_tree
        symbol_description = self.symbol_description
        symbol_meta = self.symbol_meta
        # ATTACH
        assert self._selected_binary is not None
        assert self._selected_symbol_type is not None
        bin_page = symbol_notebook_bin.get_nth_page(self._all_symbol_types.index(self._selected_symbol_type))
        assert bin_page is not None
        cast(Gtk.Box, bin_page).pack_start(symbol_window, True, True, 0)
        sym_page = symbol_notebook.get_nth_page(self._all_selected_binaries.index(self._selected_binary))
        assert sym_page is not None
        cast(Gtk.Box, sym_page).pack_start(symbol_box, True, True, 0)
        project = RomProject.get_current()
        assert project is not None
        section: SectionProtocol = getattr(
            project.get_rom_module().get_static_data().bin_sections,
            self._selected_binary,
        )
        bin_load_address = section.loadaddress
        bin_length = section.length
        symbol_description.set_text(section.description.strip())
        symbol_meta.set_markup(f(_("<b>Load Address:</b> 0x{bin_load_address:0x} | <b>Length:</b> {bin_length}")))
        model = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        model.clear()
        if self._selected_symbol_type == "data":
            symsect = section.data
        else:
            symsect = section.functions
        for symbol_name in dict(vars(symsect)).keys():
            if not symbol_name.startswith("_"):
                symbol: Symbol = getattr(symsect, symbol_name)
                if symbol is not None:
                    model.append(
                        [
                            symbol_name,
                            f"0x{symbol.absolute_address:0x}"
                            if symbol.absolute_addresses is not None and len(symbol.absolute_addresses) > 0
                            else "???",
                            str(symbol.length if symbol.length is not None else 1),
                            symbol.description.strip(),
                        ]
                    )

    @Gtk.Template.Callback()
    def on_repo_pmdsky_debug_clicked(self, *args):
        webbrowser.open_new_tab("https://github.com/UsernameFodder/pmdsky-debug")


def readable_name(bin_name: str):
    if bin_name == "arm9":
        return "ARM 9"
    if bin_name == "arm7":
        return "ARM 7"
    if bin_name == "ram":
        return "RAM"
    if bin_name == "itcm":
        return "ARM 9 ITCM"
    if bin_name.startswith("overlay"):
        try:
            ov_id = int(bin_name[7:], 10)
            return f"Overlay {ov_id}"
        except ValueError:
            pass
        return "ARM 9"
    return bin_name


def sort_bin_names(key: str):
    if not key.startswith("overlay"):
        return f"AA_{key}"
    try:
        ov_id = int(key[7:], 10)
        return f"ZZ_Overlay {ov_id:03}"
    except ValueError:
        pass
    return key
