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
import subprocess
import tempfile
from enum import Enum, auto
from subprocess import Popen
from typing import TYPE_CHECKING, cast

from gi.repository import Gtk, GLib
from skytemple_files.common.i18n_util import f, _
from skytemple_files.user_error import make_user_err

from skytemple.controller.main import MainController
from skytemple.core.async_tasks.delegator import AsyncTaskDelegator
from skytemple.core.ui_utils import data_dir
from skytemple.init_locale import make_builder, LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.gfxcrunch.module import GfxcrunchModule
logger = logging.getLogger(__name__)


class GfxcrunchStatus(Enum):
    RUNNING = auto()
    ERROR = auto()
    SUCCESS = auto()


IMG_NEUTRAL = "poochy_neutral.png"
IMG_HAPPY = "poochy_happy.png"
IMG_SAD = "poochy_sad.png"
IMGS = {
    GfxcrunchStatus.RUNNING: IMG_NEUTRAL,
    GfxcrunchStatus.ERROR: IMG_SAD,
    GfxcrunchStatus.SUCCESS: IMG_HAPPY,
}


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "gfxcrunch", "gfxcrunch.ui"))
class StGfxcrunchDialog(Gtk.Dialog):
    __gtype_name__ = "StGfxcrunchDialog"
    module: GfxcrunchModule
    console: Gtk.TextView = cast(Gtk.TextView, Gtk.Template.Child())
    spinner: Gtk.Spinner = cast(Gtk.Spinner, Gtk.Template.Child())
    close_button: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    duskako: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())

    def __init__(self, module: GfxcrunchModule):
        super().__init__()
        self.module = module

        self.status = GfxcrunchStatus.RUNNING

    def import_sprite(self, dir_fn: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_path = os.path.join(tmp_path, "tmp.wan")
            AsyncTaskDelegator.run_task(self._run_gfxcrunch([dir_fn, tmp_path]))
            self._run_window()
            if self.status == GfxcrunchStatus.SUCCESS:
                with open(tmp_path, "rb") as f:
                    return f.read()
            else:
                raise make_user_err(RuntimeError, _("The gfxcrunch process failed."))

    def export_sprite(self, wan: bytes, dir_fn: str):
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_path = os.path.join(tmp_path, "tmp.wan")
            with open(tmp_path, "wb") as f:
                f.write(wan)
            AsyncTaskDelegator.run_task(self._run_gfxcrunch([tmp_path, dir_fn]))
            self._run_window()
            if self.status != GfxcrunchStatus.SUCCESS:
                raise make_user_err(RuntimeError, _("The gfxcrunch process failed."))

    def _run_window(self):
        self.resize(750, 350)
        self.set_transient_for(MainController.window())
        self.set_attached_to(MainController.window())
        self.console.get_buffer().delete(
            self.console.get_buffer().get_start_iter(),
            self.console.get_buffer().get_end_iter(),
        )
        self._update_status(GfxcrunchStatus.RUNNING)
        self.spinner.start()
        self.close_button.set_sensitive(False)
        self.run()
        self.hide()

    async def _run_gfxcrunch(self, arg_list: list[str]):
        cmd, base_args, shell = self.module.get_gfxcrunch_cmd()
        arg_list = [cmd] + base_args + arg_list
        logger.info(f"Running gfxcrunch: {arg_list}")
        proc = Popen(
            arg_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=True,
            # creationflags=
        )

        assert proc.stdout is not None and proc.stderr is not None
        while proc.poll() is None:
            line = proc.stdout.readline()
            if line != "" and line:
                GLib.idle_add(lambda line=line: self._stdout(line))

            line = proc.stderr.readline()
            if line != "" and line:
                GLib.idle_add(lambda line=line: self._stderr(line))

        line = proc.stdout.readline()
        while line != "" and line:
            GLib.idle_add(lambda line=line: self._stdout(line))
            line = proc.stdout.readline()

        line = proc.stderr.readline()
        while line != "" and line:
            GLib.idle_add(lambda line=line: self._stderr(line))
            line = proc.stderr.readline()

        GLib.idle_add(lambda: self._done(proc.returncode))

    @staticmethod
    def _get_builder(pymodule_path: str, glade_file: str):
        path = os.path.abspath(os.path.dirname(pymodule_path))
        return make_builder(os.path.join(path, glade_file))

    def _stdout(self, line):
        buffer = self.console.get_buffer()
        buffer.insert_markup(buffer.get_end_iter(), line, -1)

    def _stderr(self, line):
        buffer = self.console.get_buffer()
        buffer.insert_markup(
            buffer.get_end_iter(),
            f'<span color="red">{line}</span>',
            -1,
        )

    def _done(self, return_code):
        self._update_status(GfxcrunchStatus.SUCCESS if return_code == 0 else GfxcrunchStatus.ERROR)
        if return_code != 0:
            self._stderr(f(_("!! Process exited with error. Exit code: {return_code} !!")))
        self.spinner.stop()
        self.close_button.set_sensitive(True)

    def _update_status(self, status):
        self.status = status
        self.duskako.set_from_file(os.path.join(data_dir(), IMGS[status]))
