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
import re
import sys
from functools import partial
from typing import TYPE_CHECKING

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple_files.graphics.w16.model import W16, W16AtImage, W16TocEntry

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule

logger = logging.getLogger(__name__)


class W16Controller(AbstractController):
    def __init__(self, module: 'MiscGraphicsModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.w16: W16 = self.module.get_w16(self.item_id)
        self._draws = []
        self._surfaces = []

        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'w16.glade')
        self.builder.connect_signals(self)

        self._reset()

        return self.builder.get_object('box_main')

    def on_draw(self, index: int, widget: Gtk.DrawingArea, ctx: cairo.Context):
        w16 = self._surfaces[index]
        ctx.set_source_rgb(0, 0, 0)
        ctx.rectangle(0, 0, *widget.get_size_request())
        ctx.fill()
        ctx.set_source_surface(w16)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()

    def on_export_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export all images as PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            _("_Save"), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            for index, image in enumerate(self.w16):
                filename = os.path.join(fn, f'{index}.png')
                img = image.get()
                img.save(filename)

    def on_import_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("To import, select a directory to import from. Files with the pattern 'XX.png'\n"
              "will be imported, where XX is a number between 0 and 99. The image dimensions must be a multiple of 8."),
            title=_("Import Images")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import images from PNGs..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            r = re.compile(rf"(\d+)\.png", re.IGNORECASE)
            imgs_dict = {int(match[1]): name
                         for match, name in self._try_match_import(r, os.listdir(fn))
                         if match is not None}
            imgs = []
            # Convert imgs to list
            for i in range(0, len(imgs_dict)):
                if i not in imgs_dict:
                    display_error(
                        None,
                        f(_('Failed importing image "{i}":\nImage for number {i} missing.')),
                        _('Image for number {i} missing.')
                    )
                    return
                imgs.append(imgs_dict[i])
            if len(imgs) == 0:
                display_error(
                    None,
                    _('No images found.'),
                    _("No images found.")
                )
                return
            for index, image_fn in enumerate(imgs):
                try:
                    with open(os.path.join(fn, image_fn), 'rb') as file:
                        image = Image.open(file)
                        if len(self.w16) > index:
                            # Existing image, update
                            self.w16[index].set(image)
                        else:
                            self.w16.append(W16AtImage.new(W16TocEntry(0, 0, 0, 0), image))
                except Exception as err:
                    logger.error(f(_("Failed importing image '{index}'.")), exc_info=err)
                    display_error(
                        sys.exc_info(),
                        f(_('Failed importing image "{index}":\n{err}')),
                        f(_("Error for '{index}'."))
                    )
            # Re-render
            self._reset()
            for draw in self._draws:
                draw.queue_draw()
            # Mark as modified
            self.module.mark_w16_as_modified(self.item_id)

    def _try_match_import(self, r, names):
        for name in names:
            yield r.match(name), name

    def _reset(self):
        grid: Gtk.Grid = self.builder.get_object('grid')
        self._surfaces = []
        for child in grid:
            grid.remove(child)
        for index, image_c in enumerate(self.w16):
            image = image_c.get()
            x = index % 4
            y = int(index / 4)
            draw = self._append(grid, x, y, index, image)
            self._draws.append(draw)
            draw.connect('draw', partial(self.on_draw, index))

    def _append(self, grid: Gtk.Grid, x, y, index, image: Image.Image) -> Gtk.DrawingArea:
        self._surfaces.append(self._get_surface(image))
        box: Gtk.Box = Gtk.Box.new(Gtk.Orientation.VERTICAL, 5)
        box.set_margin_bottom(10)
        label: Gtk.Label = Gtk.Label.new(f'{index}')
        draw_area: Gtk.DrawingArea = Gtk.DrawingArea.new()
        draw_area.set_halign(Gtk.Align.CENTER)
        draw_area.set_size_request(64, 64)
        box.pack_start(draw_area, False, True, 0)
        box.pack_start(label, False, True, 0)
        grid.attach(box, x, y, 1, 1)
        box.show_all()
        return draw_area

    def _get_surface(self, img: Image.Image):
        return pil_to_cairo_surface(img.resize((64, 64), Image.NEAREST).convert('RGBA'))
