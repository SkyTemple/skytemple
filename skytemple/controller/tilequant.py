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
import sys
from enum import Enum
from functools import partial

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_tilequant.aikku.image_converter import AikkuImageConverter, DitheringMode
from skytemple_tilequant.image_converter import ImageConverter
from skytemple_files.common.i18n_util import _

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk
logger = logging.getLogger(__name__)


class ImageConversionMode(Enum):
    DITHERING_ORDERED = 0
    DITHERING_FLOYDSTEINBERG = 1
    NO_DITHERING = 2
    JUST_REORGANIZE = 3


class TilequantController:
    """A dialog controller as an UI for tilequant."""
    def __init__(self, parent_window: Gtk.Window, builder: Gtk.Builder):
        self.window: Gtk.Window = builder.get_object('dialog_tilequant')
        self.window.set_transient_for(parent_window)
        self.window.set_attached_to(parent_window)
        
        # Filters
        png_filter = Gtk.FileFilter()
        png_filter.set_name(_("PNG image (*.png)"))
        png_filter.add_mime_type("image/png")
        png_filter.add_pattern("*.png")

        jpg_filter = Gtk.FileFilter()
        jpg_filter.set_name(_("JPEG image (*.jpg, *.jpeg)"))
        jpg_filter.add_mime_type("image/jpge")
        jpg_filter.add_pattern("*.jpg")
        jpg_filter.add_pattern("*.jpeg")

        any_filter = Gtk.FileFilter()
        any_filter.set_name(_("Any files"))
        any_filter.add_pattern("*")

        tq_input_file: Gtk.FileChooserButton = builder.get_object('tq_input_file')
        tq_input_file.add_filter(png_filter)
        tq_input_file.add_filter(jpg_filter)
        tq_input_file.add_filter(any_filter)

        tq_second_file: Gtk.FileChooserButton = builder.get_object('tq_second_file')
        tq_second_file.add_filter(png_filter)
        tq_second_file.add_filter(jpg_filter)
        tq_second_file.add_filter(any_filter)

        builder.get_object('tq_number_palettes_help').connect('clicked', partial(
            self.show_help, _('The maximum number of palettes that can be used. For normal backgrounds, '
                              'this can be a max. of 16. For map backgrounds, both layers share in total 14 palettes '
                              '(since the last 2 palettes are not rendered in game).')
        ))
        builder.get_object('tq_transparent_color_help').connect('clicked', partial(
            self.show_help, _('This exact color of the image will be imported as transparency (default: #12ab56).')
        ))
        builder.get_object('tq_second_file_help').connect('clicked', partial(
            self.show_help, _('You can use this to convert multiple images at once with the same palettes. '
                              'This is useful for map backgrounds with multiple layers, that need to share the same '
                              'palettes.')
        ))
        builder.get_object('tq_mode_help').connect('clicked', partial(
            self.show_help,
            _('Dither: Colors will be reorganized and reduced if necessary. Colors will be changed so that they '
              '"blend into" each other. This will make the image look like it contains more colors but also might '
              'decrease the overall visual quality. Two different algorithms are available.\n\n'
              'No Dithering: Color will be reorganized and reduced if necessary. No dithering will be performed.\n\n'
              'Reorganize colors only: Colors will be reorganized so that they fit the game\'s format. SkyTemple will '
              'not attempt to reduce the amount of overall colors to make this work, so you will get an error, if '
              'it\'s not possible with the current amount. However if it does work, the output image will look '
              'identical to the original image.')
        ))
        builder.get_object('tq_dither_level_help').connect('clicked', partial(
            self.show_help,
            _('Only relevant if dithering is enabled: This controls the amount of dithering applied.')
        ))
        builder.get_object('tq_convert').connect('clicked', self.convert)
        self.builder = builder
        self._previous_output_image = None
        self._previous_second_output_image = None

    def run(self, num_pals=16, num_colors=16):
        """
        Shows the tilequant dialog. Doesn't return anything.
        """
        self.builder.get_object('tq_number_palettes').set_text(str(num_pals))
        self.builder.get_object('tq_input_file').unselect_all()
        self.builder.get_object('tq_second_file').unselect_all()
        self.window.run()
        self.window.hide()

    def convert(self, *args):

        mode_cb: Gtk.ComboBox = self.builder.get_object('tq_mode')
        mode = ImageConversionMode(mode_cb.get_model()[mode_cb.get_active_iter()][0])
        dither_level = self.builder.get_object('tq_dither_level').get_value()
        has_first_image = self.builder.get_object('tq_input_file').get_filename() is not None
        has_second_image = self.builder.get_object('tq_second_file').get_filename() is not None

        if not has_first_image:
            self.error(_("Please select an input image."))
            return
        if has_second_image:
            md = SkyTempleMessageDialog(self.window,
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("Since you selected two images to convert, you will be "
                                                              "asked for both images where to save them to."))
            md.run()
            md.destroy()

        dialog = Gtk.FileChooserNative.new(
            _("Save first image as (PNG)..."),
            self.window,
            Gtk.FileChooserAction.SAVE,
            None, None
        )
        if self._previous_output_image is not None:
            dialog.set_filename(self._previous_output_image)

        add_dialog_png_filter(dialog)

        response = dialog.run()
        output_image = dialog.get_filename()
        if output_image and '.' not in output_image:
            output_image += '.png'
        self._previous_output_image = output_image
        dialog.destroy()
        if response != Gtk.ResponseType.ACCEPT:
            return

        if has_second_image:
            dialog = Gtk.FileChooserNative.new(
                _("Save second image as (PNG)..."),
                self.window,
                Gtk.FileChooserAction.SAVE,
                None, None
            )
            if self._previous_second_output_image is not None:
                dialog.set_filename(self._previous_second_output_image)
            else:
                dialog.set_filename(output_image)

            add_dialog_png_filter(dialog)

            response = dialog.run()
            second_output_image = dialog.get_filename()
            if '.' not in second_output_image:
                second_output_image += '.png'
            self._previous_second_output_image = second_output_image
            dialog.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return

        try:
            num_pals = int(self.builder.get_object('tq_number_palettes').get_text())
            input_image = self.builder.get_object('tq_input_file').get_filename()
            second_input_file = self.builder.get_object('tq_second_file').get_filename()
            transparent_color = self.builder.get_object('tq_transparent_color').get_color()
            transparent_color = (
                int(transparent_color.red_float * 255),
                int(transparent_color.green_float * 255),
                int(transparent_color.blue_float * 255)
            )
        except ValueError:
            self.error(_("You entered invalid numbers."))
        else:
            if not os.path.exists(input_image):
                self.error(_("The input image does not exist."))
                return
            if has_second_image and not os.path.exists(second_input_file):
                self.error(_("The second input image does not exist."))
                return
            with open(input_image, 'rb') as input_file:
                try:
                    if not has_second_image:
                        # Only one image
                        image = Image.open(input_file)
                    else:
                        # Two images: Merge them.
                        image1 = Image.open(input_file)
                        image2 = Image.open(second_input_file)
                        image = Image.new(
                            'RGBA',
                            (max(image1.width, image2.width), image1.height + image2.height),
                            transparent_color
                        )
                        image.paste(image1, (0, 0))
                        image.paste(image2, (0, image1.height))
                except OSError:
                    self.error(_("The input image is not a supported format."))
                    return
                try:
                    img = self._convert(image, transparent_color, mode, num_pals, dither_level)
                    if not has_second_image:
                        # Only one image
                        img.save(output_image)
                    else:
                        # Two images: Un-merge them.
                        img.crop((0, 0, image1.width, image1.height)).save(output_image)
                        img.crop((0, image1.height, image2.width, image1.height + image2.height)).save(second_output_image)
                except BaseException as err:
                    logger.error("Tilequant error.", exc_info=err)
                    self.error(str(err))
                else:
                    md = SkyTempleMessageDialog(self.window,
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                                Gtk.ButtonsType.OK, _("Image was converted."), is_success=True)
                    md.run()
                    md.destroy()

    def show_help(self, info, *args):
        md = SkyTempleMessageDialog(self.window,
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, info)
        md.run()
        md.destroy()

    def error(self, msg):
        display_error(
            sys.exc_info(),
            msg
        )

    def _convert(self, image, transparent_color, mode, num_pals, dither_level):
        if mode == ImageConversionMode.JUST_REORGANIZE:
            converter = ImageConverter(image, transparent_color=transparent_color)
            return converter.convert(num_pals, colors_per_palette=16, color_steps=-1, max_colors=256,
                                     low_to_high=False, mosaic_limiting=False)
        converter = AikkuImageConverter(image, transparent_color)
        dither_mode = DitheringMode.NONE
        if mode == ImageConversionMode.DITHERING_ORDERED:
            dither_mode = DitheringMode.ORDERED
        elif mode == ImageConversionMode.DITHERING_FLOYDSTEINBERG:
            dither_mode = DitheringMode.FLOYDSTEINBERG
        return converter.convert(
            num_pals,
            dithering_mode=dither_mode,
            dithering_level=dither_level
        )
