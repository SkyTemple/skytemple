"""Sub-controller for the map bg menu."""
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
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, List, Optional, Tuple, Sequence, MutableSequence

from range_typed_integers import u16, u16_checked

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.module.map_bg.chunk_editor_data_provider.tile_graphics_provider import MapBgStaticTileProvider, \
    MapBgAnimatedTileProvider
from skytemple.module.map_bg.chunk_editor_data_provider.tile_palettes_provider import MapBgPaletteProvider
from skytemple_files.common.protocol import TilemapEntryProtocol
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import add_extension_if_missing
from skytemple_files.graphics.bg_list_dat import BPA_EXT, DIR
from skytemple_files.graphics.bpa.protocol import BpaProtocol
from skytemple_files.graphics.bpc.protocol import BpcProtocol
from skytemple_files.graphics.bpl.protocol import BplProtocol, BplAnimationSpecProtocol
from skytemple_files.common.i18n_util import _, f

from PIL import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from natsort import ns, natsorted

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import add_dialog_gif_filter, add_dialog_png_filter, builder_get_assert
from skytemple.module.tiled_img.dialog_controller.chunk_editor import ChunkEditorController
from skytemple.module.map_bg.controller.bg_menu_dialogs.map_width_height import on_map_width_chunks_changed, \
    on_map_height_chunks_changed, on_map_wh_link_state_set
from skytemple.module.tiled_img.dialog_controller.palette_editor import PaletteEditorController

if TYPE_CHECKING:
    from skytemple.module.map_bg.controller.bg import BgController

logger = logging.getLogger(__name__)


