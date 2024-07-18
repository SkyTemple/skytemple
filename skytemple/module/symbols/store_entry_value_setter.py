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
from typing import Optional

from gi.repository import Gtk


# Font weight to use when a row has unsaved changes
FONT_WEIGHT_UNSAVED = 700
# Font weight to use when a row does not have unsaved changes
FONT_WEIGHT_SAVED = 400


class StoreEntryValueSetter:
    """
    Helper class used to set all required columns of a symbol store entry when its underlying value is updated.
    """

    @staticmethod
    def set_value(
        store_entry: Gtk.TreeModelRow, value: str, mark_unsaved: bool, model_iter: Optional[Gtk.TreeIter] = None
    ):
        """
        Sets the value of one of the entries in the TreeStore
        Using this method will update all the value columns, which ensures their consistency.
        :param store_entry Entry to update
        :param value Base value to set for all fields. Should be a string containing the numerical representation
        of the value.
        :param mark_unsaved If true, the entire row will be bolded to mark that the value is unsaved.
        :param model_iter If specified and the entry uses a model to get its list of possible values, the model entry
        specified by this iter will be updated. Useful to avoid potentially having to search for the given value
        among all the options in the model.
        """
        # Value column
        store_entry[3] = value
        # Boolean value column
        store_entry[4] = value != "" and value != "0"

        # Model column used for entry and completion value types
        model = store_entry[12]
        if model is None:
            combo_and_completion_value = ""
        else:
            if model_iter is None:
                combo_and_completion_value = StoreEntryValueSetter.get_list_store_entry_by_key(model, int(value))
            else:
                combo_and_completion_value = model[model_iter][1]

        store_entry[5] = combo_and_completion_value

        if mark_unsaved:
            # Make the text on this entry bold to mark unsaved changes
            store_entry[13] = FONT_WEIGHT_UNSAVED

    @staticmethod
    def get_list_store_entry_by_key(list_store: Gtk.ListStore, _id: int) -> str:
        """
        Given an integer representing the numeric ID of an entry in a ListStore, returns the corresponding entry.
        :raises KeyError: If none of the entries on the list have the given ID
        """
        # Try directly using the ID to address the store array. There's a good chance that ID and array positions
        # match 1:1.
        direct_entry = list_store[_id]
        if direct_entry[0] == _id:
            return direct_entry[1]
        else:
            # We need to search manually through the list
            for entry in list_store:
                if entry[0] == _id:
                    return entry[1]
            raise KeyError("None of the entries on the given ListStore uses the given key")
