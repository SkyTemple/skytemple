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
from typing import TYPE_CHECKING

import gi
from gi.repository import Gtk, Gdk
from gi.repository.GObject import TYPE_PYOBJECT
from gi.repository.GdkPixbuf import Pixbuf, Colorspace
from gi.repository.Gtk import *

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_SCENE
from skytemple.module.map_bg.controller.bg_menu import BgMenuController
from skytemple.module.map_bg.drawer import Drawer, DrawerCellRenderer, DrawerInteraction
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat.model import BMA_EXT, BPC_EXT, BPL_EXT, BPA_EXT, DIR
from skytemple_files.graphics.bma.model import MASK_PAL
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.graphics.bpl.model import BPL_NORMAL_MAX_PAL
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.map_bg.module import MapBgModule


INFO_IMEXPORT_TILES = _("""- The image consists of 8x8 tiles.
- The image is a 256-color indexed PNG.
- The 256 colors are divided into 16 16 color palettes.
- Each 8x8 tile in the image MUST only use colors from
  one of these 16 palettes.
- The first color in each palette is transparency.
- The exported palettes are only for your convenience.
  They are based on the first time the tile is used in a 
  chunk mapping (Chunks > Edit Chunks).
- Each import must result in a maximum of 1024 unique 8x8 tiles 
  (=not existing with another palette or flipped or rotated).

Animated tiles are not imported.""")

INFO_IMEXPORT_CHUNK = _("""- The image consists of 8x8 tiles.
- The image is a 256-color indexed PNG.
- The 256 colors are divided into 16 16 color palettes.
- Each 8x8 tile in the image MUST only use colors from
  one of these 16 palettes.
- The first color in each palette is transparency.
- Animated tiles are NOT exported or imported. In the export they
  are replaced with blank tiles. On import the mappings to 
  animated tiles will be lost, so make sure you note them down 
  to manually re-assign  them on import. To change animated tiles, 
  go to Tiles > Animated Tiles.
- Each import must result in a maximum of 1024 unique 8x8 tiles 
  (=not existing with another palette or flipped or rotated).

Some image editors have problems when working with indexed
images, that contain the same color multiple times. You can
make all colors on the map unique before exporting at
Palettes > Edit Palettes. Alternatively use the converter.

Please note, that chunks can not use colors from 
the last two palettes. They should not be used by any tile.

Colors that are in the wrong palette are replaced wth
transparency.

Static tiles, chunks and palettes are replaced on import. 
Animated tiles and palette animation settings are not changed.
""")

INFO_IMEXPORT_ENTIRE = _("""- The image is a 256-color indexed PNG.
- The 256 colors are divided into 16 16 color palettes.
- Each 8x8 tile in the image MUST only use colors from
  one of these 16 palettes.
- The first color in each palette is transparency.
- Animated tiles are exported as static tiles.
- Each import must result in a maximum of 1024 unique 8x8 tiles 
  (=not existing with another palette or flipped or rotated).

Some image editors have problems when working with indexed
images, that contain the same color multiple times. You can
make all colors on the map unique before exporting at
Palettes > Edit Palettes.

Colors that are in the wrong palette are replaced wth
transparency.

Static tiles are replaced on import.
Animated tiles and palette animation settings are not changed.

Since no animated tiles are imported, they need
to be (re-)assigned to chunks after the import.""")


