"""Sub-controller for the map bg menu."""
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
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, List, Optional, Tuple

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.module.map_bg.chunk_editor_data_provider.tile_graphics_provider import MapBgStaticTileProvider, \
    MapBgAnimatedTileProvider
from skytemple.module.map_bg.chunk_editor_data_provider.tile_palettes_provider import MapBgPaletteProvider
from skytemple_files.common.tiled_image import TilemapEntry
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat.model import BPA_EXT, DIR
from skytemple_files.graphics.bpa.model import BpaFrameInfo, Bpa
from skytemple_files.graphics.bpc.model import Bpc
from skytemple_files.common.i18n_util import _

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from natsort import ns, natsorted

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import add_dialog_gif_filter, add_dialog_png_filter
from skytemple.module.tiled_img.dialog_controller.chunk_editor import ChunkEditorController
from skytemple.module.map_bg.controller.bg_menu_dialogs.map_width_height import on_map_width_chunks_changed, \
    on_map_height_chunks_changed, on_map_wh_link_state_set
from skytemple.module.tiled_img.dialog_controller.palette_editor import PaletteEditorController
from skytemple_files.graphics.bpl.model import BplAnimationSpec, Bpl

if TYPE_CHECKING:
    from skytemple.module.map_bg.controller.bg import BgController

logger = logging.getLogger(__name__)


