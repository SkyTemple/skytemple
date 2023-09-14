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
import logging
import re
from typing import TYPE_CHECKING, Dict, List, Optional, cast

from gi.repository import Gtk

from functools import reduce
from math import gcd
from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.list_icon_renderer import ListIconRenderer
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import glib_async, builder_get_assert, assert_not_none, iter_tree_model
from skytemple.module.dungeon.controller.floor import POKE_CATEGORY_ID, LINKBOX_CATEGORY_ID
from skytemple_files.common.ppmdu_config.dungeon_data import Pmd2DungeonItem, Pmd2DungeonItemCategory
from skytemple.core.module_controller import AbstractController
from skytemple_files.dungeon_data.mappa_bin.protocol import MappaItemListProtocol, Probability, MAX_ITEM_ID
from skytemple_files.common.i18n_util import _
if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule

logger = logging.getLogger(__name__)

PATTERN_MD_ENTRY = re.compile(r'.*\(#(\d+)\).*')

# This is the normal item ID of the link box
# TODO: Have a way to configure this
LINKBOX_ITEM_ID = 362


ITEM_LISTS = [_("E Floors Rewards"),
              _("D Floors Rewards"),
              _("C Floors Rewards"),
              _("B Floors Rewards"),
              _("A Floors Rewards"),
              _("S Floors Rewards"),
              _("★1 Floors Rewards"),
              _("★2 Floors Rewards"),
              _("★3 Floors Rewards"),
              _("★4 Floors Rewards"),
              _("★5 Floors Rewards"),
              _("★6 Floors Rewards"),
              _("★7 Floors Rewards"),
              _("★8 Floors Rewards"),
              _("★9 Floors Rewards"),
              _("Kecleon Shop 1"),
              _("Kecleon Orbs/TMs 1"),
              _("Kecleon Shop 2"),
              _("Kecleon Orbs/TMs 2"),
              _("Kecleon Shop 3"),
              _("Kecleon Orbs/TMs 3"),
              _("Kecleon Shop 4"),
              _("Kecleon Orbs/TMs 4"),
              _("Unknown 1"),
              _("Unknown 2"),
              _("Unknown 3")]


