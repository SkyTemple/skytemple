"""Sub-controller for the map bg menu."""
import os
from functools import partial
from typing import TYPE_CHECKING

from PIL import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.ui_utils import add_dialog_gif_filter, add_dialog_png_filter
from skytemple.module.map_bg.controller.bg_menu_dialogs.chunk_editor import ChunkEditorController
from skytemple.module.map_bg.controller.bg_menu_dialogs.map_width_height import on_map_width_chunks_changed, \
    on_map_height_chunks_changed, on_map_wh_link_state_set

if TYPE_CHECKING:
    from skytemple.module.map_bg.controller.bg import BgController


class BgMenuController:
    def __init__(self, bg: 'BgController'):
        self.parent = bg

    def on_men_map_settings_activate(self):
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
        number_layers_adjustment.set_value(self.parent.bma.number_of_layers)
        number_collision_adjustment.set_value(self.parent.bma.number_of_collision_layers)
        has_data_layer.set_active(self.parent.bma.unk6 > 0)

        resp = dialog.run()
        # TODO - don't forget to update BPC also
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
        # TODO - don't forget to update BPC also
        dialog.hide()

    def on_men_map_export_gif_activate(self):
        dialog = Gtk.FileChooserDialog(
            "Save GIF of map...",
            MainController.window(),
            Gtk.FileChooserAction.SAVE,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        )

        add_dialog_gif_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        duration = 1000
        non_none_bpas = [b for b in self.parent.bpas if b is not None]
        if len(non_none_bpas) > 0:
            # Assuming the game runs 60 FPS.
            duration = round(1000 / 60 * non_none_bpas[0].frame_info[0].unk1)

        if response == Gtk.ResponseType.OK:
            frames = self.parent.bma.to_pil(self.parent.bpc, self.parent.bpl.palettes, self.parent.bpas, False, False)
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
            dialog = Gtk.FileChooserDialog(
                "Export PNGs of map...",
                MainController.window(),
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            response = dialog.run()
            fn = dialog.get_filename()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
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
                            self.parent.bma.from_pil(self.parent.bpc, self.parent.bpl, Image.open(f1), Image.open(f2), True)
            except Exception as err:
                # TODO Better exception display
                md = Gtk.MessageDialog(MainController.window(),
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK, str(err),
                                       title="SkyTemple - Error!")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_chunks_layer1_edit_activate(self):
        # This is controlled by a separate controller
        bpc_layer_to_use = 0 if self.parent.bma.number_of_layers < 2 else 1
        cntrl = ChunkEditorController(
            MainController.window(), bpc_layer_to_use, self.parent.bpc, self.parent.bpl,
            self.parent.bpas, self.parent.bpa_durations
        )
        edited_mappings = cntrl.show()
        if edited_mappings:
            self.parent.bpc.layers[bpc_layer_to_use].tilemap = edited_mappings
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def on_men_chunks_layer2_edit_activate(self):
        # This is controlled by a separate controller
        if self.parent.bma.number_of_layers < 2:
            self._no_second_layer()
        else:
            bpc_layer_to_use = 0
            cntrl = ChunkEditorController(
                MainController.window(), bpc_layer_to_use, self.parent.bpc, self.parent.bpl,
                self.parent.bpas, self.parent.bpa_durations
            )
            edited_mappings = cntrl.show()
            if edited_mappings:
                self.parent.bpc.layers[bpc_layer_to_use].tilemap = edited_mappings
                self.parent.reload_all()
                self.parent.mark_as_modified()

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

    def _export_chunks(self, layer):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_chunks_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            dialog = Gtk.FileChooserDialog(
                "Export PNG of chunks...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
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
                    md = Gtk.MessageDialog(MainController.window(),
                                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "An image must be selected.",
                                           title="Error!")
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(chunks_import_file.get_filename(), 'rb') as f:
                        palettes = self.parent.bpc.pil_to_chunks(layer, Image.open(f))
                        if chunks_import_palettes.get_active():
                            self.parent.bpl.palettes = palettes
            except Exception as err:
                # TODO Better exception display
                md = Gtk.MessageDialog(MainController.window(),
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK, str(err),
                                       title="SkyTemple - Error!")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
            self.parent.reload_all()
            self.parent.mark_as_modified()

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

    def _export_tiles(self, layer):
        dialog: Gtk.Dialog = self.parent.builder.get_object('dialog_tiles_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            dialog = Gtk.FileChooserDialog(
                "Export PNG of tiles...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
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
                    md = Gtk.MessageDialog(MainController.window(),
                                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                           Gtk.ButtonsType.OK, "An image must be selected.",
                                           title="Error!")
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                else:
                    with open(tiles_import_file.get_filename(), 'rb') as f:
                        self.parent.bpc.pil_to_tiles(layer, Image.open(f))
            except Exception as err:
                # TODO Better exception display
                md = Gtk.MessageDialog(MainController.window(),
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.OK, str(err),
                                       title="SkyTemple - Error!")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
            self.parent.reload_all()
            self.parent.mark_as_modified()

    def _no_second_layer(self):
        md = Gtk.MessageDialog(MainController.window(),
                               Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                               Gtk.ButtonsType.OK, "This map has no second layer.",
                               title="Error!")
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()