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
import os
from typing import cast, TYPE_CHECKING
from collections.abc import Sequence

import cairo
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType
from range_typed_integers import u16

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.ui_utils import (
    assert_not_none,
    iter_tree_model,
    data_dir,
)
from skytemple.init_locale import LocalePatchedGtkTemplate
from skytemple.module.tiled_img.chunk_editor_data_provider.tile_graphics_provider import (
    AbstractTileGraphicsProvider,
)
from skytemple.module.tiled_img.chunk_editor_data_provider.tile_palettes_provider import (
    AbstractTilePalettesProvider,
)
from skytemple.module.tiled_img.drawer_tiled import DrawerTiledCellRenderer, DrawerTiled
from skytemple_files.common.protocol import TilemapEntryProtocol
from skytemple_files.common.tiled_image import TilemapEntry
from skytemple_files.common.i18n_util import _

if TYPE_CHECKING:
    from skytemple.module.tiled_img.module import TiledImgModule

TILE_DIM = 8


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "tiled_img", "chunk_editor.ui"))
class StChunkEditorDialog(Gtk.Dialog):
    __gtype_name__ = "StChunkEditorDialog"
    module: TiledImgModule
    palette_ids: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    combo_box_palettes_preview: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    icon_view_tiles_in_chunk: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    flip_x: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    flip_y: Gtk.Switch = cast(Gtk.Switch, Gtk.Template.Child())
    combo_box_palettes: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    icon_view_static_tiles: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    icon_view_animated_tiles1: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    icon_view_animated_tiles2: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    icon_view_animated_tiles3: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    icon_view_animated_tiles4: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    tile_number_label: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    icon_view_chunk: Gtk.IconView = cast(Gtk.IconView, Gtk.Template.Child())
    current_tile: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    bpas: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())

    def __init__(
        self,
        parent_window,
        incoming_mappings: Sequence[TilemapEntryProtocol],
        tile_graphics: AbstractTileGraphicsProvider,
        palettes: AbstractTilePalettesProvider,
        pal_ani_durations: int,
        animated_tile_graphics: Sequence[AbstractTileGraphicsProvider | None] | None = None,
        animated_tile_durations=0,
    ):
        super().__init__()

        self.set_attached_to(parent_window)
        self.set_transient_for(parent_window)

        self.tile_graphics = tile_graphics
        self.animated_tile_graphics = animated_tile_graphics
        self.palettes = palettes
        self.animated_tile_durations = animated_tile_durations
        self.pal_ani_durations = pal_ani_durations

        self.current_tile_id = 0
        self.current_tile_drawer: DrawerTiled | None = None

        self.switching_tile = False

        self.bpa_views = [
            self.icon_view_animated_tiles1,
            self.icon_view_animated_tiles2,
            self.icon_view_animated_tiles3,
            self.icon_view_animated_tiles4,
        ]

        self.edited_mappings = []
        for mapping in incoming_mappings:
            self.edited_mappings.append(TilemapEntry.from_int(mapping.to_int()))

        self.tile_surfaces = []
        # For each palette
        for pal in range(0, len(self.palettes.get())):
            all_bpc_tiles_for_current_pal = self.tile_graphics.get_pil(self.palettes.get(), pal)
            tiles_current_pal: list[list[list[cairo.Surface]]] = []
            self.tile_surfaces.append(tiles_current_pal)

            has_pal_ani = self.palettes.is_palette_affected_by_animation(pal)
            len_pal_ani = self.palettes.animation_length() if has_pal_ani else 1

            # BPC tiles
            # For each tile...
            for tile_idx in range(0, self.tile_graphics.count()):
                # For each frame of palette animation...
                pal_ani_tile: list[list[cairo.Surface]] = []
                tiles_current_pal.append(pal_ani_tile)
                for pal_ani in range(0, len_pal_ani):
                    # Switch out the palette with that from the palette animation
                    if has_pal_ani:
                        pal_for_frame = itertools.chain.from_iterable(self.palettes.apply_palette_animations(pal_ani))
                        all_bpc_tiles_for_current_pal.putpalette(pal_for_frame)
                    pal_ani_tile.append(
                        [
                            pil_to_cairo_surface(
                                all_bpc_tiles_for_current_pal.crop(
                                    (
                                        0,
                                        tile_idx * TILE_DIM,
                                        TILE_DIM,
                                        tile_idx * TILE_DIM + TILE_DIM,
                                    )
                                ).convert("RGBA")
                            )
                        ]
                    )
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
                                bpa_ani_tile: list[cairo.Surface] = []
                                pal_ani_tile.append(bpa_ani_tile)
                                # For each frame of BPA animation...
                                for frame in all_bpa_tiles_for_current_pal:
                                    # Switch out the palette with that from the palette animation
                                    if has_pal_ani:
                                        pal_for_frame = itertools.chain.from_iterable(
                                            self.palettes.apply_palette_animations(pal_ani)
                                        )
                                        all_bpc_tiles_for_current_pal.putpalette(pal_for_frame)
                                    bpa_ani_tile.append(
                                        pil_to_cairo_surface(
                                            frame.crop(
                                                (
                                                    0,
                                                    tile_idx * TILE_DIM,
                                                    TILE_DIM,
                                                    tile_idx * TILE_DIM + TILE_DIM,
                                                )
                                            ).convert("RGBA")
                                        )
                                    )

            self.dummy_tile_map = []
            self.current_tile_picker_palette = 0
            for i in range(0, self.tile_graphics.count()):
                self.dummy_tile_map.append(
                    TilemapEntry(
                        idx=i,
                        pal_idx=self.current_tile_picker_palette,
                        flip_x=False,
                        flip_y=False,
                    )
                )

            if self.animated_tile_graphics:
                self.bpa_starts_cursor = len(self.dummy_tile_map)
                self.bpa_starts: list[int | None] = [None, None, None, None]
                for i, ani_tile_g in enumerate(self.animated_tile_graphics):
                    if ani_tile_g is not None:
                        self.bpa_starts[i] = self.bpa_starts_cursor
                        self.current_tile_picker_palette = 0
                        for j in range(0, ani_tile_g.count()):
                            self.dummy_tile_map.append(
                                TilemapEntry(
                                    idx=self.bpa_starts_cursor + j,
                                    pal_idx=self.current_tile_picker_palette,
                                    flip_x=False,
                                    flip_y=False,
                                )
                            )
                        self.bpa_starts_cursor += ani_tile_g.count()

    def show_dialog(self):
        # Init palette store
        for idx in range(0, self.palettes.number_of_palettes()):
            self.palette_ids.append([idx])
        self.combo_box_palettes_preview.set_active(0)

        self._init_icon_view_static_tiles()
        self._init_bpas()
        self._init_current_tile()
        self._init_icon_view_tiles_in_chunk()
        self._init_icon_view_chunk()

        self.resize(1420, 716)

        resp = self.run()
        self.destroy()

        if resp == ResponseType.OK:
            return self.edited_mappings
        return None

    @Gtk.Template.Callback()
    def on_combo_box_palettes_preview_changed(self, wdg: Gtk.ComboBox):
        self.current_tile_picker_palette = wdg.get_active()
        for m in self.dummy_tile_map:
            m.pal_idx = self.current_tile_picker_palette

    @Gtk.Template.Callback()
    def on_flip_x_state_set(self, wdg, state):
        self.edited_mappings[self.current_tile_id].flip_x = state

    @Gtk.Template.Callback()
    def on_flip_y_state_set(self, wdg, state):
        self.edited_mappings[self.current_tile_id].flip_y = state

    @Gtk.Template.Callback()
    def on_combo_box_palettes_changed(self, wdg: Gtk.ComboBox):
        self.edited_mappings[self.current_tile_id].pal_idx = wdg.get_active()

    def on_icon_view_chunk_selection_changed(self, icon_view: Gtk.IconView):
        """Fill the icon view containing the 3x3 tiles for the current chunk"""
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            first_tile_id = model[treeiter[0]][0]
            store: Gtk.ListStore = cast(
                Gtk.ListStore,
                assert_not_none(self.icon_view_tiles_in_chunk.get_model()),
            )
            store.clear()
            for idx in range(first_tile_id, first_tile_id + 9):
                store.append([idx])

            first_iter = store.get_iter_first()
            if first_iter is not None:
                self.icon_view_tiles_in_chunk.select_path(store.get_path(first_iter))

    def on_icon_view_tiles_in_chunk_selection_changed(self, icon_view: Gtk.IconView):
        """Change the current edited tile view"""
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            self.current_tile_id = model[treeiter[0]][0]

            mapping = self.edited_mappings[self.current_tile_id]
            if self.current_tile_drawer:
                self.current_tile_drawer.set_tile_mappings([mapping])

            self.flip_x.set_active(mapping.flip_x)
            self.flip_y.set_active(mapping.flip_y)
            self.combo_box_palettes.set_active(mapping.pal_idx)

            # Also update the selected tile
            self.switching_tile = True
            if mapping.idx < self.tile_graphics.count():
                store = cast(
                    Gtk.ListStore,
                    assert_not_none(self.icon_view_static_tiles.get_model()),
                )
                for e in iter_tree_model(store):
                    if e[0] == mapping.idx:
                        self.icon_view_static_tiles.select_path(e.path)
                        self.icon_view_static_tiles.scroll_to_path(e.path, True, 0.5, 0.5)
                        for bpa_view in self.bpa_views:
                            if bpa_view:
                                bpa_view.unselect_all()
                        break
            else:
                # BPA case
                self.icon_view_static_tiles.unselect_all()
                for i, bpa_view in enumerate(self.bpa_views):
                    assert self.animated_tile_graphics is not None
                    if self.animated_tile_graphics[i]:
                        if bpa_view and mapping.idx >= assert_not_none(self.bpa_starts[i]):
                            store = cast(Gtk.ListStore, assert_not_none(bpa_view.get_model()))
                            for e in iter_tree_model(store):
                                if e[0] == mapping.idx:
                                    bpa_view.select_path(e.path)
                                    bpa_view.scroll_to_path(e.path, True, 0.5, 0.5)
                            break
            self.switching_tile = False

    def on_icon_view_static_tiles_selection_changed(self, icon_view: Gtk.IconView):
        model, treeiter = icon_view.get_model(), icon_view.get_selected_items()
        if model is not None and treeiter is not None and treeiter != []:
            selected_bpc_tile = model[treeiter[0]][0]
            if not self.switching_tile:
                self.edited_mappings[self.current_tile_id].idx = selected_bpc_tile
                self.combo_box_palettes.set_active(self.current_tile_picker_palette)
                # == self.edited_mappings[self.current_tile_id].pal_idx = self.current_tile_picker_palette
            self.tile_number_label.set_text(str(selected_bpc_tile))

    @Gtk.Template.Callback()
    def on_add_chunk_clicked(self, *args):
        m = cast(
            Gtk.ListStore,
            assert_not_none(self.icon_view_chunk.get_model()),
        )
        m.append([len(self.edited_mappings)])
        for i in range(len(self.edited_mappings), len(self.edited_mappings) + 9):
            self.edited_mappings.append(TilemapEntry.from_int(u16(0)))

    def _init_icon_view_chunk(self):
        """Fill the icon view containing all the chunks"""
        self.icon_view_chunk.set_selection_mode(Gtk.SelectionMode.BROWSE)
        renderer = DrawerTiledCellRenderer(
            self.icon_view_chunk,
            self.animated_tile_durations,
            self.pal_ani_durations,
            True,
            self.edited_mappings,
            self.tile_surfaces,
            1,
        )

        store = Gtk.ListStore(int)
        self.icon_view_chunk.set_model(store)
        self.icon_view_chunk.pack_start(renderer, True)
        self.icon_view_chunk.add_attribute(renderer, "tileidx", 0)
        self.icon_view_chunk.connect("selection-changed", self.on_icon_view_chunk_selection_changed)

        for idx in range(0, len(self.edited_mappings), 9):
            store.append([idx])

        iter_first = store.get_iter_first()
        if iter_first is not None:
            self.icon_view_chunk.select_path(store.get_path(iter_first))
        renderer.start()

    def _init_icon_view_tiles_in_chunk(self):
        """Init the icon view containing the 3x3 tiles for the current chunk"""
        self.icon_view_tiles_in_chunk.set_selection_mode(Gtk.SelectionMode.BROWSE)
        renderer = DrawerTiledCellRenderer(
            self.icon_view_tiles_in_chunk,
            self.animated_tile_durations,
            self.pal_ani_durations,
            False,
            self.edited_mappings,
            self.tile_surfaces,
            3,
        )

        store = Gtk.ListStore(int)
        self.icon_view_tiles_in_chunk.set_model(store)
        self.icon_view_tiles_in_chunk.pack_start(renderer, True)
        self.icon_view_tiles_in_chunk.add_attribute(renderer, "tileidx", 0)
        self.icon_view_tiles_in_chunk.connect("selection-changed", self.on_icon_view_tiles_in_chunk_selection_changed)

        renderer.start()

    def _init_current_tile(self):
        self.current_tile.set_size_request(10 * TILE_DIM, 10 * TILE_DIM)

        self.current_tile_drawer = DrawerTiled(
            self.current_tile,
            [self.edited_mappings[0]],
            self.animated_tile_durations,
            self.pal_ani_durations,
            self.tile_surfaces,
        )
        self.current_tile_drawer.scale = 10
        self.current_tile_drawer.start()

    def _init_icon_view_static_tiles(self):
        """Fill the icon view containing all static tiles"""
        self.icon_view_static_tiles.set_selection_mode(Gtk.SelectionMode.BROWSE)

        renderer = DrawerTiledCellRenderer(
            self.icon_view_static_tiles,
            self.animated_tile_durations,
            self.pal_ani_durations,
            False,
            self.dummy_tile_map,
            self.tile_surfaces,
            3,
        )

        store = Gtk.ListStore(int, str)
        self.icon_view_static_tiles.set_model(store)
        self.icon_view_static_tiles.pack_start(renderer, True)
        self.icon_view_static_tiles.add_attribute(renderer, "tileidx", 0)
        self.icon_view_static_tiles.set_text_column(1)
        self.icon_view_static_tiles.connect("selection-changed", self.on_icon_view_static_tiles_selection_changed)

        for idx in range(0, self.tile_graphics.count()):
            store.append([idx, str(idx)])

        renderer.start()

    def _init_bpas(self):
        if self.animated_tile_graphics is None:
            parent = cast(Gtk.Container, assert_not_none(self.bpas.get_parent()))
            parent.remove(self.bpas)
            return
        for i, ani_tile_g in enumerate(self.animated_tile_graphics):
            view = self.bpa_views[i]
            if ani_tile_g is None:
                sw: Gtk.ScrolledWindow = cast(Gtk.ScrolledWindow, assert_not_none(view.get_parent()))
                sw.remove(view)
                label = Gtk.Label.new(
                    _("BPA slot is empty.\n\nGo to Tiles > Animated Tiles to\nmanage animated tiles.")
                )
                label.set_vexpand(True)
                label.show()
                sw.add(label)
            else:
                view.set_selection_mode(Gtk.SelectionMode.BROWSE)
                renderer = DrawerTiledCellRenderer(
                    view,
                    self.animated_tile_durations,
                    self.pal_ani_durations,
                    False,
                    self.dummy_tile_map,
                    self.tile_surfaces,
                    3,
                )

                store = Gtk.ListStore(int, str)
                view.set_model(store)
                view.pack_start(renderer, True)
                view.add_attribute(renderer, "tileidx", 0)
                view.set_text_column(1)
                view.connect(
                    "selection-changed",
                    self.on_icon_view_static_tiles_selection_changed,
                )
                for idx in range(
                    self.bpa_starts[i],  # type: ignore
                    self.bpa_starts[i] + ani_tile_g.count(),  # type: ignore
                ):
                    store.append([idx, str(idx)])

                renderer.start()