class ItemListsController(AbstractController):
    def __init__(self, module: 'MovesItemsModule', *args):
        self.module = module
        self._item_list: MappaItemListProtocol
        self._item_names: Dict[int, str] = {}
        orig_cats = module.project.get_rom_module().get_static_data().dungeon_data.item_categories

        # TODO: Support editing other item categories?
        self.item_categories = {
            0: orig_cats[0],
            1: orig_cats[1],
            2: orig_cats[2],
            3: orig_cats[3],
            4: orig_cats[4],
            5: orig_cats[5],
            6: orig_cats[6],
            8: orig_cats[8],
            9: orig_cats[9],
            10: orig_cats[10],
        }
        self.categories_for_stores = {
            'item_cat_thrown_pierce_store': orig_cats[0],
            'item_cat_thrown_rock_store': orig_cats[1],
            'item_cat_berries_store': orig_cats[2],
            'item_cat_foods_store': orig_cats[3],
            'item_cat_hold_store': orig_cats[4],
            'item_cat_tms_store': orig_cats[5],
            'item_cat_orbs_store': orig_cats[9],
            'item_cat_others_store': orig_cats[8]
        }

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'item_lists.glade')
        stack = builder_get_assert(self.builder, Gtk.Stack, 'list_stack')

        if not self.module.has_item_lists():
            stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_na'))
            return stack

        self._init_combos()
        self._init_item_spawns()

        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_thrown_pierce_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_thrown_rock_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_berries_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_foods_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_hold_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_tms_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_orbs_store', 4, 3)
        self._recalculate_spawn_chances('item_cat_others_store', 4, 3)
        
        stack.set_visible_child(builder_get_assert(self.builder, Gtk.Widget, 'box_list'))
        self.builder.connect_signals(self)
        return stack

    def _init_combos(self):
        # Init available types
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_list_ids_store')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_list_ids')
        # Init combobox
        cb_store.clear()
        for i, v in enumerate(ITEM_LISTS):
            cb_store.append([i, v])
        cb.set_active(0)
        
    def on_list_id_changed(self, *args):
        self._init_item_spawns()
        
    def _get_list_id(self):
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_list_ids_store')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_list_ids')
        return cb_store[assert_not_none(cb.get_active_iter())][0]

    @glib_async
    def on_cr_items_cat_name_changed(self, widget, path, new_iter, *args):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'item_categories_store')
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cr_item_cat_name_store')
        store[path][0] = cb_store[new_iter][0]
        store[path][1] = cb_store[new_iter][1]
        self._save_item_spawn_rates()
        self._update_cr_item_cat_name_store()

    def on_cr_items_cat_weight_edited(self, widget, path, text):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store = builder_get_assert(self.builder, Gtk.ListStore, 'item_categories_store')
        store[path][4] = text

        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._save_item_spawn_rates()

    def on_item_categories_add_clicked(self, *args):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'item_categories_store')
        dialog = builder_get_assert(self.builder, Gtk.Dialog, 'dialog_category_add')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Init available categories
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'category_add_store')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'category_add_cb')
        available_categories = self._fill_available_categories_into_store(cb_store)
        # Show error if no categories available
        if len(available_categories) < 1:
            display_error(
                None,
                'All categories are already in the list.',
                'Can not add category'
            )
            return
        cb.set_active_iter(cb_store.get_iter_first())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.APPLY:
            row = cb_store[assert_not_none(cb.get_active_iter())]
            store.append([
                row[0], row[1],
                False, "0%", "0"
            ])
            self._save_item_spawn_rates()
            self._update_cr_item_cat_name_store()

    def on_item_categories_remove_clicked(self, *args):
        tree: Gtk.TreeView = builder_get_assert(self.builder, Gtk.TreeView, 'item_categories_tree')
        model, treeiter = tree.get_selection().get_selected()
        if model.iter_n_children() < 2:  # type: ignore
            display_error(
                None,
                "The last category can not be removed.",
                "Can't remove category.",
                should_report=False
            )
            return
        if model is not None and treeiter is not None:
            cast(Gtk.ListStore, model).remove(treeiter)
        self._recalculate_spawn_chances('item_categories_store', 4, 3)
        self._save_item_spawn_rates()

    def on_cr_items_cat_thrown_pierce_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_thrown_pierce_store', path, text)

    def on_cr_items_cat_thrown_pierce_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_thrown_pierce'))

    def on_cr_items_cat_thrown_pierce_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_thrown_pierce_store', path, text)

    def on_item_cat_thrown_pierce_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_thrown_pierce_store')

    def on_item_cat_thrown_pierce_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_thrown_pierce_tree')

    def on_cr_items_cat_thrown_rock_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_thrown_rock_store', path, text)

    def on_cr_items_cat_thrown_rock_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_thrown_rock'))

    def on_cr_items_cat_thrown_rock_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_thrown_rock_store', path, text)

    def on_item_cat_thrown_rock_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_thrown_rock_store')

    def on_item_cat_thrown_rock_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_thrown_rock_tree')

    def on_cr_items_cat_berries_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_berries_store', path, text)

    def on_cr_items_cat_berries_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_berries'))

    def on_cr_items_cat_berries_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_berries_store', path, text)

    def on_item_cat_berries_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_berries_store')

    def on_item_cat_berries_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_berries_tree')

    def on_cr_items_cat_foods_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_foods_store', path, text)

    def on_cr_items_cat_foods_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_foods'))

    def on_cr_items_cat_foods_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_foods_store', path, text)

    def on_item_cat_foods_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_foods_store')

    def on_item_cat_foods_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_foods_tree')

    def on_cr_items_cat_hold_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_hold_store', path, text)

    def on_cr_items_cat_hold_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_hold'))

    def on_cr_items_cat_hold_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_hold_store', path, text)

    def on_item_cat_hold_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_hold_store')

    def on_item_cat_hold_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_hold_tree')

    def on_cr_items_cat_tms_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_tms_store', path, text)

    def on_cr_items_cat_tms_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_tms'))

    def on_cr_items_cat_tms_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_tms_store', path, text)

    def on_item_cat_tms_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_tms_store')

    def on_item_cat_tms_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_tms_tree')

    def on_cr_items_cat_orbs_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_orbs_store', path, text)

    def on_cr_items_cat_orbs_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_orbs'))

    def on_cr_items_cat_orbs_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_orbs_store', path, text)

    def on_item_cat_orbs_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_orbs_store')

    def on_item_cat_orbs_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_orbs_tree')

    def on_cr_items_cat_others_item_name_edited(self, widget, path, text):
        self._on_cat_item_name_changed('item_cat_others_store', path, text)

    def on_cr_items_cat_others_item_name_editing_started(self, renderer, editable, path):
        editable.set_completion(builder_get_assert(self.builder, Gtk.EntryCompletion, 'completion_item_others'))

    def on_cr_items_cat_others_weight_edited(self, widget, path, text):
        self._on_cat_item_weight_changed('item_cat_others_store', path, text)

    def on_item_cat_others_add_clicked(self, *args):
        self._on_cat_item_add_clicked('item_cat_others_store')

    def on_item_cat_others_remove_clicked(self, *args):
        self._on_cat_item_remove_clicked('item_cat_others_tree')

    def _on_cat_item_name_changed(self, store_name: str, path, text: str):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return

        item_ids_already_in = []
        for row in iter_tree_model(store):
            item_ids_already_in.append(int(row[0]))

        try:
            entid = int(match.group(1))
        except ValueError:
            return

        if entid not in self.categories_for_stores[store_name].item_ids():
            display_error(
                None,
                'This item does not belong in this category. Please chose another item.',
                'Invalid item id',
                should_report=False
            )
            return

        if entid in item_ids_already_in:
            display_error(
                None,
                'This item is already in the list.',
                'Can not use this item',
                should_report=False
            )
            return

        store[path][0] = entid
        store[path][1] = self._item_names[entid]
        item_icon_renderer = ListIconRenderer(5)
        itm, _ = self.module.get_item(entid)
        ##################
        ##################
        # DO NOT LOOK
        # this is awful
        liter = store.get_iter_first()
        i = 0
        found = False
        while liter:
            # dear god what is this
            if str(store.get_path(liter)) == path:
                found = True
                break
            liter = store.iter_next(liter)
            i += 1
        row_idx = i
        assert found
        # end of awfulness
        ##################
        ##################
        item_icon = item_icon_renderer.load_icon(
            store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm,)
        )
        store[path][5] = item_icon
        self._save_item_spawn_rates()

    def _on_cat_item_weight_changed(self, store_name: str, path, text: str):
        try:
            v = int(text)
            assert v >= 0
        except:
            return
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        if store[path][2]:
            return
        store[path][4] = text

        self._recalculate_spawn_chances(store_name, 4, 3)
        self._save_item_spawn_rates()

    def _on_cat_item_add_clicked(self, store_name: str):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)

        item_ids_already_in = []
        for row in iter_tree_model(store):
            item_ids_already_in.append(int(row[0]))

        i = 0
        all_item_ids = self.categories_for_stores[store_name].item_ids()
        while True:
            first_item_id = all_item_ids[i]
            if first_item_id not in item_ids_already_in:
                break
            i += 1
            if i >= len(all_item_ids):
                display_error(
                    None,
                    'All items are already in the list',
                    'Can not add item.',
                    should_report=False
                )
                return
        item_icon_renderer = ListIconRenderer(5)
        itm, _ = self.module.get_item(first_item_id)
        row_idx = store.iter_n_children()
        item_icon = item_icon_renderer.load_icon(
            store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm,)
        )
        store.append([
            first_item_id, self._item_names[first_item_id],
            False, "0%", "0", item_icon
        ])
        self._save_item_spawn_rates()

    def _on_cat_item_remove_clicked(self, tree_name: str):
        tree = builder_get_assert(self.builder, Gtk.TreeView, tree_name)
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            cast(Gtk.ListStore, model).remove(treeiter)
        self._recalculate_spawn_chances(Gtk.Buildable.get_name(tree.get_model()), 4, 3)  # type: ignore
        self._save_item_spawn_rates()

    def _init_item_spawns(self):
        self._item_list = self.module.get_item_list(self._get_list_id())
        self._init_item_completion_store()

        item_categories_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_categories_store')
        item_cat_thrown_pierce_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_thrown_pierce_store')
        item_cat_thrown_rock_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_thrown_rock_store')
        item_cat_berries_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_berries_store')
        item_cat_foods_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_foods_store')
        item_cat_hold_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_hold_store')
        item_cat_tms_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_tms_store')
        item_cat_orbs_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_orbs_store')
        item_cat_others_store = builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_others_store')
        item_stores = {
            self.item_categories[0]: item_cat_thrown_pierce_store,
            self.item_categories[1]: item_cat_thrown_rock_store,
            self.item_categories[2]: item_cat_berries_store,
            self.item_categories[3]: item_cat_foods_store,
            self.item_categories[4]: item_cat_hold_store,
            self.item_categories[5]: item_cat_tms_store,
            self.item_categories[9]: item_cat_orbs_store,
            self.item_categories[8]: item_cat_others_store
        }

        # Clear everything
        for s in [item_categories_store] + list(item_stores.values()):
            s.clear()

        il = self._item_list

        # Add item categories
        relative_weights = self._calculate_relative_weights(list(il.categories.values()))
        sum_of_all_weights = sum(relative_weights)
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
        for i, (category, chance) in enumerate(il.categories.items()):
            relative_weight = relative_weights[i]
            if category not in self.item_categories.keys():
                continue  # TODO: Support editing other item categories?
            name = self.item_categories[category].name_localized
            chance_str = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
            item_categories_store.append([
                category, name, False,
                chance_str, str(relative_weight)
            ])

        # Add items
        items_by_category = self._split_items_in_list_in_cats(il.items)
        for j, (category_m, store) in enumerate(item_stores.items()):
            item_icon_renderer = ListIconRenderer(5)
            cat_items = items_by_category[category_m.id]
            relative_weights = self._calculate_relative_weights([v for v in cat_items.values()])
            sum_of_all_weights = sum(relative_weights)
            if sum_of_all_weights <= 0:
                sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
            i = 0
            for row_idx, (item, stored_weight) in enumerate(cat_items.items()):
                relative_weight = relative_weights[i]
                i += 1
                name = self._item_names[item]
                chance_str = f'{int(relative_weight) / sum_of_all_weights * 100:.3f}%'
                itm, _ = self.module.get_item(item)
                item_icon = item_icon_renderer.load_icon(
                    store, self.module.project.get_sprite_provider().get_for_item, row_idx, row_idx, (itm, )
                )
                store.append([
                    item, name, False,
                    chance_str, str(relative_weight), item_icon
                ])
        self._update_cr_item_cat_name_store()

    def _split_items_in_list_in_cats(
            self, items: Dict[int, Probability]
    ) -> Dict[int, Dict[int, Probability]]:
        out_items: Dict[int, Dict[int, Probability]] = {}
        for cat in self.item_categories.values():
            out_items[cat.id] = {}
            for item, probability in items.items():
                if cat.is_item_in_cat(item):
                    out_items[cat.id][item] = probability
        return out_items

    def _init_item_completion_store(self):
        completion_item_thrown_pierce_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_thrown_pierce_store')
        completion_item_thrown_rock_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_thrown_rock_store')
        completion_item_berries_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_berries_store')
        completion_item_foods_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_foods_store')
        completion_item_hold_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_hold_store')
        completion_item_tms_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_tms_store')
        completion_item_orbs_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_orbs_store')
        completion_item_others_store = builder_get_assert(self.builder, Gtk.ListStore, 'completion_item_others_store')
        completion_stores = {
            self.item_categories[0]: completion_item_thrown_pierce_store,
            self.item_categories[1]: completion_item_thrown_rock_store,
            self.item_categories[2]: completion_item_berries_store,
            self.item_categories[3]: completion_item_foods_store,
            self.item_categories[4]: completion_item_hold_store,
            self.item_categories[5]: completion_item_tms_store,
            self.item_categories[9]: completion_item_orbs_store,
            self.item_categories[8]: completion_item_others_store
        }

        for i in range(0, MAX_ITEM_ID):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self._item_names[i] = f'{name} (#{i:03})'

        for category, store in completion_stores.items():
            for item in category.item_ids():
                store.append([self._item_names[item]])

    def _calculate_relative_weights(self, list_of_weights: List[int]) -> List[int]:
        weights = []
        if len(list_of_weights) < 1:
            return []
        for i in range(0, len(list_of_weights)):
            weight = list_of_weights[i]
            if weight != 0:
                last_nonzero = i - 1
                while last_nonzero >= 0 and list_of_weights[last_nonzero] == 0:
                    last_nonzero -= 1
                if last_nonzero != -1:
                    weight -= list_of_weights[last_nonzero]
            weights.append(weight)
        weights_nonzero = [w for w in weights if w != 0]
        weights_gcd = 1
        if len(weights_nonzero) > 0:
            weights_gcd = reduce(gcd, weights_nonzero)
        return [int(w / weights_gcd) for w in weights]

    def _recalculate_spawn_chances(self, store_name, weight_idx, chance_idx):
        store = builder_get_assert(self.builder, Gtk.ListStore, store_name)
        sum_of_all_weights = sum(int(row[weight_idx]) for row in iter_tree_model(store))
        if sum_of_all_weights <= 0:
            sum_of_all_weights = 1  # all weights are zero, so we just set this to 1 so it doesn't / by 0.
        for row in iter_tree_model(store):
            if sum_of_all_weights == 0:
                row[chance_idx] = '0.00%'
            else:
                row[chance_idx] = f'{int(row[weight_idx]) / sum_of_all_weights * 100:.2f}%'


    def _fill_available_categories_into_store(self, cb_store):
        available_categories = [
            cat for cat in self.item_categories.values()
            if cat not in self._item_list.categories.keys()
        ]
        # Init combobox
        cb_store.clear()
        for cat in available_categories:
            cb_store.append([cat.value, cat.name_localized])
        return available_categories
    
    def _update_cr_item_cat_name_store(self):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'cr_item_cat_name_store')
        self._fill_available_categories_into_store(store)

    def _save_item_spawn_rates(self):
        item_stores = {
            None: builder_get_assert(self.builder, Gtk.ListStore, 'item_categories_store'),
            self.item_categories[0]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_thrown_pierce_store'),
            self.item_categories[1]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_thrown_rock_store'),
            self.item_categories[2]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_berries_store'),
            self.item_categories[3]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_foods_store'),
            self.item_categories[4]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_hold_store'),
            self.item_categories[5]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_tms_store'),
            self.item_categories[9]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_orbs_store'),
            self.item_categories[8]: builder_get_assert(self.builder, Gtk.ListStore, 'item_cat_others_store')
        }

        category_weights = {}
        item_weights = {}
        for (cat, store) in item_stores.items():

            rows = []
            for row in iter_tree_model(store):
                rows.append(row[:])
            rows.sort(key=lambda e: e[0])

            sum_of_weights = sum((int(row[4]) for row in iter_tree_model(store) if row[2] is False))

            last_weight = 0
            last_weight_set_idx = None
            for row in rows:
                # Add Poké and Link Box items for those categories
                if not cat:
                    if row[0] == POKE_CATEGORY_ID:
                        item_weights[self.item_categories[POKE_CATEGORY_ID].item_ids()[0]] = 10000
                    if row[0] == LINKBOX_CATEGORY_ID:
                        item_weights[self._get_link_box_item_id()] = 10000
                was_set = False
                weight = 0
                if row[4] != "0":
                    weight = last_weight + int(10000 * (int(row[4]) / sum_of_weights))
                    last_weight = weight
                    was_set = True
                if cat is None:
                    set_idx = self.item_categories[row[0]].id
                    category_weights[set_idx] = weight
                    if was_set:
                        last_weight_set_idx = set_idx
                else:
                    set_idx = row[0]
                    item_weights[row[0]] = weight
                    if was_set:
                        last_weight_set_idx = set_idx
            if last_weight_set_idx is not None:
                if last_weight != 0 and last_weight != 10000:
                    # We did not sum up to exactly 10000, so the values we entered are not evenly
                    # divisible. Find the last non-zero we set and set it to 10000.
                    if cat is None:
                        category_weights[last_weight_set_idx] = 10000
                    else:
                        item_weights[last_weight_set_idx] = 10000

        item_weights = {k: v for k, v in sorted(item_weights.items(), key=lambda x: x[0])}

        il = self._item_list
        il.categories = category_weights
        il.items = item_weights

        self.module.mark_item_list_as_modified(self._get_list_id())

    def _get_link_box_item_id(self):
        item_ids = self.item_categories[LINKBOX_CATEGORY_ID].item_ids()
        if LINKBOX_ITEM_ID in item_ids:
            return LINKBOX_ITEM_ID
        return item_ids[0]
