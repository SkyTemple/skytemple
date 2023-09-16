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
import atexit
import contextlib
import os
import sys
from importlib.machinery import ModuleSpec
from importlib.util import spec_from_loader
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Sequence, Optional, Union, Iterable, List, Dict
from wheel.wheelfile import WheelFile

from skytemple.core.plugin_loader.loader import SkyTemplePluginLoader
from skytemple.core.settings import SkyTempleSettingsStore

if sys.version_info >= (3, 10):
    import importlib.metadata as importlib_metadata
else:
    import importlib_metadata


class SkyTemplePluginFinder(importlib_metadata.DistributionFinder):
    settings: SkyTempleSettingsStore
    plugin_dir: str
    plugin_names: List[str]
    packages: Dict[str, str]

    def __init__(self, settings: SkyTempleSettingsStore, plugin_dir: str):
        self.settings = settings
        self.plugin_dir = plugin_dir
        self.packages = {}

        # We cache the plugin list, so nobody can inject plugins after they are confirmed.
        self.plugin_names = []
        with os.scandir(self.plugin_dir) as it:
            for entry in it:
                if entry.name.lower().endswith('.whl') and entry.is_file():
                    self.plugin_names.append(entry.name)

    def st_list(self) -> Sequence[str]:
        return self.plugin_names

    def find_spec(
        self,
        fullname: str,
        path: Optional[Sequence[Union[bytes, str]]],
        target: Optional[ModuleType] = None
    ) -> Optional[ModuleSpec]:
        """
        From the docs:
        An abstract method for finding a spec for the specified module.
        If this is a top-level import, path will be None.
        Otherwise, this is a search for a subpackage or module and path will be the value of __path__
        from the parent package.
        If a spec cannot be found, None is returned.
        When passed in, target is a module object that the finder may use to make a more educated
        guess about what spec to return. importlib.util.spec_from_loader() may be useful for
        implementing concrete MetaPathFinders.
        """
        if fullname in self.packages:
            return spec_from_loader(fullname, SkyTemplePluginLoader(self.packages[fullname]))
        return None

    def find_distributions(
        self,
        context: importlib_metadata.DistributionFinder.Context = importlib_metadata.DistributionFinder.Context()
    ) -> Iterable[importlib_metadata.Distribution]:
        """
        From the docs:
        Return an iterable of all Distribution instances capable of
        loading the metadata for packages for the indicated `context`.
        """
        dists = []
        for p_name in self.plugin_names:
            p_path = os.path.join(self.plugin_dir, p_name)
            whl = WheelFile(p_path)
            whl_ctx = contextlib.ExitStack()
            atexit.register(whl_ctx.close)
            temp_dir = whl_ctx.enter_context(TemporaryDirectory())
            whl.extractall(temp_dir)
            dist = importlib_metadata.PathDistribution(
                Path(temp_dir).joinpath(whl.dist_info_path)
            )
            dists.append(dist)
            # TODO: Is this OK to do like this?
            if dist.files is not None:
                packages_in_dist = set(x.parts[0] for x in dist.files if not x.parts[0].endswith('.dist-info'))
                for package in packages_in_dist:
                    self.packages[package] = os.path.join(temp_dir, package)

        return dists
