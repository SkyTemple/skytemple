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
import os
from typing import Union, List, Optional

from gi.repository import Gtk
from gi.repository.Gtk import ResponseType, IconView, ScrolledWindow

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.ui_utils import APP, make_builder
from skytemple.module.tiled_img.chunk_editor_data_provider.tile_graphics_provider import AbstractTileGraphicsProvider
from skytemple.module.tiled_img.chunk_editor_data_provider.tile_palettes_provider import AbstractTilePalettesProvider
from skytemple.module.tiled_img.drawer_tiled import DrawerTiledCellRenderer, DrawerTiled
from skytemple_files.common.tiled_image import TilemapEntry
from skytemple_files.common.i18n_util import f, _
bpa_views = [
    'icon_view_animated_tiles1', 'icon_view_animated_tiles2',
    'icon_view_animated_tiles3', 'icon_view_animated_tiles4'
]
TILE_DIM = 8


class ChunkEditorController:
    def __init__(self,
                 parent_window, incoming_mappings: List[TilemapEntry],
                 tile_graphics: AbstractTileGraphicsProvider,
                 palettes: AbstractTilePalettesProvider,
                 pal_ani_durations: int,
                 animated_tile_graphics: List[Optional[AbstractTileGraphicsProvider]] = None,
                 animated_tile_durations=0):
        path = os.path.abspath(os.path.dirname(__file__))

        self.builder = make_builder(os.path.join(path, 'chunk_editor.glade'))

        self.dialog: Gtk.Dialog = self.builder.get_object('map_bg_chunk_editor')
        self.dialog.set_attached_to(parent_window)
        self.dialog.set_transient_for(parent_window)

        self.tile_graphics = tile_graphics
        self.animated_tile_graphics = animated_tile_graphics
        self.palettes = palettes
        self.animated_tile_durations = animated_tile_durations
        self.pal_ani_durations = pal_ani_durations

        self.current_tile_id = 0
        self.current_tile_drawer: DrawerTiled = None

        self.switching_tile = False

        self.edited_mappings = []
        for mapping in incoming_mappings:
            self.edited_mappings.append(TilemapEntry.from_int(mapping.to_int()))

        self.tile_surfaces = []
        # For each palette
        for pal in range(0, len(self.palettes.get())):
            all_bpc_tiles_for_current_pal = self.tile_graphics.get_pil(self.palettes.get(), pal)
            tiles_current_pal = []
            self.tile_surfaces.append(tiles_current_pal)

            has_pal_ani = self.palettes.is_palette_affected_by_animation(pal)
            len_pal_ani = self.palettes.animation_length() if has_pal_ani else 1

            # BPC tiles
            # For each tile...
            for tile_idx in range(0, self.tile_graphics.count()):
                # For each frame of palette animation...
                pal_ani_tile = []
                tiles_current_pal.append(pal_ani_tile)
                for pal_ani in range(0, len_pal_ani):
                    # Switch out the palette with that from the palette animation
                    if has_pal_ani:
                        pal_for_frame = itertools.chain.from_iterable(self.palettes.apply_palette_animations(pal_ani))
                        all_bpc_tiles_for_current_pal.putpalette(pal_for_frame)
                    pal_ani_tile.append([pil_to_cairo_surface(
                        all_bpc_tiles_for_current_pal.crop(
                            (0, tile_idx * TILE_DIM, TILE_DIM, tile_idx * TILE_DIM + TILE_DIM)
                        ).convert('RGBA')
                    )])
            # BPA tiles
            # For each BPA...
            if self.animated_tile_graphics is not None:
                for ani_tile_g in self.animated_tile_graphics:
                    if ani_tile_g is not None:
                        all_bpa_tiles_for_current_pal = ani_tile_g.get_pil(self.palettes.get(), pal)
                        # For each tile...
                        for tile_idx in range(0, ani_tile_g.count()):
                            pal_ani_tile = []
                            tiles_current_pal.append(pal_ani_tile)
                            # For each frame of palette animation...
                            for pal_ani in range(0, len_pal_ani):
                                bpa_ani_tile = []
                                pal_ani_tile.append(bpa_ani_tile)
                                # For each frame of BPA animation...
                                for frame in all_bpa_tiles_for_current_pal:
                                    # Switch out the palette with that from the palette animation
                                    if has_pal_ani:
                                        pal_for_frame = itertools.chain.from_iterable(self.palettes.apply_palette_animations(pal_ani))
                                        all_bpc_tiles_for_current_pal.putpalette(pal_for_frame)
                                    bpa_ani_tile.append(pil_to_cairo_surface(
                                        frame.crop(
                                            (0, tile_idx * TILE_DIM, TILE_DIM, tile_idx * TILE_DIM + TILE_DIM)
                                        ).convert('RGBA')
                                    ))

            self.builder.connect_signals(self)

            self.dummy_tile_map = []
            self.current_tile_picker_palette = 0
            for i in range(0, self.tile_graphics.count()):
                self.dummy_tile_map.append(TilemapEntry(
                    idx=i,
                    pal_idx=self.current_tile_picker_palette,
                    flip_x=False,
                    flip_y=False
                ))

            if self.animated_tile_graphics:
                self.bpa_starts_cursor = len(self.dummy_tile_map)
                self.bpa_starts = [None, None, None, None]
                for i, ani_tile_g in enumerate(self.animated_tile_graphics):
                    if ani_tile_g is not None:
                        self.bpa_starts[i] = self.bpa_starts_cursor
                        self.current_tile_picker_palette = 0
                        for j in range(0, ani_tile_g.count()):
                            self.dummy_tile_map.append(TilemapEntry(
                                idx=self.bpa_starts_cursor + j,
                                pal_idx=self.current_tile_picker_palette,
                                flip_x=False,
                                flip_y=False
                            ))
                        self.bpa_starts_cursor += ani_tile_g.count()

    def show(self):

        # Init palette store
        store = self.builder.get_object('palette_ids')
        for idx in range(0, self.palettes.number_of_palettes()):
            store.append([idx])
        self.builder.get_object('combo_box_palettes_preview').set_active(0)

        self._init_icon_view_static_tiles()
        self._init_bpas()
        self._init_current_tile()
        self._init_icon_view_tiles_in_chunk()
        self._init_icon_view_chunk()

        self.dialog.resize(1420, 716)

        resp = self.dialog.run()
        self.dialog.destroy()

        if resp == ResponseType.OK:
            return self.edited_mappings
        return None

    def on_combo_box_palettes_preview_changed(self, wdg: Gtk.ComboBox):
        self.current_tile_picker_palette = wdg.get_active()
        for m in self.dummy_tile_map:
            m.pal_idx = self.current_tile_picker_palette

    def on_flip_x_state_set(self, wdg, state):
        self.edited_mappings[self.current_tile_id].flip_x = state

    def on_flip_y_state_set(self, wdg, state):
        self.edited_mappings[self.current_tile_id].flip_y = state

    def on_combo_box_palettes_changed(self, wdg: Gtk.ComboBox):
        self.edited_mappings[self.current_tile_id].pal_idx = wdg.get_active()

    def on_icon_view_chunk_selection_changed(self, icon_view: IconView):
        """Fill the icon view containing the 3x3 tiles for the current chunk"""
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            first_tile_id = model[treeiter][0]
            icon_view_tiles_in_chunk: IconView = self.builder.get_object(f'icon_view_tiles_in_chunk')
            store: Gtk.ListStore = icon_view_tiles_in_chunk.get_model()
            store.clear()
            for idx in range(first_tile_id, first_tile_id + 9):
                store.append([idx])

            icon_view_tiles_in_chunk.select_path(store.get_path(store.get_iter_first()))

    def on_icon_view_tiles_in_chunk_selection_changed(self, icon_view: IconView):
        """Change the current edited tile view"""
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            self.current_tile_id = model[treeiter][0]

            mapping = self.edited_mappings[self.current_tile_id]
            self.current_tile_drawer.set_tile_mappings([mapping])

            self.builder.get_object('flip_x').set_active(mapping.flip_x)
            self.builder.get_object('flip_y').set_active(mapping.flip_y)
            cb: Gtk.ComboBox = self.builder.get_object('combo_box_palettes')
            cb.set_active(mapping.pal_idx)

            # Also update the selected tile
            self.switching_tile = True
            icon_view_static_tiles: IconView = self.builder.get_object(f'icon_view_static_tiles')
            if mapping.idx < self.tile_graphics.count():
                store: Gtk.ListStore = icon_view_static_tiles.get_model()
                for e in store:
                    if e[0] == mapping.idx:
                        icon_view_static_tiles.select_path(e.path)
                        icon_view_static_tiles.scroll_to_path(e.path, True, 0.5, 0.5)
                        for bpa_view in bpa_views:
                            obj = self.builder.get_object(bpa_view)
                            if obj:
                                obj.unselect_all()
                        break
            else:
                # BPA case
                icon_view_static_tiles.unselect_all()
                for i, bpa_view in enumerate(bpa_views):
                    obj = self.builder.get_object(bpa_view)
                    if self.animated_tile_graphics[i]:
                        if obj and mapping.idx >= self.bpa_starts[i]:
                            store: Gtk.ListStore = obj.get_model()
                            for e in store:
                                if e[0] == mapping.idx:
                                    obj.select_path(e.path)
                                    obj.scroll_to_path(e.path, True, 0.5, 0.5)
                            break
            self.switching_tile = False

    def on_icon_view_static_tiles_selection_changed(self, icon_view: IconView):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            selected_bpc_tile = model[treeiter][0]
            if not self.switching_tile:
                self.edited_mappings[self.current_tile_id].idx = selected_bpc_tile
                self.builder.get_object(f'combo_box_palettes').set_active(self.current_tile_picker_palette)
                # == self.edited_mappings[self.current_tile_id].pal_idx = self.current_tile_picker_palette
            self.builder.get_object(f'tile_number_label').set_text(str(selected_bpc_tile))

    def on_add_chunk_clicked(self, *args):
        m = self.builder.get_object(f'icon_view_chunk').get_model()
        m.append([len(self.edited_mappings)])
        for i in range(len(self.edited_mappings), len(self.edited_mappings)+9):
            self.edited_mappings.append(TilemapEntry.from_int(0))

    def _init_icon_view_chunk(self):
        """Fill the icon view containing all the chunks"""
        icon_view: IconView = self.builder.get_object(f'icon_view_chunk')
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        renderer = DrawerTiledCellRenderer(
            icon_view, self.animated_tile_durations, self.pal_ani_durations, True, self.edited_mappings, self.tile_surfaces, 1
        )

        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(renderer, True)
        icon_view.add_attribute(renderer, 'tileidx', 0)
        icon_view.connect('selection-changed', self.on_icon_view_chunk_selection_changed)

        for idx in range(0, len(self.edited_mappings), 9):
            store.append([idx])

        icon_view.select_path(store.get_path(store.get_iter_first()))
        renderer.start()

    def _init_icon_view_tiles_in_chunk(self):
        """Init the icon view containing the 3x3 tiles for the current chunk"""
        icon_view: IconView = self.builder.get_object(f'icon_view_tiles_in_chunk')
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)
        renderer = DrawerTiledCellRenderer(
            icon_view, self.animated_tile_durations, self.pal_ani_durations, False, self.edited_mappings, self.tile_surfaces, 3
        )

        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(renderer, True)
        icon_view.add_attribute(renderer, 'tileidx', 0)
        icon_view.connect('selection-changed', self.on_icon_view_tiles_in_chunk_selection_changed)

        renderer.start()

    def _init_current_tile(self):
        current_tile: Gtk.DrawingArea = self.builder.get_object('current_tile')

        current_tile.set_size_request(
            10 * TILE_DIM,
            10 * TILE_DIM
        )

        self.current_tile_drawer = DrawerTiled(
            current_tile, [self.edited_mappings[0]], self.animated_tile_durations, self.pal_ani_durations, self.tile_surfaces
        )
        self.current_tile_drawer.scale = 10
        self.current_tile_drawer.start()

    def _init_icon_view_static_tiles(self):
        """Fill the icon view containing all static tiles"""
        icon_view: IconView = self.builder.get_object(f'icon_view_static_tiles')
        icon_view.set_selection_mode(Gtk.SelectionMode.BROWSE)

        renderer = DrawerTiledCellRenderer(
            icon_view, self.animated_tile_durations, self.pal_ani_durations, False, self.dummy_tile_map, self.tile_surfaces, 3
        )

        store = Gtk.ListStore(int, str)
        icon_view.set_model(store)
        icon_view.pack_start(renderer, True)
        icon_view.add_attribute(renderer, 'tileidx', 0)
        icon_view.set_text_column(1)
        icon_view.connect('selection-changed', self.on_icon_view_static_tiles_selection_changed)

        for idx in range(0, self.tile_graphics.count()):
            store.append([idx, str(idx)])

        renderer.start()

    def _init_bpas(self):
        if self.animated_tile_graphics is None:
            bpas_box = self.builder.get_object('bpas')
            parent = bpas_box.get_parent()
            parent.remove(bpas_box)
            return
        for i, ani_tile_g in enumerate(self.animated_tile_graphics):
            view: IconView = self.builder.get_object(bpa_views[i])
            if ani_tile_g is None:
                sw: ScrolledWindow = view.get_parent()
                sw.remove(view)
                label = Gtk.Label.new(_('BPA slot is empty.\n\nGo to Tiles > Animated Tiles to\nmanage animated tiles.'))
                label.set_vexpand(True)
                label.show()
                sw.add(label)
            else:
                view.set_selection_mode(Gtk.SelectionMode.BROWSE)
                renderer = DrawerTiledCellRenderer(
                    view, self.animated_tile_durations, self.pal_ani_durations, False, self.dummy_tile_map, self.tile_surfaces, 3
                )

                store = Gtk.ListStore(int, str)
                view.set_model(store)
                view.pack_start(renderer, True)
                view.add_attribute(renderer, 'tileidx', 0)
                view.set_text_column(1)
                view.connect('selection-changed', self.on_icon_view_static_tiles_selection_changed)

                for idx in range(self.bpa_starts[i], self.bpa_starts[i] + ani_tile_g.count()):
                    store.append([idx, str(idx)])

                renderer.start()
