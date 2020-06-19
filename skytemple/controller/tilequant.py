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
import logging
import os
from functools import partial

from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_tilequant.image_converter import ImageConverter

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk
logger = logging.getLogger(__name__)


class TilequantController:
    """A dialog controller as an UI for tilequant."""
    def __init__(self, parent_window: Gtk.Window, builder: Gtk.Builder):
        self.window: Gtk.Window = builder.get_object('dialog_tilequant')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        
        # Filters
        png_filter = Gtk.FileFilter()
        png_filter.set_name("PNG image (*.png)")
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")

        jpg_filter = Gtk.FileFilter()
        jpg_filter.set_name("JPEG image (*.jpg, *.jpeg)")
        jpg_filter.add_mime_type("image/jpge")
        jpg_filter.add_pattern("*.jpg")
        jpg_filter.add_pattern("*.jpeg")

        any_filter = Gtk.FileFilter()
        any_filter.set_name("Any files")
        any_filter.add_pattern("*")

        tq_input_file: Gtk.FileChooserButton = builder.get_object('tq_input_file')
        tq_input_file.add_filter(jpg_filter)
        tq_input_file.add_filter(png_filter)
        tq_input_file.add_filter(any_filter)

        builder.get_object('tq_transparent_color_help').connect('clicked', partial(
            self.show_help, 'This exact color of the image will be imported as transparency (default: #12ab56).'
        ))
        builder.get_object('tq_max_colors_help').connect('clicked', partial(
            self.show_help, 'Highest overall amount of colors to test.'
        ))
        builder.get_object('tq_color_steps_help').connect('clicked', partial(
            self.show_help, 'By how much to reduce the number of colors in the image, '
                            'until a valid image is found.'
        ))
        builder.get_object('tq_direction_help').connect('clicked', partial(
            self.show_help, 'Either start with the lowest amount of colors and go up to "Max number of colors" '
                            '(Up), or the other way around (Down). Up is much faster, Down might have better quality.'
        ))
        builder.get_object('tq_color_limit_per_tile_help').connect('clicked', partial(
            self.show_help, 'Limit the tiles to a specific amount of colors they should use before '
                            'starting. This may help '
                            'increase the number of total colors in the image.'
        ))
        builder.get_object('tq_mosaic_limiting_help').connect('clicked', partial(
            self.show_help, 'Toggle mosaic limiting, enabling it will limit increasingly bigger '
                            'sections of the image to a limited amount of colors, based on '
                            '"Color Limit per Tile".'
        ))
        builder.get_object('tq_convert').connect('clicked', self.convert)
        self.builder = builder
        self._previous_output_image = None

    def run(self, num_pals=16, num_colors=16):
        """
        Shows the tilequant dialog. Doesn't return anything.
        """
        self.window.run()
        self.window.hide()

    def convert(self, *args):

        dialog = Gtk.FileChooserDialog(
            "Save PNG as...",
            self.window,
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )
        if self._previous_output_image is not None:
            dialog.set_filename(self._previous_output_image)

        add_dialog_png_filter(dialog)

        response = dialog.run()
        output_image = dialog.get_filename()
        self._previous_output_image = output_image
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return

        try:
            max_colors = int(self.builder.get_object('tq_max_colors').get_text())
            color_steps = int(self.builder.get_object('tq_color_steps').get_text())
            low_to_high = False if self.builder.get_object('tq_direction').get_active_text() == 'Down' else True
            color_limit_per_tile = int(self.builder.get_object('tq_color_limit_per_tile').get_text())
            mosaic_limiting = self.builder.get_object('tq_mosaic_limiting').get_active()
            input_image = self.builder.get_object('tq_input_file').get_filename()
            transparent_color = self.builder.get_object('tq_transparent_color').get_color()
            transparent_color = (
                int(transparent_color.red_float * 255),
                int(transparent_color.green_float * 255),
                int(transparent_color.blue_float * 255)
            )
        except ValueError:
            self.error("You entered invalid numbers.")
        else:
            if not os.path.exists(input_image):
                self.error("The input image does not exist.")
                return
            with open(input_image, 'rb') as input_file:
                try:
                    image = Image.open(input_file)
                except OSError:
                    self.error("The input image is not a supported format.")
                    return
                try:
                    converter = ImageConverter(image, BPC_TILE_DIM, BPC_TILE_DIM, transparent_color)
                    img = converter.convert(low_to_high=low_to_high,
                                            max_colors=max_colors,
                                            color_steps=color_steps,
                                            color_limit_per_tile=color_limit_per_tile,
                                            mosaic_limiting=mosaic_limiting)
                    img.save(output_image)
                except BaseException as err:
                    logger.error("Tilequant error.", exc_info=err)
                    self.error(str(err))
                else:
                    md = Gtk.MessageDialog(self.window,
                                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                           Gtk.ButtonsType.OK, "Image was conveted.")
                    md.run()
                    md.destroy()

    def show_help(self, info, *args):
        md = Gtk.MessageDialog(self.window,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                               Gtk.ButtonsType.OK, info)
        md.run()
        md.destroy()

    def error(self, msg):
        md = Gtk.MessageDialog(self.window,
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, msg,
                               title="Error!")
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()
