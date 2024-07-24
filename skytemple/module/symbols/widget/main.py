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

import os
import re
from typing import TYPE_CHECKING, cast, List, Tuple, Optional

from gi.repository import Gtk

from pmdsky_debug_py.protocol import Symbol

from skytemple.core.rom_project import RomProject
from skytemple.core.settings import SkyTempleSettingsStore
from skytemple.core.ui_utils import data_dir
from skytemple.init_locale import LocalePatchedGtkTemplate
from skytemple.module.symbols.model_getter import ModelGetter
from skytemple.module.symbols.symbol_entry.symbol_entry import SymbolEntry
from skytemple.module.symbols.symbol_entry.symbol_entry_builder import SymbolEntryBuilder
from skytemple.module.symbols.store_entry_value_setter import StoreEntryValueSetter
from skytemple_files.hardcoded.symbols.binary_data_getter import BinaryDataGetter
from skytemple_files.hardcoded.symbols.rw_symbol import RWSymbol
from skytemple_files.hardcoded.symbols.unsupported_type_error import UnsupportedTypeError

if TYPE_CHECKING:
    from skytemple.module.symbols.module import SymbolsModule

ALL_BINARIES_ID = "all"

# Dict that contains the name and description of all binaries.
# These IDs must match the ones defined in pmdsky-debug-py (AllSymbolsProtocol). Errors will be thrown otherwise.
BINARIES_DISPLAY_TEXT = {
    ALL_BINARIES_ID: "All binaries",
    "arm9": "arm9 (Main binary)",
    "arm7": "arm7 (Secondary binary)",
    "overlay0": "Overlay 0 (Top menu, common)",
    "overlay1": "Overlay 1 (Top menu, top screen)",
    "overlay2": "Overlay 2 (Wi-Fi)",
    "overlay3": "Overlay 3 (Friend rescue menu)",
    "overlay4": "Overlay 4 (Trade items menu)",
    "overlay5": "Overlay 5 (Trade teams menu)",
    "overlay6": "Overlay 6 (Wonder Mail S menu)",
    "overlay7": "Overlay 7 (WFC main menu)",
    "overlay8": "Overlay 8 (Send Demo Dungeon menu)",
    "overlay9": "Overlay 9 (Sky Jukebox menu)",
    "overlay10": "Overlay 10 (Common to Ground and Dungeon mode)",
    "overlay11": "Overlay 11 (Ground mode)",
    "overlay12": "Overlay 12 (Unused)",
    "overlay13": "Overlay 13 (Personality test)",
    "overlay14": "Overlay 14 (Sentry duty)",
    "overlay15": "Overlay 15 (Duskull Bank)",
    "overlay16": "Overlay 16 (Luminous Spring)",
    "overlay17": "Overlay 17 (Chimeco Assembly)",
    "overlay18": "Overlay 18 (Electrivire Link Shop)",
    "overlay19": "Overlay 19 (Spinda's Juice Bar)",
    "overlay20": "Overlay 20 (Recycle Shop)",
    "overlay21": "Overlay 21 (Croagunk Swap Shop)",
    "overlay22": "Overlay 22 (Overworld Kecleon Shop)",
    "overlay23": "Overlay 23 (Kangaskhan Storage)",
    "overlay24": "Overlay 24 (Chansey Day Care)",
    "overlay25": "Overlay 25 (Xatu Appraisal)",
    "overlay26": "Overlay 26 (Mission completion)",
    "overlay27": "Overlay 27 (Special episode item discard menu)",
    "overlay28": "Overlay 28 (Staff credits)",
    "overlay29": "Overlay 29 (Dungeon mode)",
    "overlay30": "Overlay 30 (Dungeon quicksave)",
    "overlay31": "Overlay 31 (In-dungeon menu)",
    "overlay32": "Overlay 32 (Unused)",
    "overlay33": "Overlay 33 (Unused)",
    "overlay34": "Overlay 34 (Game start)",
    "overlay35": "Overlay 35 (Unused)",
}

