#  Copyright 2020-2025 SkyTemple Contributors
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
from __future__ import annotations
import itertools
from typing import TYPE_CHECKING, cast
import cairo
from gi.repository import Gtk, Gdk
from skytemple.controller.main import MainController
from skytemple.core.canvas_scale import CanvasScale
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.ui_utils import data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate
from skytemple.module.dungeon_graphics.controller.bg_menu import BgMenuController
from skytemple.module.dungeon_graphics.dungeon_bg_drawer import (
    Drawer,
    DrawerCellRenderer,
)
from skytemple_files.common.util import lcm
from skytemple_files.graphics.dbg.protocol import DbgProtocol
from skytemple_files.graphics.dbg import DBG_TILING_DIM, DBG_WIDTH_AND_HEIGHT
from skytemple_files.graphics.dpc.protocol import DpcProtocol
from skytemple_files.graphics.dpci.protocol import DpciProtocol
from skytemple_files.graphics.dpci import DPCI_TILE_DIM
from skytemple_files.graphics.dpl.protocol import DplProtocol
from skytemple_files.graphics.dpl import DPL_PAL_LEN, DPL_MAX_PAL
from skytemple_files.graphics.dpla.protocol import DplaProtocol
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule  # noqa: W291
INFO_IMEXPORT_TILES = _(
    "- The image consists of 8x8 tiles.\n- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- The exported palettes are only for your convenience.\n  They are based on the first time the tile is used in a \n  chunk mapping (Chunks > Edit Chunks).\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n"
)  # noqa: W291
INFO_IMEXPORT_CHUNK = _(
    "- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n\nSome image editors have problems when working with indexed\nimages, that contain the same color multiple times. You can\nmake all colors on the map unique before exporting at\nPalettes > Edit Palettes."
)  # noqa: W291
INFO_IMEXPORT_ENTIRE = _(
    "- The images is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n\nSome image editors have problems when working with indexed\nimages, that contain the same color multiple times. You can\nmake all colors on the map unique before exporting at\nPalettes > Edit Palettes."
)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "dungeon_graphics", "dungeon_bg.ui"))
class StDungeonGraphicsDungeonBgPage(Gtk.Box):
    __gtype_name__ = "StDungeonGraphicsDungeonBgPage"
    module: DungeonGraphicsModule
    item_data: int
    dialog_map_import_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_palettes_animated_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_palettes_animated_settings_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_palettes_animated_settings_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    palette_animation11_enabled: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    palette_animation11_frame_time0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time5: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time6: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time7: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time11: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time12: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time13: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time14: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time15: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time8: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time9: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation11_frame_time10: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_enabled: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    palette_animation12_frame_time0: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time5: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time6: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time7: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time11: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time12: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time13: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time14: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time15: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time8: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time9: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    palette_animation12_frame_time10: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    dialog_settings_number_collision_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_layers_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    men_map_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer1_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer1_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_ani_settings: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_ani_edit_11: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_ani_edit_12: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tools_tilequant: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    bg_layer1: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_layers: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    tb_zoom_in: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tb_zoom_out: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tb_chunk_grid: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_tile_grid: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_bg_color: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    bg_draw_sw: Gtk.ScrolledWindow = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    bg_layers_toolbox: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_layers_toolbox_layers: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_chunks_view: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image2: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image3: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_tiles_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image4: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_map_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_map_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_map_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image5: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_chunks_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_chunks_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_chunks_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image6: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image7: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image8: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image9: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    png_filter: Gtk.FileFilter = cast(Gtk.FileFilter, Gtk.Template.Child())
    dialog_chunks_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_chunks_import_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_chunks_import_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    chunks_import_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())
    chunks_import_palettes: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    dialog_map_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_map_import_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_map_import_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    map_import_layer1: Gtk.ButtonBox = cast(Gtk.ButtonBox, Gtk.Template.Child())
    map_import_layer1_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())
    dialog_tiles_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_import_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_import_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    tiles_import_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())

    def __init__(self, module: DungeonGraphicsModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.dbg: DbgProtocol = module.get_bg_dbg(item_data)
        self.dpl: DplProtocol = module.get_bg_dpl(item_data)
        self.dpla: DplaProtocol = module.get_bg_dpla(item_data)
        self.dpc: DpcProtocol = module.get_bg_dpc(item_data)
        self.dpci: DpciProtocol = module.get_bg_dpci(item_data)
        # Cairo surfaces for each tile in each layer for each frame
        # chunks_surfaces[chunk_idx][palette_animation_frame]
        self.chunks_surfaces: list[list[list[cairo.Surface]]] = []
        self.drawer: Drawer | None = None
        self.current_icon_view_renderer: DrawerCellRenderer | None = None
        self.bg_draw: Gtk.DrawingArea | None = None
        self.bg_draw_event_box: Gtk.EventBox | None = None
        self.scale_factor = CanvasScale(1.0)
        self.bg_draw_is_clicked = False
        self._init_chunk_imgs()
        self.menu_controller = BgMenuController(self)
        self._init_drawer()
        self._init_main_area()

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.dialog_palettes_animated_settings)
        safe_destroy(self.image1)
        safe_destroy(self.image2)
        safe_destroy(self.image3)
        safe_destroy(self.dialog_tiles_export)
        safe_destroy(self.image4)
        safe_destroy(self.dialog_map_export)
        safe_destroy(self.image5)
        safe_destroy(self.dialog_chunks_export)
        safe_destroy(self.image6)
        safe_destroy(self.image7)
        safe_destroy(self.image8)
        safe_destroy(self.image9)
        safe_destroy(self.dialog_chunks_import)
        safe_destroy(self.dialog_map_import)
        safe_destroy(self.dialog_tiles_import)

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
                # Set chunk at current position
                self.mark_as_modified()
                self.dbg.place_chunk(chunk_x, chunk_y, self.drawer.get_selected_chunk_id())
                self.drawer.mappings = self.dbg.mappings

    def on_current_icon_view_selection_changed(self, icon_view: Gtk.IconView):
        model, treeiter = (icon_view.get_model(), icon_view.get_selected_items())
        if model is not None and treeiter is not None and (treeiter != []):
            chunk_id = model[treeiter[0]][0]
            if self.drawer:
                self.drawer.set_selected_chunk(chunk_id)

    @Gtk.Template.Callback()
    def on_tb_zoom_out_clicked(self, w):
        self.scale_factor /= 2
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tb_zoom_in_clicked(self, w):
        self.scale_factor *= 2
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tb_chunk_grid_toggled(self, w):
        if self.drawer:
            self.drawer.set_draw_chunk_grid(w.get_active())

    @Gtk.Template.Callback()
    def on_tb_tile_grid_toggled(self, w):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())

    @Gtk.Template.Callback()
    def on_tb_bg_color_toggled(self, w):
        if self.drawer:
            self.drawer.set_pink_bg(w.get_active())
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_pink_bg(w.get_active())

    @Gtk.Template.Callback()
    def on_men_map_export_activate(self, *args):
        self.menu_controller.on_men_map_export_activate()

    @Gtk.Template.Callback()
    def on_men_map_import_activate(self, *args):
        self.menu_controller.on_men_map_import_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer1_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_export_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer1_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_import_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer1_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_edit_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer1_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_export_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer1_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_import_activate()

    @Gtk.Template.Callback()
    def on_men_palettes_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_edit_activate()

    @Gtk.Template.Callback()
    def on_men_palettes_ani_settings_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_settings_activate()

    @Gtk.Template.Callback()
    def on_men_palettes_ani_edit_11_activate(self, *args):
        self.menu_controller.edit_palette_ani(0)

    @Gtk.Template.Callback()
    def on_men_palettes_ani_edit_12_activate(self, *args):
        self.menu_controller.edit_palette_ani(1)

    @Gtk.Template.Callback()
    def on_format_details_entire_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            INFO_IMEXPORT_ENTIRE,
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_format_details_chunks_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            INFO_IMEXPORT_CHUNK,
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_format_details_tiles_clicked(self, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            INFO_IMEXPORT_TILES,
        )
        md.set_position(Gtk.WindowPosition.CENTER)
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_converter_tool_clicked(self, *args):
        MainController.show_tilequant_dialog(DPL_MAX_PAL, DPL_PAL_LEN)

    @Gtk.Template.Callback()
    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(DPL_MAX_PAL, DPL_PAL_LEN)

    def _init_chunk_imgs(self):
        """(Re)-draw the chunk images"""
        self.chunks_surfaces = []
        # For each chunk...
        for chunk_idx in range(0, len(self.dpc.chunks)):
            # For each frame of palette animation... ( applicable for this chunk )
            pal_ani_frames: list[list[cairo.Surface]] = []
            self.chunks_surfaces.append(pal_ani_frames)
            chunk_data = self.dpc.chunks[chunk_idx]
            chunk_image = self.dpc.single_chunk_to_pil(chunk_idx, self.dpci, self.dpl.palettes)
            has_pal_ani = any(
                chunk.pal_idx >= 10 and self.dpla.has_for_palette(chunk.pal_idx - 10) for chunk in chunk_data
            )
            if not has_pal_ani:
                len_pal_ani = 1
            else:
                ani_pal_lengths = [
                    self.dpla.get_frame_count_for_palette(x) for x in (0, 1) if self.dpla.has_for_palette(x)
                ]
                if len(ani_pal_lengths) < 2:
                    len_pal_ani = ani_pal_lengths[0]
                else:
                    len_pal_ani = lcm(*ani_pal_lengths)
            for pal_ani in range(0, len_pal_ani):
                # We don't have animated tiles, so ani_frames just has one entry.
                ani_frames: list[cairo.Surface] = []
                pal_ani_frames.append(ani_frames)
                # Switch out the palette with that from the palette animation
                if has_pal_ani:
                    pal_for_frame = itertools.chain.from_iterable(
                        self.dpla.apply_palette_animations(self.dpl.palettes, pal_ani)
                    )
                    chunk_image.putpalette(pal_for_frame)
                ani_frames.append(pil_to_cairo_surface(chunk_image.convert("RGBA")))
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
        bg_draw_sw = self.bg_draw_sw
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
        self.bg_draw = Gtk.DrawingArea.new()
        self.bg_draw_event_box.add(self.bg_draw)
        bg_draw_sw.add(self.bg_draw_event_box)
        self.bg_draw.set_size_request(
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM,
            DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM,
        )
        self.drawer = Drawer(self.bg_draw, self.dbg, self.pal_ani_durations, self.chunks_surfaces)
        self.drawer.start()

    def _init_chunks_icon_view(self):
        """Fill the icon view"""
        self._deinit_chunks_icon_view()
        icon_view = self.bg_chunks_view
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.current_icon_view_renderer = DrawerCellRenderer(icon_view, self.pal_ani_durations, self.chunks_surfaces)
        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(self.current_icon_view_renderer, True)
        icon_view.add_attribute(self.current_icon_view_renderer, "chunkidx", 0)
        icon_view.connect("selection-changed", self.on_current_icon_view_selection_changed)
        for idx in range(0, len(self.chunks_surfaces)):
            store.append([idx])
        first_iter = store.get_iter_first()
        if first_iter:
            icon_view.select_path(store.get_path(first_iter))
        self.current_icon_view_renderer.start()
        self.current_icon_view_renderer.set_pink_bg(self.tb_bg_color.get_active())

    def _deinit_chunks_icon_view(self):
        """Remove the icon view for the specified layer"""
        icon_view: Gtk.IconView = self.bg_chunks_view
        icon_view.clear()
        icon_view.set_model(None)

    def mark_as_modified(self):
        self.module.mark_as_modified(self.item_data, True)

    def _init_main_area(self):
        self._init_chunks_icon_view()
        self._update_scales()

    def _update_scales(self):
        """Update drawers+DrawingArea and iconview+Renderer scales"""
        if self.bg_draw:
            self.bg_draw.set_size_request(
                round(DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM * self.scale_factor),
                round(DBG_WIDTH_AND_HEIGHT * DBG_TILING_DIM * DPCI_TILE_DIM * self.scale_factor),
            )
        if self.drawer:
            self.drawer.set_scale(self.scale_factor)
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_scale(self.scale_factor)
            # update size
            self.current_icon_view_renderer.set_fixed_size(
                int(DPCI_TILE_DIM * 3 * self.scale_factor),
                int(DPCI_TILE_DIM * 3 * self.scale_factor),
            )
            icon_view: Gtk.IconView = self.bg_chunks_view
            icon_view.queue_resize()

    def reload_all(self):
        """Reload all image related things"""
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.stop()
        self._init_chunk_imgs()
        assert self.drawer is not None
        self.drawer.reset(self.dbg, self.pal_ani_durations, self.chunks_surfaces)
        self._init_main_area()
