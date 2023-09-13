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
import logging
import os
import re
import sys
from functools import partial
from typing import TYPE_CHECKING, List, cast

import cairo
from PIL import Image
from gi.repository import Gtk, GLib
from skytemple_files.common.i18n_util import _, f
from skytemple_files.common.util import add_extension_if_missing
from skytemple_files.graphics.kao import SUBENTRIES
from skytemple_files.graphics.kao.sprite_bot_sheet import SpriteBotSheet

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import add_dialog_png_filter, builder_get_assert

if TYPE_CHECKING:
    from skytemple.module.portrait.module import PortraitModule
logger = logging.getLogger(__name__)


class PortraitController(AbstractController):
    def __init__(self, module: 'PortraitModule', item_id: int, mark_as_modified_cb):
        self.module = module
        self.item_id = item_id
        self._portrait_provider = self.module.get_portrait_provider()
        self._draws: List[Gtk.DrawingArea] = []
        self._mark_as_modified_cb = mark_as_modified_cb
        self.kao = self.module.kao

        self.builder: Gtk.Builder = None  # type: ignore

    def re_render(self):
        self._portrait_provider.reset()
        for draw in self._draws:
            draw.queue_draw()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'portrait.glade')
        self.builder.connect_signals(self)

        for index, subindex, kao in self.kao:
            gui_number = subindex + 1
            portrait_name = self.module.get_portrait_name(subindex)
            builder_get_assert(self.builder, Gtk.Label, f'portrait_label{gui_number}').set_text(portrait_name)
            draw = builder_get_assert(self.builder, Gtk.DrawingArea, f'portrait_draw{gui_number}')
            self._draws.append(draw)
            draw.connect('draw', partial(self.on_draw, subindex))

        return builder_get_assert(self.builder, Gtk.Widget, 'box_main')

    def on_draw(self, subindex: int, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        portrait = self._portrait_provider.get(self.item_id, subindex,
                                               lambda: GLib.idle_add(widget.queue_draw), False)
        ctx.set_source_rgb(1, 1, 1)
        w, h = widget.get_size_request()
        assert w is not None and h is not None
        ctx.rectangle(0, 0, w, h)
        ctx.fill()
        ctx.scale(scale, scale)
        ctx.set_source_surface(portrait)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.scale(1 / scale, 1 / scale)
        return True

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        cast(Gtk.Menu, w.get_menu()).popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def on_import_clicked(self, w: Gtk.MenuToolButton):
        cast(Gtk.Menu, w.get_menu()).popup(None, None, None, None, 0, Gtk.get_current_event_time())

    def on_delete_clicked(self, label: Gtk.Label):
        index = int(label.get_label().split(":")[0])
        self.kao.delete(self.item_id, index)
        self.re_render()
        # Mark as modified
        self.module.mark_as_modified()
        self._mark_as_modified_cb()

    def on_separate_export_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export all portraits as PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            base_filename = os.path.join(fn, f'{self.item_id + 1}')
            for subindex in range(0, SUBENTRIES):
                kao = self.kao.get(self.item_id, subindex)
                if kao:
                    filename = f'{base_filename}_{subindex}.png'
                    img = kao.get()
                    img.save(filename)

    def on_separate_import_activate(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            f(_("To import, select a directory to import from. Files with the pattern '{self.item_id + 1}_XX.png'\n"
                "will be imported, where XX is a number between 0 and 40.")),
            title=_("Import Portraits")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import portraits from PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            r = re.compile(rf"{self.item_id + 1}_(\d+)\.png", re.IGNORECASE)
            imgs = {int(match[1]): name
                    for match, name in self._try_match_import(r, os.listdir(fn))
                    if match is not None and int(match[1]) <= 40}
            for subindex, image_fn in imgs.items():
                try:
                    with open(os.path.join(fn, image_fn), 'rb') as file:
                        image = Image.open(file)
                        self.kao.set_from_img(self.item_id, subindex, image)
                except Exception as err:
                    name = self.module.get_portrait_name(subindex)
                    logger.error(f"Failed importing image '{name}'.", exc_info=err)
                    display_error(
                        sys.exc_info(),
                        f(_('Failed importing image "{name}":\n{err}')),
                        f(_(f"Error for '{name}'."))
                    )
            self.re_render()
            # Mark as modified
            self.module.mark_as_modified()
            self._mark_as_modified_cb()

    def on_spritebot_export_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export portrait as PNG sheet..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        dialog.destroy()

        fn = dialog.get_filename()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, 'png')
            SpriteBotSheet.create(self.kao, self.item_id).save(fn)

    def on_spritebot_import_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import portraits from PNG sheet..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            self.module.import_sheet(self.item_id, fn)
            self.re_render()
            self._mark_as_modified_cb()

    def on_spritecollab_browser_clicked(self, *args):
        MainController.show_spritecollab_browser()

    def _try_match_import(self, r, names):
        for name in names:
            yield r.match(name), name
