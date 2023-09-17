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

import logging
import os.path
import sys
from typing import Callable, Sequence

from skytemple.core.plugin_loader.finder import SkyTemplePluginFinder
from skytemple.core.settings import SkyTempleSettingsStore


logger = logging.getLogger(__name__)


def load_plugins(
    load_confirmation: Callable[[Sequence[str], SkyTempleSettingsStore, str], bool],
    settings: SkyTempleSettingsStore,
    plugin_dir: str
):
    """
    Load plugin wheels from the SkyTemple plugins directory.
    `load_confirmation` is prompted to confirm.
    """
    finder = SkyTemplePluginFinder(settings, plugin_dir)
    plugins = finder.st_list()
    if len(plugins) < 1:
        return
    logger.info(f"Found potential plugins to load: {plugins}")
    if load_confirmation(plugins, settings, plugin_dir):
        sys.meta_path.append(finder)
