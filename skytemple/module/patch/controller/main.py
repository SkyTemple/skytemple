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
from typing import TYPE_CHECKING, Optional, Dict

from gi.repository import Gtk

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import open_dir
from skytemple_files.patch.category import PatchCategory
from skytemple_files.patch.handler.abstract import DependantPatch
from skytemple_files.patch.patches import Patcher, PatchDependencyError
from skytemple.controller.main import MainController as MainAppController
from skytemple_files.common.i18n_util import f, _

PATCH_DIR = _('Patches')
if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule


class MainController(AbstractController):
    def __init__(self, module: 'PatchModule', *args):
        self.module = module

        self.builder = None
        self._patcher: Optional[Patcher] = None

        self._category_tabs: Dict[PatchCategory, Gtk.Widget] = {}  # category -> page
        self._category_tabs_reverse: Dict[Gtk.Widget, PatchCategory] = {}  # page -> category
        self._current_tab: Optional[PatchCategory] = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'patch_main.glade')

        self.refresh_all()

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
                                                Gtk.ButtonsType.OK_CANCEL, _("This patch is already applied. "
                                                                             "Some patches support applying them again, "
                                                                             "but you might also run into problems with some. "
                                                                             "Proceed with care."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    response = md.run()
                    md.destroy()
                    if response != Gtk.ResponseType.OK:
                        return
            except NotImplementedError:
                self._error(_("The current ROM is not supported by this patch."))
                return

            if self.module.project.has_modifications():
                self._error(_("Please save the ROM before applying the patch."))
                return

            try:
                dependencies = self._get_dependencies(name)
                if len(dependencies) > 0:
                    md = SkyTempleMessageDialog(MainAppController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                                Gtk.ButtonsType.YES_NO,
                                                _("This patch requires some other patches to be applied first:\n") + '\n'.join(dependencies) + _("\nDo you want to apply these first?"))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    response = md.run()
                    md.destroy()
                    if response != Gtk.ResponseType.YES:
                        return
                for patch in dependencies + [name]:
                    self._patcher.apply(patch)
            except RuntimeError as err:
                self._error(f(_("Error applying the patch:\n{err}")), exc_info=sys.exc_info())
            else:
                self._error(_("Patch was successfully applied. You should re-open the project, to make sure all data "
                              "is correctly loaded."), Gtk.MessageType.INFO, is_success=True)
            finally:
                self.module.mark_as_modified()
                self.refresh(self._current_tab)

    def on_btn_refresh_clicked(self, *args):
        self.refresh(self._current_tab)

    def on_btn_open_patch_dir_clicked(self, *args):
        open_dir(self.patch_dir())

    def on_patch_categories_switch_page(self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num):
        cat = self._category_tabs_reverse[page]
        sw: Gtk.ScrolledWindow = self.builder.get_object('patch_window')
        sw.get_parent().remove(sw)
        self.refresh(cat)

    def refresh_all(self):
        self._category_tabs = {}
        self._category_tabs_reverse = {}
        notebook: Gtk.Notebook = self.builder.get_object('patch_categories')
        page_num = 0
        for category in PatchCategory:
            box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
            notebook.append_page(box, Gtk.Label.new(category.print_name))
            self._category_tabs[category] = box
            self._category_tabs_reverse[box] = category
            if self._current_tab is None and page_num == 0 or self._current_tab == category:
                # Select
                notebook.set_current_page(page_num)
                self.refresh(category)
            page_num += 1

    def refresh(self, patch_category: PatchCategory):
        # ATTACH
        page = self._category_tabs[patch_category]
        page.pack_start(self.builder.get_object('patch_window'), True, True, 0)
        self._current_tab = patch_category

        tree: Gtk.TreeView = self.builder.get_object('patch_tree')
        model: Gtk.ListStore = tree.get_model()
        model.clear()
        self._patcher = self.module.project.create_patcher()
        # Load zip patches
        for fname in glob(os.path.join(self.patch_dir(), '*.skypatch')):
            try:
                self._patcher.add_pkg(fname)
            except BaseException as err:
                self._error(f(_("Error loading patch package {os.path.basename(fname)}:\n{err}")))
        # List patches:
        for patch in sorted(self._patcher.list(), key=lambda p: p.name):
            if patch.category != patch_category:
                continue
            applied_str = _('Not compatible')
            try:
                applied_str = _('Applied') if self._patcher.is_applied(patch.name) else _('Compatible')
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

    def _get_dependencies(self, name):
        to_check = [name]
        collected_deps = []
        while len(to_check) > 0:
            patch = self._patcher.get(to_check.pop())
            if isinstance(patch, DependantPatch):
                for patch_name in patch.depends_on():
                    try:
                        if not self._patcher.is_applied(patch_name):
                            if patch_name in collected_deps:
                                collected_deps.remove(patch_name)
                            collected_deps.append(patch_name)
                            to_check.append(patch_name)
                    except ValueError as err:
                        raise PatchDependencyError(f(_("The patch '{patch_name}' needs to be applied before you can "
                                                       "apply '{name}'. "
                                                       "This patch could not be found."))) from err
        return list(reversed(collected_deps))
