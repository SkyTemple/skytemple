#  Copyright 2020-2025 SkyTemple Contributors
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
import sys
from typing import TYPE_CHECKING, cast
import cairo
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple_files.common.util import add_extension_if_missing
from skytemple_files.graphics.colvec.model import Colvec
from skytemple_dtef.explorers_dtef import ExplorersDtef
from PIL import Image
from gi.repository import Gtk
from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir
from skytemple.core.string_provider import StringType
from skytemple_files.common.i18n_util import _
from skytemple_files.graphics.dma.protocol import DmaProtocol
from skytemple_files.graphics.dpc.protocol import DpcProtocol
from skytemple_files.graphics.dpci.protocol import DpciProtocol
from skytemple_files.graphics.dpl.protocol import DplProtocol
from skytemple_files.graphics.dpla.protocol import DplaProtocol

from skytemple.init_locale import LocalePatchedGtkTemplate

logger = logging.getLogger(__name__)
if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon_graphics", "colvec.ui"))
class StDungeonGraphicsColvecPage(Gtk.Paned):
    __gtype_name__ = "StDungeonGraphicsColvecPage"
    module: DungeonGraphicsModule
    item_data: str
    cb_tileset_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    cb_weather_store: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    button_import: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    export: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    cb_tileset: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    description1: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    draw_colormap: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    draw_tileset: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    cb_weather: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    description: Gtk.CellRendererText = cast(Gtk.CellRendererText, Gtk.Template.Child())
    colvec_info: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())

    def __init__(self, module: DungeonGraphicsModule, item_data: str):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._suppress_signals = True
        self._string_provider = module.project.get_string_provider()
        self.colvec: Colvec = self.module.get_colvec()
        self.dma: DmaProtocol
        self.dpl: DplProtocol
        self.dpla: DplaProtocol
        self.dpc: DpcProtocol
        self.dpci: DpciProtocol
        self._init_colvec()
        self._reinit_image()
        self.draw_tileset.connect("draw", self.exec_draw_tileset)
        self.draw_colormap.connect("draw", self.exec_draw_colormap)
        self._suppress_signals = False

    @Gtk.Template.Callback()
    def on_export_clicked(self, *args):
        cb_store = self.cb_weather_store
        cb = self.cb_weather
        it = cb.get_active_iter()
        assert it is not None
        v: int = cb_store[it][0]
        dialog = Gtk.FileChooserNative.new(
            _("Export current colormap as PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            "_Save",
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, "png")
            self.colvec.to_pil(v).save(fn)

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, *args):
        cb_store = self.cb_weather_store
        cb = self.cb_weather
        it = cb.get_active_iter()
        assert it is not None
        v: int = cb_store[it][0]
        dialog = Gtk.FileChooserNative.new(
            _("Import current colormap from PNG..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None,
            None,
        )
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                img = Image.open(fn, "r")
                self.colvec.from_pil(v, img)
                self.module.mark_colvec_as_modified()
            except Exception as err:
                display_error(sys.exc_info(), str(err), _("Error importing colormap."))
            self._reinit_image()

    def _load_tileset(self, v):
        self.dma = self.module.get_dma(v)
        self.dpl = self.module.get_dpl(v)
        self.dpla = self.module.get_dpla(v)
        self.dpc = self.module.get_dpc(v)
        self.dpci = self.module.get_dpci(v)

    @Gtk.Template.Callback()
    def on_colvec_info_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "This colormap defines color palette transformations used by the game during dungeons (for weather effects).\nEach color color component (RGB) is changed to the corresponding color component of the n-th color map entry (where n is the old color component value).\nThis transformation also applies to monsters and items sprites."
            ),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_tileset_changed(self, widget):
        if not self._suppress_signals:
            cb_store = self.cb_tileset_store
            cb = self.cb_tileset
            it = cb.get_active_iter()
            assert it is not None
            v: int = cb_store[it][0]
            self._load_tileset(v)
            self._reinit_image()

    @Gtk.Template.Callback()
    def on_weather_changed(self, widget):
        if not self._suppress_signals:
            self._reinit_image()

    def _init_colvec(self):
        # Init available weathers
        cb_store = self.cb_weather_store
        cb = self.cb_weather
        self._fill_available_weathers_into_store(cb_store)
        cb.set_active(0)
        # Init available tilesets
        cb2_store = self.cb_tileset_store
        cb2 = self.cb_tileset
        self._fill_available_tilesets_into_store(cb2_store)
        self._load_tileset(0)
        cb2.set_active(0)

    def _reinit_image(self):
        cb_store = self.cb_weather_store
        cb = self.cb_weather
        it = cb.get_active_iter()
        assert it is not None
        v: int = cb_store[it][0]
        surface = self.colvec.to_pil(v)
        surface = surface.resize((surface.width * 16, surface.height * 16), resample=Image.NEAREST)
        self.colormap = pil_to_cairo_surface(surface.convert("RGBA"))
        self.surface = None
        if self.dma:
            self.dtef = ExplorersDtef(self.dma, self.dpc, self.dpci, self.dpl, self.dpla)
            surface = self.dtef.get_tiles()[0]
            # Apply colormap
            surface.putpalette(self.colvec.apply_colormap(v, list(surface.palette.palette)))
            self.surface = pil_to_cairo_surface(surface.convert("RGBA"))
        self.draw_tileset.queue_draw()
        self.draw_colormap.queue_draw()

    def _fill_available_tilesets_into_store(self, cb_store):
        # Init combobox
        cb_store.clear()
        for v in range(self.module.nb_tilesets()):
            cb_store.append([v, f"Tileset {v}"])

    def _fill_available_weathers_into_store(self, cb_store):
        # Init combobox
        cb_store.clear()
        for v in range(self.colvec.nb_colormaps()):
            cb_store.append([v, self._string_provider.get_value(StringType.WEATHER_NAMES, v)])

    def exec_draw_tileset(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True

    def exec_draw_colormap(self, wdg, ctx: cairo.Context, *args):
        if self.colormap:
            wdg.set_size_request(self.colormap.get_width(), self.colormap.get_height())
            ctx.fill()
            ctx.set_source_surface(self.colormap, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
