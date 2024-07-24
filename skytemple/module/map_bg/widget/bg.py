#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
import typing
from typing import TYPE_CHECKING, cast
from collections.abc import Iterable, Sequence
import cairo
from gi.repository import Gtk, Gdk
from skytemple.controller.main import MainController
from skytemple.core.canvas_scale import CanvasScale
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.mapbg_util.map_tileset_overlay import MapTilesetOverlay
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_SCENE
from skytemple.core.ui_utils import data_dir, safe_destroy
from skytemple.init_locale import LocalePatchedGtkTemplate
from skytemple.module.map_bg.controller.bg_menu import BgMenuController
from skytemple.module.map_bg.drawer import Drawer, DrawerCellRenderer, DrawerInteraction
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptLevelMapType
from skytemple_files.common.types.file_types import FileType
from skytemple_files.graphics.bg_list_dat import BMA_EXT, BPC_EXT, BPL_EXT, BPA_EXT, DIR
from skytemple_files.graphics.bma import MASK_PAL
from skytemple_files.graphics.bma.protocol import BmaProtocol
from skytemple_files.graphics.bpc import BPC_TILE_DIM
from skytemple_files.graphics.bpl import BPL_NORMAL_MAX_PAL
from skytemple_files.common.i18n_util import _
from skytemple_files.hardcoded.ground_dungeon_tilesets import resolve_mapping_for_level

if TYPE_CHECKING:
    from skytemple.module.map_bg.module import MapBgModule  # noqa: W291
