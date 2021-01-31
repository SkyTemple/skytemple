"""Sub-controller for the dungeon bg menu."""
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
import itertools
import logging
import sys
from collections import OrderedDict
from typing import TYPE_CHECKING, Union

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_graphics_provider import DungeonTilesProvider
from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_palettes_provider import DungeonPalettesProvider
from skytemple_files.common.util import chunks
from skytemple_files.graphics.dpc.model import DPC_TILING_DIM
from skytemple_files.common.i18n_util import f, _

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple.module.tiled_img.dialog_controller.chunk_editor import ChunkEditorController
from skytemple.module.tiled_img.dialog_controller.palette_editor import PaletteEditorController

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.controller.dungeon_bg import DungeonBgController
    from skytemple.module.dungeon_graphics.controller.tileset import TilesetController

logger = logging.getLogger(__name__)


class BgMenuController:
    def __init__(self, bg: Union['TilesetController', 'DungeonBgController']):
        self.parent = bg

    def on_men_map_export_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_map_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            dialog = Gtk.FileChooserNative.new(
                _("Export PNG of map..."),
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None, None
            )

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.ACCEPT:
                img = self.parent.dbg.to_pil(self.parent.dpc, self.parent.dpci, self.parent.dpl.palettes)
                img.save(fn)

    def on_men_map_import_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_map_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        bg_import_file: Gtk.FileChooserButton = self.parent.builder.get_object(
            'map_import_layer1_file'
        )
        bg_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            try:
                img_path = bg_import_file.get_filename()
                self.parent.dbg.from_pil(self.parent.dpc, self.parent.dpci, self.parent.dpl, Image.open(img_path), True)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err)
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_chunks_layer1_edit_activate(self):
        all_tilemaps = list(itertools.chain.from_iterable(self.parent.dpc.chunks))
        static_tiles_provider = DungeonTilesProvider(self.parent.dpci)
        palettes_provider = DungeonPalettesProvider(self.parent.dpl, self.parent.dpla)
        cntrl = ChunkEditorController(
            MainController.window(), all_tilemaps,
            static_tiles_provider, palettes_provider,
            self.parent.pal_ani_durations
        )
        edited_mappings = cntrl.show()
        if edited_mappings:
            self.parent.dpc.chunks = list(chunks(edited_mappings, DPC_TILING_DIM * DPC_TILING_DIM))
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl

    def on_men_chunks_layer1_export_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_chunks_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            dialog = Gtk.FileChooserNative.new(
                _("Export PNG of chunks..."),
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None, None
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.ACCEPT:
                try:
                    self.parent.dpc.chunks_to_pil(self.parent.dpci, self.parent.dpl.palettes, 16).save(fn)
                except BaseException as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        _("Error exporting the tileset.")
                    )

    def on_men_chunks_layer1_import_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_chunks_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        chunks_import_file: Gtk.FileChooserButton = self.parent.builder.get_object(
            'chunks_import_file'
        )
        chunks_import_palettes: Gtk.Switch = self.parent.builder.get_object(
            'chunks_import_palettes'
        )
        chunks_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.OK:
            try:
                if chunks_import_file.get_filename() is None:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                                Gtk.ButtonsType.OK, _("An image must be selected."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(chunks_import_file.get_filename(), 'rb') as f:
                        tiles, palettes = self.parent.dpc.pil_to_chunks(Image.open(f))
                        self.parent.dpci.tiles = tiles
                        if chunks_import_palettes.get_active():
                            self.parent.dpl.palettes = palettes
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing the tileset.")
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_tiles_layer1_export_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            dialog = Gtk.FileChooserNative.new(
                _("Export PNG of tiles..."),
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None, None
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.ACCEPT:
                try:
                    self.parent.dpci.tiles_to_pil(self.parent.dpl.palettes, 16).save(fn)
                except BaseException as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        _("Error exporting the tileset.")
                    )

    def on_men_tiles_layer1_import_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        tiles_import_file: Gtk.FileChooserButton = self.parent.builder.get_object(
            'tiles_import_file'
        )
        tiles_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.OK:
            try:
                if tiles_import_file.get_filename() is None:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                                Gtk.ButtonsType.OK, _("An image must be selected."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(tiles_import_file.get_filename(), 'rb') as f:
                        self.parent.dpci.pil_to_tiles(Image.open(f))
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing the tileset.")
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_palettes_edit_activate(self):
        dict_pals = OrderedDict()
        for i, pal in enumerate(self.parent.dpl.palettes):
            dict_pals[f'{i}'] = pal.copy()

        cntrl = PaletteEditorController(
            MainController.window(), dict_pals
        )
        edited_palettes = cntrl.show()
        if edited_palettes:
            self.parent.dpl.palettes = edited_palettes
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl

    def on_men_palettes_ani_settings_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_palettes_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        self.parent.builder.get_object('palette_animation11_enabled').set_active(self.parent.dpla.has_for_palette(0))
        self.parent.builder.get_object('palette_animation12_enabled').set_active(self.parent.dpla.has_for_palette(1))

        for aidx, offset in (11, 0), (12, 16):
            for cidx in range(0, 16):
                self.parent.builder.get_object(f'palette_animation{aidx}_frame_time{cidx}').set_text(
                    str(self.parent.dpla.durations_per_frame_for_colors[offset + cidx])
                )

        response = dialog.run()
        dialog.hide()

        if response == Gtk.ResponseType.OK:
            had_errors = False
            for palid, aidx, offset in ((0, 11, 0), (1, 12, 16)):
                if self.parent.builder.get_object(f'palette_animation{aidx}_enabled').get_active():
                    # Has palette animations!
                    self.parent.dpla.enable_for_palette(palid)
                else:
                    # Doesn't have
                    self.parent.dpla.disable_for_palette(palid)
                for cidx in range(0, 16):
                    try:
                        time = int(self.parent.builder.get_object(f'palette_animation{aidx}_frame_time{cidx}').get_text())
                    except:
                        time = 0
                        had_errors = True
                    self.parent.dpla.durations_per_frame_for_colors[offset + cidx] = time

            if had_errors:
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                            Gtk.ButtonsType.OK, _("Some values were invalid (not a number). "
                                                                  "They were replaced with 0."),
                                            title=_("Warning!"))
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

            self.parent.reload_all()
            self.parent.mark_as_modified()

    def edit_palette_ani(self, ani_pal_id):
        if not self.parent.dpla.has_for_palette(ani_pal_id):
            md = SkyTempleMessageDialog(MainController.window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, _("Palette Animation is not enabled for this palette."),
                                        title=_("Warning!"))
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
            return
        # This is controlled by a separate controller
        dict_pals = OrderedDict()

        list_of_colors = self.parent.dpla.colors[ani_pal_id*16:(ani_pal_id+1)*16]
        # We need to transpose the list to instead have a list of frames.
        list_of_frames = list([] for _ in range(0, int(len(list_of_colors[0]) / 3)))
        for color in list_of_colors:
            for frame_idx, c in enumerate(chunks(color, 3)):
                list_of_frames[frame_idx] += c
        for i, pal in enumerate(list_of_frames):
            dict_pals[f'F{i + 1}'] = pal.copy()

        cntrl = PaletteEditorController(
            MainController.window(), dict_pals, False, True, False
        )
        edited_palettes = cntrl.show()
        if edited_palettes:
            # Transpose back
            edited_colors = list([] for _ in range(0, int(len(edited_palettes[0]) / 3)))
            for palette in edited_palettes:
                for color_idx, c in enumerate(chunks(palette, 3)):
                    edited_colors[color_idx] += c

            self.parent.dpla.colors[ani_pal_id*16:(ani_pal_id+1)*16] = edited_colors
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl
