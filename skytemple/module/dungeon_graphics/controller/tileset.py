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
import math
import os
import shutil
import sys
import webbrowser
from collections import OrderedDict
from functools import partial
from typing import TYPE_CHECKING, List, Iterable, Callable

import cairo

from skytemple.core.error_handler import display_error
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import BinaryName
from skytemple.core.ui_utils import add_dialog_xml_filter
from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_graphics_provider import DungeonTilesProvider
from skytemple.module.dungeon_graphics.chunk_editor_data_provider.tile_palettes_provider import DungeonPalettesProvider
from skytemple.module.dungeon_graphics.controller.bg_menu import BgMenuController
from skytemple.module.tiled_img.dialog_controller.chunk_editor import ChunkEditorController
from skytemple_dtef import get_template_file
from skytemple_dtef.explorers_dtef import ExplorersDtef, VAR0_FN, VAR2_FN, VAR1_FN
from skytemple_dtef.explorers_dtef_importer import ExplorersDtefImporter
from skytemple_files.common.xml_util import prettify
from skytemple_files.hardcoded.dungeons import SecondaryTerrainTableEntry, HardcodedDungeons

try:
    from PIL import Image
except ImportError:
    from pil import Image
from gi.repository import Gtk

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.module.dungeon_graphics.dungeon_chunk_drawer import DungeonChunkCellDrawer
from skytemple_files.common.util import lcm, chunks
from skytemple_files.graphics.dma.model import Dma, DmaExtraType, DmaType
from skytemple_files.graphics.dpc.model import Dpc
from skytemple_files.graphics.dpci.model import Dpci
from skytemple_files.graphics.dpl.model import Dpl
from skytemple_files.graphics.dpla.model import Dpla
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.dungeon_graphics.module import DungeonGraphicsModule


URL_HELP = 'https://github.com/SkyTemple/skytemple-dtef/blob/main/docs/SkyTemple.rst'


