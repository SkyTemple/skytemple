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
import csv
import logging
import os
import pathlib
import re
import sys
import tempfile
import webbrowser
from typing import TYPE_CHECKING, Dict, Optional, List, Any, Callable, cast

import cairosvg
from gi.repository import Gtk, GLib, Gio, GdkPixbuf
from range_typed_integers import u8, u16, i32, i32_checked, u16_checked, u8_checked, u32

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import is_dark_theme, catch_overflow, builder_get_assert, iter_tree_model
from skytemple.module.monster.level_up_graph import LevelUpGraphProvider
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import open_utf8, add_extension_if_missing
from skytemple_files.data.level_bin_entry.model import LevelBinEntry
from skytemple_files.data.waza_p.protocol import WazaPProtocol, MoveLearnsetProtocol, LevelUpMoveProtocol
from skytemple_files.common.i18n_util import f, _
from skytemple_files.user_error import UserValueError

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule
logger = logging.getLogger(__name__)
MOVE_NAME_PATTERN = re.compile(r'.*\((\d+)\).*')
CSV_LEVEL = _("Level")
CSV_EXP_POINTS = _("Exp. Points")  # TRANSLATORS: Experience Points
CSV_HP = _("HP+")  # TRANSLATORS: Health Points+
CSV_ATK = _("ATK+")  # TRANSLATORS: Attack+
CSV_SP_ATK = _("Sp. ATK+")  # TRANSLATORS: Special Attack+
CSV_DEF = _("DEF+")  # TRANSLATORS: Defense+
CSV_SP_DEF = _("Sp. DEF+")  # TRANSLATORS: Special Defense+


def render_graph_template(title, svg):
    polyfill = """
  (function (constructor) {
    if (constructor &&
        constructor.prototype &&
        constructor.prototype.children == null) {
        Object.defineProperty(constructor.prototype, 'children', {
            get: function () {
                var i = 0, node, nodes = this.childNodes, children = [];
                //iterate all childNodes
                while (node = nodes[i++]) {
                    //remenber those, that are Node.ELEMENT_NODE (1)
                    if (node.nodeType === 1) { children.push(node); }
                }
                return children;
            }
        });
    }
  //apply the fix to all HTMLElements (window.Element) and to SVG/XML (window.Node)
})(window.Node || window.Element);
    """
    return f"""<!DOCTYPE html>
<html>
  <head>
    <script type="text/javascript">{polyfill}</script>
    <script type="text/javascript" src="https://raw.githubusercontent.com/rogodec/svg-innerhtml-polyfill/master/index.js"></script>
    <script type="text/javascript" src="http://kozea.github.com/pygal.js/latest/pygal-tooltips.min.js"></script>
    <title>{title}</title>
  </head>
  <body style="margin:0">
    <figure style="margin:0">
      {svg}
    </figure>
  </body>
</html>
    """


