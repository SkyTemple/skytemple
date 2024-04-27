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
import logging
import os
import sys
import textwrap
import traceback
import warnings
from glob import glob
from types import TracebackType
from typing import TYPE_CHECKING, Optional, overload, Union, Literal, cast
from gi.repository import Gtk, Gdk
from skytemple_files.common.warnings import DeprecatedToBeRemovedWarning
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog, IMG_SAD
from skytemple.core.ui_utils import open_dir, data_dir, assert_not_none, safe_destroy
from skytemple.module.patch.controller.param_dialog import (
    ParamDialogController,
    PatchCanceledError,
)
from skytemple_files.patch.category import PatchCategory
from skytemple_files.patch.errors import PatchNotConfiguredError
from skytemple_files.patch.handler.abstract import DependantPatch
from skytemple_files.patch.patches import Patcher
from skytemple_files.patch.errors import PatchDependencyError
from skytemple.controller.main import MainController as MainAppController
from skytemple_files.common.i18n_util import f, _
from skytemple.controller.main import MainController as MainSkyTempleController

PATCH_DIR = _("Patches")
if TYPE_CHECKING:
    from skytemple.module.patch.module import PatchModule
logger = logging.getLogger(__name__)
ErrorsTuple = tuple[
    str,
    Union[
        tuple[type[BaseException], BaseException, TracebackType],
        tuple[None, None, None],
    ],
]


