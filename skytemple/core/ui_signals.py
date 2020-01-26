"""GObject for custom UI signals"""
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