INFO_IMEXPORT_TILES = _(
    "- The image consists of 8x8 tiles.\n- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- The exported palettes are only for your convenience.\n  They are based on the first time the tile is used in a \n  chunk mapping (Chunks > Edit Chunks).\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n\nAnimated tiles are not imported."
)  # noqa: W291
INFO_IMEXPORT_CHUNK = _(
    "- The image consists of 8x8 tiles.\n- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- Animated tiles are NOT exported or imported. In the export they\n  are replaced with blank tiles. On import the mappings to \n  animated tiles will be lost, so make sure you note them down \n  to manually re-assign  them on import. To change animated tiles, \n  go to Tiles > Animated Tiles.\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n\nSome image editors have problems when working with indexed\nimages, that contain the same color multiple times. You can\nmake all colors on the map unique before exporting at\nPalettes > Edit Palettes. Alternatively use the converter.\n\nPlease note, that chunks can not use colors from \nthe last two palettes. They should not be used by any tile.\n\nColors that are in the wrong palette are replaced wth\ntransparency.\n\nStatic tiles, chunks and palettes are replaced on import. \nAnimated tiles and palette animation settings are not changed.\n"
)  # noqa: W291
INFO_IMEXPORT_ENTIRE = _(
    "- The image is a 256-color indexed PNG.\n- The 256 colors are divided into 16 16 color palettes.\n- Each 8x8 tile in the image MUST only use colors from\n  one of these 16 palettes.\n- The first color in each palette is transparency.\n- Animated tiles are exported as static tiles.\n- Each import must result in a maximum of 1024 unique 8x8 tiles \n  (=not existing with another palette or flipped or rotated).\n\nSome image editors have problems when working with indexed\nimages, that contain the same color multiple times. You can\nmake all colors on the map unique before exporting at\nPalettes > Edit Palettes.\n\nColors that are in the wrong palette are replaced wth\ntransparency.\n\nStatic tiles are replaced on import.\nAnimated tiles and palette animation settings are not changed.\n\nSince no animated tiles are imported, they need\nto be (re-)assigned to chunks after the import."
)
import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "map_bg", "bg.ui"))
class StMapBgBgPage(Gtk.Box):
    __gtype_name__ = "StMapBgBgPage"
    module: MapBgModule
    item_data: int
    bg_layers: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    tb_zoom_in: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tb_zoom_out: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    tb_chunk_grid: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_tile_grid: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_hide_other: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_rectangle: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_bg_color: Gtk.ToggleToolButton = cast(Gtk.ToggleToolButton, Gtk.Template.Child())
    tb_goto_scene: Gtk.ToolButton = cast(Gtk.ToolButton, Gtk.Template.Child())
    bg_draw_sw: Gtk.ScrolledWindow = cast(Gtk.ScrolledWindow, Gtk.Template.Child())
    bg_layers_toolbox: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_layers_toolbox_collision: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    collison_switch: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bg_layers_toolbox_data: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    data_combo_box: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    bg_layers_toolbox_layers: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_chunks_view: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    dialog_map_import_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_palettes_animated_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_palettes_animated_settings_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_palettes_animated_settings_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    palette_animation_enabled: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    pallete_anim_setting_unk3_p1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p1: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p2: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p3: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p4: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p5: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p5: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p6: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p6: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p7: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p7: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p8: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p8: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p9: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p9: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p10: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p10: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p11: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p11: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p12: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p12: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p13: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p13: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p14: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p14: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p15: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p15: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk3_p16: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    pallete_anim_setting_unk4_p16: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    dialog_settings_number_collision_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings_number_layers_adjustment: Gtk.Adjustment = cast(Gtk.Adjustment, Gtk.Template.Child())
    dialog_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_settings_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_settings_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    settings_has_data_layer: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    dialog_tiles_animated_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_animated_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_animated_export_label_sep: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    dialog_tiles_animated_export_radio_sep: Gtk.RadioButton = cast(Gtk.RadioButton, Gtk.Template.Child())
    dialog_tiles_animated_export_radio_single: Gtk.RadioButton = cast(Gtk.RadioButton, Gtk.Template.Child())
    dialog_tiles_animated_export_select_bpa: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    dialog_tiles_animated_export_export_btn: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_animated_export_import_btn: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_animated_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_animated_settings_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_animated_settings_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    bpa_enable1: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box1: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable2: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box2: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable3: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box3: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable4: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box4: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable5: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box5: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable6: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box6: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable7: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box7: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bpa_enable8: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    bpa_box8: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    dialog_width_height: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_width_height_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_width_height_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    map_width_chunks: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    map_height_chunks: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    map_wh_link: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    map_wh_link_target: Gtk.ListBox = cast(Gtk.ListBox, Gtk.Template.Child())
    map_width_tiles: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    map_height_tiles: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    men_map_settings: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_width_height: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_export_gif: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_map_go_scripts: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer1_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer2_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer2_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_chunks_layer2_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer1_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer1_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer2_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_layer2_import: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_ani_settings: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tiles_ani_export: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_ani_settings: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_palettes_ani_edit: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    men_tools_tilequant: Gtk.MenuItem = cast(Gtk.MenuItem, Gtk.Template.Child())
    bg_notebook: Gtk.Notebook = cast(Gtk.Notebook, Gtk.Template.Child())
    bg_layer1: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_layer2: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_col1: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_col2: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    bg_data: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    metadata: Gtk.Grid = cast(Gtk.Grid, Gtk.Template.Child())
    filename_bma: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpc: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpl: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa1: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa2: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa3: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa4: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa5: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa6: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa7: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    filename_bpa8: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    editor_rest_room_note: Gtk.InfoBar = cast(Gtk.InfoBar, Gtk.Template.Child())
    btn_toggle_overlay_rendering: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    editor_warning_palette: Gtk.InfoBar = cast(Gtk.InfoBar, Gtk.Template.Child())
    btn_about_palettes: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image1: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_chunks_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_chunks_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_chunks_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image2: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_map_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_map_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_map_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image3: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    dialog_tiles_export: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_export_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_export_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    image4: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
    image5: Gtk.Image = cast(Gtk.Image, Gtk.Template.Child())
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
    map_import_layer2: Gtk.ButtonBox = cast(Gtk.ButtonBox, Gtk.Template.Child())
    map_import_layer2_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())
    dialog_tiles_import: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    dialog_tiles_import_btn_close: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    dialog_tiles_import_btn_ok: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    tiles_import_file: Gtk.FileChooserButton = cast(Gtk.FileChooserButton, Gtk.Template.Child())

    def __init__(self, module: MapBgModule, item_data: int):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.notebook: Gtk.Notebook | None = None
        self.bma = module.get_bma(item_data)
        self.bpl = module.get_bpl(item_data)
        self.bpc = module.get_bpc(item_data)
        self.bpas = module.get_bpas(item_data)
        self.first_cursor_pos = (0, 0)
        self.last_bma: BmaProtocol | None = None
        # Cairo surfaces for each tile in each layer for each frame
        # chunks_surfaces[layer_number][chunk_idx][palette_animation_frame][frame]
        self.chunks_surfaces: list[Sequence[Iterable[list[cairo.Surface]]]] = []
        self.bpa_durations = 0
        self.drawer: Drawer | None = None
        self.current_icon_view_renderer: DrawerCellRenderer | None = None
        self.bg_draw: Gtk.DrawingArea | None = None
        self.bg_draw_event_box: Gtk.EventBox | None = None
        self._tileset_drawer_overlay: MapTilesetOverlay | None = None
        self.scale_factor = CanvasScale(1.0)
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
            self.bma = module.get_bma(item_data)
            self.bpl = module.get_bpl(item_data)
            self.bpc = module.get_bpc(item_data)
            self.bpas = module.get_bpas(item_data)
        self.set_warning_palette()
        self.notebook = self.bg_notebook
        self._init_drawer()
        current_page = self.notebook.get_nth_page(self.notebook.get_current_page())
        if current_page:
            self._init_tab(typing.cast(Gtk.Box, current_page))
        self._refresh_metadata()
        self._init_rest_room_note()
        try:
            # Invalidate SSA scene cache for this BG
            # TODO: This is obviously very ugly coupling...
            from skytemple.module.script.widget.ssa import StScriptSsaPage

            StScriptSsaPage.map_bg_surface_cache = (None,)
        except ImportError:
            pass
        if self._was_asset_copied:
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                _(
                    "This map background shared some asset files with other map backgrounds.\nSkyTemple can't edit shared files, so those assets were copied."
                ),
                title=_("SkyTemple - Notice"),
            )
            md.run()
            md.destroy()
            self.module.mark_as_modified(self.item_data)
            self.module.mark_level_list_as_modified()

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.bg_layers_toolbox_collision)
        safe_destroy(self.bg_layers_toolbox_data)
        safe_destroy(self.bg_layers_toolbox_layers)
        safe_destroy(self.dialog_palettes_animated_settings)
        safe_destroy(self.dialog_settings)
        safe_destroy(self.dialog_tiles_animated_export)
        safe_destroy(self.dialog_tiles_animated_settings)
        safe_destroy(self.dialog_width_height)
        safe_destroy(self.bg_layers)
        safe_destroy(self.image1)
        safe_destroy(self.dialog_chunks_export)
        safe_destroy(self.image2)
        safe_destroy(self.dialog_map_export)
        safe_destroy(self.image3)
        safe_destroy(self.dialog_tiles_export)
        safe_destroy(self.image4)
        safe_destroy(self.image5)
        safe_destroy(self.image6)
        safe_destroy(self.image7)
        safe_destroy(self.image8)
        safe_destroy(self.image9)
        safe_destroy(self.dialog_chunks_import)
        safe_destroy(self.dialog_map_import)
        safe_destroy(self.dialog_tiles_import)

    @Gtk.Template.Callback()
    def on_bg_notebook_switch_page(self, notebook, page, *args):
        self._init_tab(page)

    def on_bg_draw_click(self, box, button: Gdk.EventButton):
        correct_mouse_x = int(button.x / self.scale_factor)
        correct_mouse_y = int(button.y / self.scale_factor)
        if button.button == 1:
            assert self.drawer
            if not self.bg_draw_is_clicked:
                self.last_bma = self.bma.deepcopy()
            self.bg_draw_is_clicked = True
            if self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                snap_x = correct_mouse_x - correct_mouse_x % (self.bma.tiling_width * BPC_TILE_DIM)
                snap_y = correct_mouse_y - correct_mouse_y % (self.bma.tiling_height * BPC_TILE_DIM)
            else:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
            self.first_cursor_pos = (snap_x, snap_y)
            if self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                self._set_chunk_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.COL:
                self._set_col_at_pos(snap_x, snap_y)
            elif self.drawer.get_interaction_mode() == DrawerInteraction.DAT:
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
                tilling_x = self.bma.tiling_width * BPC_TILE_DIM
                tilling_y = self.bma.tiling_height * BPC_TILE_DIM
            else:
                snap_x = correct_mouse_x - correct_mouse_x % BPC_TILE_DIM
                snap_y = correct_mouse_y - correct_mouse_y % BPC_TILE_DIM
                tilling_x = BPC_TILE_DIM
                tilling_y = BPC_TILE_DIM
            self.drawer.set_mouse_position(snap_x, snap_y)
            if self.bg_draw_is_clicked:
                tb_rectangle = self.tb_rectangle
                if tb_rectangle.get_active():
                    # TODO: Clearly not optimized
                    assert self.last_bma
                    last_bma_copy = self.last_bma.deepcopy()
                    self.bma.layer0 = last_bma_copy.layer0
                    self.bma.layer1 = last_bma_copy.layer1
                    self.bma.collision = last_bma_copy.collision
                    self.bma.collision2 = last_bma_copy.collision2
                    self.bma.unknown_data_block = last_bma_copy.unknown_data_block
                    x_pos = [snap_x, self.first_cursor_pos[0]]
                    x_pos.sort()
                    y_pos = [snap_y, self.first_cursor_pos[1]]
                    y_pos.sort()
                    y = y_pos[0]
                    while y < y_pos[1] + tilling_y:
                        x = x_pos[0]
                        while x < x_pos[1] + tilling_x:
                            if self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                                self._set_chunk_at_pos(x, y)
                            elif self.drawer.get_interaction_mode() == DrawerInteraction.COL:
                                self._set_col_at_pos(x, y)
                            elif self.drawer.get_interaction_mode() == DrawerInteraction.DAT:
                                self._set_data_at_pos(x, y)
                            x += tilling_x
                        y += tilling_y
                elif self.drawer.get_interaction_mode() == DrawerInteraction.CHUNKS:
                    self._set_chunk_at_pos(snap_x, snap_y)
                elif self.drawer.get_interaction_mode() == DrawerInteraction.COL:
                    self._set_col_at_pos(snap_x, snap_y)
                elif self.drawer.get_interaction_mode() == DrawerInteraction.DAT:
                    self._set_data_at_pos(snap_x, snap_y)
                self.drawer.reset_bma(self.bma)

    def _set_chunk_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            chunk_x = int(mouse_x / (self.bma.tiling_width * BPC_TILE_DIM))
            chunk_y = int(mouse_y / (self.bma.tiling_height * BPC_TILE_DIM))
            if 0 <= chunk_x < self.bma.map_width_chunks and 0 <= chunk_y < self.bma.map_height_chunks:
                # Set chunk at current position
                self.mark_as_modified()
                self.bma.place_chunk(
                    self.current_chunks_icon_layer,
                    chunk_x,
                    chunk_y,
                    self.drawer.get_selected_chunk_id(),
                )
                self.drawer.mappings = [self.bma.layer0, self.bma.layer1]  # type: ignore

    def _set_col_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            if 0 <= tile_x < self.bma.map_width_camera and 0 <= tile_y < self.bma.map_height_camera:
                # Set collision at current position
                self.mark_as_modified()
                self.bma.place_collision(
                    self.drawer.get_edited_collision(),
                    tile_x,
                    tile_y,
                    self.drawer.get_interaction_col_solid(),
                )

    def _set_data_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            if 0 <= tile_x < self.bma.map_width_camera and 0 <= tile_y < self.bma.map_height_camera:
                # Set data value at current position
                self.mark_as_modified()
                self.bma.place_data(tile_x, tile_y, self.drawer.get_interaction_dat_value())

    def on_current_icon_view_selection_changed(self, icon_view: Gtk.IconView):
        model, treeiter = (icon_view.get_model(), icon_view.get_selected_items())
        if model is not None and treeiter is not None and (treeiter != []):
            chunk_id = model[treeiter[0]][0]
            if self.drawer:
                self.drawer.set_selected_chunk(chunk_id)

    @Gtk.Template.Callback()
    def on_collison_switch_state_set(self, wdg, state):
        if self.drawer:
            self.drawer.set_interaction_col_solid(state)

    @Gtk.Template.Callback()
    def on_data_combo_box_changed(self, cb: Gtk.ComboBox):
        if self.drawer:
            self.drawer.set_interaction_dat_value(cb.get_active())

    @Gtk.Template.Callback()
    def on_tb_zoom_out_clicked(self, w):
        self.scale_factor /= 2
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tb_zoom_in_clicked(self, w):
        self.scale_factor *= 2
        self._update_scales()

    @Gtk.Template.Callback()
    def on_tb_hide_other_toggled(self, w):
        if self.drawer:
            self.drawer.set_show_only_edited_layer(w.get_active())

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
    def on_tb_goto_scene_clicked(self, w):
        try:
            associated = self.module.get_associated_script_map(self.item_data)
            if associated is None:
                raise ValueError()
            self.module.project.request_open(OpenRequest(REQUEST_TYPE_SCENE, associated.name), True)
        except ValueError:
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.DESTROY_WITH_PARENT,
                Gtk.MessageType.INFO,
                Gtk.ButtonsType.OK,
                _("A script map with the same name as this background does not exist."),
                title=_("No Scenes Found"),
            )
            md.run()
            md.destroy()

    @Gtk.Template.Callback()
    def on_men_map_settings_activate(self, *args):
        self.menu_controller.on_men_map_settings_activate()

    @Gtk.Template.Callback()
    def on_men_map_width_height_activate(self, *args):
        self.menu_controller.on_men_map_width_height_activate()

    @Gtk.Template.Callback()
    def on_men_map_export_gif_activate(self, *args):
        self.menu_controller.on_men_map_export_gif_activate()

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
    def on_men_chunks_layer2_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_export_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer2_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_import_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer1_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_edit_activate()

    @Gtk.Template.Callback()
    def on_men_chunks_layer2_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer2_edit_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer1_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_export_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer1_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_import_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer2_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer2_export_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_layer2_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer2_import_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_ani_settings_activate(self, *args):
        self.menu_controller.on_men_tiles_ani_settings_activate()

    @Gtk.Template.Callback()
    def on_men_tiles_ani_export_activate(self, *args):
        self.menu_controller.on_men_tiles_ani_export_activate()

    @Gtk.Template.Callback()
    def on_dialog_tiles_animated_export_export_btn_clicked(self, *args):
        self.menu_controller.on_dialog_tiles_animated_export_export_btn_clicked()

    @Gtk.Template.Callback()
    def on_dialog_tiles_animated_export_import_btn_clicked(self, *args):
        self.menu_controller.on_dialog_tiles_animated_export_import_btn_clicked()

    @Gtk.Template.Callback()
    def on_men_palettes_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_edit_activate()

    @Gtk.Template.Callback()
    def on_men_palettes_ani_settings_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_settings_activate()

    @Gtk.Template.Callback()
    def on_palette_animation_enabled_state_set(self, wdg, state, *args):
        self.menu_controller.on_palette_animation_enabled_state_set(state)

    @Gtk.Template.Callback()
    def on_men_palettes_ani_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_edit_activate()

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
        MainController.show_tilequant_dialog(14, 16)

    @Gtk.Template.Callback()
    def on_men_tools_tilequant_activate(self, *args):
        MainController.show_tilequant_dialog(14, 16)

    def set_warning_palette(self):
        editor_warning_palette = self.editor_warning_palette
        editor_warning_palette.set_revealed(self.weird_palette)

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
            chunks_current_layer: list[list[list[cairo.Surface]]] = []
            self.chunks_surfaces.append(chunks_current_layer)
            # For each chunk...
            for chunk_idx in range(0, self.bpc.layers[layer_idx_bpc].chunk_tilemap_len):
                # For each frame of palette animation... ( applicable for this chunk )
                pal_ani_frames: list[list[cairo.Surface]] = []
                chunks_current_layer.append(pal_ani_frames)
                chunk_data = self.bpc.get_chunk(layer_idx_bpc, chunk_idx)
                chunk_images = self.bpc.single_chunk_animated_to_pil(
                    layer_idx_bpc, chunk_idx, self.bpl.palettes, self.bpas
                )
                if not self.weird_palette:
                    for x in chunk_images:
                        for n in x.tobytes("raw", "P"):
                            n //= 16
                            if n >= self.bpl.number_palettes or n >= BPL_NORMAL_MAX_PAL:
                                # If one chunk uses weird palette values, display the warning
                                self.weird_palette = True
                                break
                        if self.weird_palette:
                            break
                has_pal_ani = any(self.bpl.is_palette_affected_by_animation(chunk.pal_idx) for chunk in chunk_data)
                len_pal_ani = len(self.bpl.animation_palette) if has_pal_ani else 1
                for pal_ani in range(0, len_pal_ani):
                    # For each frame of tile animation...
                    bpa_ani_frames: list[cairo.Surface] = []
                    pal_ani_frames.append(bpa_ani_frames)
                    for img in chunk_images:
                        # Switch out the palette with that from the palette animation
                        if has_pal_ani:
                            pal_for_frame = itertools.chain.from_iterable(self.bpl.apply_palette_animations(pal_ani))
                            img.putpalette(pal_for_frame)
                        # Remove alpha first
                        img_mask = img.copy()
                        img_mask.putpalette(MASK_PAL)
                        img_mask = img_mask.convert("1")
                        img = img.convert("RGBA")
                        img.putalpha(img_mask)
                        bpa_ani_frames.append(pil_to_cairo_surface(img))
            # TODO: No BPAs at different speeds supported at the moment
            self.bpa_durations = 0
            for bpa in self.bpas:
                if bpa is not None:
                    single_bpa_duration = (
                        max(info.duration_per_frame for info in bpa.frame_info) if len(bpa.frame_info) > 0 else 9999
                    )
                    if single_bpa_duration > self.bpa_durations:
                        self.bpa_durations = single_bpa_duration
            # TODO: No BPL animations at different speeds supported at the moment
            self.pal_ani_durations = 0
            if self.bpl.has_palette_animation:
                self.pal_ani_durations = max(spec.duration_per_frame for spec in self.bpl.animation_specs)
        self.set_warning_palette()

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
            self.bma.map_width_chunks * self.bma.tiling_width * BPC_TILE_DIM,
            self.bma.map_height_chunks * self.bma.tiling_height * BPC_TILE_DIM,
        )
        self.drawer = Drawer(
            self.bg_draw,
            self.bma,
            self.bpa_durations,
            self.pal_ani_durations,
            self.chunks_surfaces,
        )
        if self._tileset_drawer_overlay:
            self.drawer.add_overlay(self._tileset_drawer_overlay)
        self.drawer.start()

    def _init_drawer_layer_selected(self):
        assert self.drawer is not None
        self.drawer.set_edited_layer(self.current_chunks_icon_layer)
        # Set drawer state based on some buttons
        self.drawer.set_show_only_edited_layer(self.tb_hide_other.get_active())
        self.drawer.set_draw_chunk_grid(self.tb_chunk_grid.get_active())
        self.drawer.set_draw_tile_grid(self.tb_tile_grid.get_active())
        self.drawer.set_pink_bg(self.tb_bg_color.get_active())

    def _init_drawer_collision_selected(self, collision_id):
        assert self.drawer is not None
        self.drawer.set_edited_collision(collision_id)
        self.drawer.set_interaction_col_solid(self.collison_switch.get_active())
        # Set drawer state based on some buttons
        self.drawer.set_draw_chunk_grid(self.tb_chunk_grid.get_active())
        self.drawer.set_draw_tile_grid(self.tb_tile_grid.get_active())
        self.drawer.set_pink_bg(self.tb_bg_color.get_active())

    def _init_drawer_data_layer_selected(self):
        assert self.drawer is not None
        self.drawer.set_edit_data_layer()
        cb: Gtk.ComboBox = self.data_combo_box
        self.drawer.set_interaction_dat_value(cb.get_active())
        # Set drawer state based on some buttons
        self.drawer.set_draw_chunk_grid(self.tb_chunk_grid.get_active())
        self.drawer.set_draw_tile_grid(self.tb_tile_grid.get_active())

    def _init_chunks_icon_view(self, layer_number: int):
        """Fill the icon view for the specified layer"""
        self._deinit_chunks_icon_view()
        self.current_chunks_icon_layer = layer_number
        icon_view = self.bg_chunks_view
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        self.current_icon_view_renderer = DrawerCellRenderer(
            icon_view,
            layer_number,
            self.bpa_durations,
            self.pal_ani_durations,
            self.chunks_surfaces,
        )
        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(self.current_icon_view_renderer, True)
        icon_view.add_attribute(self.current_icon_view_renderer, "chunkidx", 0)
        icon_view.connect("selection-changed", self.on_current_icon_view_selection_changed)
        for idx in range(0, len(self.chunks_surfaces[layer_number])):
            store.append([idx])
        siter = store.get_iter_first()
        if siter:
            icon_view.select_path(store.get_path(siter))
        self.current_icon_view_renderer.start()
        self.current_icon_view_renderer.set_pink_bg(self.tb_bg_color.get_active())

    def _deinit_chunks_icon_view(self):
        """Remove the icon view for the specified layer"""
        icon_view = self.bg_chunks_view
        icon_view.clear()
        icon_view.set_model(None)

    def _init_data_layer_combobox(self):
        cb = self.data_combo_box
        if cb.get_model() is None:
            store = Gtk.ListStore(str, int)
            for i in range(0, 256):
                if i == 0:
                    store.append([_("None"), i])
                else:
                    store.append([f"0x{i:02x}", i])
            cb.set_model(store)
            cell = Gtk.CellRendererText()
            cb.pack_start(cell, True)
            cb.add_attribute(cell, "text", 0)
            cb.set_active(0)

    def mark_as_modified(self):
        self.module.mark_as_modified(self.item_data)

    def _init_tab(self, notebook_page: Gtk.Box):
        layers_box = self.bg_layers
        toolbox_box = self.bg_layers_toolbox
        toolbox_box_child_layers = self.bg_layers_toolbox_layers
        toolbox_box_child_collision = self.bg_layers_toolbox_collision
        toolbox_box_child_data = self.bg_layers_toolbox_data
        if Gtk.Buildable.get_name(notebook_page) != "metadata":
            for child in notebook_page.get_children():
                notebook_page.remove(child)
            for child in toolbox_box.get_children():
                toolbox_box.remove(child)
        page_name = Gtk.Buildable.get_name(notebook_page)
        if page_name == "bg_layer2" and self.bma.number_of_layers < 2:
            # Layer 2: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                _("This map only has one layer.\nYou can add a second layer at Map > Settings.")
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name in ["bg_layer1", "bg_layer2"]:
            # Layer 1 / 2
            layers_box_parent = layers_box.get_parent()
            if layers_box_parent:
                typing.cast(Gtk.Container, layers_box_parent).remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)
            toolbox_box_child_layers_parent = toolbox_box_child_layers.get_parent()
            if toolbox_box_child_layers_parent:
                typing.cast(Gtk.Container, toolbox_box_child_layers_parent).remove(toolbox_box_child_layers)
            toolbox_box.pack_start(toolbox_box_child_layers, True, True, 0)
            self._init_chunks_icon_view(0 if page_name == "bg_layer1" else 1)
            self._init_drawer_layer_selected()
        elif page_name == "bg_col1" and self.bma.number_of_collision_layers < 1:
            # Collision 1: Does not exist
            label = Gtk.Label.new(_("This map has no collision.\nYou can add collision at Map > Settings."))
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name == "bg_col2" and self.bma.number_of_collision_layers < 2:
            # Collision 2: Does not exist
            label = Gtk.Label.new(
                _("This map has no second collision layer.\nYou can add a second collision layer at Map > Settings.")
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name in ["bg_col1", "bg_col2"]:
            # Collision 1 / 2
            layers_box_parent = layers_box.get_parent()
            if layers_box_parent:
                typing.cast(Gtk.Container, layers_box_parent).remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)
            toolbox_box_child_layers_parent = toolbox_box_child_layers.get_parent()
            if toolbox_box_child_layers_parent:
                typing.cast(Gtk.Container, toolbox_box_child_layers_parent).remove(toolbox_box_child_collision)
            toolbox_box.pack_start(toolbox_box_child_collision, True, True, 0)
            self._init_drawer_collision_selected(0 if page_name == "bg_col1" else 1)
        elif page_name == "bg_data" and self.bma.unk6 < 1:
            # Data Layer: Does not exist
            label = Gtk.Label.new(_("This map has no data layer.\nYou can add a data layer at Map > Settings."))
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name == "bg_data":
            # Data Layer
            layers_box_parent = layers_box.get_parent()
            if layers_box_parent:
                typing.cast(Gtk.Container, layers_box_parent).remove(layers_box)
            notebook_page.pack_start(layers_box, True, True, 0)
            toolbox_box_child_data_parent = toolbox_box_child_data.get_parent()
            if toolbox_box_child_data_parent:
                typing.cast(Gtk.Container, toolbox_box_child_data_parent).remove(toolbox_box_child_data)
            toolbox_box.pack_start(toolbox_box_child_data, True, True, 0)
            self._init_data_layer_combobox()
            self._init_drawer_data_layer_selected()
        else:
            # Metadata
            # Nothing to do, tab is already finished.
            pass
        self._update_scales()

    def _refresh_metadata(self):
        level_entry = self.module.get_level_entry(self.item_data)
        self.filename_bma.set_text(level_entry.bma_name + BMA_EXT)
        self.filename_bpc.set_text(level_entry.bpc_name + BPC_EXT)
        self.filename_bpl.set_text(level_entry.bpl_name + BPL_EXT)
        for i in range(0, 8):
            if level_entry.bpa_names[i] is not None:
                getattr(self, f"filename_bpa{i + 1}").set_text(level_entry.bpa_names[i] + BPA_EXT)
            else:
                getattr(self, f"filename_bpa{i + 1}").set_text("n/a")

    def _update_scales(self):
        """Update drawers+DrawingArea and iconview+Renderer scales"""
        assert self.bg_draw is not None
        self.bg_draw.set_size_request(
            round(self.bma.map_width_chunks * self.bma.tiling_width * BPC_TILE_DIM * self.scale_factor),
            round(self.bma.map_height_chunks * self.bma.tiling_height * BPC_TILE_DIM * self.scale_factor),
        )
        if self.drawer:
            self.drawer.set_scale(self.scale_factor)
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.set_scale(self.scale_factor)
            # update size
            self.current_icon_view_renderer.set_fixed_size(
                int(BPC_TILE_DIM * 3 * self.scale_factor),
                int(BPC_TILE_DIM * 3 * self.scale_factor),
            )
            icon_view = self.bg_chunks_view
            icon_view.queue_resize()

    def reload_all(self):
        """Reload all image related things"""
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.stop()
        self.bpas = self.module.get_bpas(self.item_data)
        self._init_chunk_imgs()
        if self.drawer:
            self.drawer.reset(
                self.bma,
                self.bpa_durations,
                self.pal_ani_durations,
                self.chunks_surfaces,
            )
        if self.notebook is not None:
            tab = self.notebook.get_nth_page(self.notebook.get_current_page())
            if tab is not None:
                self._init_tab(typing.cast(Gtk.Box, tab))
        self._refresh_metadata()

    def _init_rest_room_note(self):
        mode_10_or_11_level = None
        for level in self.module.get_all_associated_script_maps(self.item_data):
            if (
                level.mapty_enum == Pmd2ScriptLevelMapType.TILESET
                or level.mapty_enum == Pmd2ScriptLevelMapType.FIXED_ROOM
            ):
                mode_10_or_11_level = level
                break
        info_bar = self.editor_rest_room_note
        if mode_10_or_11_level:
            mappings, mappa, fixed, dungeon_bin_context, dungeon_list = self.module.get_mapping_dungeon_assets()
            with dungeon_bin_context as dungeon_bin:
                mapping = resolve_mapping_for_level(
                    mode_10_or_11_level,
                    mappings,
                    mappa,
                    fixed,
                    dungeon_bin,
                    dungeon_list,
                )
            if mapping:
                dma, dpc, dpci, dpl, _, fixed_room = mapping
                self._tileset_drawer_overlay = MapTilesetOverlay(dma, dpc, dpci, dpl, fixed_room)
                if self.drawer:
                    self.drawer.add_overlay(self._tileset_drawer_overlay)
            else:
                info_bar.destroy()
        else:
            info_bar.destroy()

    def _perform_asset_copy(self):
        """Check if assets need to be copied, and if so do so."""
        map_list = self.module.bgs
        entry = self.module.get_level_entry(self.item_data)
        if map_list.find_bma(entry.bma_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bma_name, BMA_EXT)
            self.module.project.create_new_file(new_rom_filename, self.bma, FileType.BMA)
            entry.bma_name = new_name
        if map_list.find_bpl(entry.bpl_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bpl_name, BPL_EXT)
            self.module.project.create_new_file(new_rom_filename, self.bpl, FileType.BPL)
            entry.bpl_name = new_name
        if map_list.find_bpc(entry.bpc_name) > 1:
            self._was_asset_copied = True
            new_name, new_rom_filename = self._find_new_name(entry.bpc_name, BPC_EXT)
            self.module.project.create_new_file(new_rom_filename, self.bpc, FileType.BPC)
            entry.bpc_name = new_name
        for bpa_id, bpa in enumerate(entry.bpa_names):
            if bpa is not None:
                if map_list.find_bpa(bpa) > 1:
                    self._was_asset_copied = True
                    new_name, new_rom_filename = self._find_new_name(bpa, BPA_EXT)
                    self.module.project.create_new_file(new_rom_filename, self.bpas[bpa_id], FileType.BPA)
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
        return (try_name, try_rom_filename)

    @Gtk.Template.Callback()
    def on_btn_about_palettes_clicked(self, w, *args):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _(
                "Map backgrounds can be used as primary or secondary.\nWhen used as primary, the background can have up to 14 palettes, using slots from 0 to 13.\nWhen used as secondary, the background can only have 1 palette, using slot 14, and every palette value will have a new value of (old_value{chr(0xA0)}+{chr(0xA0)}14){chr(0xA0)}mod{chr(0xA0)}16.\nIt is still possible to use palette values above those limits, but this is only in cases where a background needs to reference a palette from the other background.\nNote: in the original game, almost every background is used as primary, the exceptions being mainly the weather (W) backgrounds.\n"
            ),
            title=_("Background Palettes"),
        )
        md.run()
        md.destroy()

    @Gtk.Template.Callback()
    def on_btn_toggle_overlay_rendering_clicked(self, *args):
        assert self._tileset_drawer_overlay is not None
        self._tileset_drawer_overlay.enabled = not self._tileset_drawer_overlay.enabled
