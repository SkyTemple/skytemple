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
import os
import sys
from glob import glob
from typing import TYPE_CHECKING, Optional

from gi.repository import Gtk

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import open_dir
from skytemple_files.patch.patches import Patcher
from skytemple.controller.main import MainController as MainAppController

PATCH_DIR = 'Patches'
if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule


class MainController(AbstractController):
    def __init__(self, module: 'PatchModule', *args):
        self.module = module

        self.builder = None
        self._patcher: Optional[Patcher] = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'patch_main.glade')

        self.refresh()

        self.builder.connect_signals(self)
        return self.builder.get_object('box_patches')

    def on_btn_apply_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('patch_tree')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            name = model[treeiter][0]
            try:
                if self._patcher.is_applied(name):
                    md = SkyTempleMessageDialog(MainAppController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                                Gtk.ButtonsType.OK_CANCEL, "This patch is already applied. "
                                                                           "Some patches support applying them again, "
                                                                           "but you might also run into problems with some. "
                                                                           "Proceed with care.")
                    md.set_position(Gtk.WindowPosition.CENTER)
                    response = md.run()
                    md.destroy()
                    if response != Gtk.ResponseType.OK:
                        return
            except NotImplementedError:
                self._error("The current ROM is not supported by this patch.")
                return

            if self.module.project.has_modifications():
                self._error("Please save the ROM before applying the patch.")
                return

            try:
                self._patcher.apply(name)
            except RuntimeError as err:
                self._error(f"Error applying the patch:\n{err}", exc_info=sys.exc_info())
            else:
                self._error(f"Patch was successfully applied. You should re-open the project, to make sure all data is "
                            f"correctly loaded.", Gtk.MessageType.INFO, is_success=True)
            finally:
                self.module.mark_as_modified()

    def on_btn_refresh_clicked(self, *args):
        self.refresh()

    def on_btn_open_patch_dir_clicked(self, *args):
        open_dir(self.patch_dir())

    def refresh(self):
        tree: Gtk.TreeView = self.builder.get_object('patch_tree')
        model: Gtk.ListStore = tree.get_model()
        model.clear()
        self._patcher = self.module.project.create_patcher()
        # Load zip patches
        for fname in glob(os.path.join(self.patch_dir(), '*.skypatch')):
            try:
                self._patcher.add_pkg(fname)
            except BaseException as err:
                self._error(f"Error loading patch package {os.path.basename(fname)}:\n{err}")
        # List patches:
        for patch in self._patcher.list():
            applied_str = 'Not compatible'
            try:
                applied_str = 'Applied' if self._patcher.is_applied(patch.name) else 'Compatible'
            except NotImplementedError:
                pass
            model.append([
                patch.name, patch.author, patch.description, applied_str
            ])

    def _error(self, msg, type=Gtk.MessageType.ERROR, exc_info=None, is_success=False):
        if type == Gtk.MessageType.ERROR:
            display_error(
                exc_info,
                msg
            )
        else:
            md = SkyTempleMessageDialog(MainAppController.window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, type,
                                        Gtk.ButtonsType.OK, msg, is_success=is_success)
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()

    def patch_dir(self):
        return self.module.project.get_project_file_manager().dir(PATCH_DIR)