# Regex used to extract IDs from the values used in text completion entries. Should match the format used by
# ModelGetter._create_model() when creating dynamic entries.
COMPLETION_ENTRY_REGEX = re.compile(r"\([$#](\d+)\)$")


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "symbols", "main.ui"))
class StSymbolsMainPage(Gtk.Stack):
    """
    Represents the main widget for the symbol editing screen
    """

    __gtype_name__ = "StSymbolsMainPage"

    module: SymbolsModule
    settings: SkyTempleSettingsStore
    item_data: None
    project: RomProject
    symbol_data_getter: BinaryDataGetter
    # IDs of all the binaries that have at least one data symbol
    binaries: List[str]
    # List used to create and store SymbolEntry instances
    entry_list: List[SymbolEntry]

    # UI elements
    content_box: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    check_show_warning: Gtk.CheckButton = cast(Gtk.CheckButton, Gtk.Template.Child())
    binary_combobox: Gtk.ComboBoxText = cast(Gtk.ComboBoxText, Gtk.Template.Child())
    symbols_search: Gtk.SearchEntry = cast(Gtk.SearchEntry, Gtk.Template.Child())
    symbols_treestore: Gtk.TreeStore = cast(Gtk.TreeStore, Gtk.Template.Child())
    symbols_treefilter: Gtk.TreeModelFilter = cast(Gtk.TreeModelFilter, Gtk.Template.Child())
    symbols_completion: Gtk.EntryCompletion = cast(Gtk.EntryCompletion, Gtk.Template.Child())

    def __init__(self, module: SymbolsModule, item_data):
        super().__init__()

        self.module = module
        self.settings = SkyTempleSettingsStore()
        self.item_data = item_data
        project = RomProject.get_current()
        assert project is not None
        self.project = project
        self.symbol_data_getter = BinaryDataGetter(self.project.get_rom_module().get_static_data())
        self.binaries = []
        self.entry_list = []

        self.symbols_treefilter.set_visible_func(filter_callback, self)
        self.set_check_show_warning()

        # Create the ModelGetter instance now so we can call ModelGetter.get() later without having to worry about
        # passing self.project around
        ModelGetter.get_or_create(project)

        self._fill_binary_list()
        self._fill_entries()

        # Default to "all binaries"
        self.binary_combobox.set_active(0)

    def set_check_show_warning(self):
        """
        Checks the config to know whether the warning screen should be shown or not. Sets the state of the checkbox
        accordingly. If it should not be shown, directly shows the content box.
        """
        show_warning = self.settings.get_show_symbols_screen_warning()
        self.check_show_warning.set_active(show_warning)
        if not show_warning:
            self.set_visible_child(self.content_box)

    def _fill_binary_list(self):
        """
        Fills both self.binaries and the binary combobox in the UI
        """
        binaries = self.symbol_data_getter.get_binary_names(["arm", "overlay"])
        binaries.sort(key=sort_bin_names)

        self.binary_combobox.append(ALL_BINARIES_ID, get_binary_display_text(ALL_BINARIES_ID))
        for binary_id in binaries:
            if self.symbol_data_getter.has_data_symbols(binary_id):
                self.binaries.append(binary_id)
                self.binary_combobox.append(binary_id, get_binary_display_text(binary_id))

    def _fill_entries(self):
        """
        Creates all the UI entries, one for each symbol
        """

        # Get all relevant symbols

        # List of symbols. Each entry is a tuple of two elements: The symbol and the ID of its corresponding binary
        symbols: List[Tuple[Symbol, str]] = []
        for binary_id in self.binaries:
            symbols += [(s, binary_id) for s in self.symbol_data_getter.get_data_symbols(binary_id)]
        symbols.sort(key=lambda _entry: _entry[0].name)

        # Loop symbols and create RWSymbol instances and UI elements for each one that has a type
        for entry in symbols:
            symbol = entry[0]
            binary_id = entry[1]
            if symbol.c_type is not None and symbol.c_type != "" and "[Runtime]" not in symbol.description:
                protocol = self.symbol_data_getter.get_binary_section_protocol(binary_id)
                # Try to create an RWSymbol instance
                try:
                    rw_symbol = RWSymbol.from_symbol(symbol)
                except (UnsupportedTypeError, ValueError):
                    # Symbol not supported, skip
                    continue

                symbol_entry = (
                    SymbolEntryBuilder()
                    .set_rom_project(self.project)
                    .set_name_type_desc_from_symbol(symbol)
                    .set_rw_data(rw_symbol, binary_id, protocol)
                    .build()
                )
                symbol_entry.register(self.entry_list, self.symbols_treestore)

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_binary_list_changed(self, binary_list_element: Gtk.ComboBoxText):
        self.symbols_treefilter.refilter()

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_search_input_changed(self, search_entry_element: Gtk.SearchEntry):
        self.symbols_treefilter.refilter()

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_cr_value_completion_editing_started(self, widget: Gtk.CellRenderer, editable: Gtk.CellEditable, path: str):
        if isinstance(editable, Gtk.Entry):
            store_entry = self.symbols_treefilter[path]
            model = store_entry[12]
            self.symbols_completion.set_model(model)
            editable.set_completion(self.symbols_completion)
        else:
            raise NotImplementedError()

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_cr_text_value_changed(self, widget: Gtk.CellRendererText, path: str, new_value: str, *args):
        self.on_value_changed(path, new_value)

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_cr_bool_value_changed(self, widget: Gtk.CellRendererToggle, path: str, *args):
        # The internal state of the widget is updated after the signal handler is run, so to get the new value, we
        # need to invert the current state.
        new_value = not widget.get_active()
        self.on_value_changed(path, "1" if new_value else "0")

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_cr_combo_value_changed(self, widget: Gtk.CellRendererCombo, path: str, new_iter: Gtk.TreeIter, *args):
        # Retrieve the numeric ID of the new value

        # WORKAROUND: For some reason, model-linked properties in the widget are None sometimes when this method
        # is called, even if they are set in the model (in particular, this happens only if the entry is part of
        # a struct).
        # To fix this, we pull the model directly from the TreeFilter.
        model = self.symbols_treefilter[path][12]
        new_value = model[new_iter][0]
        self.on_value_changed(path, str(new_value), new_iter)

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_cr_completion_value_changed(self, widget: Gtk.CellRendererText, path: str, new_value: str, *args):
        match = COMPLETION_ENTRY_REGEX.search(new_value)
        if match:
            _id = match.group(1)
            # Convert to int and then back to string to remove leading zeroes
            new_value_final = str(int(_id))
            self.on_value_changed(path, new_value_final)

    def on_value_changed(self, path: str, new_value: str, model_iter: Optional[Gtk.TreeIter] = None):
        """
        Common value change callback function. Run when the value of one of the simple symbols in the UI is changed.
        Sets the corresponding internal value, both in the SimpleSymbolEntry (which in turn sets it in the corresponding
        binary) and in the TreeModel.
        """
        store_entry = self.symbols_treefilter[path]
        symbol_entry_id = store_entry[6]
        symbol_entry = self.entry_list[symbol_entry_id]

        if new_value == symbol_entry.get_str_value():
            # No need to write the data again or mark the row as unsaved
            return

        if symbol_entry.set_value(new_value):
            StoreEntryValueSetter.set_value(store_entry, new_value, True, model_iter)
            self.module.graphical_mark_as_modified()

    # noinspection PyUnusedLocal
    @Gtk.Template.Callback()
    def on_btn_proceed_clicked(self, widget: Gtk.Button, *args):
        self.set_visible_child(self.content_box)
        show_warning = self.check_show_warning.get_active()
        if not show_warning:
            self.settings.set_show_symbols_screen_warning(False)


