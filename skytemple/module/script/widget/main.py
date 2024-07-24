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
from typing import TYPE_CHECKING, Optional, cast
from gi.repository import Gtk
from range_typed_integers import i16, i16_checked, u8, u32, u8_checked
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import BinaryName
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import (
    glib_async,
    catch_overflow,
    assert_not_none,
    iter_tree_model,
    safe_destroy,
    data_dir,
)
from skytemple_files.common.i18n_util import _
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.common.ppmdu_config.script_data import (
    Pmd2ScriptLevelMapType,
    Pmd2ScriptLevel,
)
from skytemple_files.hardcoded.dungeons import HardcodedDungeons
from skytemple_files.hardcoded.ground_dungeon_tilesets import GroundTilesetMapping
from skytemple_files.list.level.model import LevelListBin

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule
SCRIPT_SCENES = _("Script Scenes")
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "script", "main.ui"))
class StScriptMainPage(Gtk.Box):
    __gtype_name__ = "StScriptMainPage"
    module: ScriptModule
    item_data: int
    dungeon_tileset_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    generic_input_dialog: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    generic_input_dialog_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    generic_input_dialog_entry: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    generic_input_dialog_sublabel: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    level_list_tree_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    mapbg_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    maptype_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    nameid_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    td_dungeon_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    td_level_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    list_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    box_na: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    box_edit: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    level_list_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_name: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    cr_nameid: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_maptype: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_mapid: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_weather: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    btn_add: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    box_edit1: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    dungeon_tileset_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    cr_td_level: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_td_dungeon: Gtk.CellRendererCombo = cast(Gtk.CellRendererCombo, Gtk.Template.Child())
    cr_td_floor_number: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())

    def __init__(self, module: ScriptModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._list: LevelListBin
        self._dungeon_tilesets: list[GroundTilesetMapping]
        self._labels_mapid: dict[int, str] = {}
        self._labels_maptype: dict[int, str] = {}
        self._labels_overworld_strings: dict[int, str] = {}
        self._labels_td_level: dict[int, str] = {}
        self._labels_td_dungeon: dict[int, str] = {}
        stack = self.list_stack
        if not self.module.has_level_list():
            stack.set_visible_child(self.box_na)
        else:
            self._list = self.module.get_level_list()
            self._init_label_stores()
            self._init_list_store()
            stack.set_visible_child(self.box_edit)
        self._dungeon_tilesets = self.module.get_dungeon_tilesets()
        self._init_td_label_stores()
        self._init_td_list_store()

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.generic_input_dialog)

    @Gtk.Template.Callback()
    def on_cr_name_edited(self, widget, path, text):
        store = self.level_list_tree_store
        if len(text) < 1 or len(text) > 8:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("The length of the level name must be between 1-8 characters."),
            )
            md.run()
            md.destroy()
            return
        text = text.upper()
        store[path][1] = text
        self._save()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_nameid_changed(self, widget, path, new_iter, *args):
        store = self.level_list_tree_store
        cb_store = self.nameid_store
        store[path][2] = cb_store[new_iter][0]
        store[path][6] = cb_store[new_iter][1]
        self._save()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_maptype_changed(self, widget, path, new_iter, *args):
        store = self.level_list_tree_store
        cb_store = self.maptype_store
        store[path][3] = cb_store[new_iter][0]
        store[path][7] = cb_store[new_iter][1]
        self._save()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_mapid_changed(self, widget, path, new_iter, *args):
        store = self.level_list_tree_store
        cb_store = self.mapbg_store
        store[path][4] = cb_store[new_iter][0]
        store[path][8] = cb_store[new_iter][1]
        self._save()

    @Gtk.Template.Callback()
    @catch_overflow(i16)
    def on_cr_weather_edited(self, widget, path, text):
        store = self.level_list_tree_store
        try:
            i16_checked(int(text))
        except ValueError:
            return
        store[path][5] = text
        self._save()

    @Gtk.Template.Callback()
    def on_btn_add_clicked(self, *args):
        response, new_name = self._show_generic_input(
            _("Level Name"),
            _("Create Level"),
            _(
                'If you also need a new background for this level, you can create one under "Map Backgrounds" and assign it to this level afterwards.'
            ),
        )
        if response != Gtk.ResponseType.OK:
            return
        new_name = new_name.upper()
        if len(new_name) < 1 or len(new_name) > 8:
            md = SkyTempleMessageDialog(
                SkyTempleMainController.window(),
                Gtk.DialogFlags.MODAL,
                Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("The length of the level name must be between 1-8 characters."),
            )
            md.run()
            md.destroy()
            return
        new_id = max(lst.id for lst in self._list.list) + 1
        store = self.level_list_tree_store
        store.append(
            [
                str(new_id),
                new_name,
                0,
                0,
                0,
                str(-1),
                self._labels_overworld_strings[0],
                self._labels_maptype[0],
                self._labels_mapid[0],
            ]
        )
        self.module.create_new_level(new_name)
        self._save()
        md = SkyTempleMessageDialog(
            SkyTempleMainController.window(),
            Gtk.DialogFlags.MODAL,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("New level created."),
            is_success=True,
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_td_level_changed(self, widget, path, new_iter, *args):
        store = self.dungeon_tileset_store
        cb_store = self.td_level_store
        store[path][1] = cb_store[new_iter][0]
        store[path][3] = cb_store[new_iter][1]
        self._save_td()

    @Gtk.Template.Callback()
    @glib_async
    def on_cr_td_dungeon_changed(self, widget, path, new_iter, *args):
        store = self.dungeon_tileset_store
        cb_store = self.td_dungeon_store
        store[path][2] = cb_store[new_iter][0]
        store[path][4] = cb_store[new_iter][1]
        self._save_td()

    @Gtk.Template.Callback()
    @catch_overflow(u8)
    def on_cr_td_floor_number_edited(self, widget, path, text):
        store = self.dungeon_tileset_store
        try:
            u8_checked(int(text))
        except ValueError:
            return
        store[path][5] = text
        self._save_td()

    def _show_generic_input(self, label_text, ok_text, sublabel_text=""):
        dialog: Gtk.Dialog = self.generic_input_dialog
        entry: Gtk.Entry = self.generic_input_dialog_entry
        label: Gtk.Label = self.generic_input_dialog_label
        sublabel: Gtk.Label = self.generic_input_dialog_sublabel
        label.set_text(label_text)
        sublabel.set_text(sublabel_text)
        btn_cancel = dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        btn = dialog.add_button(ok_text, Gtk.ResponseType.OK)
        btn.set_can_default(True)
        btn.grab_default()
        entry.set_activates_default(True)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())
        response = dialog.run()
        dialog.hide()
        assert_not_none(cast(Optional[Gtk.Container], btn.get_parent())).remove(btn)
        assert_not_none(cast(Optional[Gtk.Container], btn_cancel.get_parent())).remove(btn_cancel)
        return (response, entry.get_text())

    def _init_label_stores(self):
        self._labels_mapid = {}
        self._labels_maptype = {}
        self._labels_overworld_strings = {}
        lvls = []
        store = self.mapbg_store
        for i, level in enumerate(self.module.get_bg_level_list().level):
            lvls.append((i, level.bma_name))
        for i, level in sorted(lvls, key=lambda lst: lst[1]):
            lbl = f"{level} (#{i:03})"
            self._labels_mapid[i] = lbl
            store.append([i, lbl])
        store = self.maptype_store
        for val in Pmd2ScriptLevelMapType:
            self._labels_maptype[val.value] = val.name_localized
            store.append([val.value, val.name_localized])
        store = self.nameid_store
        for i in range(0, 312):
            lbl, lbl_id = self.module.get_map_display_name(i)
            self._labels_overworld_strings[i] = lbl + f" (#{lbl_id + 1:04})"
            store.append([i, lbl + f" (#{lbl_id + 1:04})"])

    def _init_list_store(self):
        store = self.level_list_tree_store
        for i, level in enumerate(self._list.list):
            store.append(
                [
                    str(level.id),
                    level.name,
                    level.nameid,
                    level.mapty,
                    level.mapid,
                    str(level.weather),
                    self._labels_overworld_strings[level.nameid],
                    self._labels_maptype[level.mapty],
                    self._labels_mapid[level.mapid],
                ]
            )

    def _init_td_label_stores(self):
        self._labels_td_level = {}
        self._labels_td_dungeon = {}
        store = self.td_level_store
        self._labels_td_level[-1] = _("None")
        store.append([-1, _("None")])
        if hasattr(self, "_list") and self._list:
            for level in self._list.list:
                lbl = f"{level.name} (#{level.id:03})"
                self._labels_td_level[level.id] = lbl
                store.append([level.id, lbl])
        else:
            for i in range(0, 400):
                lbl = f"? (#{i:03})"
                self._labels_td_level[i] = lbl
                store.append([i, lbl])
        static = self.module.project.get_rom_module().get_static_data()
        dungeons = HardcodedDungeons.get_dungeon_list(self.module.project.get_binary(BinaryName.ARM9), static)
        store = self.td_dungeon_store
        for i, dungeon in enumerate(dungeons):
            lbl = f"{self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_SELECTION, i)} (#{i:03})"
            self._labels_td_dungeon[i] = lbl
            store.append([i, lbl])

    def _init_td_list_store(self):
        store = self.dungeon_tileset_store
        for i, dt in enumerate(self._dungeon_tilesets):
            store.append(
                [
                    str(i),
                    dt.ground_level,
                    dt.dungeon_id,
                    self._labels_td_level[dt.ground_level],
                    self._labels_td_dungeon[dt.dungeon_id],
                    str(dt.floor_id),
                ]
            )

    def _save(self):
        self._list.list.clear()
        for row in iter_tree_model(self.level_list_tree_store):
            self._list.list.append(
                Pmd2ScriptLevel(
                    id=int(row[0]),
                    mapty=row[3],
                    nameid=row[2],
                    mapid=row[4],
                    weather=i16(int(row[5])),
                    name=row[1],
                )
            )
        # UPDATE STATIC DATA
        self.module.project.get_rom_module().get_static_data().script_data.level_list = self._list.list
        self.module.mark_level_list_as_modified()

    def _save_td(self):
        self._dungeon_tilesets.clear()
        for row in iter_tree_model(self.dungeon_tileset_store):
            self._dungeon_tilesets.append(GroundTilesetMapping(row[1], row[2], u8(int(row[5])), u32(0)))
        self.module.save_dungeon_tilesets(self._dungeon_tilesets)