class BgMenuController:
    def __init__(self, bg: 'BgController'):
        self.parent = bg

    def on_men_map_settings_activate(self):
        bma = self.parent.bma
        bpc = self.parent.bpc
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        number_layers_adjustment = builder_get_assert(self.parent.builder, Gtk.Adjustment, 'dialog_settings_number_layers_adjustment')
        number_collision_adjustment = builder_get_assert(self.parent.builder, Gtk.Adjustment, 'dialog_settings_number_collision_adjustment')
        has_data_layer = builder_get_assert(self.parent.builder, Gtk.Switch, 'settings_has_data_layer')
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
                builder_get_assert(self.parent.builder, Gtk.Widget, 'map_import_layer2_file').set_sensitive(True)
            elif number_layers <= 1 and bma.number_of_layers > 1:
                # A LAYER WAS REMOVE
                has_a_change = True
                bma.remove_upper_layer()
                bpc.remove_upper_layer()
                self.parent.module.remove_bpa_upper_layer(self.parent.item_id)
                builder_get_assert(self.parent.builder, Gtk.Widget, 'map_import_layer2_file').set_sensitive(False)
            number_col_layers = number_collision_adjustment.get_value()
            if number_col_layers > 0 and bma.number_of_collision_layers <= 0:
                # COLLISION 1 WAS ADDED
                has_a_change = True
                bma.number_of_collision_layers = u16(1)
                bma.collision = [False for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if number_col_layers > 1 and bma.number_of_collision_layers <= 1:
                # COLLISION 2 WAS ADDED
                has_a_change = True
                bma.number_of_collision_layers = u16(2)
                bma.collision2 = [False for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if number_col_layers <= 1 and bma.number_of_collision_layers > 1:
                # COLLISION 2 WAS REMOVED
                has_a_change = True
                bma.number_of_collision_layers = u16(1)
                bma.collision2 = None
            if number_col_layers <= 0 and bma.number_of_collision_layers > 0:
                # COLLISION 1 WAS REMOVED
                has_a_change = True
                bma.number_of_collision_layers = u16(0)
                bma.collision = None
            has_data_layer_now = has_data_layer.get_active()
            if has_data_layer_now and not bma.unk6:
                # DATA LAYER WAS ADDED
                has_a_change = True
                bma.unk6 = u16(1)
                bma.unknown_data_block = [0 for _ in range(0, bma.map_width_camera * bma.map_height_camera)]
            if not has_data_layer_now and bma.unk6:
                # DATA LAYER WAS REMOVED
                has_a_change = True
                bma.unk6 = u16(0)
                bma.unknown_data_block = None
            
            if has_a_change:
                self.parent.reload_all()
                self.parent.mark_as_modified()
        dialog.hide()

    def on_men_map_width_height_activate(self):
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_width_height')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        map_width_chunks  = builder_get_assert(self.parent.builder, Gtk.Entry, 'map_width_chunks')
        map_height_chunks = builder_get_assert(self.parent.builder, Gtk.Entry, 'map_height_chunks')
        map_width_tiles = builder_get_assert(self.parent.builder, Gtk.Entry, 'map_width_tiles')
        map_height_tiles = builder_get_assert(self.parent.builder, Gtk.Entry, 'map_height_tiles')
        map_wh_link  = builder_get_assert(self.parent.builder, Gtk.Switch, 'map_wh_link')
        map_wh_link_target = builder_get_assert(self.parent.builder, Gtk.ListBox, 'map_wh_link_target')
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
                for x in params:
                    if x<=0 or x>=256:
                        raise ValueError("Invalid parameter.")
            except ValueError:
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK, _("Incorrect values.\nOnly enter numbers from 1 to 255 for chunks and tiles dimensions."))
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
        dialog.destroy()

        duration = 1000
        non_none_bpas = [b for b in self.parent.bpas if b is not None]
        if len(non_none_bpas) > 0:
            # Assuming the game runs 60 FPS.
            duration = round(1000 / 60 * non_none_bpas[0].frame_info[0].duration_per_frame)

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            fn = add_extension_if_missing(fn, 'gif')
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
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_map_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            fdialog = Gtk.FileChooserNative.new(
                _("Export PNGs of map..."),
                MainController.window(),
                Gtk.FileChooserAction.SELECT_FOLDER,
                _("_Save"), None
            )

            response = fdialog.run()
            fn = fdialog.get_filename()
            fdialog.destroy()

            if response == Gtk.ResponseType.ACCEPT and fn is not None:
                base_filename = os.path.join(fn, f'{self.parent.module.bgs.level[self.parent.item_id].bma_name}_layer')

                layer1 = self.parent.bma.to_pil_single_layer(self.parent.bpc, self.parent.bpl.palettes, self.parent.bpas, 0)
                layer1.save(base_filename + '1.png')

                if self.parent.bma.number_of_layers > 1:
                    layer2 = self.parent.bma.to_pil_single_layer(self.parent.bpc, self.parent.bpl.palettes, self.parent.bpas, 2)
                    layer2.save(base_filename + '2.png')

    def on_men_map_import_activate(self):
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_map_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        map_import_layer1_file = builder_get_assert(self.parent.builder, Gtk.FileChooserButton, 'map_import_layer1_file')
        map_import_layer2_file = builder_get_assert(self.parent.builder, Gtk.FileChooserButton, 'map_import_layer2_file')
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
                # Make sure to raise an error if the images have less than 256 colors. Otherwise this could cause issues.
                img1: Optional[Image.Image] = None
                img2: Optional[Image.Image] = None
                if img1_path is not None:
                    with open(img1_path, 'rb') as f1:
                        img1 = Image.open(f1)
                        img1.load()
                        if img1.mode == "P":
                            if len(img1.palette.palette) < 768:
                                raise ValueError(_("The image for the first layer has less than 256 colors. Please make sure the image contains 256 colors, even if less are used."))
                if img2_path is not None:
                    with open(img2_path, 'rb') as f2:
                        img2 = Image.open(f2)
                        img2.load()
                        if img2.mode == "P":
                            if len(img2.palette.palette) < 768:
                                raise ValueError(_("The image for the second layer has less than 256 colors. Please make sure the image contains 256 colors, even if less are used."))
                palettes_from_lower_layer = 16  # builder_get_assert(self.parent.builder, XXXXXXXXX, 'dialog_map_import_palette_config').get_value()
                if self.parent.bma.number_of_layers < 2 and img1_path is not None:
                    self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, img1, None, True)
                elif img1_path is not None and img2_path is None:
                    self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, img1, None, True)
                elif img1_path is None and img2_path is not None:
                    self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, None, img2, True)
                elif img1_path is not None and img2_path is not None:
                    self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, img1, img2,
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
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_tiles_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        bpas_frame_info_entries = []
        for i, bpa in enumerate(self.parent.bpas):
            gui_i = i + 1
            enabled = builder_get_assert(self.parent.builder, Gtk.Switch, f'bpa_enable{gui_i}')
            # If there's no second layer: Disable activating the BPA
            # TODO: Currently when removing layers, BPAs are not removed. Is that a problem?
            if self.parent.bma.number_of_layers <= 1 and i > 3:
                enabled.set_sensitive(False)
            enabled.set_active(bpa is not None)
            dialog.resize(470, 450)

            this_frame_info_entries: List[Gtk.Entry] = []
            bpas_frame_info_entries.append(this_frame_info_entries)

            bpa_duration_box = builder_get_assert(self.parent.builder, Gtk.Box, f'bpa_box{gui_i}')
            for child in bpa_duration_box.get_children():
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
                if bpa is None and builder_get_assert(self.parent.builder, Gtk.Switch, f'bpa_enable{gui_i}').get_active():
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
                    self.parent.module.set_level_entry_bpa(self.parent.item_id, i, new_bpa_filename)
                    # Refresh controller state
                    self.parent.bpas = self.parent.module.get_bpas(self.parent.item_id)
                    new_bpa = self.parent.bpas[i]
                    assert new_bpa is not None
                    # Add to BPC
                    self.parent.bpc.process_bpa_change(i, new_bpa.number_of_tiles)
                if bpa is not None and not builder_get_assert(self.parent.builder, Gtk.Switch, f'bpa_enable{gui_i}').get_active():
                    # HAS TO BE DELETED
                    # Delete from BPC
                    self.parent.bpc.process_bpa_change(i, u16(0))
                    # Delete from MapBG list
                    self.parent.module.set_level_entry_bpa(self.parent.item_id, i, None)
                    # Refresh controller state
                    self.parent.bpas = self.parent.module.get_bpas(self.parent.item_id)
                if bpa is not None:
                    new_frame_info = []
                    for entry_i, entry in enumerate(bpa_entries):
                        try:
                            number_of_frames = int(entry.get_text())
                        except ValueError:
                            number_of_frames = 0
                            had_errors = True
                        new_frame_info.append(FileType.BPA.get_frame_info_model_cls()(number_of_frames, 0))
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
        if len([x for x in self.parent.bpas if x is not None]) < 1:
            display_error(
                None,
                f(_("This map has no BPA for animated tiles activated.")),
                _("No animated tiles"),
                should_report=False
            )
            return
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_tiles_animated_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        cb = builder_get_assert(self.parent.builder, Gtk.ComboBox, 'dialog_tiles_animated_export_select_bpa')
        store = Gtk.ListStore(str, int)

        label_sep = builder_get_assert(self.parent.builder, Gtk.Label, 'dialog_tiles_animated_export_label_sep')
        label_sep.set_text(label_sep.get_text().replace('@@@name_pattern@@@', self._get_bpa_export_name_pattern(
            'X', 'Y'
        )))

        for i, bpa in enumerate(self.parent.bpas):
            if bpa is not None:
                store.append([f'BPA{i+1}', i])
        cb.set_model(store)
        if len(cb.get_cells()) < 1:
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
        bpa_select = builder_get_assert(self.parent.builder, Gtk.ComboBox, 'dialog_tiles_animated_export_select_bpa')
        active_iter = bpa_select.get_active_iter()
        assert active_iter is not None
        active_bpa_index = bpa_select.get_model()[active_iter][1]
        active_bpa = self.parent.bpas[active_bpa_index]
        is_single_mode = builder_get_assert(self.parent.builder, Gtk.RadioButton, 'dialog_tiles_animated_export_radio_single').get_active()
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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            # TODO: Support specifying palette
            pal = self.parent.bpl.palettes[0]
            try:
                if is_single_mode:
                    if not fn.endswith('.png'):
                        fn += '.png'
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
        bpa_select = builder_get_assert(self.parent.builder, Gtk.ComboBox, 'dialog_tiles_animated_export_select_bpa')
        active_iter = bpa_select.get_active_iter()
        assert active_iter is not None
        active_bpa_index = bpa_select.get_model()[active_iter][1]
        active_bpa = self.parent.bpas[active_bpa_index]
        is_single_mode = builder_get_assert(self.parent.builder, Gtk.RadioButton, 'dialog_tiles_animated_export_radio_single').get_active()
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

        if response == Gtk.ResponseType.ACCEPT and fn is not None:
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
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_palettes_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        builder_get_assert(self.parent.builder, Gtk.Switch, 'palette_animation_enabled').set_active(self.parent.bpl.has_palette_animation)
        self.on_palette_animation_enabled_state_set(self.parent.bpl.has_palette_animation)
        if self.parent.bpl.has_palette_animation:
            for i, spec in enumerate(self.parent.bpl.animation_specs):
                builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk3_p{i+1}').set_text(str(spec.duration_per_frame))
                builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk4_p{i+1}').set_text(str(spec.number_of_frames))

        response = dialog.run()
        dialog.hide()

        if response == Gtk.ResponseType.OK:
            had_errors = False
            has_palette_animation = False
            new_sepcs: MutableSequence[BplAnimationSpecProtocol] = []
            if builder_get_assert(self.parent.builder, Gtk.Switch, 'palette_animation_enabled').get_active():
                # Has palette animations!
                has_palette_animation = True
                for i in range(1, 17):
                    try:
                        duration_per_frame = int(builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk3_p{i}').get_text())
                    except ValueError:
                        duration_per_frame = 0
                        had_errors = True
                    try:
                        number_of_frames = int(builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk4_p{i}').get_text())
                    except ValueError:
                        number_of_frames = 0
                        had_errors = True
                    try:
                        new_sepcs.append(FileType.BPL.get_animation_spec_model_cls()(
                            u16_checked(duration_per_frame), u16_checked(number_of_frames)
                        ))
                    except OverflowError:
                        had_errors = True

            if has_palette_animation and all(spec.number_of_frames == 0 for spec in new_sepcs):
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK, _('All "number of frames" values were invalid or 0. No values were saved.'))
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

                self.parent.reload_all()
                self.parent.mark_as_modified()
                return
            elif has_palette_animation and all(spec.duration_per_frame == 0 for spec in new_sepcs):
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                            Gtk.ButtonsType.OK, _('All "frame time" values were invalid or 0. No values were saved.'))
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

                self.parent.reload_all()
                self.parent.mark_as_modified()
                return
            elif had_errors:
                self.parent.bpl.has_palette_animation = has_palette_animation
                self.parent.bpl.animation_specs = new_sepcs
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                            Gtk.ButtonsType.OK, _("Some values were invalid (not a number). "
                                                                  "They were replaced with 0."),
                                            title=_("Warning!"))
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

            self.parent.bpl.has_palette_animation = has_palette_animation
            self.parent.bpl.animation_specs = new_sepcs

            if has_palette_animation:
                # Add at least one palette if palette animation was just enabled
                if self.parent.bpl.animation_palette is None or self.parent.bpl.animation_palette == []:
                    self.parent.bpl.animation_palette = [[0, 0, 0] * 15]

            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_palette_animation_enabled_state_set(self, state):
        for i in range(1, 17):
            builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk3_p{i}').set_sensitive(state)
            builder_get_assert(self.parent.builder, Gtk.Entry, f'pallete_anim_setting_unk4_p{i}').set_sensitive(state)

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
            dict_pals[f'F{i + 1}'] = list(pal)

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
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_chunks_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            fdialog = Gtk.FileChooserNative.new(
                _("Export PNG of chunks..."),
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None, None
            )

            add_dialog_png_filter(fdialog)

            response = fdialog.run()
            fn = fdialog.get_filename()
            if fn is not None:
                fn = add_extension_if_missing(fn, 'png')
            fdialog.destroy()

            if response == Gtk.ResponseType.ACCEPT and fn is not None:
                self.parent.bpc.chunks_to_pil(layer, self.parent.bpl.palettes, 20).save(fn)

    def _import_chunks(self, layer):
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_chunks_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        chunks_import_file = builder_get_assert(self.parent.builder, Gtk.FileChooserButton, 'chunks_import_file')
        chunks_import_palettes = builder_get_assert(self.parent.builder, Gtk.Switch, 'chunks_import_palettes')
        chunks_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            try:
                fn = chunks_import_file.get_filename()
                if fn is None:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                                Gtk.ButtonsType.OK, _("An image must be selected."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(fn, 'rb') as f:
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
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_tiles_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            fdialog = Gtk.FileChooserNative.new(
                _("Export PNG of tiles..."),
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                None, None
            )

            add_dialog_png_filter(fdialog)

            response = dialog.run()
            fn = fdialog.get_filename()
            fdialog.destroy()

            if response == Gtk.ResponseType.ACCEPT and fn is not None:
                fn = add_extension_if_missing(fn, 'png')
                self.parent.bpc.tiles_to_pil(layer, self.parent.bpl.palettes, 20).save(fn)

    def _import_tiles(self, layer):
        dialog = builder_get_assert(self.parent.builder, Gtk.Dialog, 'dialog_tiles_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        tiles_import_file = builder_get_assert(self.parent.builder, Gtk.FileChooserButton, 'tiles_import_file')
        tiles_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == ResponseType.OK:
            try:
                fn = tiles_import_file.get_filename()
                if fn is None:
                    md = SkyTempleMessageDialog(MainController.window(),
                                                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                                Gtk.ButtonsType.OK, _("An image must be selected."))
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(fn, 'rb') as f:
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
        self, bpc_layer_to_use, bpc: BpcProtocol, bpl: BplProtocol, bpas: List[Optional[BpaProtocol]]
    ) -> Tuple[
        List[TilemapEntryProtocol], MapBgStaticTileProvider, List[Optional[MapBgAnimatedTileProvider]], MapBgPaletteProvider
    ]:
        palettes = MapBgPaletteProvider(bpl)
        static_tiles = MapBgStaticTileProvider(bpc, bpc_layer_to_use)

        bpa_start = 0 if bpc_layer_to_use == 0 else 4
        bpas = bpas[bpa_start:bpa_start+4]
        animated_tiles: List[Optional[MapBgAnimatedTileProvider]] = []
        for bpa in bpas:
            if bpa is None:
                animated_tiles.append(None)
            else:
                animated_tiles.append(MapBgAnimatedTileProvider(bpa))

        return bpc.layers[bpc_layer_to_use].tilemap, static_tiles, animated_tiles, palettes
