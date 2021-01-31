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

from gi.repository import Gtk, Gdk
from gi.repository.Gtk import *

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.module.dungeon_graphics.controller.bg_menu import BgMenuController
from skytemple.module.dungeon_graphics.dungeon_bg_drawer import Drawer, DrawerCellRenderer
from skytemple_files.common.util import lcm
from skytemple_files.graphics.dbg.model import Dbg, DBG_TILING_DIM, DBG_WIDTH_AND_HEIGHT
from skytemple_files.graphics.dpc.model import Dpc
from skytemple_files.graphics.dpci.model import Dpci, DPCI_TILE_DIM
from skytemple_files.graphics.dpl.model import Dpl, DPL_MAX_PAL, DPL_PAL_LEN
from skytemple_files.graphics.dpla.model import Dpla
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule


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
""")

INFO_IMEXPORT_CHUNK = _("""- The image is a 256-color indexed PNG.
- The 256 colors are divided into 16 16 color palettes.
- Each 8x8 tile in the image MUST only use colors from
  one of these 16 palettes.
- The first color in each palette is transparency.
- Each import must result in a maximum of 1024 unique 8x8 tiles 
  (=not existing with another palette or flipped or rotated).

Some image editors have problems when working with indexed
images, that contain the same color multiple times. You can
make all colors on the map unique before exporting at
Palettes > Edit Palettes.""")

INFO_IMEXPORT_ENTIRE = _("""- The images is a 256-color indexed PNG.
- The 256 colors are divided into 16 16 color palettes.
- Each 8x8 tile in the image MUST only use colors from
  one of these 16 palettes.
- The first color in each palette is transparency.
- Each import must result in a maximum of 1024 unique 8x8 tiles 
  (=not existing with another palette or flipped or rotated).