class BgMenuController:
    def __init__(self, bg: 'BgController'):
        self.parent = bg

    def on_men_map_settings_activate(self):
        bma = self.parent.bma
        bpc = self.parent.bpc
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        number_layers_adjustment: Gtk.Adjustment = self.parent.builder.get_object(
            'dialog_settings_number_layers_adjustment'
        )
        number_collision_adjustment: Gtk.Adjustment = self.parent.builder.get_object(
            'dialog_settings_number_collision_adjustment'
        )
        has_data_layer: Gtk.Switch = self.parent.builder.get_object(
            'settings_has_data_layer'
        )
        number_layers_adjustment.set_value(bma.number_of_layers)
        number_collision_adjustment.set_value(bma.number_of_collision_layers)
        has_data_layer.set_active(bma.unk6 > 0)

        resp = dialog.run()
        if resp == ResponseType.OK:
            has_a_change = False
            number_layers = number_layers_adjustment.get_value()
            if number_layers > 1 and bma.number_of_layers <= 1:
                # A LAYER WAS ADDED
                has_a_change = True
                bma.add_upper_layer()
                bpc.add_upper_layer()
            elif number_layers <= 1 and bma.number_of_layers > 1:
                # A LAYER WAS REMOVE
                has_a_change = True
                bma.remove_upper_layer()
                bpc.remove_upper_layer()
                self.parent.module.remove_bpa_upper_layer(self.parent.item_id)
            number_col_layers = number_collision_adjustment.get_value()
            if number_col_layers > 1 and bma.number_of_collision_layers <= 0:
                # COLLISION 1 WAS ADDED
                has_a_change = True
                bma.number_of_collision_layers = 1
                bma.collision = [False for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if number_col_layers > 1 and bma.number_of_collision_layers <= 1:
                # COLLISION 2 WAS ADDED
                has_a_change = True
                bma.number_of_collision_layers = 2
                bma.collision2 = [False for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if number_col_layers <= 1 and bma.number_of_collision_layers > 1:
                # COLLISION 2 WAS REMOVED
                has_a_change = True
                bma.number_of_collision_layers = 1
                bma.collision2 = None
            if number_col_layers <= 0 and bma.number_of_collision_layers > 0:
                # COLLISION 1 WAS REMOVED
                has_a_change = True
                bma.number_of_collision_layers = 0
                bma.collision = None
            has_data_layer_now = has_data_layer.get_active()
            if has_data_layer_now and not bma.unk6:
                # DATA LAYER WAS ADDED
                has_a_change = True
                bma.unk6 = True
                bma.unknown_data_block = [0 for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if not has_data_layer_now and bma.unk6:
                # DATA LAYER WAS REMOVED
                has_a_change = True
                bma.unk6 = False
                bma.unknown_data_block = None
            
            if has_a_change:
                self.parent.reload_all()
                self.parent.mark_as_modified()
        dialog.hide()

    def on_men_map_width_height_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_width_height')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        map_width_chunks: Gtk.Entry = self.parent.builder.get_object(
            'map_width_chunks'
        )
        map_height_chunks: Gtk.Entry = self.parent.builder.get_object(
            'map_height_chunks'
        )
        map_width_tiles: Gtk.Entry = self.parent.builder.get_object(
            'map_width_tiles'
        )
        map_height_tiles: Gtk.Entry = self.parent.builder.get_object(
            'map_height_tiles'
        )
        map_wh_link: Gtk.Switch = self.parent.builder.get_object(
            'map_wh_link'
        )
        map_wh_link_target: Gtk.Switch = self.parent.builder.get_object(
            'map_wh_link_target'
        )
        map_width_chunks.set_text(str(self.parent.bma.map_width_chunks))
        map_height_chunks.set_text(str(self.parent.bma.map_height_chunks))
        map_width_tiles.set_text(str(self.parent.bma.map_width_camera))
        map_height_tiles.set_text(str(self.parent.bma.map_height_camera))
        if self.parent.bma.map_width_camera == self.parent.bma.map_width_chunks * self.parent.bma.tiling_width and \
                self.parent.bma.map_height_camera == self.parent.bma.map_height_chunks * self.parent.bma.tiling_height:
            map_wh_link.set_active(True)
            map_wh_link_target.set_sensitive(False)
        else:
            map_wh_link.set_active(False)
            map_wh_link_target.set_sensitive(True)

        map_width_chunks.connect('changed', partial(on_map_width_chunks_changed, self.parent.builder))
        map_height_chunks.connect('changed', partial(on_map_height_chunks_changed,  self.parent.builder))
        map_wh_link.connect('state-set', partial(on_map_wh_link_state_set,  self.parent.builder))

        resp = dialog.run()
        if resp == ResponseType.OK:
            try:
                params = (
                    int(map_width_chunks.get_text()), int(map_height_chunks.get_text()),
                    int(map_width_tiles.get_text()), int(map_height_tiles.get_text()),
                )
            except ValueError:
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK, _("Please only enter numbers for the map size."))
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
            else:
                self.parent.bma.resize(*params)
                self.parent.reload_all()
                self.parent.mark_as_modified()
        dialog.hide()

    def on_men_map_export_gif_activate(self):
        dialog = Gtk.FileChooserNative.new(
            _("Save GIF of map..."),
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            None, None
        )

        add_dialog_gif_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        if '.' not in fn:
            fn += '.gif'
        dialog.destroy()

        duration = 1000
        non_none_bpas = [b for b in self.parent.bpas if b is not None]
        if len(non_none_bpas) > 0:
            # Assuming the game runs 60 FPS.
            duration = round(1000 / 60 * non_none_bpas[0].frame_info[0].duration_per_frame)

        if response == Gtk.ResponseType.ACCEPT:
            frames = self.parent.bma.to_pil(self.parent.bpc, self.parent.bpl, self.parent.bpas, False, False)
            frames[0].save(
                fn,
                save_all=True,
                append_images=frames[1:],
                duration=duration,
                loop=0,
                optimize=False
            )

    def on_men_map_export_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_map_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            dialog = Gtk.FileChooserNative.new(
                _("Export PNGs of map..."),
                MainController.window(),
                Gtk.FileChooserAction.SELECT_FOLDER,
                _("_Save"), None
            )

            response = dialog.run()
            fn = dialog.get_filename()
            dialog.destroy()

            if response == Gtk.ResponseType.ACCEPT:
                base_filename = os.path.join(fn, f'{self.parent.module.bgs.level[self.parent.item_id].bma_name}_layer')

                layer1 = self.parent.bma.to_pil_single_layer(self.parent.bpc, self.parent.bpl.palettes, self.parent.bpas, 0)
                layer1.save(base_filename + '1.png')

                if self.parent.bma.number_of_layers > 1:
                    layer2 = self.parent.bma.to_pil_single_layer(self.parent.bpc, self.parent.bpl.palettes, self.parent.bpas, 2)
                    layer2.save(base_filename + '2.png')

    def on_men_map_import_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_map_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        map_import_layer1_file: Gtk.FileChooserButton = self.parent.builder.get_object(
            'map_import_layer1_file'
        )
        map_import_layer2_file: Gtk.FileChooserButton = self.parent.builder.get_object(
            'map_import_layer2_file'
        )
        map_import_layer1_file.unselect_all()
        map_import_layer2_file.unselect_all()
        if self.parent.bma.number_of_layers < 2:
            map_import_layer2_file.set_sensitive(False)

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            try:
                img1_path = map_import_layer1_file.get_filename()
                img2_path = map_import_layer2_file.get_filename()
                palettes_from_lower_layer = 16  # self.parent.builder.get_object('dialog_map_import_palette_config').get_value()
                if self.parent.bma.number_of_layers < 2 and img1_path is not None:
                    with open(img1_path, 'rb') as f:
                        self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, Image.open(f), None, True)
                elif img1_path is not None and img2_path is None:
                    with open(img1_path, 'rb') as f1:
                        self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, Image.open(f1), None, True)
                elif img1_path is None and img2_path is not None:
                    with open(img2_path, 'rb') as f2:
                        self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, None, Image.open(f2), True)
                elif img1_path is not None and img2_path is not None:
                    with open(img1_path, 'rb') as f1:
                        with open(img2_path, 'rb') as f2:
                            self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, Image.open(f1), Image.open(f2),
                                                     True, how_many_palettes_lower_layer=int(palettes_from_lower_layer))
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err)
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_chunks_layer1_edit_activate(self):
        # This is controlled by a separate controller
        bpc_layer_to_use = 0 if self.parent.bma.number_of_layers < 2 else 1
        mappings, static_tiles_provider, animated_tiles_providers, palettes_provider = self._get_chunk_editor_provider(
            bpc_layer_to_use, self.parent.bpc, self.parent.bpl, self.parent.bpas
        )
        cntrl = ChunkEditorController(
            MainController.window(), mappings, static_tiles_provider, palettes_provider, self.parent.pal_ani_durations,
            animated_tiles_providers, self.parent.bpa_durations
        )
        edited_mappings = cntrl.show()
        if edited_mappings:
            # TODO: Hardcoded chunk size
            new_chunk_size = int(len(edited_mappings) / 9)
            if new_chunk_size > self.parent.bpc.layers[bpc_layer_to_use].chunk_tilemap_len:
                self.parent.bpc.layers[bpc_layer_to_use].chunk_tilemap_len = new_chunk_size
            self.parent.bpc.layers[bpc_layer_to_use].tilemap = edited_mappings.copy()
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl

    def on_men_chunks_layer2_edit_activate(self):
        # This is controlled by a separate controller
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            bpc_layer_to_use = 0
            mappings, static_tiles_provider, animated_tiles_providers, palettes_provider = self._get_chunk_editor_provider(
                bpc_layer_to_use, self.parent.bpc, self.parent.bpl, self.parent.bpas
            )
            cntrl = ChunkEditorController(
                MainController.window(), mappings, static_tiles_provider, palettes_provider, self.parent.pal_ani_durations,
                animated_tiles_providers, self.parent.bpa_durations
            )
            edited_mappings = cntrl.show()

            if edited_mappings:
                # TODO: Hardcoded chunk size
                new_chunk_size = int(len(edited_mappings) / 9)
                if new_chunk_size > self.parent.bpc.layers[bpc_layer_to_use].chunk_tilemap_len:
                    self.parent.bpc.layers[bpc_layer_to_use].chunk_tilemap_len = new_chunk_size
                self.parent.bpc.layers[bpc_layer_to_use].tilemap = edited_mappings
                self.parent.reload_all()
                self.parent.mark_as_modified()
            del cntrl

    def on_men_chunks_layer1_export_activate(self):
        self._export_chunks(0 if self.parent.bma.number_of_layers < 2 else 1)

    def on_men_chunks_layer1_import_activate(self):
        self._import_chunks(0 if self.parent.bma.number_of_layers < 2 else 1)

    def on_men_chunks_layer2_export_activate(self):
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            self._export_chunks(0)

    def on_men_chunks_layer2_import_activate(self):
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            self._import_chunks(0)

    def on_men_tiles_layer1_export_activate(self):
        self._export_tiles(0 if self.parent.bma.number_of_layers < 2 else 1)

    def on_men_tiles_layer1_import_activate(self):
        self._import_tiles(0 if self.parent.bma.number_of_layers < 2 else 1)

    def on_men_tiles_layer2_export_activate(self):
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            self._export_tiles(0)

    def on_men_tiles_layer2_import_activate(self):
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            self._import_tiles(0)

    def on_men_tiles_ani_settings_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        bpas_frame_info_entries = []
        for i, bpa in enumerate(self.parent.bpas):
            gui_i = i + 1
            enabled = self.parent.builder.get_object(f'bpa_enable{gui_i}')
            # If there's no second layer: Disable activating the BPA
            # TODO: Currently when removing layers, BPAs are not removed. Is that a problem?
            if self.parent.bma.number_of_layers <= 1 and i > 3:
                enabled.set_sensitive(False)
            enabled.set_active(bpa is not None)
            dialog.resize(470, 450)

            this_frame_info_entries = []
            bpas_frame_info_entries.append(this_frame_info_entries)

            bpa_duration_box: Gtk.Box = self.parent.builder.get_object(f'bpa_box{gui_i}')
            for child in bpa_duration_box:
                bpa_duration_box.remove(child)
            if bpa is None or len(bpa.frame_info) < 1:
                l = Gtk.Label.new(_("This BPA has no frames.\n"
                                    "Enable the BPA and import images for a BPA to add frames."))
                l.show()
                bpa_duration_box.add(l)
            else:
                # Fill value for existing BPAs
                for frame_info in bpa.frame_info:
                    entry: Gtk.Entry = Gtk.Entry.new()
                    entry.set_input_purpose(Gtk.InputPurpose.NUMBER)
                    entry.set_width_chars(4)
                    entry.set_max_length(4)
                    entry.set_text(str(frame_info.duration_per_frame))
                    entry.set_halign(Gtk.Align.START)
                    entry.show()
                    this_frame_info_entries.append(entry)
                    bpa_duration_box.pack_start(entry, False, True, 5)

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            had_errors = False
            for i, (bpa, bpa_entries) in enumerate(zip(self.parent.bpas, bpas_frame_info_entries)):
                gui_i = i + 1
                if bpa is None and self.parent.builder.get_object(f'bpa_enable{gui_i}').get_active():
                    # HAS TO BE ADDED
                    map_bg_entry = self.parent.module.get_level_entry(self.parent.item_id)
                    # Add file
                    new_bpa_filename = f"{map_bg_entry.bpl_name}{gui_i}"
                    new_bpa_filename_with_ext = new_bpa_filename.lower() + BPA_EXT
                    try:
                        self.parent.module.project.create_new_file(f"{DIR}/{new_bpa_filename_with_ext}",
                                                                   FileType.BPA.new(), FileType.BPA)
                    except FileExistsError:
                        # Hm, okay, then we just re-use this file.
                        pass
                    # Add to MapBG list
                    map_bg_entry.bpa_names[i] = new_bpa_filename
                    # Refresh controller state
                    self.parent.bpas = self.parent.module.get_bpas(self.parent.item_id)
                    new_bpa = self.parent.bpas[i]
                    # Add to BPC
                    self.parent.bpc.process_bpa_change(i, new_bpa.number_of_tiles)
                    self.parent.module.mark_level_list_as_modified()
                if bpa is not None and not self.parent.builder.get_object(f'bpa_enable{gui_i}').get_active():
                    # HAS TO BE DELETED
                    map_bg_entry = self.parent.module.get_level_entry(self.parent.item_id)
                    # Delete from BPC
                    self.parent.bpc.process_bpa_change(i, 0)
                    # Delete from MapBG list
                    map_bg_entry.bpa_names[i] = None
                    # Refresh controller state
                    self.parent.bpas = self.parent.module.get_bpas(self.parent.item_id)
                    self.parent.module.mark_level_list_as_modified()
                if bpa is not None:
                    new_frame_info = []
                    for entry_i, entry in enumerate(bpa_entries):
                        try:
                            number_of_frames = int(entry.get_text())
                        except ValueError:
                            number_of_frames = 0
                            had_errors = True
                        new_frame_info.append(BpaFrameInfo(number_of_frames, 0))
                    bpa.frame_info = new_frame_info

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

    def on_men_tiles_ani_export_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_animated_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        cb: Gtk.ComboBox = self.parent.builder.get_object('dialog_tiles_animated_export_select_bpa')
        store = Gtk.ListStore(str, int)

        label_sep: Gtk.Label = self.parent.builder.get_object('dialog_tiles_animated_export_label_sep')
        label_sep.set_text(label_sep.get_text().replace('@@@name_pattern@@@', self._get_bpa_export_name_pattern(
            'X', 'Y'
        )))

        for i, bpa in enumerate(self.parent.bpas):
            if bpa is not None:
                store.append([f'BPA{i+1}', i])
        cb.set_model(store)
        cell = Gtk.CellRendererText()
        cb.pack_start(cell, True)
        cb.add_attribute(cell, 'text', 0)
        cb.set_active(0)

        dialog.run()
        # The dialog has two buttons with separate connected signals (
        #   on_dialog_tiles_animated_export_export_btn_activate, on_dialog_tiles_animated_export_import_btn_activate
        # )
        dialog.hide()

    def on_dialog_tiles_animated_export_export_btn_clicked(self):
        bpa_select = self.parent.builder.get_object('dialog_tiles_animated_export_select_bpa')
        active_bpa_index = bpa_select.get_model()[bpa_select.get_active_iter()][1]
        active_bpa = self.parent.bpas[active_bpa_index]
        is_single_mode = self.parent.builder.get_object('dialog_tiles_animated_export_radio_single').get_active()
        file_chooser_mode = Gtk.FileChooserAction.SAVE if is_single_mode else Gtk.FileChooserAction.SELECT_FOLDER
        dialog = Gtk.FileChooserNative.new(
            _("Export animated tiles (BPA)"),
            MainController.window(),
            file_chooser_mode,
            None, None
        )

        if is_single_mode:
            add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            # TODO: Support specifying palette
            pal = self.parent.bpl.palettes[0]
            try:
                if is_single_mode:
                    active_bpa.tiles_to_pil(pal).save(fn)
                else:
                    for i, img in enumerate(active_bpa.tiles_to_pil_separate(pal, 20)):
                        img.save(os.path.join(fn, self._get_bpa_export_name_pattern(active_bpa_index+1, i)))
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                            Gtk.ButtonsType.OK, _("The animated tiles were successfully exported."),
                                            title=_("SkyTemple - Success!"), is_success=True)
                md.run()
                md.destroy()
            except Exception as err:
                logger.error(_("Error during BPA export"), exc_info=err)
                display_error(
                    sys.exc_info(),
                    str(err)
                )

    def on_dialog_tiles_animated_export_import_btn_clicked(self):
        bpa_select = self.parent.builder.get_object('dialog_tiles_animated_export_select_bpa')
        active_bpa_index = bpa_select.get_model()[bpa_select.get_active_iter()][1]
        active_bpa = self.parent.bpas[active_bpa_index]
        is_single_mode = self.parent.builder.get_object('dialog_tiles_animated_export_radio_single').get_active()
        file_chooser_mode = Gtk.FileChooserAction.OPEN if is_single_mode else Gtk.FileChooserAction.SELECT_FOLDER
        dialog = Gtk.FileChooserNative.new(
            _("Import animated tiles (BPA)"),
            MainController.window(),
            file_chooser_mode,
            None, None
        )

        if is_single_mode:
            add_dialog_png_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                if is_single_mode:
                    filenames_base = [os.path.basename(fn)]
                    with open(fn, 'rb') as f:
                        active_bpa.pil_to_tiles(Image.open(f))
                        self.parent.bpc.process_bpa_change(active_bpa_index, active_bpa.number_of_tiles)
                else:
                    r = re.compile(
                        f"{self.parent.module.bgs.level[self.parent.item_id].bma_name}_bpa{active_bpa_index+1}_\d+\.png",
                        re.IGNORECASE
                    )
                    filenames_base = natsorted(filter(r.match, os.listdir(fn)), alg=ns.IGNORECASE)
                    img_handles = [open(os.path.join(fn, base_name), 'rb') for base_name in filenames_base]
                    try:
                        images = [Image.open(h) for h in img_handles]
                        active_bpa.pil_to_tiles_separate(images)
                        self.parent.bpc.process_bpa_change(active_bpa_index, active_bpa.number_of_tiles)
                    finally:
                        for handle in img_handles:
                            handle.close()
                # Don't forget to update the BPC!
                bpa_relative_idx = active_bpa_index % 4
                bpc_layer_for_bpa = 0 if active_bpa_index < 4 else 1
                self.parent.bpc.layers[bpc_layer_for_bpa].bpas[bpa_relative_idx] = active_bpa.number_of_tiles
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                            Gtk.ButtonsType.OK, _("The animated tiles were successfully imported, using the files: ")
                                                                + ', '.join(filenames_base) + ".",
                                            title=_("SkyTemple - Success!"), is_success=True)
                md.run()
                md.destroy()
            except Exception as err:
                logger.error(_("Error during BPA import"), exc_info=err)
                display_error(
                    sys.exc_info(),
                    str(err)
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_palettes_edit_activate(self):
        # This is controlled by a separate controller
        dict_pals = OrderedDict()
        for i, pal in enumerate(self.parent.bpl.get_real_palettes()):
            dict_pals[f'{i}'] = pal.copy()

        cntrl = PaletteEditorController(
            MainController.window(), dict_pals
        )
        edited_palettes = cntrl.show()
        if edited_palettes:
            self.parent.bpl.set_palettes(edited_palettes)
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl

    def on_men_palettes_ani_settings_activate(self):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_palettes_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        self.parent.builder.get_object('palette_animation_enabled').set_active(self.parent.bpl.has_palette_animation)
        self.on_palette_animation_enabled_state_set(self.parent.bpl.has_palette_animation)
        if self.parent.bpl.has_palette_animation:
            for i, spec in enumerate(self.parent.bpl.animation_specs):
                self.parent.builder.get_object(f'pallete_anim_setting_unk3_p{i+1}').set_text(str(spec.duration_per_frame))
                self.parent.builder.get_object(f'pallete_anim_setting_unk4_p{i+1}').set_text(str(spec.number_of_frames))

        response = dialog.run()
        dialog.hide()

        if response == Gtk.ResponseType.OK:
            had_errors = False
            if self.parent.builder.get_object('palette_animation_enabled').get_active():
                # Has palette animations!
                self.parent.bpl.has_palette_animation = True
                self.parent.bpl.animation_specs = []
                for i in range(1, 17):
                    try:
                        duration_per_frame = int(self.parent.builder.get_object(f'pallete_anim_setting_unk3_p{i}').get_text())
                    except ValueError:
                        duration_per_frame = 0
                        had_errors = True
                    try:
                        number_of_frames = int(self.parent.builder.get_object(f'pallete_anim_setting_unk4_p{i}').get_text())
                    except ValueError:
                        number_of_frames = 0
                        had_errors = True
                    self.parent.bpl.animation_specs.append(BplAnimationSpec(
                        duration_per_frame=duration_per_frame,
                        number_of_frames=number_of_frames
                    ))
                # Add at least one palette if palette animation was just enabled
                if self.parent.bpl.animation_palette is None or self.parent.bpl.animation_palette == []:
                    self.parent.bpl.animation_palette = [[0, 0, 0] * 15]
            else:
                # Doesn't have
                self.parent.bpl.has_palette_animation = False
                self.parent.bpl.animation_specs = None

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

    def on_palette_animation_enabled_state_set(self, state):
        for i in range(1, 17):
            self.parent.builder.get_object(f'pallete_anim_setting_unk3_p{i}').set_sensitive(state)
            self.parent.builder.get_object(f'pallete_anim_setting_unk4_p{i}').set_sensitive(state)

    def on_men_palettes_ani_edit_activate(self):
        if not self.parent.bpl.has_palette_animation:
            md = SkyTempleMessageDialog(MainController.window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                        Gtk.ButtonsType.OK, _("Palette Animation is not enabled."),
                                        title=_("Warning!"))
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
            return
        # This is controlled by a separate controller
        dict_pals = OrderedDict()

        for i, pal in enumerate(self.parent.bpl.animation_palette):
            dict_pals[f'F{i + 1}'] = pal.copy()

        cntrl = PaletteEditorController(
            MainController.window(), dict_pals, False, True, False
        )
        edited_palettes = cntrl.show()
        if edited_palettes:
            self.parent.bpl.animation_palette = edited_palettes
            self.parent.reload_all()
            self.parent.mark_as_modified()
        del cntrl

    def _export_chunks(self, layer):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_chunks_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
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
                self.parent.bpc.chunks_to_pil(layer, self.parent.bpl.palettes, 20).save(fn)

    def _import_chunks(self, layer):
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

        if resp == ResponseType.OK:
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
                        palettes = self.parent.bpc.pil_to_chunks(layer, Image.open(f))
                        if chunks_import_palettes.get_active():
                            self.parent.bpl.palettes = palettes
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err)
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def _export_tiles(self, layer):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
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
                self.parent.bpc.tiles_to_pil(layer, self.parent.bpl.palettes, 20).save(fn)

    def _import_tiles(self, layer):
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

        if resp == ResponseType.OK:
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
                        self.parent.bpc.pil_to_tiles(layer, Image.open(f))
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err)
                )
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def _no_second_layer(self):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                    Gtk.ButtonsType.OK, _("This map has no second layer."))
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def _get_bpa_export_name_pattern(self, bpa_number, frame_number):
        return f'{self.parent.module.bgs.level[self.parent.item_id].bma_name}_bpa{bpa_number}_{frame_number}.png'

    def _get_chunk_editor_provider(
        self, bpc_layer_to_use, bpc: Bpc, bpl: Bpl, bpas: List[Optional[Bpa]]
    ) -> Tuple[
        List[TilemapEntry], MapBgStaticTileProvider, List[Optional[MapBgAnimatedTileProvider]], MapBgPaletteProvider
    ]:
        palettes = MapBgPaletteProvider(bpl)
        static_tiles = MapBgStaticTileProvider(bpc, bpc_layer_to_use)

        bpa_start = 0 if bpc_layer_to_use == 0 else 4
        bpas = bpas[bpa_start:bpa_start+4]
        animated_tiles = []
        for bpa in bpas:
            if bpa is None:
                animated_tiles.append(None)
            else:
                animated_tiles.append(MapBgAnimatedTileProvider(bpa))

        return bpc.layers[bpc_layer_to_use].tilemap, static_tiles, animated_tiles, palettes
