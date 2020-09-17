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
import logging
import re
from functools import partial
from itertools import zip_longest
from typing import TYPE_CHECKING, Optional, Dict

import cairo
from gi.repository import Gtk, GLib, GdkPixbuf
from gi.repository.Gtk import TreeModel, TreeModelFilter, TreeSelection

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.third_party_util.cellrenderercustomtext import CustomEditable, CellRendererTextView
from skytemple_files.common.ppmdu_config.data import Pmd2Language, Pmd2StringBlock
from skytemple_files.data.str.model import Str
if TYPE_CHECKING:
    from skytemple.module.strings.module import StringsModule

ORANGE = 'orange'
ORANGE_RGB = (1, 0.65, 0)
PATTERN_MD_ENTRY = re.compile(r'.*\(\$(\d+)\).*')
logger = logging.getLogger(__name__)


class StringsController(AbstractController):
    def __init__(self, module: 'StringsModule', lang: Pmd2Language):
        self.module = module
        self.langname = lang.name
        self.filename = lang.filename

        self.builder = None
        self._str: Optional[Str] = None
        self._tree_iters_by_idx: Dict[int, Gtk.TreeIter] = {}
        self._list_store: Optional[Gtk.ListStore] = None
        self._string_cats: Optional[Dict[str, Pmd2StringBlock]] = None
        self._filter: Optional[TreeModelFilter] = None
        self._active_category: Optional[Pmd2StringBlock] = None
        self._search_text = ""

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'strings.glade')
        self.builder.get_object('lang_name').set_text(f'{self.langname} Text Strings')

        self._str = self.module.get_string_file(self.filename)
        self._string_cats = self.module.project.get_rom_module().get_static_data().string_index_data.string_blocks

        self.refresh_cats()
        self.refresh_list()

        self.builder.connect_signals(self)
        return self.builder.get_object('main_box')

    def on_cr_string_edited(self, widget, path, text):
        self._filter[path][1] = text
        self._str.strings[self._filter[path][0] - 1] = text
        self.module.mark_as_modified(self.filename)

    def refresh_cats(self):
        tree: Gtk.TreeView = self.builder.get_object('category_tree')
        cat_store: Gtk.ListStore = tree.get_model()
        cat_store.clear()
        cat_store.append(["(All)", None])
        for cat in self._collect_categories():
            cat_store.append([cat.name, cat])
        tree.get_selection().select_iter(cat_store.get_iter_first())

    def refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('string_tree')

        renderer_editabletext = CellRendererTextView()
        renderer_editabletext.set_property('editable', True)
        column_editabletext = Gtk.TreeViewColumn(
            "String", renderer_editabletext, text=1, editable=2
        )
        tree.append_column(column_editabletext)
        renderer_editabletext.connect('edited', self.on_cr_string_edited)

        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()
        # Iterate strings
        for idx, entry in enumerate(self._str.strings):
            self._list_store.append([idx + 1, entry, True, None])

        # Apply filter
        self._filter: TreeModelFilter = self._list_store.filter_new()
        tree.set_model(self._filter)
        self._filter.set_visible_func(self._visibility_func)

    def on_category_tree_selection_changed(self, selection: TreeSelection):
        """Open a file selected in a tree"""
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            self._active_category = model[treeiter][1]
            self._filter.refilter()

    def on_search_search_changed(self, search: Gtk.SearchEntry):
        self._search_text = search.get_text()
        self._filter.refilter()

    def _visibility_func(self, model, iter, *args):
        if self._active_category is not None:
            if not (self._active_category.begin <= model[iter][0] - 1 < self._active_category.end):
                return False
        if self._search_text != "":
            if self._search_text not in model[iter][1]:
                return False
        return True

    def _collect_categories(self):
        current_index = 0
        for cat in sorted(self._string_cats.values(), key=lambda c: c.begin):
            if cat.begin > current_index:
                # yield a placeholder category
                yield Pmd2StringBlock(f"({current_index} - {cat.begin - 1})", current_index, cat.begin)
            yield cat
            current_index = cat.end