class TilesetController(AbstractController):
    _last_open_tab_id = 0
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
        self.dtef = None

        self.menu_controller = BgMenuController(self)

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'tileset.glade')
        self._init_rules()
        self._init_rule_icon_views()
        self._init_chunk_picker_icon_view()
        self._init_secondary_terrain()
        self.builder.connect_signals(self)
        editor = self.builder.get_object('editor')
        root = self.builder.get_object('editor_root')
        root.set_current_page(self.__class__._last_open_tab_id)
        self.on_editor_root_switch_page(None, None, self.__class__._last_open_tab_id)
        self.builder.get_object('label_tileset_name').set_text(f(_('Dungeon Tileset {self.item_id} Rules')))
        self.builder.get_object('label_tileset_name2').set_text(f(_('Dungeon Tileset {self.item_id}')))
        return editor

    def on_editor_root_switch_page(self, w, p, pnum, *args):
        self.__class__._last_open_tab_id = pnum
        if pnum == 1:
            for renderer in self.current_icon_view_renderers:
                renderer.start()
        else:
            self._load_dtef_rendering()
            for renderer in self.current_icon_view_renderers:
                renderer.stop()

    # SIMPLE MODE

    def on_btn_import_clicked(self, *args):
        md = SkyTempleMessageDialog(MainController.window(),
                                    Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                    Gtk.ButtonsType.OK, _("To import select the XML file in the DTEF tileset package. If it "
                                                          "is still zipped, unzip it first."),
                                    title="SkyTemple")
        md.run()
        md.destroy()

        dialog = Gtk.FileChooserNative.new(
            _("Import dungeon tileset..."),
            MainController.window(),
            Gtk.FileChooserAction.OPEN,
            None, None
        )

        filter = Gtk.FileFilter()
        filter.set_name(_("DTEF XML document (*.dtef.xml)"))
        filter.add_pattern("*.dtef.xml")
        dialog.add_filter(filter)
        add_dialog_xml_filter(dialog)

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                dirname = os.path.dirname(fn)
                fn_xml = fn
                fn_var0 = os.path.join(dirname, VAR0_FN)
                fn_var1 = os.path.join(dirname, VAR1_FN)
                fn_var2 = os.path.join(dirname, VAR2_FN)
                dtef_importer = ExplorersDtefImporter(self.dma, self.dpc, self.dpci, self.dpl, self.dpla)
                dtef_importer.do_import(
                    dirname, fn_xml, fn_var0, fn_var1, fn_var2
                )

                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                            Gtk.ButtonsType.OK, _("The tileset was successfully imported."),
                                            title=_("Success!"), is_success=True)
                md.run()
                md.destroy()
                self.mark_as_modified()
                MainController.reload_view()
            except BaseException as e:
                display_error(
                    sys.exc_info(),
                    str(e),
                    _("Error importing the tileset.")
                )

    def on_btn_export_clicked(self, *args):
        dialog = Gtk.FileChooserNative.new(
            _("Export dungeon tileset..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            try:
                # Write XML
                with open(os.path.join(fn, 'tileset.dtef.xml'), 'w') as f:
                    f.write(prettify(self.dtef.get_xml()))
                # Write Tiles
                var0, var1, var2, rest = self.dtef.get_tiles()
                var0fn, var1fn, var2fn, restfn = self.dtef.get_filenames()
                var0.save(os.path.join(fn, var0fn))
                var1.save(os.path.join(fn, var1fn))
                var2.save(os.path.join(fn, var2fn))
                rest.save(os.path.join(fn, restfn))
                shutil.copy(get_template_file(), os.path.join(fn, 'template.png'))

                md = SkyTempleMessageDialog(MainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
                                            Gtk.ButtonsType.OK, _("The tileset was successfully exported."),
                                            title=_("Success!"), is_success=True)
                md.run()
                md.destroy()
            except BaseException as e:
                display_error(
                    sys.exc_info(),
                    str(e),
                    _("Error exporting the tileset.")
                )

    def on_btn_help_clicked(self, *args):
        webbrowser.open_new_tab(URL_HELP)

    # END SIMPLE MODE

    def on_men_chunks_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_edit_activate()

    def on_men_chunks_export_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_export_activate()

    def on_men_chunks_import_activate(self, *args):
        self.menu_controller.on_men_chunks_layer1_import_activate()

    def on_men_tiles_export_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_export_activate()

    def on_men_tiles_import_activate(self, *args):
        self.menu_controller.on_men_tiles_layer1_import_activate()

    def on_men_palettes_edit_activate(self, *args):
        self.menu_controller.on_men_palettes_edit_activate()

    def on_men_palettes_ani_settings_activate(self, *args):
        self.menu_controller.on_men_palettes_ani_settings_activate()

    def on_men_palettes_ani_edit_11_activate(self, *args):
        self.menu_controller.edit_palette_ani(0)

    def on_men_palettes_ani_edit_12_activate(self, *args):
        self.menu_controller.edit_palette_ani(1)

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

    def on_secondary_terrain_type_changed(self, w: Gtk.ComboBox):
        idx = w.get_active()
        static = self.module.project.get_rom_module().get_static_data()
        secondary_terrains = HardcodedDungeons.get_secondary_terrains(
            self.module.project.get_binary(BinaryName.ARM9), static
        )
        secondary_terrains[self.item_id] = SecondaryTerrainTableEntry(idx)

        def update(arm9):
            HardcodedDungeons.set_secondary_terrains(secondary_terrains, arm9, static)
        self.module.project.modify_binary(BinaryName.ARM9, update)

        self.mark_as_modified()

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
        self.module.mark_as_modified(self.item_id, False)

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

        self._init_an_icon_view("rules_chunk_picker", init_store, True, True)

    def _init_an_icon_view(self, name: str, init_store: Callable[[Gtk.ListStore], None], selection_draw_solid, select_first=False):
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
            self.renderer = None
            for child in icon_view.get_cells():
                if isinstance(child, DungeonChunkCellDrawer):
                    self.renderer = child
                    break

        init_store(store)
        if select_first:
            icon_view.select_path(store.get_path(store.get_iter_first()))

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

    def _load_dtef_rendering(self):
        self.dtef = ExplorersDtef(self.dma, self.dpc, self.dpci, self.dpl, self.dpla)
        box: Gtk.Box = self.builder.get_object('dungeon_image_placeholder')
        for child in box:
            box.remove(child)
        image: Gtk.Image = Gtk.Image.new_from_surface(pil_to_cairo_surface(self.dtef.get_tiles()[0].convert('RGBA')))
        box.pack_start(image, True, True, 0)
        box.show_all()

    def _init_secondary_terrain(self):
        w: Gtk.ComboBox = self.builder.get_object('secondary_terrain_type')
        s: Gtk.ListStore = w.get_model()
        for v in SecondaryTerrainTableEntry:
            s.append([v.value, v.name.capitalize()])

        secondary_terrain = HardcodedDungeons.get_secondary_terrains(
            self.module.project.get_binary(BinaryName.ARM9), self.module.project.get_rom_module().get_static_data()
        )[self.item_id]
        w.set_active(secondary_terrain.value)