def get_binary_display_text(binary_id: str) -> str:
    """
    Given the ID of one of the game's binaries, returns a string with a readable name and a short description
    """
    try:
        return BINARIES_DISPLAY_TEXT[binary_id]
    except KeyError:
        return binary_id


def sort_bin_names(key: str):
    if not key.startswith("overlay"):
        return f"AA_{key}"
    try:
        ov_id = int(key[7:], 10)
        return f"ZZ_Overlay {ov_id:03}"
    except ValueError:
        pass
    return key


def filter_callback(model: Gtk.TreeModel, tree_iter: Gtk.TreeIter, symbols_page: StSymbolsMainPage):
    """
    Callback function called by Gtk.TreeModelFilter in order to determine if a given TreeIter (UI row) should be
    displayed or not.
    """
    model_entry = model[tree_iter]
    entry_name = model_entry[0]
    binary_id = model_entry[7]
    current_search_term = symbols_page.symbols_search.get_text()
    current_binary = symbols_page.binary_combobox.get_active_id()

    # Transform the search term to make it easier to search for symbols without having to match the casing or the
    # underscores
    current_search_term = current_search_term.upper()
    current_search_term = current_search_term.replace(" ", "_")

    # Determine if the row should be displayed, based on the currently selected binary and the current search term.
    if current_search_term != "" and current_search_term not in entry_name:
        # Excluded since it doesn't match the current search
        return False
    if current_binary is None:
        # Excluded since no binary was selected yet
        return False
    if current_binary != ALL_BINARIES_ID and binary_id != current_binary:
        # Excluded since it's not part of the currently selected binary
        return False
    return True
