from typing import TYPE_CHECKING

import gi
from gi.repository import Gtk, Gdk
from gi.repository.GObject import TYPE_PYOBJECT
from gi.repository.GdkPixbuf import Pixbuf, Colorspace
from gi.repository.Gtk import *

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.module.map_bg.controller.bg_menu import BgMenuController
from skytemple.module.map_bg.drawer import Drawer, DrawerCellRenderer, DrawerInteraction
from skytemple_files.graphics.bma.model import MASK_PAL
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM

if TYPE_CHECKING:
    from skytemple.module.map_bg.module import MapBgModule


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

        self.chunks_layer0 = None
        self.chunks_layer1 = None

        # Cairo surfaces for each tile in each layer for each frame
        # chunks_surfaces[layer_number][palette_animation_frame][frame][chunk_idx]
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

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'map_bg.glade')
        self.notebook = self.builder.get_object('bg_notebook')
        self._init_drawer()
        self._init_tab(self.notebook.get_nth_page(self.notebook.get_current_page()))
        self.builder.connect_signals(self)
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
            chunk_mapping_idx = int(chunk_y * self.bma.map_width_chunks + chunk_x)
            # Set chunk at current position
            self.mark_as_modified()
            if self.current_chunks_icon_layer == 0 and chunk_mapping_idx <= len(self.bma.layer0):
                self.bma.layer0[chunk_mapping_idx] = self.drawer.get_selected_chunk_id()
            elif self.current_chunks_icon_layer == 1 and chunk_mapping_idx <= len(self.bma.layer1):
                self.bma.layer1[chunk_mapping_idx] = self.drawer.get_selected_chunk_id()

    def _set_col_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            tile_idx = int(tile_y * self.bma.map_width_camera + tile_x)
            max_tile = self.bma.map_width_camera * self.bma.map_height_camera
            # Set collision at current position
            self.mark_as_modified()
            if self.drawer.get_edited_collision() == 0 and tile_idx <= max_tile:
                self.bma.collision[tile_idx] = self.drawer.get_interaction_col_solid()
            elif self.drawer.get_edited_collision() == 1 and tile_idx <= max_tile:
                self.bma.collision2[tile_idx] = self.drawer.get_interaction_col_solid()

    def _set_data_at_pos(self, mouse_x, mouse_y):
        if self.drawer:
            tile_x = int(mouse_x / BPC_TILE_DIM)
            tile_y = int(mouse_y / BPC_TILE_DIM)
            tile_idx = int(tile_y * self.bma.map_width_camera + tile_x)
            max_tile = self.bma.map_width_camera * self.bma.map_height_camera
            # Set data value at current position
            self.mark_as_modified()
            if tile_idx <= max_tile:
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

    def on_men_chunks_edit_activate(self, *args):
        self.menu_controller.on_men_chunks_edit_activate()

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

    def _init_chunk_imgs(self):
        """(Re)-draw the chunk images"""
        if self.bpc.number_of_layers > 1:
            self.chunks_layer0 = self.bpc.chunks_animated_to_pil(1, self.bpl.palettes, self.bpas, 1)
            self.chunks_layer1 = self.bpc.chunks_animated_to_pil(0, self.bpl.palettes, self.bpas, 1)
            number_of_chunks = [self.bpc.layers[1].chunk_tilemap_len, self.bpc.layers[0].chunk_tilemap_len]
        else:
            self.chunks_layer0 = self.bpc.chunks_animated_to_pil(0, self.bpl.palettes, self.bpas, 1)
            self.chunks_layer1 = None
            number_of_chunks = [self.bpc.layers[0].chunk_tilemap_len]

        layers = [self.chunks_layer0]
        if self.chunks_layer1 is not None:
            layers.append(self.chunks_layer1)

        self.chunks_surfaces = []
        chunk_width = self.bma.tiling_width * BPC_TILE_DIM
        chunk_height = self.bma.tiling_height * BPC_TILE_DIM
        # For each layer...
        for layer_idx, layer in enumerate(layers):
            chunks_current_layer = []
            # For each frame of palette animation...
            # TODO: Palette animation
            for pal_ani in range(0, 1):
                chunks_current_pal = []
                # For each frame of tile animation...
                for img in layer:
                    # Remove alpha first
                    img_mask = img.copy()
                    img_mask.putpalette(MASK_PAL)
                    img_mask = img_mask.convert('1')
                    img = img.convert('RGBA')
                    img.putalpha(img_mask)

                    chunks_current_frame = []
                    # For each chunk...
                    for chunk_idx in range(0, number_of_chunks[layer_idx]):
                        chunks_current_frame.append(pil_to_cairo_surface(
                            img.crop((0, chunk_idx * chunk_width, chunk_width, chunk_idx * chunk_width + chunk_height))
                        ))
                    chunks_current_pal.append(chunks_current_frame)
                chunks_current_layer.append(chunks_current_pal)
            self.chunks_surfaces.append(chunks_current_layer)

            # TODO: No BPAs at different speeds supported at the moment
            self.bpa_durations = 0
            for bpa in self.bpas:
                if bpa is not None:
                    single_bpa_duration = max(info.unk1 for info in bpa.frame_info)
                    if single_bpa_duration > self.bpa_durations:
                        self.bpa_durations = single_bpa_duration

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

        self.drawer = Drawer(self.bg_draw, self.bma, self.bpa_durations, self.chunks_surfaces)
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
        self.current_icon_view_renderer = DrawerCellRenderer(icon_view, layer_number, self.bpa_durations, self.chunks_surfaces)
        store = Gtk.ListStore(int)
        icon_view.set_model(store)
        icon_view.pack_start(self.current_icon_view_renderer, True)
        icon_view.add_attribute(self.current_icon_view_renderer, 'chunkidx', 0)
        icon_view.connect('selection-changed', self.on_current_icon_view_selection_changed)

        for idx in range(0, len(self.chunks_surfaces[layer_number][0][0])):
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
                    store.append([f'None', i])
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

        for child in notebook_page.get_children():
            notebook_page.remove(child)
        for child in toolbox_box.get_children():
            toolbox_box.remove(child)

        page_name = Gtk.Buildable.get_name(notebook_page)
        if page_name == 'bg_layer2' and self.bma.number_of_layers < 2:
            # Layer 2: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                'This map only has one layer.\n'
                'You can add a second layer at Map > Settings.'
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
                'This map has no collision.\n'
                'You can add collision at Map > Settings.'
            )
            label.set_vexpand(True)
            label.show()
            notebook_page.add(label)
        elif page_name == 'bg_col2' and self.bma.number_of_collision_layers < 2:
            # Collision 2: Does not exist
            label: Gtk.Label = Gtk.Label.new(
                'This map has no second collision layer.\n'
                'You can add a second collision layer at Map > Settings.'
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
                'This map has no data layer.\n'
                'You can add a data layer at Map > Settings.'
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
        if self.drawer:
            self.drawer.stop()
        if self.current_icon_view_renderer:
            self.current_icon_view_renderer.stop()
        self._init_chunk_imgs()
        self.drawer.reset(self.bma, self.bpa_durations, self.chunks_surfaces)
        self.drawer.start()
        self._init_tab(self.notebook.get_nth_page(self.notebook.get_current_page()))

