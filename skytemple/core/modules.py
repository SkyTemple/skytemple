"""Module that manages and loads modules"""
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

import os
import sys
import logging
from typing import TYPE_CHECKING, Type, Sequence

from typing import Dict

from skytemple_files.common.i18n_util import _, f
from skytemple_files.common.project_file_manager import ProjectFileManager

from skytemple.core.plugin_loader import load_plugins
from skytemple.core.settings import SkyTempleSettingsStore
from gi.repository import Gtk

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata

if TYPE_CHECKING:
    from skytemple.module.rom.module import RomModule

MODULE_ENTRYPOINT_KEY = 'skytemple.module'
logger = logging.getLogger(__name__)


class Modules:
    _modules: Dict = {}

    @classmethod
    def load(cls, settings: SkyTempleSettingsStore):
        # Load plugins
        plugin_dir = os.path.join(ProjectFileManager.shared_config_dir(), "plugins")
        os.makedirs(plugin_dir, exist_ok=True)
        load_plugins(cls.confirm_plugin_load, settings, plugin_dir)

        # Look up package entrypoints for modules
        cls._modules = {}
        try:
            cls._modules = {
                entry_point.name:
                    entry_point.load() for entry_point in importlib_metadata.entry_points().select(group=MODULE_ENTRYPOINT_KEY)
            }
        except Exception as ex:
            logger.error("Failed loading modules.", exc_info=ex)
            raise ex

        if len(cls._modules) < 1:
            logger.error("No modules found.")
            raise ValueError("No modules found.")
        dependencies = {}
        for k, module in cls._modules.items():
            dependencies[k] = module.depends_on()
        resolved_deps = dep(dependencies)
        cls._modules = dict(sorted(cls._modules.items(), key=lambda x: resolved_deps.index(x[0])))
        for module in cls._modules.values():
            module.load()

    # noinspection PyUnusedLocal
    @classmethod
    def confirm_plugin_load(cls, plugin_names: Sequence[str], settings: SkyTempleSettingsStore, plugin_dir: str) -> bool:
        plugin_names = sorted(plugin_names)
        if plugin_names != settings.get_approved_plugins():
            plugin_names_str = ",".join(plugin_names)
            text = f(_(
                "SkyTemple found the following plugins in your plugins directory ({plugin_dir}).\n\n"
                "Do you want to continue with these plugins? These plugins contain code which will run on your computer "
                "once you accept this dialog with 'Yes'.\n"
                "Only continue if you trust the authors of the patches. "
                "Malicious people could otherwise hijack your computer and/or steal information.\n\n"
                "Clicking 'Yes' will remember this plugin configuration and not ask you again next time."
            ))
            md = Gtk.MessageDialog(
                title="SkyTemple",
                message_type=Gtk.MessageType.WARNING,
                buttons=Gtk.ButtonsType.YES_NO,
                text=text
            )
            sw = Gtk.ScrolledWindow()
            tv = Gtk.TextView()
            tv.get_buffer().set_text(plugin_names_str)
            sw.add(tv)
            content = md.get_content_area()
            content.pack_start(sw, True, True, 0)
            sw.set_size_request(100, 80)
            content.show_all()
            response = md.run()
            md.hide()
            md.destroy()
            proceed = response == Gtk.ResponseType.YES
            if proceed:
                settings.set_approved_plugins(plugin_names)
            return proceed
        return True


    @classmethod
    def all(cls):
        """Returns a list of all loaded modules, ordered by dependencies"""
        return cls._modules

    @classmethod
    def get_rom_module(cls) -> Type['RomModule']:
        assert cls._modules["rom"] is not None
        return cls._modules["rom"]


def dep(arg):
    """
    Dependency resolver

    "arg" is a dependency dictionary in which
    the values are the dependencies of their respective keys.

    Source: http://code.activestate.com/recipes/576570-dependency-resolver/

    Copyright: Louis RIVIERE
    Original license: MIT
    """
    d = dict((k, set(arg[k])) for k in arg)
    r = []
    while d:
        # values not in keys (items without dep)
        t = set(i for v in d.values() for i in v)-set(d.keys())
        # and keys without value (items without dep)
        t.update(k for k, v in d.items() if not v)
        # can be done right away
        r.append(t)
        # and cleaned up
        d = dict(((k, v-t) for k, v in d.items() if v))
    return [item for s in r for item in s]
