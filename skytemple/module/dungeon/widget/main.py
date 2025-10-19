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
import sys
import textwrap
from itertools import chain
from typing import TYPE_CHECKING, Optional, cast
from collections.abc import Sequence
from gi.repository import Gtk, Gdk
from range_typed_integers import u8, u8_checked
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple.core.string_provider import StringType
from skytemple_files.dungeon_data.mappa_bin.validator.exception import (
    DungeonTotalFloorCountInvalidError,
    DungeonValidatorError,
    InvalidFloorListReferencedError,
    InvalidFloorReferencedError,
    FloorReusedError,
    DungeonMissingFloorError,
)
from skytemple_files.hardcoded.dungeons import DungeonDefinition
from skytemple.controller.main import MainController as MainSkyTempleController
from skytemple_files.common.i18n_util import _
from skytemple.core.ui_utils import iter_tree_model, data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.dungeon.module import DungeonModule, DungeonGroup
DUNGEONS_NAME = _("Dungeons")
DND_TARGETS = [Gtk.TargetEntry.new("MY_TREE_MODEL_ROW", Gtk.TargetFlags.SAME_WIDGET, 0)]
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon", "main.ui"))
class StDungeonMainPage(Gtk.Box):
    __gtype_name__ = "StDungeonMainPage"
    module: DungeonModule
    item_data: None
    edit_groups_img: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    fix_dungeons_img: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    fix_dungeons: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    edit_groups: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    store_dungeon_errors: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    dialog_fix_dungeon_errors: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    button3: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    button4: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    tree_errors: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_errors_fix: Gtk.CellRendererToggle = cast(Gtk.CellRendererToggle, Gtk.Template.Child())
    cr_errors_dungeon: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_dungeons_error_name: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_dungeons_error_description: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_dungeons_solution: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    store_grouped_dungeons: Gtk.TreeStore = cast(Gtk.TreeStore, Gtk.Template.Child())
    dialog_groups: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    button1: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    button2: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    tree_grouped: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    store_ungrouped_dungeons: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())

    def __init__(self, module: DungeonModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.string_provider = self.module.project.get_string_provider()
        # Enable drag and drop
        dungeons_tree = self.tree_grouped
        dungeons_tree.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK, DND_TARGETS, Gdk.DragAction.MOVE)
        dungeons_tree.enable_model_drag_dest(DND_TARGETS, Gdk.DragAction.MOVE)

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.edit_groups_img)
        safe_destroy(self.fix_dungeons_img)
        safe_destroy(self.dialog_fix_dungeon_errors)
        safe_destroy(self.dialog_groups)

    @Gtk.Template.Callback()
    def on_fix_dungeons_clicked(self, *args):
        dialog = self.dialog_fix_dungeon_errors
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())
        dialog.resize(900, 520)
        dungeon_list = self.module.get_dungeon_list()
        validator = self.module.get_validator()
        validator.validate(dungeon_list)
        store = self.store_dungeon_errors
        store.clear()
        validator.errors.sort(key=lambda e: e.dungeon_id)
        for e in validator.errors:
            if not isinstance(e, DungeonTotalFloorCountInvalidError):
                if isinstance(e, FloorReusedError):
                    i = e.reused_of_dungeon_with_id
                    e.reused_of_dungeon_name = f"{'dungeon'} {i} ({self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, i)})"
                dungeon_name = f"{e.dungeon_id}: {self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_MAIN, e.dungeon_id)}"  # selected
                # dungeon_name
                # dungeon_id
                # error_name
                # error_description
                # solution
                # error
                store.append(
                    [
                        True,
                        dungeon_name,
                        e.dungeon_id,
                        textwrap.fill(e.name, 40),
                        textwrap.fill(str(e), 40),
                        textwrap.fill(self._get_solution_text(dungeon_list, e), 40),
                        e,
                    ]
                )
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.APPLY:
            # Step 1, fix all selected errors
            for row in iter_tree_model(store):
                if row[0]:  # selected
                    self._fix_error(dungeon_list, row[6])
            # Step 2, fix all open DungeonTotalFloorCountInvalidError
            validator.validate(dungeon_list)
            for error in validator.errors:
                if isinstance(error, DungeonTotalFloorCountInvalidError):
                    self._fix_error(dungeon_list, error)
            # Step 3 report status
            if not validator.validate(dungeon_list):
                md = SkyTempleMessageDialog(
                    MainSkyTempleController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.WARNING,
                    Gtk.ButtonsType.OK,
                    _(
                        "Dungeon Errors were fixed.\nHowever there are still errors left. Re-open the dialog to fix the rest. If they are still not fixed, please report a bug!"
                    ),
                    title=_("Fix Dungeon Errors"),
                )
            else:
                md = SkyTempleMessageDialog(
                    MainSkyTempleController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("Dungeon Errors were successfully fixed."),
                    title=_("Fix Dungeon Errors"),
                    is_success=True,
                )
            md.run()
            md.destroy()
            self.module.save_dungeon_list(dungeon_list)
            self.module.save_mappa()
            self.module.mark_root_as_modified()
            self.module.rebuild_dungeon_tree()

    @Gtk.Template.Callback()
    def on_cr_errors_fix_toggled(self, widget, path):
        store = self.store_dungeon_errors
        store[path][0] = not widget.get_active()

    @Gtk.Template.Callback()
    def on_edit_groups_clicked(self, *args):
        if not self.module.get_validator().validate(self.module.get_dungeon_list()):
            display_error(
                None,
                _("The game currently contains invalid dungeons. Please click 'Fix Dungeon Errors' first."),
            )
            return
        dialog = self.dialog_groups
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())
        expected_dungeon_ids = self._load_dungeons()
        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.APPLY:
            try:
                # Collect new dungeon groupings and tell module to re-group dungeons
                new_groups: list[DungeonGroup | int] = sorted(self._collect_new_groups_from_dialog(), key=int)
                dungeon_ids_from_dialog = set(
                    chain.from_iterable([x] if isinstance(x, int) else x.dungeon_ids for x in new_groups)
                )
                # Sanity check
                if expected_dungeon_ids != dungeon_ids_from_dialog:
                    display_error(
                        None,
                        _(
                            "Dungeons were missing in the list. This is a bug in SkyTemple! Please try again and report this!"
                        ),
                        _("Failed regrouping the dungeons."),
                    )
                    return
                self.module.regroup_dungeons(new_groups)
            except BaseException as ex:
                display_error(
                    sys.exc_info(),
                    _("An internal error occurred: ") + str(ex),
                    _("Failed regrouping the dungeons."),
                )
                return
        dialog.hide()

    def _load_dungeons(self):
        from skytemple.module.dungeon.module import DungeonGroup

        dungeons_tree = self.tree_grouped
        dungeons = cast(Optional[Gtk.TreeStore], dungeons_tree.get_model())
        assert dungeons is not None
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

    @Gtk.Template.Callback()
    def on_tree_grouped_drag_data_get(self, w: Gtk.TreeView, context, selection: Gtk.SelectionData, target_id, etime):
        model, treeiter = w.get_selection().get_selected()
        if treeiter is not None:
            dungeon_id = model[treeiter][1]
            was_group = model[treeiter][0]
            if not was_group:
                selection.set(selection.get_target(), 8, bytes(dungeon_id, "utf-8"))

    @Gtk.Template.Callback()
    def on_tree_grouped_drag_data_received(
        self, w: Gtk.TreeView, context, x, y, selection: Gtk.SelectionData, info, etime
    ):
        model = cast(Optional[Gtk.TreeStore], w.get_model())
        assert model is not None
        dungeon_id_str = str(selection.get_data(), "utf-8")
        if dungeon_id_str == "":
            return
        dungeon_id = int(dungeon_id_str)
        dungeon_iter = self._find_dungeon_iter(model, dungeon_id)
        assert dungeon_iter is not None
        drop_info = w.get_dest_row_at_pos(x, y)
        if drop_info:
            path, position = drop_info
            if model.get_path(dungeon_iter) != path:  # do not continue when dragging on itself.
                iter = model.get_iter(path)
                did_drag = True
                # Did we drag onto a group or a dungeon in a group?
                new_group_iter = self._get_group_iter(model, iter, position)
                old_group_iter = self._get_group_iter(model, dungeon_iter, Gtk.TreeViewDropPosition.INTO_OR_BEFORE)
                if not new_group_iter:
                    # After/Before top level:
                    # Don't do anything
                    if (
                        position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE
                        or position == Gtk.TreeViewDropPosition.INTO_OR_AFTER
                    ):
                        # Inside top level, dungeon:
                        # Build new group
                        dungeon_id_insert = model[iter][1]
                        before_iter = model.iter_previous(iter)
                        assert iter is not None
                        model.remove(iter)
                        if before_iter is None:
                            new_iter = model.insert(None, 0, self._generate_group_row(dungeon_id_insert))
                        else:
                            new_iter = model.insert_after(
                                model.iter_parent(before_iter),
                                before_iter,
                                self._generate_group_row(dungeon_id_insert),
                            )
                        model.append(new_iter, self._generate_dungeon_row(dungeon_id_insert))
                        model.append(new_iter, self._generate_dungeon_row(dungeon_id))
                        w.expand_row(model.get_path(new_iter), False)
                    elif old_group_iter is not None:
                        self._reinsert(model, dungeon_id, self._generate_dungeon_row(dungeon_id))
                    else:
                        did_drag = False
                elif new_group_iter == iter:
                    # Inside top level, group:
                    # Add to end of group
                    assert new_group_iter is not None
                    model.append(new_group_iter, self._generate_dungeon_row(dungeon_id))
                # After/Before in group / Inside in group:
                # Add it to group after/before this element
                elif position == Gtk.TreeViewDropPosition.INTO_OR_BEFORE or position == Gtk.TreeViewDropPosition.BEFORE:
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
                            rem_iter = model.iter_nth_child(old_group_iter, 0)
                            assert rem_iter is not None
                            dungeon_id_that_was_in_group = model[rem_iter][1]
                            assert old_group_iter is not None
                            model.remove(old_group_iter)
                            self._reinsert(
                                model,
                                dungeon_id_that_was_in_group,
                                self._generate_dungeon_row(dungeon_id_that_was_in_group),
                            )
                    # Select the newly inserted.
                    dungeon_iter = self._find_dungeon_iter(model, dungeon_id)
                    w.get_selection().select_iter(dungeon_iter)
                    w.scroll_to_cell(model.get_path(dungeon_iter), None, True, 0.5, 0.5)
        if context.get_actions() == Gdk.DragAction.MOVE:
            # We remove the source data manual.
            context.finish(True, False, etime)

    def _get_group_iter(
        self,
        model: Gtk.TreeStore,
        liter: Gtk.TreeIter | None,
        position: Gtk.TreeViewDropPosition,
    ) -> Gtk.TreeIter | None:
        # If we drag before or after and not into, we work with the parent instead!
        if position == Gtk.TreeViewDropPosition.BEFORE or position == Gtk.TreeViewDropPosition.AFTER:
            if liter is not None:
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
        return [
            False,
            str(dungeon_id),
            self.string_provider.get_value(StringType.DUNGEON_NAMES_MAIN, dungeon_id),
        ]

    def _generate_group_row(self, base_dungeon_id):
        base_dungeon_id = int(base_dungeon_id)
        return [
            True,
            str(base_dungeon_id),
            self.module.generate_group_label(base_dungeon_id),
        ]

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
            return (self._find_next_dungeon_iter(model, dungeon_id), False)
        # If 0 : Insert at top of tree
        return (None, True)

    def _reinsert(self, model, dungeon_id, new_row):
        # We dragged something out of a group or we removed a group, we need to re-insert.
        after_iter, prepend_instead = self._reinsert_get_pos(model, dungeon_id)
        if not prepend_instead:
            model.insert_before(None, after_iter, new_row)
        else:
            model.prepend(None, new_row)

    # </editor-fold>

    def _collect_new_groups_from_dialog(self, start=None, allow_groups=True) -> Sequence[DungeonGroup | int]:
        from skytemple.module.dungeon.module import DungeonGroup

        model = self.store_grouped_dungeons
        treeiter: Gtk.TreeIter | None
        if start is None:
            treeiter = model.get_iter_first()
        else:
            treeiter = start
        dungeons: list[DungeonGroup | int] = []
        while treeiter is not None:
            if model.iter_n_children(treeiter) > 0:
                assert model[treeiter][0], "Only groups may have children."
                if not allow_groups:
                    raise ValueError("Group was not allowed on this level.")
                sub_group_dungeons = self._collect_new_groups_from_dialog(model.iter_nth_child(treeiter, 0), False)
                assert len(sub_group_dungeons) > 0 and all(isinstance(x, int) for x in sub_group_dungeons)

                dungeons.append(
                    DungeonGroup(sub_group_dungeons[0], sub_group_dungeons, [])  # type: ignore
                )
            else:
                assert not model[treeiter][0], "Empty groups are not allowed."
                dungeons.append(int(model[treeiter][1]))
            treeiter = model.iter_next(treeiter)
        return dungeons

    def _get_solution_text(self, dungeons: list[DungeonDefinition], e: DungeonValidatorError):
        if isinstance(e, InvalidFloorListReferencedError):
            return _("Create a new floor list with one empty floor for this dungeon.")
        if isinstance(e, InvalidFloorReferencedError):
            return _("Correct the floor count for this dungeon. If no floor exists, generate one.")
        if isinstance(e, FloorReusedError):
            return _("Create a new floor list with one empty floor for this dungeon.")
        if isinstance(e, DungeonMissingFloorError):
            # Special case for Regigigas Chamber
            if self._is_regigias_special_case(dungeons, e):
                return _("Remove the unused floor.")
            return _("Add the remaining floors to the dungeon.")
        return "???"

    def _is_regigias_special_case(self, dungeons, e):
        return (
            e.dungeon_id == 61
            and dungeons[e.dungeon_id].mappa_index == 52
            and (dungeons[e.dungeon_id].start_after == 18)
            and (e.floors_in_mappa_not_referenced == [19])
        )

    def _fix_error(self, dungeons: list[DungeonDefinition], e: DungeonValidatorError):
        mappa = self.module.get_mappa()
        if isinstance(e, DungeonTotalFloorCountInvalidError):
            dungeons[e.dungeon_id].number_floors_in_group = e.expected_floor_count_in_group
        elif isinstance(e, InvalidFloorListReferencedError) or isinstance(e, FloorReusedError):
            dungeons[e.dungeon_id].mappa_index = self.module.mappa_generate_and_insert_new_floor_list()
            dungeons[e.dungeon_id].start_after = u8(0)
            dungeons[e.dungeon_id].number_floors = u8(1)
            dungeons[e.dungeon_id].number_floors_in_group = u8(1)
        elif isinstance(e, InvalidFloorReferencedError):
            valid_floors = len(mappa.floor_lists[e.dungeon.mappa_index]) - e.dungeon.start_after
            if valid_floors > 0:
                dungeons[e.dungeon_id].number_floors = u8_checked(valid_floors)
            else:
                mappa.add_floor_to_floor_list(e.dungeon.mappa_index, self.module.mappa_generate_new_floor())
                dungeons[e.dungeon_id].number_floors = u8(1)
        elif isinstance(e, DungeonMissingFloorError):
            # Special case for Regigigas Chamber
            if self._is_regigias_special_case(dungeons, e):
                # Remove additional floors
                # Collect floors to keep
                floor_list = [
                    floor
                    for i, floor in enumerate(mappa.floor_lists[e.dungeon.mappa_index])
                    if i not in e.floors_in_mappa_not_referenced
                ]
                # Then first remove all
                while len(mappa.floor_lists[e.dungeon.mappa_index]) > 0:
                    mappa.remove_floor_from_floor_list(e.dungeon.mappa_index, 0)
                # Re-add floors to keep
                for floor in floor_list:
                    mappa.add_floor_to_floor_list(e.dungeon.mappa_index, floor)
            # Add additional floors
            # TODO: Raise error or warning if we can't fix it? It should really always be consecutive.
            elif min(e.floors_in_mappa_not_referenced) == e.dungeon.start_after + e.dungeon.number_floors:
                if check_consecutive(e.floors_in_mappa_not_referenced):
                    max_floor_id = max(e.floors_in_mappa_not_referenced)
                    dungeons[e.dungeon_id].number_floors = u8_checked(
                        max_floor_id - dungeons[e.dungeon_id].start_after + 1
                    )


def check_consecutive(lst):
    return sorted(lst) == list(range(min(lst), max(lst) + 1))
