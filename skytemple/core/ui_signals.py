"""GObject for custom UI signals"""
#  Copyright 2020 Parakoopa
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

from gi.repository.GObject import GObject, SignalFlags, TYPE_PYOBJECT

SIGNAL_OPENED = 'rom_project_opened'
SIGNAL_OPENED_ERROR = 'rom_project_opened_error'
SIGNAL_SAVED = 'rom_project_saved'
SIGNAL_SAVED_ERROR = 'rom_project_saved_error'
SIGNAL_VIEW_LOADED = 'module_view_loaded'
SIGNAL_VIEW_LOADED_ERROR = 'module_view_loaded_error'


class SkyTempleSignalContainer(GObject):
    __gsignals__ = {
        SIGNAL_OPENED:                  (SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_OPENED_ERROR:            (SignalFlags.RUN_FIRST, None, (str, )),
        SIGNAL_SAVED:                   (SignalFlags.RUN_FIRST, None, ()),
        SIGNAL_SAVED_ERROR:             (SignalFlags.RUN_FIRST, None, (str, )),
                                                                      # AbstractModule, AbstractController
        SIGNAL_VIEW_LOADED:             (SignalFlags.RUN_FIRST, None, (TYPE_PYOBJECT,   TYPE_PYOBJECT,     int)),
                                                                      # BaseException
        SIGNAL_VIEW_LOADED_ERROR:       (SignalFlags.RUN_FIRST, None, (TYPE_PYOBJECT, ))
    }