@Gtk.Template(filename=os.path.join(data_dir(), "widget", "patch", "asm.ui"))
class StPatchAsmPage(Gtk.Box):
    __gtype_name__ = "StPatchAsmPage"
    module: PatchModule
    item_data: None
    patch_categories: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    btn_open_patch_dir: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_refresh: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    cnt_btns: Gtk.ButtonBox = cast(Gtk.ButtonBox, Gtk.Template.Child())
    btn_apply: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    btn_show_issues: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    issue_buffer: Gtk.TextBuffer = cast(Gtk.TextBuffer, Gtk.Template.Child())
    issue_dialog: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    button1: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    issue_img_container: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    label_issue_load: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_issue_apply: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_error_load: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_error_apply: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    label_issue_note: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    issue_info: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    patch_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    patch_window: Gtk.ScrolledWindow = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    patch_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())

    def __init__(self, module: PatchModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self._patcher: Patcher = self.module.project.create_patcher()
        self._were_issues_activated = False
        self._issues: dict[str, list[warnings.WarningMessage]] = {}
        self._acknowledged_danger = False
        self._accepted_danger = False
        self._category_tabs: dict[PatchCategory, Gtk.Box] = {}  # category -> page
        self._category_tabs_reverse: dict[
            Gtk.Widget, PatchCategory
        ] = {}  # page -> category
        self._current_tab: PatchCategory | None = None
        self._load_image_for_issue_dialog()
        self.refresh_all()
        self._suppress_signals = False

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.btn_show_issues)
        safe_destroy(self.issue_dialog)
        safe_destroy(self.patch_window)

    @Gtk.Template.Callback()
    def on_btn_show_issues_clicked(self, *args):
        tree = self.patch_tree
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            name = model[treeiter][0]
            if name in self._issues:
                self._error_or_issue(True, False, {name: self._issues[name]})
            else:
                self._msg(
                    _("This patch has had no issues loading."), Gtk.MessageType.INFO
                )

    @Gtk.Template.Callback()
    def on_btn_apply_clicked(self, *args):
        tree = self.patch_tree
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            name = model[treeiter][0]
            try:
                if self._patcher.is_applied(name):
                    md = SkyTempleMessageDialog(
                        MainAppController.window(),
                        Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        Gtk.MessageType.WARNING,
                        Gtk.ButtonsType.OK_CANCEL,
                        _(
                            "This patch is already applied. Some patches support applying them again, but you might also run into problems with some. Proceed with care."
                        ),
                    )
                    md.set_position(Gtk.WindowPosition.CENTER)
                    response = md.run()
                    md.destroy()
                    if response != Gtk.ResponseType.OK:
                        return
            except NotImplementedError:
                self._msg(_("The current ROM is not supported by this patch."))
                return
            if self.module.project.has_modifications():
                self._msg(_("Please save the ROM before applying the patch."))
                return
            if name == "ExpandPokeList":
                md = SkyTempleMessageDialog(
                    MainAppController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.WARNING,
                    Gtk.ButtonsType.YES_NO,
                    _(
                        "This patch extends the Pokémon list. It is very experimental and WILL break a few things. Once applied you can not remove it again. Proceed?"
                    ),
                )
                md.set_position(Gtk.WindowPosition.CENTER)
                response = md.run()
                md.destroy()
                if response != Gtk.ResponseType.YES:
                    return
            some_skipped = False
            patch = "???"
            issues: dict[str, list[warnings.WarningMessage]] = {}
            try:
                dependencies = self._get_dependencies(name)
                if len(dependencies) > 0:
                    md = SkyTempleMessageDialog(
                        MainAppController.window(),
                        Gtk.DialogFlags.DESTROY_WITH_PARENT,
                        Gtk.MessageType.INFO,
                        Gtk.ButtonsType.YES_NO,
                        _(
                            "This patch requires some other patches to be applied first:\n"
                        )
                        + "\n".join(dependencies)
                        + _("\nDo you want to apply these first?"),
                    )
                    md.set_position(Gtk.WindowPosition.CENTER)
                    response = md.run()
                    md.destroy()
                    if response != Gtk.ResponseType.YES:
                        return
                for patch in dependencies + [name]:
                    with warnings.catch_warnings(record=True) as w:
                        warnings.filterwarnings("always", category=DeprecationWarning)
                        try:
                            self._apply(patch)
                        except PatchCanceledError:
                            some_skipped = True
                            break
                    # We filter out Gtk deprecations.
                    w = [x for x in w if "Gtk." not in str(x.message)]
                    if len(w) > 0:
                        issues[patch] = w
            except PatchNotConfiguredError as ex:
                err = str(ex)
                if ex.config_parameter != "*":
                    err += _(
                        '\nConfiguration field with errors: "{}"\nError: {}'
                    ).format(ex.config_parameter, ex.error)
                self._msg(
                    f(_("Error applying the patch:\n{err}")),
                    exc_info=sys.exc_info(),
                    should_report=False,
                )
            except BaseException as err:
                self._error_or_issue(
                    False,
                    True,
                    [
                        (
                            f(
                                _(
                                    "Failed applying patch '{patch}'. The ROM may be corrupted now."
                                )
                            ),
                            sys.exc_info(),
                        )
                    ],
                )
            else:
                if len(issues) > 0:
                    self._error_or_issue(False, False, issues)
                if not some_skipped:
                    self._msg(
                        _(
                            "Patch was successfully applied. The ROM will now be reloaded."
                        ),
                        Gtk.MessageType.INFO,
                        is_success=True,
                    )
                else:
                    self._msg(
                        _(
                            "Not all patches were applied successfully. The ROM will now be reloaded."
                        ),
                        Gtk.MessageType.INFO,
                    )
            finally:
                self.module.mark_asm_patches_as_modified()
                self.refresh(self._current_tab)
                MainSkyTempleController.save(
                    lambda: MainSkyTempleController.reload_project()
                )

    @Gtk.Template.Callback()
    def on_btn_refresh_clicked(self, *args):
        self.refresh(self._current_tab)

    @Gtk.Template.Callback()
    def on_btn_open_patch_dir_clicked(self, *args):
        open_dir(self.patch_dir())

    @Gtk.Template.Callback()
    def on_patch_categories_switch_page(
        self, notebook: Gtk.Notebook, page: Gtk.Widget, page_num
    ):
        if not self._suppress_signals:
            cat = self._category_tabs_reverse[page]
            sw = self.patch_window
            assert_not_none(cast(Optional[Gtk.Container], sw.get_parent())).remove(sw)
            self.refresh(cat)

    def refresh_all(self):
        self._category_tabs = {}
        self._category_tabs_reverse = {}
        notebook = self.patch_categories
        page_num = 0
        for category in PatchCategory:
            box = Gtk.Box.new(Gtk.Orientation.HORIZONTAL, 0)
            notebook.append_page(box, Gtk.Label.new(category.print_name))
            self._category_tabs[category] = box
            self._category_tabs_reverse[box] = category
            if (
                self._current_tab is None
                and page_num == 0
                or self._current_tab == category
            ):
                # Select
                notebook.set_current_page(page_num)
                self.refresh(category)
            page_num += 1

    def refresh(self, patch_category: PatchCategory | None):
        assert patch_category is not None
        # ATTACH
        page = self._category_tabs[patch_category]
        page.pack_start(self.patch_window, True, True, 0)
        self._current_tab = patch_category
        tree = self.patch_tree
        model = assert_not_none(cast(Optional[Gtk.ListStore], tree.get_model()))
        model.clear()
        self._patcher = self.module.project.create_patcher()
        errors: list[ErrorsTuple] = []
        self._issues = {}
        # Load zip patches
        for fname in glob(os.path.join(self.patch_dir(), "*.skypatch")):
            if not self._acknowledged_danger:
                self._show_code_warning()
            if not self._accepted_danger:
                break
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings("always", category=DeprecationWarning)
                try:
                    patch = self._patcher.add_pkg(fname)
                    if len(w) > 0:
                        self._issues[patch.name] = w
                # We catch BaseExceptions, because we don't want loaded patch packages to do fun stuff like close
                # the app by raising SystemExit (though I suppose if they wanted to, they could).
                except BaseException:
                    errors.append(
                        (
                            f(
                                _(
                                    "Error loading patch package {os.path.basename(fname)}."
                                )
                            ),
                            sys.exc_info(),
                        )
                    )
        # List patches:
        for patch in sorted(self._patcher.list(), key=lambda p: p.name):
            with warnings.catch_warnings(record=True) as w:
                warnings.filterwarnings("always", category=DeprecationWarning)
                try:
                    if patch.category != patch_category:
                        continue
                    applied_str = _("Not compatible")
                    try:
                        applied_str = (
                            _("Applied")
                            if self._patcher.is_applied(patch.name)
                            else _("Compatible")
                        )
                    except NotImplementedError:
                        pass
                    if len(w) > 0:
                        self._issues[patch.name] = w
                    model.append(
                        [
                            patch.name,
                            patch.author,
                            patch.description,
                            applied_str,
                            "orange" if patch.name in self._issues else None,
                        ]
                    )
                except BaseException:
                    errors.append(
                        (
                            f(_("Error loading patch package {patch.name}.")),
                            sys.exc_info(),
                        )
                    )
        if len(errors) > 0:
            self._error_or_issue(True, True, errors)
        if len(self._issues) > 0:
            self._activate_issues()

    def _msg(
        self,
        msg,
        type=Gtk.MessageType.ERROR,
        exc_info=None,
        is_success=False,
        should_report=False,
    ):
        if type == Gtk.MessageType.ERROR:
            display_error(exc_info, msg, should_report=should_report)
        else:
            md = SkyTempleMessageDialog(
                MainAppController.window(),
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                type,
                Gtk.ButtonsType.OK,
                msg,
                is_success=is_success,
            )
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()

    def patch_dir(self):
        return self.module.project.get_project_file_manager().dir(PATCH_DIR)

    def _get_dependencies(self, name):
        to_check = [name]
        collected_deps: list[str] = []
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
                        raise PatchDependencyError(
                            f(
                                _(
                                    "The patch '{patch_name}' needs to be applied before you can apply '{name}'. This patch could not be found."
                                )
                            )
                        ) from err
        return list(reversed(collected_deps))

    def _apply(self, patch: str):
        patches = (
            self.module.project.get_rom_module()
            .get_static_data()
            .asm_patches_constants.patches
        )
        parameter_data = None
        if patch in patches:
            if len(patches[patch].parameters) > 0:
                parameter_data = ParamDialogController(
                    MainSkyTempleController.window()
                ).run(patch, patches[patch].parameters)
        self._patcher.apply(patch, parameter_data)

    def _load_image_for_issue_dialog(self):
        img: Gtk.Image = Gtk.Image.new_from_file(os.path.join(data_dir(), IMG_SAD))
        self.issue_img_container.pack_start(img, False, False, 0)

    @overload
    def _error_or_issue(
        self,
        is_load: bool,
        is_error: Literal[True],
        errors_or_issues: list[ErrorsTuple],
    ): ...

    @overload
    def _error_or_issue(
        self,
        is_load: bool,
        is_error: Literal[False],
        errors_or_issues: dict[str, list[warnings.WarningMessage]],
    ): ...

    def _error_or_issue(self, is_load: bool, is_error: bool, errors_or_issues):
        """Show the compatibility issues / patch error dialog with the appropriate content based on the situation."""
        # todo also make sure to set transient and parent.
        dialog = self.issue_dialog
        dialog.set_position(Gtk.WindowPosition.CENTER)
        dialog.set_transient_for(MainSkyTempleController.window())
        dialog.set_parent(MainSkyTempleController.window())
        try:
            screen: Gdk.Screen = dialog.get_screen()
            monitor = screen.get_monitor_geometry(
                screen.get_monitor_at_window(
                    assert_not_none(screen.get_active_window())
                )
            )
            dialog.resize(round(monitor.width * 0.65), round(monitor.height * 0.65))
        except BaseException:
            dialog.resize(1015, 865)
        self.label_issue_load.hide()
        self.label_issue_apply.hide()
        self.label_error_load.hide()
        self.label_error_apply.hide()
        self.label_issue_note.hide()
        if is_load and is_error:
            self.label_error_load.show()
        elif is_load:
            self.label_issue_load.show()
            self.label_issue_note.show()
        elif is_error:
            self.label_error_apply.show()
        else:
            self.label_issue_apply.show()
            self.label_issue_note.show()
        buffer = self.issue_info.get_buffer()
        if is_error:
            errors: list[ErrorsTuple] = errors_or_issues
            text = ""
            for error_str, exc_info in errors:
                text += error_str + "\n"
                text += "".join(traceback.format_exception(*exc_info))
                text += "\n"
            buffer.set_text(text)
        else:
            issues: dict[str, list[warnings.WarningMessage]] = errors_or_issues
            text = ""
            for patch_name, patch_issues in issues.items():
                text += f"Warnings generated while processing {patch_name}:\n"
                for issue in patch_issues:
                    text += textwrap.indent(
                        warnings.formatwarning(
                            issue.message,
                            issue.category,
                            issue.filename,
                            issue.lineno,
                            issue.line,
                        ),
                        ">> ",
                    )
                    if isinstance(issue.message, DeprecatedToBeRemovedWarning):
                        text += f">> ! This will break in SkyTemple Files {'.'.join((str(x) for x in issue.message.expected_removal))}\n"
                    text += "\n"
                text += "\n"
            buffer.set_text(text)
        dialog.run()
        dialog.hide()

    def _activate_issues(self):
        """Show the 'Show Issues' button, if it isn't shown already. Also show a note about why."""
        if not self._were_issues_activated:
            self.cnt_btns.pack_start(self.btn_show_issues, True, True, 0)
            self._were_issues_activated = True
            self._msg(
                _(
                    "Some of the loaded patches had compatibility issues. They were still loaded correctly but may stop working in future SkyTemple versions. These patches were marked orange in the list of patches. Highlight one of these patches and click the 'Show Issues' button for more information."
                ),
                Gtk.MessageType.WARNING,
            )

    def _show_code_warning(self):
        """Show a warning about patches being loaded, set self.*_danger variables accordingly."""
        md = SkyTempleMessageDialog(
            MainAppController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.YES_NO,
            _(
                "Warning! The project directory for this ROM contains custom patches. These patches may contain code which will run on your computer once you accept this dialog with 'Yes'. Only continue if you trust the authors of the patches. Malicious people could otherwise hijack your computer and/or steal information.\n\nDo you want to continue loading these patches? By selecting 'No', only the built-in patches will be loaded."
            ),
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.set_transient_for(MainSkyTempleController.window())
        md.set_parent(MainSkyTempleController.window())
        response = md.run()
        md.destroy()
        self._acknowledged_danger = True
        self._accepted_danger = response == Gtk.ResponseType.YES

    @Gtk.Template.Callback()
    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True
