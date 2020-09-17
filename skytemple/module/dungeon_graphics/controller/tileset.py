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

import itertools
import math
import sys
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, List, Iterable, Callable

import cairo

from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_graphics_provider import DungeonTilesProvider
from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_palettes_provider import DungeonPalettesProvider
from skytemple.module.tiled_img.dialog_controller.chunk_editor import ChunkEditorController

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.core.ui_utils import add_dialog_png_filter
from skytemple.module.dungeon_graphics.dungeon_chunk_drawer import DungeonChunkCellDrawer
from skytemple.module.tiled_img.dialog_controller.palette_editor import PaletteEditorController
from skytemple_files.common.util import lcm, chunks
from skytemple_files.graphics.dma.model import Dma, DmaExtraType, DmaType
from skytemple_files.graphics.dpc.model import Dpc, DPC_TILING_DIM
from skytemple_files.graphics.dpci.model import Dpci
from skytemple_files.graphics.dpl.model import Dpl
from skytemple_files.graphics.dpla.model import Dpla

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule


class TilesetController(AbstractController):
    def __init__(self, module: 'DungeonGraphicsModule', item_id: int):
        self.module = module
        self.item_id = item_id

        self.builder = None

        self.dma: Dma = module.get_dma(item_id)
        self.dpl: Dpl = module.get_dpl(item_id)
        self.dpla: Dpla = module.get_dpla(item_id)
        self.dpc: Dpc = module.get_dpc(item_id)
        self.dpci: Dpci = module.get_dpci(item_id)

        self.rules = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0]
        ]
        self.pal_ani_durations = 0

        self.current_icon_view_renderers: List[DungeonChunkCellDrawer] = []

        self.chunks_surfaces: Iterable[Iterable[List[cairo.Surface]]] = []

        self._init_chunk_imgs()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'tileset.glade')
        self._init_rules()
        self._init_rule_icon_views()
        self._init_chunk_picker_icon_view()
        self.builder.connect_signals(self)
        return self.builder.get_object('editor_dungeon_tilesets')

    def on_men_chunks_edit_activate(self, *args):
        all_tilemaps = list(itertools.chain.from_iterable(self.dpc.chunks))
        static_tiles_provider = DungeonTilesProvider(self.dpci)
        palettes_provider = DungeonPalettesProvider(self.dpl, self.dpla)
        cntrl = ChunkEditorController(
            MainController.window(), all_tilemaps,
            static_tiles_provider, palettes_provider,
            self.pal_ani_durations
        )
        edited_mappings = cntrl.show()
        if edited_mappings:
            self.dpc.chunks = list(chunks(edited_mappings, DPC_TILING_DIM * DPC_TILING_DIM))
            self.reload_all()
            self.mark_as_modified()
        del cntrl

    def on_men_chunks_export_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_chunks_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            dialog = Gtk.FileChooserDialog(
                "Export PNG of chunks...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                try:
                    self.dpc.chunks_to_pil(self.dpci, self.dpl.palettes, 16).save(fn)
                except BaseException as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        "Error exporting the tileset."
                    )

    def on_men_chunks_import_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_chunks_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        chunks_import_file: Gtk.FileChooserButton = self.builder.get_object(
            'chunks_import_file'
        )
        chunks_import_palettes: Gtk.Switch = self.builder.get_object(
            'chunks_import_palettes'
        )
        chunks_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.OK:
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
                        tiles, palettes = self.dpc.pil_to_chunks(Image.open(f))
                        self.dpci.tiles = tiles
                        if chunks_import_palettes.get_active():
                            self.dpl.palettes = palettes
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    "Error importing the tileset."
                )
            self.reload_all()
            self.mark_as_modified()

    def on_men_tiles_export_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_tiles_export')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == Gtk.ResponseType.OK:
            dialog = Gtk.FileChooserDialog(
                "Export PNG of tiles...",
                MainController.window(),
                Gtk.FileChooserAction.SAVE,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
            )

            add_dialog_png_filter(dialog)

            response = dialog.run()
            fn = dialog.get_filename()
            if '.' not in fn:
                fn += '.png'
            dialog.destroy()

            if response == Gtk.ResponseType.OK:
                try:
                    self.dpci.tiles_to_pil(self.dpl.palettes, 16).save(fn)
                except BaseException as err:
                    display_error(
                        sys.exc_info(),
                        str(err),
                        "Error exporting the tileset."
                    )

    def on_men_tiles_import_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_tiles_import')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        # Set dialog settings to map settings
        tiles_import_file: Gtk.FileChooserButton = self.builder.get_object(
            'tiles_import_file'
        )
        tiles_import_file.unselect_all()

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.OK:
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
                        self.dpci.pil_to_tiles(Image.open(f))
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    "Error importing the tileset."
                )
            self.reload_all()
            self.mark_as_modified()

    def on_men_palettes_edit_activate(self, *args):
        dict_pals = OrderedDict()
        for i, pal in enumerate(self.dpl.palettes):
            dict_pals[f'{i}'] = pal.copy()

        cntrl = PaletteEditorController(
            MainController.window(), dict_pals
        )
        edited_palettes = cntrl.show()
        if edited_palettes:
            self.dpl.palettes = edited_palettes
            self.reload_all()
            self.mark_as_modified()
        del cntrl

    def on_men_palettes_ani_settings_activate(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_palettes_animated_settings')
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        self.builder.get_object('palette_animation11_enabled').set_active(self.dpla.has_for_palette(0))
        self.builder.get_object('palette_animation12_enabled').set_active(self.dpla.has_for_palette(1))

        self.builder.get_object(f'palette_animation11_frame_time').set_text(str(self.dpla.get_duration_for_palette(0)))
        self.builder.get_object(f'palette_animation12_frame_time').set_text(str(self.dpla.get_duration_for_palette(1)))

        response = dialog.run()
        dialog.hide()

        if response == Gtk.ResponseType.OK:
            had_errors = False
            for palid, enabled, frame_time in ((0, 'palette_animation11_enabled', 'palette_animation11_frame_time'), (1, 'palette_animation12_enabled', 'palette_animation12_frame_time')):
                if self.builder.get_object(enabled).get_active():
                    # Has palette animations!
                    self.dpla.enable_for_palette(palid)
                else:
                    # Doesn't have
                    self.dpla.disable_for_palette(palid)
                try:
                    time = int(self.builder.get_object(frame_time).get_text())
                except:
                    time = 0
                    had_errors = True
                self.dpla.set_duration_for_palette(palid, time)

            if had_errors:
                md = Gtk.MessageDialog(MainController.window(),
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                       Gtk.ButtonsType.OK, "Some values were invalid (not a number). "
                                                           "They were replaced with 0.",
                                       title="Warning!")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

            self.reload_all()
            self.mark_as_modified()

    def on_men_palettes_ani_edit_11_activate(self, *args):
        self._edit_palette_ani(0)

    def on_men_palettes_ani_edit_12_activate(self, *args):
        self._edit_palette_ani(1)

    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(12, 16)

    def on_rules_active_type_changed(self, widget, *area):
        self.update_chunks_from_current_rules()

    def on_rules_a0_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(0, widget.get_active())

    def on_rules_a1_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(1, widget.get_active())

    def on_rules_a2_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(2, widget.get_active())

    def on_rules_a3_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(3, widget.get_active())

    def on_rules_a4_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(4, widget.get_active())

    def on_rules_a5_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(5, widget.get_active())

    def on_rules_a6_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(6, widget.get_active())

    def on_rules_a7_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(7, widget.get_active())

    def on_rules_a8_toggled(self, widget: Gtk.CheckButton, *area):
        self._rules_pos_toggle(8, widget.get_active())

    def on_rules_chunk_picker_selection_changed(self, icon_view: Gtk.IconView):
        pass

    def on_rules_main_1_selection_changed(self, icon_view):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            self._rule_updated(model[treeiter][0], 0)

    def on_rules_main_2_selection_changed(self, icon_view):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            self._rule_updated(model[treeiter][0], 1)

    def on_rules_main_3_selection_changed(self, icon_view):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            self._rule_updated(model[treeiter][0], 2)

    def on_rules_extra_selection_changed(self, icon_view_extra):
        model, treeiter = icon_view_extra.get_model(), icon_view_extra.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            i = model[treeiter][0]
            icon_view_picker = self.builder.get_object('rules_chunk_picker')
            model, treeiter = icon_view_picker.get_model(), icon_view_picker.get_selected_items()
            if model is not None and treeiter is not None and treeiter != []:
                edited_value = model[treeiter][1]
                extra_type = DmaExtraType.FLOOR1
                if i > 15:
                    extra_type = DmaExtraType.WALL_OR_VOID
                if i > 31:
                    extra_type = DmaExtraType.FLOOR2
                self.dma.set_extra(extra_type, i % 16, edited_value)
                self.update_chunks_extra()
                self.mark_as_modified()

    def mark_as_modified(self):
        self.module.mark_as_modified(self.item_id)

    def reload_all(self):
        """Reload all image related things"""
        for renderer in self.current_icon_view_renderers:
            renderer.stop()
        self._init_chunk_imgs()
        for renderer in self.current_icon_view_renderers:
            renderer.reset(self.pal_ani_durations, self.chunks_surfaces)
        self._init_rule_icon_views()
        self._init_chunk_picker_icon_view()

    def _init_chunk_imgs(self):
        """(Re)-draw the chunk images"""
        self.chunks_surfaces = []

        # For each chunk...
        for chunk_idx in range(0, len(self.dpc.chunks)):
            # For each frame of palette animation... ( applicable for this chunk )
            pal_ani_frames = []
            self.chunks_surfaces.append(pal_ani_frames)

            chunk_data = self.dpc.chunks[chunk_idx]
            chunk_image = self.dpc.single_chunk_to_pil(chunk_idx, self.dpci, self.dpl.palettes)
            has_pal_ani = any(chunk.pal_idx >= 10 and self.dpla.has_for_palette(chunk.pal_idx - 10) for chunk in chunk_data)
            if not has_pal_ani:
                len_pal_ani = 1
            else:
                ani_pal_lengths = [self.dpla.get_frame_count_for_palette(x) for x in (0, 1) if self.dpla.has_for_palette(x)]
                if len(ani_pal_lengths) < 2:
                    len_pal_ani = ani_pal_lengths[0]
                else:
                    len_pal_ani = lcm(*ani_pal_lengths)

            for pal_ani in range(0, len_pal_ani):
                # We don't have animated tiles, so ani_frames just has one entry.
                ani_frames = []
                pal_ani_frames.append(ani_frames)
                # Switch out the palette with that from the palette animation
                if has_pal_ani:
                    pal_for_frame = itertools.chain.from_iterable(self.dpla.apply_palette_animations(self.dpl.palettes, pal_ani))
                    chunk_image.putpalette(pal_for_frame)
                ani_frames.append(pil_to_cairo_surface(chunk_image.convert('RGBA')))

        # TODO: No DPLA animations at different speeds supported at the moment
        ani_pal11 = 9999
        ani_pal12 = 9999
        if self.dpla.has_for_palette(0):
            ani_pal11 = self.dpla.get_duration_for_palette(0)
        if self.dpla.has_for_palette(1):
            ani_pal12 = self.dpla.get_duration_for_palette(1)

        self.pal_ani_durations = min(ani_pal11, ani_pal12)

    def _init_rule_icon_views(self):
        """Fill the icon views for the three variations and the extra rules."""
        def init_main_rules_store(store):
            for idx in range(0, 9):
                store.append([idx, 0])

        def init_extra_rules_store(store):
            for extra_type in (DmaExtraType.FLOOR1, DmaExtraType.WALL_OR_VOID, DmaExtraType.FLOOR2):
                for idx, val in enumerate(self.dma.get_extra(extra_type)):
                    store.append([idx + 16 * extra_type.value, val])

        for i, v_icon_view_name in enumerate(("rules_main_1", "rules_main_2", "rules_main_3")):
            self._init_an_icon_view(v_icon_view_name, init_main_rules_store, False)

        self._init_an_icon_view("rules_extra", init_extra_rules_store, False)

        self.update_chunks_from_current_rules()

    def _init_chunk_picker_icon_view(self):
        """Fill the icon view for the chunk picker"""
        def init_store(store):
            for idx in range(0, len(self.dpc.chunks)):
                store.append([idx, idx])

        self._init_an_icon_view("rules_chunk_picker", init_store, True)

    def _init_an_icon_view(self, name: str, init_store: Callable[[Gtk.ListStore], None], selection_draw_solid):
        icon_view: Gtk.IconView = self.builder.get_object(name)
        if icon_view.get_model() == None:
            #                     id, val
            store = Gtk.ListStore(int, int)
            icon_view.set_model(store)
            renderer = DungeonChunkCellDrawer(icon_view, self.pal_ani_durations, self.chunks_surfaces, selection_draw_solid)
            self.current_icon_view_renderers.append(renderer)
            icon_view.pack_start(renderer, True)
            icon_view.add_attribute(renderer, 'chunkidx', 1)
        else:
            store = icon_view.get_model()
            store.clear()
            renderer = None
            for child in icon_view.get_cells():
                if isinstance(child, DungeonChunkCellDrawer):
                    renderer = child
                    break

        init_store(store)

        icon_view.select_path(store.get_path(store.get_iter_first()))
        if renderer is not None:
            renderer.start()

    def _edit_palette_ani(self, ani_pal_id):
        if not self.dpla.has_for_palette(ani_pal_id):
            md = Gtk.MessageDialog(MainController.window(),
                                   Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                                   Gtk.ButtonsType.OK, "Palette Animation is not enabled for this palette.",
                                   title="Warning!")
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()
            return
        # This is controlled by a separate controller
        dict_pals = OrderedDict()

        list_of_colors = self.dpla.colors[ani_pal_id*16:(ani_pal_id+1)*16]
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

            self.dpla.colors[ani_pal_id*16:(ani_pal_id+1)*16] = edited_colors
            self.reload_all()
            self.mark_as_modified()
        del cntrl

    def _rules_pos_toggle(self, i, state):
        y = i % 3
        x = math.floor(i / 3)
        self.rules[x][y] = state
        self.update_chunks_from_current_rules()

    def _init_rules(self):
        def ia(i):
            return self.builder.get_object(f'rules_a{i}').get_active()
        self.rules = list(chunks([ia(i) for i in range(0, 9)], 3))

    def update_chunks_from_current_rules(self):
        solid_type = self._get_current_solid_type()
        all_chunk_mapping_vars = []
        for y, row in enumerate(self.rules):
            for x, solid in enumerate(row):
                chunk_type = solid_type if solid else DmaType.FLOOR
                solid_neighbors = Dma.get_tile_neighbors(self.rules, x, y, bool(solid))
                all_chunk_mapping_vars.append(self.dma.get(chunk_type, solid_neighbors))

        for i, v_icon_view_name in enumerate(("rules_main_1", "rules_main_2", "rules_main_3")):
            icon_view_model: Gtk.ListStore = self.builder.get_object(v_icon_view_name).get_model()
            icon_view_model.clear()
            for j, idxs in enumerate(all_chunk_mapping_vars):
                icon_view_model.append([j, idxs[i]])

    def update_chunks_extra(self):
        store = self.builder.get_object('rules_extra').get_model()
        store.clear()
        for extra_type in (DmaExtraType.FLOOR1, DmaExtraType.WALL_OR_VOID, DmaExtraType.FLOOR2):
            for idx, val in enumerate(self.dma.get_extra(extra_type)):
                store.append([idx + 16 * extra_type.value, val])

    def _get_current_solid_type(self):
        combo_box: Gtk.ComboBoxText = self.builder.get_object("rules_active_type")
        return DmaType.WALL if combo_box.get_active_text() == 'Wall' else DmaType.WATER

    def _rule_updated(self, i, variation):
        icon_view = self.builder.get_object('rules_chunk_picker')
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:

            x = i % 3
            y = math.floor(i / 3)
            edited_value = model[treeiter][1]
            solid = bool(self.rules[x][y])
            self.dma.set(
                self._get_current_solid_type() if solid else DmaType.FLOOR,
                Dma.get_tile_neighbors(self.rules, x, y, solid),
                variation, edited_value
            )
            self.update_chunks_from_current_rules()
            self.mark_as_modified()
