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
from __future__ import annotations

from enum import Enum, auto
from typing import Optional, TYPE_CHECKING, Union, Any, Type, Iterable, cast

from gi.repository import Gtk

if TYPE_CHECKING:
    from skytemple.core.abstract_module import AbstractModule
    from skytemple.core.module_controller import AbstractController


class RecursionType(Enum):
    NONE = auto()
    UP = auto()
    DOWN = auto()


class ItemTreeEntryRef:
    """
    A reference to an entry in the SkyTemple item tree.
    """
    _tree: Gtk.TreeStore
    _self: Gtk.TreeIter

    # DO NOT construct these yourself in module code.
    def __init__(self, tree: Gtk.TreeStore, node: Gtk.TreeIter):
        """Create a reference. This must not be used from modules."""
        self._tree = tree
        self._self = node

    def entry(self) -> ItemTreeEntry:
        row = self._tree[self._self]
        return ItemTreeEntry(
            row[0], row[1], row[2], row[3], row[4]
        )

    def update(self, new_entry_data: ItemTreeEntry):
        """Update the entry. All kwargs-only parameters in __init__ of ItemTreeEntry are ignored."""
        row = self._tree[self._self]
        row[0] = new_entry_data.icon
        row[1] = new_entry_data.name
        row[2] = new_entry_data.module
        row[3] = new_entry_data.view_class
        row[4] = new_entry_data.item_data
        _recursive_generate_item_store_row_label(row)

    def delete_all_children(self):
        """Delete all child nodes. Warning: This invalidates any `ItemTreeEntryRef` pointing to old children."""
        child = self._tree.iter_children(self._self)
        while child is not None:
            nxt = self._tree.iter_next(child)
            self._tree.remove(child)
            child = nxt

    def children(self) -> Iterable[ItemTreeEntryRef]:
        children = []
        titer = self._tree.iter_children(self._self)
        while titer is not None:
            children.append(ItemTreeEntryRef(self._tree, titer))
            titer = self._tree.iter_next(titer)
        return children


class ItemTreeEntry:
    """
    An entry to be placed in the SkyTemple item tree.
    """
    __slots__ = [
        '_icon',
        '_name',
        '_module',
        '_view_class',
        '_item_data',
        '_modified'
    ]

    _icon: str
    _name: str
    _module: AbstractModule
    _view_class: Union[Type[Gtk.Widget], Type[AbstractController]]
    _item_data: Any
    _modified: bool

    def __init__(
        self,
        icon: str,
        name: str,
        module: AbstractModule,
        view_class: Union[Type[Gtk.Widget], Type[AbstractController]],
        item_data: Any,
        *,
        modified: bool = False
    ):
        """
        Create an entry model. This can be added to an item tree or used to update an `ItemTreeEntryRef`.
        Modules should not try to set the kwargs-only arguments,
        as they are ignored by add/update operations.

        The `view_class` should be a `Gtk.Widget`. The controller based approach is deprecated.
        If a widget is used it must take exactly two parameters for __init__:

        - module: The `AbstractModule` that the view was loaded from.
                  This is the `module` value passed into this method.
        - item_data: The `item_data` object that can provide additional context to
                     the view, such as a file name or ID that is currently being edited.
                     This is the `item_data` value passed into this method.
        """
        self._icon = icon
        self._name = name
        self._module = module
        self._view_class = view_class
        self._item_data = item_data
        self._modified = modified

    @property
    def icon(self) -> str:
        return self._icon

    @property
    def name(self) -> str:
        return self._name

    @property
    def module(self) -> AbstractModule:
        return self._module

    @property
    def view_class(self) -> Union[Type[Gtk.Widget], Type[AbstractController]]:
        return self._view_class

    @property
    def item_data(self) -> Any:
        return self._item_data

    @property
    def modified(self) -> bool:
        return self._modified


# noinspection PyProtectedMember
class ItemTree:
    """
    The SkyTemple item tree (navigation tree on the left side of the UI).
    """
    _tree: Gtk.TreeStore
    _root_node: Optional[Gtk.TreeIter]
    _finalized: bool

    # DO NOT construct these yourself in module code.
    def __init__(self, tree: Gtk.TreeStore):
        """Create a reference. This must not be used from modules."""
        self._tree = tree
        self._root_node = None
        self._finalized = False

    def set_root(self, root: ItemTreeEntry) -> ItemTreeEntryRef:
        """This must only be called from the ROM module."""
        new_iter = self._tree.append(None, [
            root.icon,
            root.name,
            root.module,
            root.view_class,
            root.item_data,
            False,
            '',
            True
        ])
        self._root_node = new_iter
        return ItemTreeEntryRef(self._tree, new_iter)

    def add_entry(self, root: Optional[ItemTreeEntryRef], entry: ItemTreeEntry) -> ItemTreeEntryRef:
        """Add a new entry. All kwargs-only parameters in __init__ of ItemTreeEntry are ignored."""
        root_iter = self._root_node
        if root is not None:
            root_iter = root._self
        assert root_iter is not None
        new_iter = self._tree.append(root_iter, [
            entry.icon,
            entry.name,
            entry.module,
            entry.view_class,
            entry.item_data,
            False,
            '',
            True
        ])

        if self._finalized:
            # If we already finalized we need to generate the label now.
            _recursive_generate_item_store_row_label(self._tree[new_iter])

        return ItemTreeEntryRef(self._tree, new_iter)

    def mark_as_modified(self, entry: ItemTreeEntryRef, recursion_type: RecursionType = RecursionType.NONE):
        row = self._tree[entry._self]
        if recursion_type == RecursionType.UP:
            _recursive_up_item_store_mark_as_modified(row, True)
        elif recursion_type == RecursionType.DOWN:
            _recursive_down_item_store_mark_as_modified(row, True)
        else:
            row[5] = True
            _generate_item_store_row_label(row)

    def mark_all_as_unmodified(self):
        first_iter = self._tree.get_iter_first()
        if first_iter:
            _recursive_down_item_store_mark_as_modified(self._tree[first_iter], False)

    def finalize(self):
        """Finalize the tree. Do not call this from modules!"""
        first_iter = self._tree.get_iter_first()
        if first_iter:
            _recursive_generate_item_store_row_label(self._tree[first_iter])
        self._finalized = True


def _recursive_up_item_store_mark_as_modified(row: Gtk.TreeModelRow, modified=True):
    """Starting at the row, move UP the tree and set column 5 (starting at 0) to modified."""
    row[5] = modified
    _generate_item_store_row_label(row)
    if row.parent is not None:
        _recursive_up_item_store_mark_as_modified(cast(Gtk.TreeModelRow, row.parent), modified)

def _recursive_down_item_store_mark_as_modified(row: Gtk.TreeModelRow, modified=True):
    """Starting at the row, move DOWN the tree and set column 5 (starting at 0) to modified."""
    row[5] = modified
    _generate_item_store_row_label(row)
    for child in row.iterchildren():
        _recursive_down_item_store_mark_as_modified(child, modified)


def _generate_item_store_row_label(row: Gtk.TreeModelRow):
    """Set column number 6 (final_label) based on the values in the other columns"""
    row[6] = f"{'*' if row[5] else ''}{row[1]}"


def _recursive_generate_item_store_row_label(row: Gtk.TreeModelRow):
    """Like generate_item_store_row_label but recursive DOWN the tree"""
    _generate_item_store_row_label(row)
    for child in row.iterchildren():
        _recursive_generate_item_store_row_label(child)
