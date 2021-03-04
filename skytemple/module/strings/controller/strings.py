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
import csv
import logging
import re
import sys
from typing import TYPE_CHECKING, Optional, Dict

from gi.repository import Gtk
from gi.repository.Gtk import TreeModelFilter, TreeSelection

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.third_party_util.cellrenderercustomtext import CellRendererTextView
from skytemple.core.ui_utils import add_dialog_csv_filter
from skytemple_files.common.ppmdu_config.data import Pmd2Language, Pmd2StringBlock
from skytemple_files.data.str.model import Str, open_utf8
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.strings.module import StringsModule

ORANGE = 'orange'
ORANGE_RGB = (1, 0.65, 0)
PATTERN_MD_ENTRY = re.compile(r'.*\(\$(\d+)\).*')
logger = logging.getLogger(__name__)


class StringsController(AbstractController):
    def __init__(self, module: 'StringsModule', lang: Pmd2Language):
        self.module = module
        self.langname = lang.name_localized
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
        self.builder.get_object('lang_name').set_text(f(_('{self.langname} Text Strings')))

        self._str = self.module.get_string_file(self.filename)
        self._string_cats = self.module.project.get_rom_module().get_static_data().string_index_data.string_blocks

        self.refresh_cats()
        self.refresh_list()

        self.builder.connect_signals(self)
        return self.builder.get_object('main_box')

    def on_cr_string_edited(self, widget, path, text):
        idx = self._filter[path][0] - 1
        logger.debug(f'String edited - {idx} - {path} - {self._str.strings[idx]} -> {text}')
        self._filter[path][1] = text
        self._str.strings[idx] = text
        self.module.mark_as_modified(self.filename)

    def refresh_cats(self):
        tree: Gtk.TreeView = self.builder.get_object('category_tree')
        cat_store: Gtk.ListStore = tree.get_model()
        cat_store.clear()
        cat_store.append([_("(All)"), None])
        for cat in self._collect_categories():
            cat_store.append([cat.name_localized, cat])
        tree.get_selection().select_iter(cat_store.get_iter_first())

    def refresh_list(self):
        tree: Gtk.TreeView = self.builder.get_object('string_tree')

        renderer_editabletext = CellRendererTextView()
        renderer_editabletext.set_property('editable', True)
        column_editabletext = Gtk.TreeViewColumn(
            _("String"), renderer_editabletext, text=1, editable=2
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

    def on_btn_import_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Import is done from a CSV file with the following specifications:\n"
              "- Has to contain all strings in order, one per row\n"
              "- Strings may be quoted with: \" and escaped with double quotes.")
        )
        md.run()
        md.destroy()
        save_diag = Gtk.FileChooserNative.new(
            _("Import strings from..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        add_dialog_csv_filter(save_diag)
        response = save_diag.run()
        fn = save_diag.get_filename()
        save_diag.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                with open_utf8(fn) as csv_file:
                    csv_reader = csv.reader(csv_file)
                    strings = []
                    for row in csv_reader:
                        if len(row) > 0:
                            strings.append(row[0])
                    if len(self._str.strings) != len(strings):
                        raise ValueError(f(_("The CSV file must contain exactly {len(self._str.strings)} strings, "
                                             "has {len(strings)}.")))
                    self._str.strings = strings
                self.module.mark_as_modified(self.filename)
                MainController.reload_view()
            except BaseException as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error exporting the strings.")
                )

    def on_btn_export_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Export is done to a CSV file with the following specifications:\n"
              "- Contains all strings in order, one per row\n"
              "- Strings may be quoted with: \" and escaped with double quotes.")
        )
        md.run()
        md.destroy()

        save_diag = Gtk.FileChooserNative.new(
            _("Export strings as..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        add_dialog_csv_filter(save_diag)
        response = save_diag.run()
        fn = save_diag.get_filename()
        save_diag.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.csv'
            with open_utf8(fn, 'w') as result_file:
                wr = csv.writer(result_file)
                wr.writerows([[x] for x in self._str.strings])

    def _visibility_func(self, model, iter, *args):
        if self._active_category is not None:
            if not (self._active_category.begin <= model[iter][0] - 1 < self._active_category.end):
                return False
        if self._search_text != "":
            if self._search_text.lower() not in model[iter][1].lower():
                return False
        return True

    def _collect_categories(self):
        current_index = 0
        for cat in sorted(self._string_cats.values(), key=lambda c: c.begin):
            if cat.begin > current_index:
                # yield a placeholder category
                name = f"({current_index} - {cat.begin - 1})"
                yield Pmd2StringBlock(name, name, current_index, cat.begin)
            yield cat
            current_index = cat.end
