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
import re
import sys
from functools import partial
from typing import TYPE_CHECKING, cast
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
from skytemple.core.ui_utils import add_dialog_png_filter, data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.portrait.module import PortraitModule
logger = logging.getLogger(__name__)


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "portrait", "portrait.ui"))
class StPortraitPortraitPage(Gtk.Box):
    __gtype_name__ = "StPortraitPortraitPage"
    module: PortraitModule
    item_data: int
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image10: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image11: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image12: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image13: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image14: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image15: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image16: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image17: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image18: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image19: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image2: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image20: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image21: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image22: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image23: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image24: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image25: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image26: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image27: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image28: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image29: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image3: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image30: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image31: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image32: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image33: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image34: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image35: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image36: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image37: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image38: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image39: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image4: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image40: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image5: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image6: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image7: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image8: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image9: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    button_import: Gtk.MenuToolButton = cast(Gtk.MenuToolButton, Gtk.Template.Child())
    separate_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    spritebot_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    export: Gtk.MenuToolButton = cast(Gtk.MenuToolButton, Gtk.Template.Child())
    separate_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    spritebot_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    spritecollab_browser: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    portrait_draw1: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label1: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_label41: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw2: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label2: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw3: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label3: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw4: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label4: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw5: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label5: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw6: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label6: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw7: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label7: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw8: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label8: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw9: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label9: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw10: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label10: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw11: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label11: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw12: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label12: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw13: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label13: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw14: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label14: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw15: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label15: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw16: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label16: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw17: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label17: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw18: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label18: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw19: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label19: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw20: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label20: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw21: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label21: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw22: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label22: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw23: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label23: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw24: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label24: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw25: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label25: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw26: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label26: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw27: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label27: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw28: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label28: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw29: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label29: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw30: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label30: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw31: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label31: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw32: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label32: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw33: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label33: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw34: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label34: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw35: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label35: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw36: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label36: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw37: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label37: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw38: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label38: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw39: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label39: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    portrait_draw40: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    portrait_label40: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())

    def __init__(self, module: PortraitModule, item_data: int, mark_as_modified_cb):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._portrait_provider = self.module.get_portrait_provider()
        self._draws: list[Gtk.DrawingArea] = []
        self._mark_as_modified_cb = mark_as_modified_cb
        self.kao = self.module.kao
        for index, subindex, kao in self.kao:
            gui_number = subindex + 1
            portrait_name = self.module.get_portrait_name(subindex)
            getattr(self, f"portrait_label{gui_number}").set_text(portrait_name)
            draw = getattr(self, f"portrait_draw{gui_number}")
            self._draws.append(draw)
            draw.connect("draw", partial(self.on_draw, subindex))

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.image1)
        safe_destroy(self.image10)
        safe_destroy(self.image11)
        safe_destroy(self.image12)
        safe_destroy(self.image13)
        safe_destroy(self.image14)
        safe_destroy(self.image15)
        safe_destroy(self.image16)
        safe_destroy(self.image17)
        safe_destroy(self.image18)
        safe_destroy(self.image19)
        safe_destroy(self.image2)
        safe_destroy(self.image20)
        safe_destroy(self.image21)
        safe_destroy(self.image22)
        safe_destroy(self.image23)
        safe_destroy(self.image24)
        safe_destroy(self.image25)
        safe_destroy(self.image26)
        safe_destroy(self.image27)
        safe_destroy(self.image28)
        safe_destroy(self.image29)
        safe_destroy(self.image3)
        safe_destroy(self.image30)
        safe_destroy(self.image31)
        safe_destroy(self.image32)
        safe_destroy(self.image33)
        safe_destroy(self.image34)
        safe_destroy(self.image35)
        safe_destroy(self.image36)
        safe_destroy(self.image37)
        safe_destroy(self.image38)
        safe_destroy(self.image39)
        safe_destroy(self.image4)
        safe_destroy(self.image40)
        safe_destroy(self.image5)
        safe_destroy(self.image6)
        safe_destroy(self.image7)
        safe_destroy(self.image8)
        safe_destroy(self.image9)

    def re_render(self):
        self._portrait_provider.reset()
        for draw in self._draws:
            draw.queue_draw()

    def on_draw(self, subindex: int, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        portrait = self._portrait_provider.get(
            self.item_data, subindex, lambda: GLib.idle_add(widget.queue_draw), False
        )
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

    @Gtk.Template.Callback()
    def on_export_clicked(self, w: Gtk.MenuToolButton):
        cast(Gtk.Menu, w.get_menu()).popup(None, None, None, None, 0, Gtk.get_current_event_time())

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, w: Gtk.MenuToolButton):
        cast(Gtk.Menu, w.get_menu()).popup(None, None, None, None, 0, Gtk.get_current_event_time())

    @Gtk.Template.Callback()
    def on_delete_clicked(self, label: Gtk.Label):
        index = int(label.get_label().split(":")[0])
        self.kao.delete(self.item_data, index)
        self.re_render()
        # Mark as modified
        self.module.mark_as_modified()
        self._mark_as_modified_cb()

    @Gtk.Template.Callback()
    def on_separate_export_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export all portraits as PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"),
            None,
        )
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            base_filename = os.path.join(fn, f"{self.item_data + 1}")
            for subindex in range(0, SUBENTRIES):
                kao = self.kao.get(self.item_data, subindex)
                if kao:
                    filename = f"{base_filename}_{subindex}.png"
                    img = kao.get()
                    img.save(filename)

    @Gtk.Template.Callback()
    def on_separate_import_activate(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            f(
                _(
                    "To import, select a directory to import from. Files with the pattern '{self.item_data + 1}_XX.png'\nwill be imported, where XX is a number between 0 and 39."
                )
            ),
            title=_("Import Portraits"),
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import portraits from PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None,
            None,
        )
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            r = re.compile(f"{self.item_data + 1}_(\\d+)\\.png", re.IGNORECASE)
            imgs = {
                int(match[1]): name
                for match, name in self._try_match_import(r, os.listdir(fn))
                if match is not None and int(match[1]) <= 40
            }
            for subindex, image_fn in imgs.items():
                try:
                    with open(os.path.join(fn, image_fn), "rb") as file:
                        image = Image.open(file)
                        self.kao.set_from_img(self.item_data, subindex, image)
                except Exception as err:
                    name = self.module.get_portrait_name(subindex)
                    logger.error(f"Failed importing image '{name}'.", exc_info=err)
                    display_error(
                        sys.exc_info(),
                        f(_('Failed importing image "{name}":\n{err}')),
                        f(_(f"Error for '{name}'.")),
                    )
            self.re_render()
            # Mark as modified
            self.module.mark_as_modified()
            self._mark_as_modified_cb()

    @Gtk.Template.Callback()
    def on_spritebot_export_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export portrait as PNG sheet..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None,
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        dialog.destroy()
        fn = dialog.get_filename()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, "png")
            SpriteBotSheet.create(self.kao, self.item_data).save(fn)

    @Gtk.Template.Callback()
    def on_spritebot_import_activate(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Import portraits from PNG sheet..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None,
            None,
        )
        add_dialog_png_filter(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            self.module.import_sheet(self.item_data, fn)
            self.re_render()
            self._mark_as_modified_cb()

    @Gtk.Template.Callback()
    def on_spritecollab_browser_clicked(self, *args):
        MainController.show_spritecollab_browser()

    def _try_match_import(self, r, names):
        for name in names:
            yield (r.match(name), name)
