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
import sys
from itertools import chain
from typing import TYPE_CHECKING, Optional, List, Union

from gi.repository import Gtk, Gdk

from skytemple.core.error_handler import display_error
from skytemple.core.module_controller import AbstractController
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple.core.string_provider import StringType

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonGroup

DUNGEONS_NAME = 'Dungeons'
DND_TARGETS = [
    ('MY_TREE_MODEL_ROW', Gtk.TargetFlags.SAME_WIDGET, 0)
]


class MainController(AbstractController):
    def __init__(self, module: 'DungeonModule', *args):
        self.module = module

        self.builder = None

        self.string_provider = self.module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'main.glade')

        # Enable drag and drop
        dungeons_tree: Gtk.TreeView = self.builder.get_object('tree_grouped')
        dungeons_tree.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, DND_TARGETS, Gdk.DragAction.MOVE)
        dungeons_tree.enable_model_drag_dest(DND_TARGETS, Gdk.DragAction.MOVE)

        self.builder.connect_signals(self)
        return self.builder.get_object('main_box')

    def on_edit_groups_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_groups')
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())

        expected_dungeon_ids = self._load_dungeons()

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.APPLY:
            try:
                # Collect new dungeon groupings and tell module to re-group dungeons
                new_groups: List[Union['DungeonGroup', int]] = sorted(self._collect_new_groups_from_dialog(), key=int)
                dungeon_ids_from_dialog = set(chain.from_iterable([x] if isinstance(x, int) else x.dungeon_ids for x in new_groups))

                # Sanity check
                if expected_dungeon_ids != dungeon_ids_from_dialog:
                    display_error(
                        None,
                        "Dungeons were missing in the list. This is a bug in SkyTemple! "
                        "Please try again and report this!",
                        "Failed regrouping the dungeons."
                    )
                    return

                self.module.regroup_dungeons(new_groups)
            except BaseException as ex:
                display_error(
                    sys.exc_info(),
                    "An internal error occurred: " + str(ex),
                    "Failed regrouping the dungeons."
                )
                return

        dialog.hide()

    def _load_dungeons(self):
        from skytemple.module.dungeon.module import DungeonGroup

        dungeons_tree: Gtk.TreeView = self.builder.get_object('tree_grouped')
        dungeons: Gtk.TreeStore = dungeons_tree.get_model()
        dungeons.clear()

        dungeon_ids = set()
        for dungeon_or_group in self.module.load_dungeons():
            if isinstance(dungeon_or_group, DungeonGroup):
                group_root = dungeons.append(None, self._generate_group_row(dungeon_or_group.base_dungeon_id))
                for dungeon_id in dungeon_or_group.dungeon_ids:
                    dungeon_ids.add(dungeon_id)
                    dungeons.append(group_root, self._generate_dungeon_row(dungeon_id))
            else:
                dungeon_ids.add(dungeon_or_group)
                dungeons.append(None, self._generate_dungeon_row(dungeon_or_group))
        return dungeon_ids

    # <editor-fold desc="DRAGGING AND DROPPING IN THE GROUP DIALOG" defaultstate="collapsed">

    def on_tree_grouped_drag_data_get(self, w: Gtk.TreeView, context, selection: Gtk.SelectionData, target_id, etime):
        model, treeiter = w.get_selection().get_selected()
        dungeon_id = model[treeiter][1]
        was_group = model[treeiter][0]
        if not was_group:
            selection.set(selection.get_target(), 8, bytes(dungeon_id, 'utf-8'))

    def on_tree_grouped_drag_data_received(self, w: Gtk.TreeView, context, x, y, selection: Gtk.SelectionData, info, etime):
        model: Gtk.TreeStore = w.get_model()
        dungeon_id = int(str(selection.get_data(), 'utf-8'))
        dungeon_iter = self._find_dungeon_iter(model, dungeon_id)
        assert dungeon_iter is not None

        drop_info = w.get_dest_row_at_pos(x, y)

        if drop_info:
            path, position = drop_info
            iter = model.get_iter(path)
            did_drag = True

            # Did we drag onto a group or a dungeon in a group?
            new_group_iter = self._get_group_iter(model, iter, position)
            old_group_iter = self._get_group_iter(model, dungeon_iter, Gtk.TreeViewDropPosition.INTO_OR_BEFORE)

            if not new_group_iter:
                # After/Before top level:
                # Don't do anything
                if position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE or position == Gtk.TreeViewDropPosition.INTO_OR_AFTER:
                    # Inside top level, dungeon:
                    # Build new group
                    dungeon_id_insert = model[iter][1]
                    before_iter = model.iter_previous(iter)
                    assert iter is not None
                    model.remove(iter)
                    new_iter = model.insert_after(model.iter_parent(before_iter), before_iter, self._generate_group_row(
                        dungeon_id_insert
                    ))
                    model.append(new_iter, self._generate_dungeon_row(dungeon_id_insert))
                    model.append(new_iter, self._generate_dungeon_row(dungeon_id))
                    w.expand_row(model.get_path(new_iter), False)
                elif old_group_iter is not None:
                    self._reinsert(model, dungeon_id, self._generate_dungeon_row(dungeon_id))
                else:
                    did_drag = False
            else:
                if new_group_iter == iter:
                    # Inside top level, group:
                    # Add to end of group
                    assert new_group_iter is not None
                    model.append(new_group_iter, self._generate_dungeon_row(dungeon_id))
                else:
                    # After/Before in group / Inside in group:
                    # Add it to group after/before this element
                    if position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE or position == Gtk.TreeViewDropPosition.BEFORE:
                        assert new_group_iter is not None
                        model.insert_before(new_group_iter, iter, self._generate_dungeon_row(dungeon_id))
                    else:
                        assert new_group_iter is not None
                        model.insert_after(new_group_iter, iter, self._generate_dungeon_row(dungeon_id))

            if did_drag:
                assert dungeon_iter is not None
                # Remove the original iter.
                model.remove(dungeon_iter)

                # Check if group headers (main id) needs to be rewritten:
                if old_group_iter:
                    self._rewrite_group_header_id_and_pos(model, old_group_iter)
                if new_group_iter and new_group_iter != old_group_iter:
                    self._rewrite_group_header_id_and_pos(model, new_group_iter)

                if old_group_iter and old_group_iter != new_group_iter:
                    # If was in group:
                    # Remove from group
                    # (If removing dungeons from a group, recalculate group id, name,
                    # position and if it even still needs to exist)
                    if model.iter_n_children(old_group_iter) < 2:
                        # Remove group
                        dungeon_id_that_was_in_group = model[model.iter_nth_child(old_group_iter, 0)][1]
                        assert old_group_iter is not None
                        model.remove(old_group_iter)
                        self._reinsert(model, dungeon_id_that_was_in_group, self._generate_dungeon_row(dungeon_id_that_was_in_group))

                # Select the newly inserted.
                dungeon_iter = self._find_dungeon_iter(model, dungeon_id)
                w.get_selection().select_iter(dungeon_iter)
                w.scroll_to_cell(model.get_path(dungeon_iter), None, True, 0.5, 0.5)

        if context.get_actions() == Gdk.DragAction.MOVE:
            # We remove the source data manual.
            context.finish(True, False, etime)

    def _get_group_iter(self, model: Gtk.TreeStore, liter: Gtk.TreeIter,
                        position: Gtk.TreeViewDropPosition) -> Optional[Gtk.TreeIter]:
        # If we drag before or after and not into, we work with the parent instead!
        if position == Gtk.TreeViewDropPosition.BEFORE or position == Gtk.TreeViewDropPosition.AFTER:
            liter = model.iter_parent(liter)

        if liter:
            if model[liter][0]:
                return liter
            else:
                parent = model.iter_parent(liter)
                if parent and model[parent][0]:
                    return parent
        return None

    def _generate_dungeon_row(self, dungeon_id):
        dungeon_id = int(dungeon_id)
        return [False, str(dungeon_id), self.string_provider.get_value(StringType.DUNGEON_NAMES_MAIN, dungeon_id)]

    def _generate_group_row(self, base_dungeon_id):
        base_dungeon_id = int(base_dungeon_id)
        return [True, str(base_dungeon_id), self.module.generate_group_label(base_dungeon_id)]

    def _find_dungeon_iter(self, model, dungeon_id, start=None):
        if start:
            treeiter = start
        else:
            treeiter = model.get_iter_first()
        while treeiter is not None:
            if model.iter_n_children(treeiter) > 0:
                candidate = self._find_dungeon_iter(model, dungeon_id, model.iter_nth_child(treeiter, 0))
                if candidate:
                    return candidate

            if not model[treeiter][0] and model[treeiter][1] == str(dungeon_id):
                return treeiter

            treeiter = model.iter_next(treeiter)
        return None

    def _find_next_dungeon_iter(self, model, dungeon_id):
        """Returns the dungeon or group iter right after the given dungeon ID, so the place to insert the dungeon at."""
        treeiter = model.get_iter_first()
        while treeiter is not None:
            this_id = int(model[treeiter][1])
            if this_id > dungeon_id:
                return treeiter
            treeiter = model.iter_next(treeiter)
        return None

    def _rewrite_group_header_id_and_pos(self, model, group_iter):
        current_group_dungeon_id = model[group_iter][1]
        first_dungeon_in_group_id = model[model.iter_nth_child(group_iter, 0)][1]
        if current_group_dungeon_id != first_dungeon_in_group_id:
            # We need to re-write...
            model[group_iter][:] = self._generate_group_row(first_dungeon_in_group_id)
            after_iter, prepend_instead = self._reinsert_get_pos(model, first_dungeon_in_group_id)
            if not prepend_instead:
                model.move_before(group_iter, after_iter)
            else:
                model.move_after(group_iter, None)

    def _reinsert_get_pos(self, model, dungeon_id):
        """Returns where to insert a dungeon on the top level. Second returned value is True? Then just prepend!"""
        dungeon_id = int(dungeon_id)
        if dungeon_id > 0:
            # Get next dungeon and insert before
            return self._find_next_dungeon_iter(model, dungeon_id), False
        # If 0 : Insert at top of tree
        return None, True

    def _reinsert(self, model, dungeon_id, new_row):
        # We dragged something out of a group or we removed a group, we need to re-insert.
        after_iter, prepend_instead = self._reinsert_get_pos(model, dungeon_id)
        if not prepend_instead:
            model.insert_before(None, after_iter, new_row)
        else:
            model.prepend(None, new_row)

    # </editor-fold>

    def _collect_new_groups_from_dialog(self, start=None, allow_groups=True) -> List[Union['DungeonGroup', int]]:
        from skytemple.module.dungeon.module import DungeonGroup
        model: Gtk.TreeStore = self.builder.get_object('store_grouped_dungeons')
        treeiter: Gtk.TreeIter
        if start is None:
            treeiter = model.get_iter_first()
        else:
            treeiter = start

        dungeons = []
        while treeiter is not None:
            if model.iter_n_children(treeiter) > 0:
                assert model[treeiter][0], "Only groups may have children."
                if not allow_groups:
                    raise ValueError("Group was not allowed on this level.")
                sub_group_dungeons = self._collect_new_groups_from_dialog(model.iter_nth_child(treeiter, 0), False)
                assert len(sub_group_dungeons) > 0 and all(isinstance(x, int) for x in sub_group_dungeons)
                dungeons.append(DungeonGroup(
                    sub_group_dungeons[0], sub_group_dungeons, []
                ))
            else:
                assert not model[treeiter][0], "Empty groups are not allowed."
                dungeons.append(int(model[treeiter][1]))

            treeiter = model.iter_next(treeiter)
        return dungeons