Some image editors have problems when working with indexed
images, that contain the same color multiple times. You can
make all colors on the map unique before exporting at
Palettes > Edit Palettes.""")


class DungeonBgController(AbstractController):
    def __init__(self, module: 'DungeonGraphicsModule', item_id: int):
        self.module = module
        self.item_id = item_id

        self.builder = None

        self.dbg: Dbg = module.get_bg_dbg(item_id)
        self.dpl: Dpl = module.get_bg_dpl(item_id)
        self.dpla: Dpla = module.get_bg_dpla(item_id)
        self.dpc: Dpc = module.get_bg_dpc(item_id)
        self.dpci: Dpci = module.get_bg_dpci(item_id)

        # Cairo surfaces for each tile in each layer for each frame
        # chunks_surfaces[chunk_idx][palette_animation_frame]
        self.chunks_surfaces = []

        self.drawer: Drawer = None
        self.current_icon_view_renderer: DrawerCellRenderer = None

        self.bg_draw: DrawingArea = None
        self.bg_draw_event_box: EventBox = None

        self.scale_factor = 1

        self.bg_draw_is_clicked = False

        self._init_chunk_imgs()

        self.menu_controller = BgMenuController(self)

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'dungeon_bg.glade')
        self._init_drawer()
        self._init_main_area()
        self.builder.connect_signals(self)
        return self.builder.get_object('editor_map_bg')

    def on_bg_draw_click(self, box, button: Gdk.EventButton):
        correct_mouse_x = int(button.x / self.scale_factor)
        correct_mouse_y = int(button.y / self.scale_factor)
        if button.button == 1:
            self.bg_draw_is_clicked = True
            snap_x = correct_mouse_x - correct_mouse_x % (DBG_TILING_DIM * DPCI_TILE_DIM)
            snap_y = correct_mouse_y - correct_mouse_y % (DBG_TILING_DIM * DPCI_TILE_DIM)
            self._set_chunk_at_pos(snap_x, snap_y)

    def on_bg_draw_release(self, box, button: Gdk.EventButton):
        if button.button == 1:
            self.bg_draw_is_clicked = False

    def on_bg_draw_mouse_move(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int(motion.x / self.scale_factor)
        correct_mouse_y = int(motion.y / self.scale_factor)
        if self.drawer:
            snap_x = correct_mouse_x - correct_mouse_x % (DBG_TILING_DIM * DPCI_TILE_DIM)
            snap_y = correct_mouse_y - correct_mouse_y % (DBG_TILING_DIM * DPCI_TILE_DIM)
            self.drawer.set_mouse_position(snap_x, snap_y)
            if self.bg_draw_is_clicked:
                self._set_chunk_at_pos(snap_x, snap_y)

    def _set_chunk_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            chunk_x = int(mouse_x / (DBG_TILING_DIM * DPCI_TILE_DIM))
            chunk_y = int(mouse_y / (DBG_TILING_DIM * DPCI_TILE_DIM))
            if 0 <= chunk_x < DBG_WIDTH_AND_HEIGHT and 0 <= chunk_y < DBG_WIDTH_AND_HEIGHT:
                chunk_mapping_idx = int(chunk_y * DBG_WIDTH_AND_HEIGHT + chunk_x)
                # Set chunk at current position
                self.mark_as_modified()
                self.dbg.mappings[chunk_mapping_idx] = self.drawer.get_selected_chunk_id()

    def on_current_icon_view_selection_changed(self, icon_view: IconView):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            chunk_id = model[treeiter][0]
            if self.drawer:
                self.drawer.set_selected_chunk(chunk_id)

    def on_tb_zoom_out_clicked(self, w):
        self.scale_factor /= 2
        self._update_scales()

    def on_tb_zoom_in_clicked(self, w):
        self.scale_factor *= 2
        self._update_scales()

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

    def on_men_map_export_activate(self, *args):
        self.menu_controller.on_men_map_export_activate()

    def on_men_map_import_activate(self, *args):
        self.menu_controller.on_men_map_import_activate()

    def on_men_chunks_layer1_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_export_activate()

    def on_men_chunks_layer1_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_import_activate()

    def on_men_chunks_layer1_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_edit_activate()

    def on_men_tiles_layer1_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_export_activate()

    def on_men_tiles_layer1_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_import_activate()

    def on_men_palettes_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_edit_activate()

    def on_men_palettes_ani_settings_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_settings_activate()

    def on_men_palettes_ani_edit_11_activate(self, *args):
        self.menu_controller.edit_palette_ani(0)

    def on_men_palettes_ani_edit_12_activate(self, *args):
        self.menu_controller.edit_palette_ani(1)

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
        MainController.show_tilequant_dialog(DPL_MAX_PAL, DPL_PAL_LEN)

    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(DPL_MAX_PAL, DPL_PAL_LEN)

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
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM,
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM
        )

        self.drawer = Drawer(self.bg_draw, self.dbg, self.pal_ani_durations, self.chunks_surfaces)
        self.drawer.start()

    def _init_chunks_icon_view(self):
        """Fill the icon view"""
        self._deinit_chunks_icon_view()
        icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.current_icon_view_renderer = DrawerCellRenderer(icon_view, self.pal_ani_durations, self.chunks_surfaces)
        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(self.current_icon_view_renderer, True)
        icon_view.add_attribute(self.current_icon_view_renderer, 'chunkidx', 0)
        icon_view.connect('selection-changed', self.on_current_icon_view_selection_changed)

        for idx in range(0, len(self.chunks_surfaces)):
            store.append([idx])

        icon_view.select_path(store.get_path(store.get_iter_first()))
        self.current_icon_view_renderer.start()

        self.current_icon_view_renderer.set_pink_bg(self.builder.get_object(f'tb_bg_color').get_active())

    def _deinit_chunks_icon_view(self):
        """Remove the icon view for the specified layer"""
        icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
        icon_view.clear()
        icon_view.set_model(None)

    def mark_as_modified(self):
        self.module.mark_as_modified(self.item_id, True)

    def _init_main_area(self):
        self._init_chunks_icon_view()
        self._update_scales()

    def _update_scales(self):
        """Update drawers+DrawingArea and iconview+Renderer scales"""
        self.bg_draw.set_size_request(
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM * self.scale_factor,
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM * self.scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self.scale_factor)

        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_scale(self.scale_factor)
            # update size
            self.current_icon_view_renderer.set_fixed_size(
                int(DPCI_TILE_DIM * 3 * self.scale_factor), int(DPCI_TILE_DIM * 3 * self.scale_factor)
            )

            icon_view: IconView = self.builder.get_object(f'bg_chunks_view')
            icon_view.queue_resize()

    def reload_all(self):
        """Reload all image related things"""
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.stop()
        self._init_chunk_imgs()
        self.drawer.reset(self.dbg, self.pal_ani_durations, self.chunks_surfaces)
        self._init_main_area()