class LevelUpController(AbstractController):
    _last_open_tab_id = 0

    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self.builder: Gtk.Builder = None  # type: ignore
        self.item_id = item_id
        self._string_provider = self.module.project.get_string_provider()
        self._move_names: Dict[int, str] = {}
        self._level_bin_entry: Optional[LevelBinEntry] = None
        self._waza_p: WazaPProtocol = self.module.get_waza_p()
        self._support_webview = False
        self._webview = None
        self._render_graph = True
        self._has_stats = True

    @property
    def has_stats(self) -> bool:
        return self._has_stats

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'level_up.glade')

        self._init_move_names()
        self._init_stats_notebook()
        self._init_move_notebooks()
        self._init_webview()
        self._init_graph()

        notebook = builder_get_assert(self.builder, Gtk.Notebook, 'level_up_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        self.builder.connect_signals(self)
        return notebook

    def on_level_up_notebook_switch_page(self, notebook, page, page_num):
        self.__class__._last_open_tab_id = page_num
        if page_num == 0 and self._render_graph:
            self.render_graph()

    def on_open_browser_clicked(self, *args):
        webbrowser.open_new_tab(pathlib.Path(self.get_tmp_html_path()).as_uri())

    @catch_overflow(i32)
    def on_stats_exp_edited(self, widget, path, text):
        self._edit('stats_store', path, 1, text, i32_checked)
        self._rebuild_stats()

    @catch_overflow(u16)
    def on_stats_hp_edited(self, widget, path, text):
        self._edit('stats_store', path, 2, text, u16_checked)
        self._rebuild_stats()

    @catch_overflow(u8)
    def on_stats_atk_edited(self, widget, path, text):
        self._edit('stats_store', path, 3, text, u8_checked)
        self._rebuild_stats()

    @catch_overflow(u8)
    def on_stats_sp_atk_edited(self, widget, path, text):
        self._edit('stats_store', path, 4, text, u8_checked)
        self._rebuild_stats()

    @catch_overflow(u8)
    def on_stats_def_edited(self, widget, path, text):
        self._edit('stats_store', path, 5, text, u8_checked)
        self._rebuild_stats()

    @catch_overflow(u8)
    def on_stats_sp_def_edited(self, widget, path, text):
        self._edit('stats_store', path, 6, text, u8_checked)
        self._rebuild_stats()

    @catch_overflow(u16)
    def on_level_up_level_edited(self, widget, path, text):
        self._edit('level_up_store', path, 0, text, u16_checked)
        self._rebuild_level_up()

    @catch_overflow(u16)
    def on_level_up_move_edited(self, widget, path, text):
        self._edit_move('level_up_store', path, 1, 2, text)
        self._rebuild_level_up()

    def on_level_up_add_clicked(self, *args):
        self._add('level_up_store', True)
        self._rebuild_level_up()

    def on_level_up_remove_clicked(self, *args):
        self._remove('level_up_tree')
        self._rebuild_level_up()

    @catch_overflow(u32)
    def on_hmtm_move_edited(self, widget, path, text):
        self._edit_move('hmtm_store', path, 0, 1, text)
        self._rebuild_hmtm()

    def on_hmtm_add_clicked(self, *args):
        self._add('hmtm_store')
        self._rebuild_hmtm()

    def on_hmtm_remove_clicked(self, *args):
        self._remove('hmtm_tree')
        self._rebuild_hmtm()

    @catch_overflow(u32)
    def on_egg_move_edited(self, widget, path, text):
        self._edit_move('egg_store', path, 0, 1, text)
        self._rebuild_egg()

    def on_egg_add_clicked(self, *args):
        self._add('egg_store')
        self._rebuild_egg()

    def on_egg_remove_clicked(self, *args):
        self._remove('egg_tree')
        self._rebuild_egg()

    def on_level_up_move_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_moves'))

    def on_hmtm_move_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_moves'))

    def on_egg_move_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_moves'))

    def on_stats_export_clicked(self, *args):
        assert self._level_bin_entry is not None
        dialog = Gtk.FileChooserNative.new(
            _("Save CSV..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        self._add_dialog_file_filters(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, 'csv')
            try:
                rows : List[List[Any]] = [[CSV_LEVEL, CSV_EXP_POINTS, CSV_HP, CSV_ATK, CSV_SP_ATK, CSV_DEF, CSV_SP_DEF]]
                for i, level in enumerate(self._level_bin_entry.levels):
                    rows.append([i + 1, level.experience_required, level.hp_growth,
                                 level.attack_growth, level.special_attack_growth,
                                 level.defense_growth, level.special_defense_growth])
                with open_utf8(fn, 'w', newline='') as file:
                    writer = csv.writer(file)
                    writer.writerows(rows)
            except BaseException as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error saving the CSV.")
                )

    def on_stats_import_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import CSV..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        self._add_dialog_file_filters(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                with open_utf8(fn, mode='r') as csv_file:
                    is_missing = _('is missing in the CSV')
                    content = list(csv.DictReader(csv_file))
                    if CSV_LEVEL not in content[0]:
                        raise ValueError(f'{CSV_LEVEL} {is_missing}.')
                    if CSV_EXP_POINTS not in content[0]:
                        raise ValueError(f'{CSV_EXP_POINTS} {is_missing}.')
                    if CSV_HP not in content[0]:
                        raise ValueError(f'{CSV_HP} {is_missing}.')
                    if CSV_ATK not in content[0]:
                        raise ValueError(f'{CSV_ATK} {is_missing}.')
                    if CSV_SP_ATK not in content[0]:
                        raise ValueError(f'{CSV_SP_ATK} {is_missing}.')
                    if CSV_DEF not in content[0]:
                        raise ValueError(f'{CSV_DEF} {is_missing}.')
                    if CSV_SP_DEF not in content[0]:
                        raise ValueError(f'{CSV_SP_DEF} {is_missing}.')
                    try:
                        levels = [int(row[CSV_LEVEL]) for row in content]
                        for row in content:
                            int(row[CSV_EXP_POINTS])
                            int(row[CSV_HP])
                            int(row[CSV_ATK])
                            int(row[CSV_SP_ATK])
                            int(row[CSV_DEF])
                            int(row[CSV_SP_DEF])
                    except ValueError:
                        raise ValueError(_('All values must be numbers.'))
                    all_levels = set(range(1, 101))
                    if len(levels) != len(all_levels) or set(levels) != all_levels:
                        raise ValueError(_("The CSV must contain one entry per level."))
                    content.sort(key=lambda row: int(row[CSV_LEVEL]))
            except BaseException as err:
                display_error(
                    sys.exc_info(),
                    _("Invalid CSV file:\n") + str(err),
                    _("Error reading the CSV.")
                )
                return
            try:
                store = builder_get_assert(self.builder, Gtk.ListStore, 'stats_store')
                store.clear()
                for row in content:
                    store.append([row[CSV_LEVEL], row[CSV_EXP_POINTS], row[CSV_HP],
                                  row[CSV_ATK], row[CSV_SP_ATK],
                                  row[CSV_DEF], row[CSV_SP_DEF]])
            except BaseException as err:
                display_error(
                    sys.exc_info(),
                    _("Warning: The stats view might be corrupted now,\n"
                      "but the data in ROM is still unchanged,\n"
                      "simply reload this view!\n") + str(err),
                    _("Error reading the CSV.")
                )
                return
            self._rebuild_stats()

    def _rebuild_stats(self):
        assert self._level_bin_entry is not None
        store = builder_get_assert(self.builder, Gtk.ListStore, 'stats_store')
        for row in iter_tree_model(store):
            level, exp, hp, atk, sp_atk, defense, sp_def = (int(x) for x in row)
            level_entry = self._level_bin_entry.levels[level - 1]
            level_entry.experience_required = i32(exp)
            level_entry.hp_growth = u16(hp)
            level_entry.attack_growth = u8(atk)
            level_entry.special_attack_growth = u8(sp_atk)
            level_entry.defense_growth = u8(defense)
            level_entry.special_defense_growth = u8(sp_def)
        self.queue_render_graph()
        self._mark_stats_as_modified()

    def _rebuild_level_up(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'level_up_store')
        learn_set = self._waza_p.learnsets[self.item_id]
        level_up_moves = []
        for row in iter_tree_model(store):
            level_up_moves.append(FileType.WAZA_P.get_level_up_model()(u16(int(row[1])), u16(int(row[0]))))
        level_up_moves.sort(key=lambda l: l.level_id)
        learn_set.level_up_moves = level_up_moves
        self.queue_render_graph()
        self._mark_moves_as_modified()

    def _rebuild_hmtm(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'hmtm_store')
        learn_set = self._waza_p.learnsets[self.item_id]
        learn_set.tm_hm_moves = []
        for row in iter_tree_model(store):
            learn_set.tm_hm_moves.append(u32(int(row[0])))
        self._mark_moves_as_modified()

    def _rebuild_egg(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'egg_store')
        learn_set = self._waza_p.learnsets[self.item_id]
        learn_set.egg_moves = []
        for row in iter_tree_model(store):
            learn_set.egg_moves.append(u32(int(row[0])))
        self._mark_moves_as_modified()

    def _mark_stats_as_modified(self):
        assert self._level_bin_entry is not None
        self.module.set_m_level_bin_entry(self.item_id - 1, self._level_bin_entry)

    def _mark_moves_as_modified(self):
        self.module.mark_waza_as_modified(self.item_id)

    def _edit(self, store_name, path, index, val, check_fn: Callable[[Any], Any]):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        try:
            check_fn(int(val))
        except ValueError:
            return
        store[path][index] = val

    def _edit_move(self, store_name, path, index_id, index_name, val):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        match = MOVE_NAME_PATTERN.match(val)
        if match is None:
            return
        try:
            move_id = u16_checked(int(match.group(1)))
        except ValueError:
            return
        # move name:
        try:
            store[path][index_name] = self._move_names[move_id]
        except KeyError as e:
            raise UserValueError(_("No move with this ID found."))
        # move id:
        store[path][index_id] = move_id

    def _add(self, store_name, with_level=False):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        if with_level:
            store.append(["1", 0, self._move_names[0]])
        else:
            store.append([0, self._move_names[0]])

    def _remove(self, tree_name):
        tree = builder_get_assert(self.builder, Gtk.TreeView, tree_name)
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            cast(Gtk.ListStore, model).remove(treeiter)

    def _init_move_names(self):
        move_names_store = builder_get_assert(self.builder, Gtk.ListStore, 'move_names_store')
        for idx, name in enumerate(self._string_provider.get_all(StringType.MOVE_NAMES)):
            self._move_names[idx] = f'{name} ({idx:03})'
            move_names_store.append([idx, self._move_names[idx]])

    def _init_stats_notebook(self):
        stats_store = builder_get_assert(self.builder, Gtk.ListStore, 'stats_store')

        entry_id = self.item_id - 1
        if entry_id < 0 or entry_id >= self.module.count_m_level_entries():
            # No valid entry
            stats_box = builder_get_assert(self.builder, Gtk.Box, 'stats_box')
            for child in stats_box.get_children():
                stats_box.remove(child)
            self._render_graph = False
            self._has_stats = False
            stats_box.pack_start(Gtk.Label.new(_('This Pokémon has no stats.')), True, True, 0)
        else:
            self._level_bin_entry = self.module.get_m_level_bin_entry(entry_id)
            assert self._level_bin_entry is not None
            for i, level in enumerate(self._level_bin_entry.levels):
                level_id = i + 1
                stats_store.append([
                    str(level_id), str(level.experience_required), str(level.hp_growth),
                    str(level.attack_growth), str(level.special_attack_growth),
                    str(level.defense_growth), str(level.special_defense_growth)
                ])

    def _init_move_notebooks(self):
        level_up_store = builder_get_assert(self.builder, Gtk.ListStore, 'level_up_store')
        hmtm_store = builder_get_assert(self.builder, Gtk.ListStore, 'hmtm_store')
        egg_store = builder_get_assert(self.builder, Gtk.ListStore, 'egg_store')

        if self.item_id < 0 or self.item_id >= len(self._waza_p.learnsets):
            # No valid entry
            level_up_box = builder_get_assert(self.builder, Gtk.Box, 'level_up_box')
            hmtm_box = builder_get_assert(self.builder, Gtk.Box, 'hmtm_box')
            egg_box = builder_get_assert(self.builder, Gtk.Box, 'egg_box')
            for child in level_up_box.get_children():
                level_up_box.remove(child)
            for child in hmtm_box.get_children():
                hmtm_box.remove(child)
            for child in egg_box.get_children():
                egg_box.remove(child)
            level_up_box.pack_start(Gtk.Label.new(_('This Pokémon has no moves.')), True, True, 0)
            hmtm_box.pack_start(Gtk.Label.new(_('This Pokémon has no moves.')), True, True, 0)
            egg_box.pack_start(Gtk.Label.new(_('This Pokémon has no moves.')), True, True, 0)
            self._has_stats = False
        else:
            entry = self._waza_p.learnsets[self.item_id]
            # Level up
            for level_and_move in entry.level_up_moves:
                level_up_store.append([
                    str(level_and_move.level_id),
                    level_and_move.move_id, self._move_names[level_and_move.move_id]
                ])
            # HM/TM
            for move_id in entry.tm_hm_moves:
                hmtm_store.append([
                    move_id, self._move_names[move_id]
                ])
            # Egg
            for move_id in entry.egg_moves:
                egg_store.append([
                    move_id, self._move_names[move_id]
                ])

    def _init_webview(self):
        try:
            import gi
            gi.require_version('WebKit2', '4.0')
            from gi.repository import WebKit2  # type: ignore
            graph_webkit_box = builder_get_assert(self.builder, Gtk.Box, 'graph_webkit_box')

            self._webview: WebKit2.WebView = WebKit2.WebView()  # type: ignore
            self._webview.load_uri(pathlib.Path(self.get_tmp_html_path()).as_uri())  # type: ignore
            scrolled_window: Gtk.ScrolledWindow = Gtk.ScrolledWindow.new()
            scrolled_window.add(self._webview)  # type: ignore
            graph_webkit_box.pack_start(scrolled_window, True, True, 0)

            self._support_webview = True
        except BaseException as ex:
            logger.warning("Failed loading WebKit, falling back to image.", exc_info=ex)

    def _init_graph(self):
        if self._level_bin_entry is None:
            # No valid entry
            graph_box = builder_get_assert(self.builder, Gtk.Box, 'graph_box')
            for child in graph_box.get_children():
                graph_box.remove(child)
            graph_box.pack_start(Gtk.Label.new(_('This Pokémon has no stats.')), True, True, 0)
        else:
            self.queue_render_graph()

    def queue_render_graph(self):
        self._render_graph = True

    def render_graph(self):
        self._render_graph = False
        if self._level_bin_entry is None:
            return
        stack = builder_get_assert(self.builder, Gtk.Stack, 'graph_stack')
        if self.item_id < len(self._waza_p.learnsets):
            learnset = self._waza_p.learnsets[self.item_id]
        else:
            learnset = FileType.WAZA_P.get_learnset_model()([], [], [])
        graph_provider = LevelUpGraphProvider(
            self.module.get_entry(self.item_id), self._level_bin_entry, learnset,
            self._string_provider.get_all(StringType.MOVE_NAMES)
        )
        svg = graph_provider.provide(
            dark=is_dark_theme(MainController.window()),
            disable_xml_declaration=True
        ).render()

        with open_utf8(self.get_tmp_html_path(), 'w') as f:
            f.write(render_graph_template(
                f'{self._string_provider.get_value(StringType.POKEMON_NAMES, self.item_id)} {_("Stats Graph")} (SkyTemple)',
                svg
            ))

        if not self._support_webview:
            graph_fallbck_box = builder_get_assert(self.builder, Gtk.Box, 'graph_fallbck_box')
            first = True
            for child in graph_fallbck_box.get_children():
                if first:
                    first = False
                    continue
                graph_fallbck_box.remove(child)
            stack.set_visible_child(graph_fallbck_box)
            stream = Gio.MemoryInputStream.new_from_bytes(GLib.Bytes.new(
                cairosvg.svg2png(bytestring=bytes(svg, 'utf-8'), dpi=72)
            ))
            pixbuf = GdkPixbuf.Pixbuf.new_from_stream(stream, None)
            img = Gtk.Image.new_from_pixbuf(pixbuf)
            img.show()
            graph_fallbck_box.pack_start(img, True, True, 0)
        else:
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Box, 'graph_webkit_box'))
            self._webview.reload()  # type: ignore

    @staticmethod
    def get_tmp_html_path():
        return os.path.join(tempfile.gettempdir(), 'skytemple_graph.html')

    def _add_dialog_file_filters(self, dialog):
        filter_csv = Gtk.FileFilter()
        filter_csv.set_name(_("CSV (*.csv)"))
        filter_csv.add_mime_type("text/csv")
        filter_csv.add_pattern("*.csv")
        dialog.add_filter(filter_csv)

        filter_any = Gtk.FileFilter()
        filter_any.set_name(_("Any files"))
        filter_any.add_pattern("*")
        dialog.add_filter(filter_any)

