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
import sys
from enum import Enum
from functools import partial
from typing import Optional, cast

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import add_dialog_png_filter, builder_get_assert
from skytemple_files.user_error import USER_ERROR_MARK
from tilequant import Tilequant, DitheringMode
from skytemple_files.common.i18n_util import _

from PIL import Image
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
        self.window = builder_get_assert(builder, Gtk.Dialog, 'dialog_tilequant')
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

        tq_input_file = builder_get_assert(builder, Gtk.FileChooserButton, 'tq_input_file')
        tq_input_file.add_filter(png_filter)
        tq_input_file.add_filter(jpg_filter)
        tq_input_file.add_filter(any_filter)

        tq_second_file = builder_get_assert(builder, Gtk.FileChooserButton, 'tq_second_file')
        tq_second_file.add_filter(png_filter)
        tq_second_file.add_filter(jpg_filter)
        tq_second_file.add_filter(any_filter)

        builder_get_assert(builder, Gtk.Button, 'tq_number_palettes_help').connect('clicked', partial(
            self.show_help, _('The maximum number of palettes that can be used. For normal backgrounds, '
                              'this can be a max. of 16. For map backgrounds, both layers share in total 14 palettes '
                              '(since the last 2 palettes are not rendered in game).')
        ))
        builder_get_assert(builder, Gtk.Button, 'tq_transparent_color_help').connect('clicked', partial(
            self.show_help, _('This exact color of the image will be imported as transparency (default: #12ab56).')
        ))
        builder_get_assert(builder, Gtk.Button, 'tq_second_file_help').connect('clicked', partial(
            self.show_help, _('You can use this to convert multiple images at once with the same palettes. '
                              'This is useful for map backgrounds with multiple layers, that need to share the same '
                              'palettes.')
        ))
        builder_get_assert(builder, Gtk.Button, 'tq_mode_help').connect('clicked', partial(
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
        builder_get_assert(builder, Gtk.Button, 'tq_dither_level_help').connect('clicked', partial(
            self.show_help,
            _('Only relevant if dithering is enabled: This controls the amount of dithering applied.')
        ))
        builder_get_assert(builder, Gtk.Button, 'tq_convert').connect('clicked', self.convert)
        self.builder = builder
        self._previous_output_image: Optional[str] = None
        self._previous_second_output_image: Optional[str] = None

    def run(self, num_pals=16, num_colors=16):
        """
        Shows the tilequant dialog. Doesn't return anything.
        """
        builder_get_assert(self.builder, Gtk.Entry, 'tq_number_palettes').set_text(str(num_pals))
        builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_input_file').unselect_all()
        builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_second_file').unselect_all()
        self.window.run()
        self.window.hide()

    def convert(self, *args):

        mode_cb = builder_get_assert(self.builder, Gtk.ComboBox, 'tq_mode')
        active_iter = mode_cb.get_active_iter()
        if active_iter is None:
            return
        mode = ImageConversionMode(mode_cb.get_model()[active_iter][0])
        dither_level = builder_get_assert(self.builder, Gtk.Adjustment, 'tq_dither_level').get_value()
        has_first_image = builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_input_file').get_filename() is not None
        has_second_image = builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_second_file').get_filename() is not None

        if not has_first_image:
            self.error(_("Please select an input image."), should_report=False)
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
        if output_image is None:
            return
        if '.' not in output_image:
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
            if second_output_image is not None:
                if '.' not in second_output_image:
                    second_output_image += '.png'
            self._previous_second_output_image = second_output_image
            dialog.destroy()
            if response != Gtk.ResponseType.ACCEPT:
                return

        try:
            num_tile_cluster_passes = int(builder_get_assert(self.builder, Gtk.Entry, 'tq_num_tile_cluster_passes').get_text())
            assert num_tile_cluster_passes > 0
        except (ValueError, AssertionError):
            num_tile_cluster_passes = 0
        try:
            num_color_cluster_passes = int(builder_get_assert(self.builder, Gtk.Entry, 'tq_num_color_cluster_passes').get_text())
            assert num_color_cluster_passes > 0
        except (ValueError, AssertionError):
            num_color_cluster_passes = 0
            
        try:
            num_pals = int(builder_get_assert(self.builder, Gtk.Entry, 'tq_number_palettes').get_text())
            input_image = builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_input_file').get_filename()
            second_input_file = builder_get_assert(self.builder, Gtk.FileChooserButton, 'tq_second_file').get_filename()
            transparent_color_v = builder_get_assert(self.builder, Gtk.ColorButton, 'tq_transparent_color').get_color()
            assert input_image is not None
            assert transparent_color_v is not None
            transparent_color = (
                int(cast(float, transparent_color_v.red_float) * 255),
                int(cast(float, transparent_color_v.green_float) * 255),
                int(cast(float, transparent_color_v.blue_float) * 255)
            )
        except (ValueError, AssertionError):
            self.error(_("You entered invalid numbers."), should_report=False)
        else:
            if not os.path.exists(input_image):
                self.error(_("The input image does not exist."), should_report=False)
                return
            if has_second_image and second_input_file is not None and not os.path.exists(second_input_file):
                self.error(_("The second input image does not exist."), should_report=False)
                return
            with open(input_image, 'rb') as input_file:
                try:
                    if not has_second_image or second_input_file is None:
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
                    self.error(_("The input image is not a supported format."), should_report=False)
                    return
                try:
                    img = self._convert(image, transparent_color, mode, num_pals, dither_level, num_color_cluster_passes, num_tile_cluster_passes)
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

    def error(self, msg, should_report=True):
        display_error(
            sys.exc_info(),
            msg,
            should_report=should_report
        )

    def _convert(self, image, transparent_color, mode, num_pals, dither_level, num_color_cluster_passes, num_tile_cluster_passes):
        converter = Tilequant(image, transparent_color)
        if mode == ImageConversionMode.JUST_REORGANIZE:
            try:
                return converter.simple_convert(num_pals, 16)
            except ValueError as e:
                setattr(e, USER_ERROR_MARK, True)
                raise e
        dither_mode = DitheringMode.NONE
        if mode == ImageConversionMode.DITHERING_ORDERED:
            dither_mode = DitheringMode.ORDERED
        elif mode == ImageConversionMode.DITHERING_FLOYDSTEINBERG:
            dither_mode = DitheringMode.FLOYDSTEINBERG
        return converter.convert(
            num_pals,
            dithering_mode=dither_mode,
            dithering_level=dither_level,
            num_color_cluster_passes=num_color_cluster_passes,
            num_tile_cluster_passes=num_tile_cluster_passes
        )
