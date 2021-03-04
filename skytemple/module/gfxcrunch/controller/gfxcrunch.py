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
import logging
import os
import subprocess
import tempfile
from enum import Enum, auto
from subprocess import Popen
from typing import TYPE_CHECKING, List
from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import data_dir, APP, make_builder
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.gfxcrunch.module import GfxcrunchModule
logger = logging.getLogger(__name__)


class GfxcrunchStatus(Enum):
    RUNNING = auto()
    ERROR = auto()
    SUCCESS = auto()


IMG_NEUTRAL = 'poochy_neutral.png'
IMG_HAPPY = 'poochy_happy.png'
IMG_SAD = 'poochy_sad.png'
IMGS = {
    GfxcrunchStatus.RUNNING: IMG_NEUTRAL,
    GfxcrunchStatus.ERROR: IMG_SAD,
    GfxcrunchStatus.SUCCESS: IMG_HAPPY
}


class GfxcrunchController:
    def __init__(self, module: 'GfxcrunchModule'):
        self.module = module

        self.builder = self._get_builder(__file__, 'gfxcrunch.glade')
        self.builder.connect_signals(self)
        self.buffer: Gtk.TextBuffer = self.builder.get_object('console').get_buffer()
        self.status = GfxcrunchStatus.RUNNING

    def import_sprite(self, dir_fn: str) -> bytes:
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_path = os.path.join(tmp_path, 'tmp.wan')
            AsyncTaskRunner.instance().run_task(self._run_gfxcrunch([dir_fn, tmp_path]))
            self._run_window()
            if self.status == GfxcrunchStatus.SUCCESS:
                with open(tmp_path, 'rb') as f:
                    return f.read()
            else:
                raise RuntimeError(_("The gfxcrunch process failed."))

    def export_sprite(self, wan: bytes, dir_fn: str):
        with tempfile.TemporaryDirectory() as tmp_path:
            tmp_path = os.path.join(tmp_path, 'tmp.wan')
            with open(tmp_path, 'wb') as f:
                f.write(wan)
            AsyncTaskRunner.instance().run_task(self._run_gfxcrunch([tmp_path, dir_fn]))
            self._run_window()
            if self.status != GfxcrunchStatus.SUCCESS:
                raise RuntimeError(_("The gfxcrunch process failed."))

    def _run_window(self):
        dialog: Gtk.Dialog = self.builder.get_object('dialog')
        dialog.resize(750, 350)
        dialog.set_transient_for(MainController.window())
        dialog.set_attached_to(MainController.window())
        self.buffer.delete(self.buffer.get_start_iter(), self.buffer.get_end_iter())
        self._update_status(GfxcrunchStatus.RUNNING)
        self.builder.get_object('spinner').start()
        self.builder.get_object('close').set_sensitive(False)
        dialog.run()
        dialog.hide()

    async def _run_gfxcrunch(self, arg_list: List[str]):
        cmd, base_args, shell = self.module.get_gfxcrunch_cmd()
        arg_list = [cmd] + base_args + arg_list
        logger.info(f"Running gfxcrunch: {arg_list}")
        proc = Popen(
            arg_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=shell,
            universal_newlines=True
            #creationflags=
        )

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
        self.buffer.insert_markup(self.buffer.get_end_iter(), line, -1)

    def _stderr(self, line):
        self.buffer.insert_markup(self.buffer.get_end_iter(), f'<span color="red">{line}</span>', -1)

    def _done(self, return_code):
        self._update_status(GfxcrunchStatus.SUCCESS if return_code == 0 else GfxcrunchStatus.ERROR)
        if return_code != 0:
            self._stderr(f(_('!! Process exited with error. Exit code: {return_code} !!')))
        self.builder.get_object('spinner').stop()
        self.builder.get_object('close').set_sensitive(True)

    def _update_status(self, status):
        self.status = status
        img: Gtk.Image = self.builder.get_object('duskako')
        img.set_from_file(os.path.join(data_dir(), IMGS[status]))
