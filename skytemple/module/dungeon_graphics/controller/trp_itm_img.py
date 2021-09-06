#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import os
import sys
from enum import Enum, auto
from typing import TYPE_CHECKING, Union

import cairo
from PIL import Image
from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple_files.common.i18n_util import _
from skytemple_files.common.util import make_palette_colors_unique
from skytemple_files.graphics.img_itm.model import ImgItm
from skytemple_files.graphics.img_trp.model import ImgTrp

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule


class ImgType(Enum):
    ITM = auto()
    TRP = auto()


IMAGE_ZOOM = 4
MAX_ENTRIES = 10000


class TrpItmImgController(AbstractController):
    def __init__(self, module: 'DungeonGraphicsModule', img_type: ImgType):
        self.module = module
        self.img_type = img_type
        self.img: Union[ImgItm, ImgTrp] = self.module.get_icons(img_type)

        self.builder = None
        self.image_idx = 0
        self.palette_idx = 0

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'trp_itm_img.glade')
        if self.img_type == ImgType.ITM:
            self.builder.get_object('lbl_name').set_text(_('Items'))
        else:
            self.builder.get_object('lbl_name').set_text(_('Traps'))

        self._init_sprites()

        self.builder.connect_signals(self)
        self.builder.get_object('draw').connect('draw', self.draw)
        return self.builder.get_object('editor')

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        self.img.palettes = make_palette_colors_unique(self.img.palettes)
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("This will export the currently selected image with the currently selected palette. "
              "The image file itself contains all palettes, you can choose to import the edited palettes on import."),
            title=_("Export Images")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Export current image to folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            _('_Save'), None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            if '.' not in fn:
                fn += '.png'
            self.img.to_pil(self.image_idx, self.palette_idx).save(fn)

    def on_import_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Import image..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )
        add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            dialog: Gtk.Dialog = self.builder.get_object('dialog_import')

            dialog.set_attached_to(MainController.window())
            dialog.set_transient_for(MainController.window())

            resp = dialog.run()
            dialog.hide()
            if resp == Gtk.ResponseType.OK:
                import_palette = self.builder.get_object('switch_import_palette').get_active()
                import_new = self.builder.get_object('switch_import_new').get_active()
                img = Image.open(fn)
                if import_new:
                    idx = len(self.img.sprites)
                    self.img.sprites.append(None)
                else:
                    idx = self.image_idx
                try:
                    self.img.from_pil(idx, img, import_palette)
                    self.module.mark_icons_as_modified(self.img_type, self.img)
                    self.module.project.get_sprite_provider().reset()
                except Exception as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        "Error importing sprite."
                    )
                self._init_sprites(idx, self.palette_idx)

    def _init_sprites(self, sprite_idx=0, palette_idx=0):
        self.builder.get_object('entry_id').set_text(str(sprite_idx))
        self.builder.get_object('entry_id').set_increments(1, 1)
        self.builder.get_object('entry_id').set_range(0, len(self.img.sprites) - 1)
        self.builder.get_object('entry_palette').set_text(str(palette_idx))
        self.builder.get_object('entry_palette').set_increments(1, 1)
        self.builder.get_object('entry_palette').set_range(0, len(self.img.palettes) - 1)
        self._switch_entry()

    def on_entry_id_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1

        if val < 0:
            val = 0
            widget.set_text(str(val))
        elif val >= len(self.img.sprites):
            val = len(self.img.sprites) - 1
            widget.set_text(str(val))
        self._switch_entry()

    def on_entry_palette_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1

        if val < 0:
            val = 0
            widget.set_text(str(val))
        elif val >= len(self.img.palettes):
            val = len(self.img.palettes) - 1
            widget.set_text(str(val))
        self._switch_entry()

    def _switch_entry(self):
        self.image_idx = int(self.builder.get_object('entry_id').get_text())
        self.palette_idx = int(self.builder.get_object('entry_palette').get_text())
        surface = self.img.to_pil(self.image_idx, self.palette_idx)
        stack: Gtk.Stack = self.builder.get_object('entry_stack')
        if surface:
            stack.set_visible_child(self.builder.get_object('entry_viewer'))
            surface = surface.resize((surface.width * IMAGE_ZOOM, surface.height * IMAGE_ZOOM))
            self.surface = pil_to_cairo_surface(surface.convert('RGBA'))
            self.builder.get_object('draw').queue_draw()
        else:
            stack.set_visible_child(self.builder.get_object('no_entry_label'))
            self.surface = pil_to_cairo_surface(Image.new('RGBA', size=(1, 1)))

    def draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
        return True