class BgController(AbstractController):
    def __init__(self, module: 'MapBgModule', item_id: int):
        self.module = module
        self.item_id = item_id

        self.builder = None
        self.notebook: Notebook = None

        self.bma = module.get_bma(item_id)
        self.bpl = module.get_bpl(item_id)
        self.bpc = module.get_bpc(item_id)
        self.bpas = module.get_bpas(item_id)

        # Cairo surfaces for each tile in each layer for each frame
        # chunks_surfaces[layer_number][chunk_idx][palette_animation_frame][frame]
        self.chunks_surfaces = []
        self.bpa_durations = 0

        self.drawer: Drawer = None
        self.current_icon_view_renderer: DrawerCellRenderer = None

        self.bg_draw: DrawingArea = None
        self.bg_draw_event_box: EventBox = None

        self.scale_factor = 1
        self.current_chunks_icon_layer = 0

        self.bg_draw_is_clicked = False

        self._init_chunk_imgs()

        self.menu_controller = BgMenuController(self)

        # SkyTemple can not correctly edit MapBG files which are shared between multiple MapBGs.
        # We have to copy them!
        self._was_asset_copied = False
        self._perform_asset_copy()
        if self._was_asset_copied:
            # Force reload of the models, if we had to copy.
            self.bma = module.get_bma(item_id)
            self.bpl = module.get_bpl(item_id)
            self.bpc = module.get_bpc(item_id)
            self.bpas = module.get_bpas(item_id)

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'map_bg.glade')
        self.set_warning_palette()
        self.notebook = self.builder.get_object('bg_notebook')
        self._init_drawer()
        self._init_tab(self.notebook.get_nth_page(self.notebook.get_current_page()))
        self._refresh_metadata()
        self._init_rest_room_note()
        self.builder.connect_signals(self)
        try:
            # Invalidate SSA scene cache for this BG
            # TODO: This is obviously very ugly coupling...
            from skytemple.module.script.controller.ssa import SsaController
            SsaController.map_bg_surface_cache = (None, )
        except ImportError:
            pass
        if self._was_asset_copied:
                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                            Gtk.ButtonsType.OK, _("This map background shared some asset files with "
                                                                  "other map backgrounds.\n"
                                                                  "SkyTemple can't edit shared files, so "
                                                                  "those assets were copied."),
                                            title=_("SkyTemple - Notice"))
                md.run()
                md.destroy()
                self.module.mark_as_modified(self.item_id)
                self.module.mark_level_list_as_modified()
        return self.builder.get_object('editor_map_bg')

    def on_bg_notebook_switch_page(self, notebook, page, *args):
        self._init_tab(page)

    def on_bg_draw_click(self, box, button: Gdk.EventButton):
        correct_mouse_x = int(button.x / self.scale_factor)
        correct_mouse_y = int(button.y / self.scale_factor)
        if button.button == 1:
            self.bg_draw_is_clicked = True
            if self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                snap_x = correct_mouse_x - correct_mouse_x % (self.bma.tiling_width * BPC_TILE_DIM)
                snap_y = correct_mouse_y - correct_mouse_y % (self.bma.tiling_height * BPC_TILE_DIM)
                self._set_chunk_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.COL:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
                self._set_col_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.DAT:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
                self._set_data_at_pos(snap_x, snap_y)

    def on_bg_draw_release(self, box, button: Gdk.EventButton):
        if button.button == 1:
            self.bg_draw_is_clicked = False

    def on_bg_draw_mouse_move(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int(motion.x / self.scale_factor)
        correct_mouse_y = int(motion.y / self.scale_factor)
        if self.drawer:
            if self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                snap_x = correct_mouse_x - correct_mouse_x % (self.bma.tiling_width * BPC_TILE_DIM)
                snap_y = correct_mouse_y - correct_mouse_y % (self.bma.tiling_height * BPC_TILE_DIM)
                self.drawer.set_mouse_position(snap_x, snap_y)
                if self.bg_draw_is_clicked:
                    self._set_chunk_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.COL:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
                self.drawer.set_mouse_position(snap_x, snap_y)
                if self.bg_draw_is_clicked:
                    self._set_col_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.DAT:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
                self.drawer.set_mouse_position(snap_x, snap_y)
                if self.bg_draw_is_clicked:
                    self._set_data_at_pos(snap_x, snap_y)

    def _set_chunk_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            chunk_x = int(mouse_x / (self.bma.tiling_width * BPC_TILE_DIM))
            chunk_y = int(mouse_y / (self.bma.tiling_height * BPC_TILE_DIM))
            if 0 <= chunk_x < self.bma.map_width_chunks and 0 <= chunk_y < self.bma.map_height_chunks:
                chunk_mapping_idx = int(chunk_y * self.bma.map_width_chunks + chunk_x)
                # Set chunk at current position
                self.mark_as_modified()
                if self.current_chunks_icon_layer == 0:
                    self.bma.layer0[chunk_mapping_idx] = self.drawer.get_selected_chunk_id()
                elif self.current_chunks_icon_layer == 1:
                    self.bma.layer1[chunk_mapping_idx] = self.drawer.get_selected_chunk_id()

    def _set_col_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            if 0 <= tile_x < self.bma.map_width_camera and 0 <= tile_y < self.bma.map_height_camera:
                tile_idx = int(tile_y * self.bma.map_width_camera + tile_x)
                # Set collision at current position
                self.mark_as_modified()
                if self.drawer.get_edited_collision() == 0:
                    self.bma.collision[tile_idx] = self.drawer.get_interaction_col_solid()
                elif self.drawer.get_edited_collision() == 1:
                    self.bma.collision2[tile_idx] = self.drawer.get_interaction_col_solid()

    def _set_data_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            if 0 <= tile_x < self.bma.map_width_camera and 0 <= tile_y < self.bma.map_height_camera:
                tile_idx = int(tile_y * self.bma.map_width_camera + tile_x)
                # Set data value at current position
                self.mark_as_modified()
                self.bma.unknown_data_block[tile_idx] = self.drawer.get_interaction_dat_value()

    def on_current_icon_view_selection_changed(self, icon_view: IconView):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            chunk_id = model[treeiter][0]
            if self.drawer:
                self.drawer.set_selected_chunk(chunk_id)

    def on_collison_switch_state_set(self, wdg, state):
        if self.drawer:
            self.drawer.set_interaction_col_solid(state)

    def on_data_combo_box_changed(self, cb: ComboBox):
        if self.drawer:
            self.drawer.set_interaction_dat_value(cb.get_active())

    def on_tb_zoom_out_clicked(self, w):
        self.scale_factor /= 2
        self._update_scales()

    def on_tb_zoom_in_clicked(self, w):
        self.scale_factor *= 2
        self._update_scales()

    def on_tb_hide_other_toggled(self, w):
        if self.drawer:
            self.drawer.set_show_only_edited_layer(w.get_active())

    def on_tb_chunk_grid_toggled(self, w):
        if self.drawer:
            self.drawer.set_draw_chunk_grid(w.get_active())

    def on_tb_tile_grid_toggled(self, w):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())

    def on_tb_bg_color_toggled(self, w):
        if self.drawer:
            self.drawer.set_pink_bg(w.get_active())
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_pink_bg(w.get_active())

    def on_tb_goto_scene_clicked(self, w):
        try:
            associated = self.module.get_associated_script_map(self.item_id)
            if associated is None:
                raise ValueError()
            self.module.project.request_open(OpenRequest(
                REQUEST_TYPE_SCENE, associated.name
            ), True)
        except ValueError:
            md = SkyTempleMessageDialog(MainController.window(),
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                        Gtk.ButtonsType.OK, _("A script map with the same name as "
                                                              "this background does not exist."),
                                        title=_("No Scenes Found"))
            md.run()
            md.destroy()

    def on_men_map_settings_activate(self, *args):
        self.menu_controller.on_men_map_settings_activate()

    def on_men_map_width_height_activate(self, *args):
        self.menu_controller.on_men_map_width_height_activate()

    def on_men_map_export_gif_activate(self, *args):
        self.menu_controller.on_men_map_export_gif_activate()

    def on_men_map_export_activate(self, *args):
        self.menu_controller.on_men_map_export_activate()

    def on_men_map_import_activate(self, *args):
        self.menu_controller.on_men_map_import_activate()

    def on_men_chunks_layer1_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_export_activate()

    def on_men_chunks_layer1_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_import_activate()

    def on_men_chunks_layer2_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_export_activate()

    def on_men_chunks_layer2_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_import_activate()

    def on_men_chunks_layer1_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_edit_activate()

    def on_men_chunks_layer2_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_edit_activate()

    def on_men_tiles_layer1_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_export_activate()

    def on_men_tiles_layer1_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_import_activate()

    def on_men_tiles_layer2_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer2_export_activate()

    def on_men_tiles_layer2_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer2_import_activate()

    def on_men_tiles_ani_settings_activate(self, *args):
        self.menu_controller.on_men_tiles_ani_settings_activate()

    def on_men_tiles_ani_export_activate(self, *args):
        self.menu_controller.on_men_tiles_ani_export_activate()

    def on_dialog_tiles_animated_export_export_btn_clicked(self, *args):
        self.menu_controller.on_dialog_tiles_animated_export_export_btn_clicked()

    def on_dialog_tiles_animated_export_import_btn_clicked(self, *args):
        self.menu_controller.on_dialog_tiles_animated_export_import_btn_clicked()

    def on_men_palettes_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_edit_activate()

    def on_men_palettes_ani_settings_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_settings_activate()

    def on_palette_animation_enabled_state_set(self, wdg, state, *args):
        self.menu_controller.on_palette_animation_enabled_state_set(state)

    def on_men_palettes_ani_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_edit_activate()

    def on_format_details_entire_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, INFO_IMEXPORT_ENTIRE)
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def on_format_details_chunks_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, INFO_IMEXPORT_CHUNK)
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def on_format_details_tiles_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, INFO_IMEXPORT_TILES)
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    def on_converter_tool_clicked(self, *args):
        MainController.show_tilequant_dialog(14, 16)

    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(14, 16)

    def set_warning_palette(self):
        if self.builder:
            self.builder.get_object('editor_warning_palette').set_revealed(self.weird_palette)
        
    def _init_chunk_imgs(self):
        """(Re)-draw the chunk images"""

        # Set the weird palette warning to false
        self.weird_palette = False
        
        if self.bpc.number_of_layers > 1:
            layer_idxs_bpc = [1, 0]
        else:
            layer_idxs_bpc = [0]

        self.chunks_surfaces = []

        # For each layer...
        for layer_idx, layer_idx_bpc in enumerate(layer_idxs_bpc):
            chunks_current_layer = []
            self.chunks_surfaces.append(chunks_current_layer)
            # For each chunk...
            for chunk_idx in range(0, self.bpc.layers[layer_idx_bpc].chunk_tilemap_len):
                # For each frame of palette animation... ( applicable for this chunk )
                pal_ani_frames = []
                chunks_current_layer.append(pal_ani_frames)

                chunk_data = self.bpc.get_chunk(layer_idx_bpc, chunk_idx)
                chunk_images = self.bpc.single_chunk_animated_to_pil(layer_idx_bpc, chunk_idx, self.bpl.palettes, self.bpas)
                if not self.weird_palette:
                    for x in chunk_images:
                        for n in x.tobytes("raw", "P"):
                            n//=16
                            if n>=self.bpl.number_palettes or n>=BPL_NORMAL_MAX_PAL:
                                # If one chunk uses weird palette values, display the warning
                                self.weird_palette = True
                                break
                        if self.weird_palette:break 
                has_pal_ani = any(self.bpl.is_palette_affected_by_animation(chunk.pal_idx) for chunk in chunk_data)
                len_pal_ani = len(self.bpl.animation_palette) if has_pal_ani else 1

                for pal_ani in range(0, len_pal_ani):
                    # For each frame of tile animation...
                    bpa_ani_frames = []
                    pal_ani_frames.append(bpa_ani_frames)
                    for img in chunk_images:
                        # Switch out the palette with that from the palette animation
                        if has_pal_ani:
                            pal_for_frame = itertools.chain.from_iterable(self.bpl.apply_palette_animations(pal_ani))
                            img.putpalette(pal_for_frame)
                        # Remove alpha first
                        img_mask = img.copy()
                        img_mask.putpalette(MASK_PAL)
                        img_mask = img_mask.convert('1')
                        img = img.convert('RGBA')
                        img.putalpha(img_mask)
                        bpa_ani_frames.append(pil_to_cairo_surface(img))

            # TODO: No BPAs at different speeds supported at the moment
            self.bpa_durations = 0
            for bpa in self.bpas:
                if bpa is not None:
                    single_bpa_duration = max(info.duration_per_frame for info in bpa.frame_info) if len(bpa.frame_info) > 0 else 9999
                    if single_bpa_duration > self.bpa_durations:
                        self.bpa_durations = single_bpa_duration

            # TODO: No BPL animations at different speeds supported at the moment
            self.pal_ani_durations = 0
            if self.bpl.has_palette_animation:
                self.pal_ani_durations = max(spec.duration_per_frame for spec in self.bpl.animation_specs)
        self.set_warning_palette()
    def _init_drawer(self):
        """(Re)-initialize the main drawing area"""
        bg_draw_sw: ScrolledWindow = self.builder.get_object('bg_draw_sw')
        for child in bg_draw_sw.get_children():
            bg_draw_sw.remove(child)
        if self.bg_draw_event_box:
            for child in self.bg_draw_event_box.get_children():
                self.bg_draw_event_box.remove(child)
            self.bg_draw_event_box.destroy()

        if self.bg_draw:
            self.bg_draw.destroy()

        self.bg_draw_event_box = Gtk.EventBox()
        self.bg_draw_event_box.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.bg_draw_event_box.connect("button-press-event", self.on_bg_draw_click)
        self.bg_draw_event_box.connect("button-release-event", self.on_bg_draw_release)
        self.bg_draw_event_box.connect("motion-notify-event", self.on_bg_draw_mouse_move)

        self.bg_draw: DrawingArea = Gtk.DrawingArea.new()
        self.bg_draw_event_box.add(self.bg_draw)

        bg_draw_sw.add(self.bg_draw_event_box)

        self.bg_draw.set_size_request(
            self.bma.map_width_chunks * self.bma.tiling_width * BPC_TILE_DIM,
            self.bma.map_height_chunks * self.bma.tiling_height * BPC_TILE_DIM
        )

        self.drawer = Drawer(self.bg_draw, self.bma, self.bpa_durations, self.pal_ani_durations, self.chunks_surfaces)
        self.drawer.start()

    def _init_drawer_layer_selected(self):
        self.drawer.set_edited_layer(self.current_chunks_icon_layer)

        # Set drawer state based on some buttons
        self.drawer.set_show_only_edited_layer(self.builder.get_object(f'tb_hide_other').get_active())
        self.drawer.set_draw_chunk_grid(self.builder.get_object(f'tb_chunk_grid').get_active())
        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tb_tile_grid').get_active())
        self.drawer.set_pink_bg(self.builder.get_object(f'tb_bg_color').get_active())

    def _init_drawer_collision_selected(self, collision_id):
        self.drawer.set_edited_collision(collision_id)
        self.drawer.set_interaction_col_solid(self.builder.get_object('collison_switch').get_active())

        # Set drawer state based on some buttons
        self.drawer.set_draw_chunk_grid(self.builder.get_object(f'tb_chunk_grid').get_active())
        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tb_tile_grid').get_active())
        self.drawer.set_pink_bg(self.builder.get_object(f'tb_bg_color').get_active())

    def _init_drawer_data_layer_selected(self):
        self.drawer.set_edit_data_layer()
        cb: ComboBox = self.builder.get_object('data_combo_box')
        self.drawer.set_interaction_dat_value(cb.get_active())

        # Set drawer state based on some buttons
        self.drawer.set_draw_chunk_grid(self.builder.get_object(f'tb_chunk_grid').get_active())
        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tb_tile_grid').get_active())

    def _init_chunks_icon_view(self, layer_number: int):
        """Fill the icon view for the specified layer"""
        self._deinit_chunks_icon_view()

        self.current_chunks_icon_layer = layer_number

        icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.current_icon_view_renderer = DrawerCellRenderer(icon_view, layer_number,
                                                             self.bpa_durations, self.pal_ani_durations,
                                                             self.chunks_surfaces)
        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(self.current_icon_view_renderer, True)
        icon_view.add_attribute(self.current_icon_view_renderer, 'chunkidx', 0)
        icon_view.connect('selection-changed', self.on_current_icon_view_selection_changed)

        for idx in range(0, len(self.chunks_surfaces[layer_number])):
            store.append([idx])

        icon_view.select_path(store.get_path(store.get_iter_first()))
        self.current_icon_view_renderer.start()

        self.current_icon_view_renderer.set_pink_bg(self.builder.get_object(f'tb_bg_color').get_active())

    def _deinit_chunks_icon_view(self):
        """Remove the icon view for the specified layer"""
        icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
        icon_view.clear()
        icon_view.set_model(None)

    def _init_data_layer_combobox(self):
        cb: ComboBox = self.builder.get_object(f'data_combo_box')
        if cb.get_model() is None:
            store = Gtk.ListStore(str, int)
            for i in range(0, 256):
                if i == 0:
                    store.append([_('None'), i])
                else:
                    store.append([f'0x{i:02x}', i])
            cb.set_model(store)
            cell = Gtk.CellRendererText()
            cb.pack_start(cell, True)
            cb.add_attribute(cell, 'text', 0)
            cb.set_active(0)

    def mark_as_modified(self):
        self.module.mark_as_modified(self.item_id)

    def _init_tab(self, notebook_page: Box):
        layers_box = self.builder.get_object('bg_layers')

        toolbox_box = self.builder.get_object('bg_layers_toolbox')
        toolbox_box_child_layers = self.builder.get_object('bg_layers_toolbox_layers')
        toolbox_box_child_collision = self.builder.get_object('bg_layers_toolbox_collision')
        toolbox_box_child_data = self.builder.get_object('bg_layers_toolbox_data')

        if Gtk.Buildable.get_name(notebook_page) != 'metadata':
            for child in notebook_page.get_children():
                    notebook_page.remove(child)
            for child in toolbox_box.get_children():
                toolbox_box.remove(child)

        page_name = Gtk.Buildable.get_name(notebook_page)
        if page_name == 'bg_layer2' and self.bma.number_of_layers < 2:
            # Layer 2: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                _('This map only has one layer.\n'
                  'You can add a second layer at Map > Settings.')
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name in ['bg_layer1', 'bg_layer2']:
            # Layer 1 / 2
            if layers_box.get_parent():
                layers_box.get_parent().remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)

            if toolbox_box_child_layers.get_parent():
                toolbox_box_child_layers.get_parent().remove(toolbox_box_child_layers)
            toolbox_box.pack_start(toolbox_box_child_layers, True, True, 0)

            self._init_chunks_icon_view(0 if page_name == 'bg_layer1' else 1)
            self._init_drawer_layer_selected()
        elif page_name == 'bg_col1' and self.bma.number_of_collision_layers < 1:
            # Collision 1: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                _('This map has no collision.\n'
                  'You can add collision at Map > Settings.')
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name == 'bg_col2' and self.bma.number_of_collision_layers < 2:
            # Collision 2: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                _('This map has no second collision layer.\n'
                  'You can add a second collision layer at Map > Settings.')
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name in ['bg_col1', 'bg_col2']:
            # Collision 1 / 2
            if layers_box.get_parent():
                layers_box.get_parent().remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)

            if toolbox_box_child_collision.get_parent():
                toolbox_box_child_collision.get_parent().remove(toolbox_box_child_collision)
            toolbox_box.pack_start(toolbox_box_child_collision, True, True, 0)

            self._init_drawer_collision_selected(0 if page_name == 'bg_col1' else 1)
        elif page_name == 'bg_data' and self.bma.unk6 < 1:
            # Data Layer: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                _('This map has no data layer.\n'
                  'You can add a data layer at Map > Settings.')
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name == 'bg_data':
            # Data Layer
            if layers_box.get_parent():
                layers_box.get_parent().remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)

            if toolbox_box_child_data.get_parent():
                toolbox_box_child_data.get_parent().remove(toolbox_box_child_data)
            toolbox_box.pack_start(toolbox_box_child_data, True, True, 0)

            self._init_data_layer_combobox()
            self._init_drawer_data_layer_selected()
        else:
            # Metadata
            # Nothing to do, tab is already finished.
            pass

        self._update_scales()

    def _refresh_metadata(self):
        level_entry = self.module.get_level_entry(self.item_id)
        self.builder.get_object('filename_bma').set_text(level_entry.bma_name + BMA_EXT)
        self.builder.get_object('filename_bpc').set_text(level_entry.bpc_name + BPC_EXT)
        self.builder.get_object('filename_bpl').set_text(level_entry.bpl_name + BPL_EXT)
        for i in range(0, 8):
            if level_entry.bpa_names[i] is not None:
                self.builder.get_object(f'filename_bpa{i + 1}').set_text(level_entry.bpa_names[i] + BPA_EXT)
            else:
                self.builder.get_object(f'filename_bpa{i + 1}').set_text("n/a")

    def _update_scales(self):
        """Update drawers+DrawingArea and iconview+Renderer scales"""
        self.bg_draw.set_size_request(
            self.bma.map_width_chunks * self.bma.tiling_width * BPC_TILE_DIM * self.scale_factor,
            self.bma.map_height_chunks * self.bma.tiling_height * BPC_TILE_DIM * self.scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self.scale_factor)

        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_scale(self.scale_factor)
            # update size
            self.current_icon_view_renderer.set_fixed_size(
                int(BPC_TILE_DIM * 3 * self.scale_factor), int(BPC_TILE_DIM * 3 * self.scale_factor)
            )

            icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
            icon_view.queue_resize()

    def reload_all(self):
        """Reload all image related things"""
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.stop()
        self.bpas = self.module.get_bpas(self.item_id)
        self._init_chunk_imgs()
        self.drawer.reset(self.bma, self.bpa_durations, self.pal_ani_durations, self.chunks_surfaces)
        self._init_tab(self.notebook.get_nth_page(self.notebook.get_current_page()))
        self._refresh_metadata()

    def _init_rest_room_note(self):
        """If the data layer of this map contains 0x08, this is probably a rest room"""
        info_bar = self.builder.get_object('editor_rest_room_note')
        if self.bma.unknown_data_block is None or not any(v == 8 for v in self.bma.unknown_data_block):
            info_bar.destroy()

    def _perform_asset_copy(self):
        """Check if assets need to be copied, and if so do so."""
        map_list = self.module.bgs
        entry = self.module.get_level_entry(self.item_id)
        if map_list.find_bma(entry.bma_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bma_name, BMA_EXT)
            self.module.project.create_new_file(new_rom_filename,
                                                self.bma, FileType.BMA)
            entry.bma_name = new_name
        if map_list.find_bpl(entry.bpl_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bpl_name, BPL_EXT)
            self.module.project.create_new_file(new_rom_filename,
                                                self.bpl, FileType.BPL)
            entry.bpl_name = new_name
        if map_list.find_bpc(entry.bpc_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bpc_name, BPC_EXT)
            self.module.project.create_new_file(new_rom_filename,
                                                self.bpc, FileType.BPC)
            entry.bpc_name = new_name
        for bpa_id, bpa in enumerate(entry.bpa_names):
            if bpa is not None:
                if map_list.find_bpa(bpa) > 1:
                    self._was_asset_copied = True
                    new_name, new_rom_filename = self._find_new_name(bpa, BPA_EXT)
                    self.module.project.create_new_file(new_rom_filename,
                                                        self.bpas[bpa_id], FileType.BPA)
                    entry.bpa_names[bpa_id] = new_name

    def _find_new_name(self, name_upper, ext):
        """Tries to find a free new name to place in the ROM."""
        if name_upper[-1].isdigit():
            # Is already a digit, add one
            try_name = name_upper[:-1] + str(int(name_upper[-1]) + 1)
        else:
            try_name = f"{name_upper}1"
        try_rom_filename = f"{DIR}/{try_name.lower()}{ext}"
        if self.module.project.file_exists(try_rom_filename):
            return self._find_new_name(try_name, ext)
        return try_name, try_rom_filename
    

    def on_btn_about_palettes_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("Map backgrounds can be used as primary or secondary.\n"
              "When used as primary, the background can have up to 14 palettes, using slots from 0 to 13.\n"
              "When used as secondary, the background can only have 1 palette, using slot 14, and every palette value will have a new value of (old_value{chr(0xA0)}+{chr(0xA0)}14){chr(0xA0)}mod{chr(0xA0)}16.\n"
              "It is still possible to use palette values above those limits, but this is only in cases where a background needs to reference a palette from the other background.\n"
              "Note: in the original game, almost every background is used as primary, the exceptions being mainly the weather (W) backgrounds.\n"),
            title=_("Background Palettes")
        )
        md.run()
        md.destroy()
