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
import logging
from typing import TYPE_CHECKING, Optional, Dict, List

from gi.repository import Gtk, Gdk

from desmume.emulator import SCREEN_WIDTH, SCREEN_HEIGHT
from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import OpenRequest, REQUEST_TYPE_MAP_BG
from skytemple.core.string_provider import StringType
from skytemple.module.lists.controller import WORLD_MAP_DEFAULT_ID
from skytemple.module.lists.world_map_drawer import WorldMapDrawer
from skytemple_files.common.ppmdu_config.data import Pmd2Data
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.hardcoded.dungeons import MapMarkerPlacement
from skytemple_files.common.i18n_util import f, _

try:
    from PIL import Image
except:
    from pil import Image

if TYPE_CHECKING:
    from skytemple.module.lists.module import ListsModule
    from skytemple.module.map_bg.module import MapBgModule

SCALE = 2
logger = logging.getLogger(__name__)


class WorldMapController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        self.module = module
        self.map_bg_module: 'MapBgModule' = module.project.get_module('map_bg')
        self.builder = None
        self.drawer: Optional[WorldMapDrawer] = None
        self.dialog_drawer: Optional[WorldMapDrawer] = None
        self._location_names: Dict[int, str] = {}
        self._markers: Optional[List[MapMarkerPlacement]] = []
        self._config: Optional[Pmd2Data] = None
        self._tree_iters_by_idx = {}
        self._level_id = None
        self._edited_marker = None
        self._edited_pos = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'world_map.glade')
        lst: Gtk.Box = self.builder.get_object('box_list')
        self._markers = self.module.get_world_map_markers()
        self._config = self.module.project.get_rom_module().get_static_data()

        # Build the location names list
        self._location_names[0] = self.module.project.get_string_provider().get_value(StringType.GROUND_MAP_NAMES, 0)
        for idx in range(0, 180):
            name = self.module.project.get_string_provider().get_value(StringType.DUNGEON_NAMES_SELECTION, idx)
            self._location_names[idx+1] = name
        
        for idx in range(0, len(self._markers)-181):
            name = self.module.project.get_string_provider().get_value(StringType.GROUND_MAP_NAMES, idx+1)
            self._location_names[idx+181] = name

        self._init_list()
        self._init_drawer()
        self._level_id = WORLD_MAP_DEFAULT_ID
        self._change_map_bg(WORLD_MAP_DEFAULT_ID, self.builder.get_object('draw'), self.drawer)
        self.builder.connect_signals(self)
        return lst

    def _init_list(self):
        tree: Gtk.TreeView = self.builder.get_object('tree')
        self._list_store: Gtk.ListStore = tree.get_model()
        self._list_store.clear()

        # Iterate list
        for idx, entry in enumerate(self._markers):
            l_iter = self._list_store.append([
                str(idx), self._get_map_name(entry),
                self._get_position(entry), self._get_dungeon_name(idx)
            ])
            self._tree_iters_by_idx[idx] = l_iter

    def on_edit_selected_clicked(self, *args):
        self._edit()

    def on_tree_key_press_event(self, w, event: Gdk.EventKey):
        if event.keyval == Gdk.KEY_Return:
            self._edit()

    def on_tree_button_press_event(self, w, event: Gdk.EventButton):
        if event.button == 1 and event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self._edit()

    def on_tree_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        if model is not None and treeiter is not None:
            idx = model[treeiter][0]
            self.drawer.set_selected(self._markers[int(idx)])
            map_name = model[treeiter][1]
            if map_name != '':
                #TODO: Use the list from the game when available
                ll_by_name = self._config.script_data.level_list__by_name
                if self._level_id != ll_by_name[map_name].id:
                    self._level_id = ll_by_name[map_name].id
                    self._change_map_bg(ll_by_name[map_name].id, self.builder.get_object('draw'), self.drawer)

    def on_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        if not self.drawer:
            return
        correct_mouse_x = int(button.x / SCALE)
        correct_mouse_y = int(button.y / SCALE)
        if button.button == 1:
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)
            # Select.
            selected = self.drawer.get_under_mouse()
            if selected is not None:
                tree: Gtk.TreeView
                tree, l_iter = self.builder.get_object('tree'), self._tree_iters_by_idx[self._markers.index(selected)]
                tree.get_selection().select_iter(l_iter)
                tree.scroll_to_cell(tree.get_model().get_path(l_iter))

    def on_edit_map_bg_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_MAP_BG, self._level_id
        ))

    def _init_drawer(self):
        draw = self.builder.get_object('draw')
        self.drawer = WorldMapDrawer(draw, self._markers, self._get_dungeon_name, SCALE)
        self.drawer.start()

        draw = self.builder.get_object('diag_draw')
        self.dialog_drawer = WorldMapDrawer(draw, self._markers, self._get_dungeon_name, SCALE)
        self.dialog_drawer.start()

    def _change_map_bg(self, level_id: int, draw, drawer):
        if level_id!=-1:
            bma = self.map_bg_module.get_bma(self._get_map_id(level_id))
            bpl = self.map_bg_module.get_bpl(self._get_map_id(level_id))
            bpc = self.map_bg_module.get_bpc(self._get_map_id(level_id))
            bpas = self.map_bg_module.get_bpas(self._get_map_id(level_id))
            surface = pil_to_cairo_surface(
                bma.to_pil(bpc, bpl, bpas, False, False, single_frame=True)[0].convert('RGBA')
            )
            if drawer:
                if level_id == WORLD_MAP_DEFAULT_ID:
                    draw.set_size_request(504 * SCALE, 336 * SCALE)
                else:
                    bma_width = bma.map_width_camera * BPC_TILE_DIM
                    bma_height = bma.map_height_camera * BPC_TILE_DIM
                    draw.set_size_request(
                        bma_width * SCALE, bma_height * SCALE
                    )
                drawer.level_id = level_id
                drawer.map_bg = surface
                draw.queue_draw()
        else:
            surface = pil_to_cairo_surface(
                Image.new(mode="RGBA", size=(1,1), color=(0,0,0,0))
            )
            drawer.level_id = -1
            drawer.map_bg = surface
            draw.set_size_request(1,1)
            draw.queue_draw()

    ## TODO: The 2 following methods should use the actual level list from the game when it will be implemented
    def _get_map_name(self, entry: MapMarkerPlacement):
        if entry.level_id < 0:
            return ''
        return self._config.script_data.level_list__by_id[entry.level_id].name
    def _get_map_id(self, level_id: int):
        if level_id < 0:
            return -1
        return int(self._config.script_data.level_list__by_id[level_id].mapid)

    def _get_position(self, entry: MapMarkerPlacement):
        if entry.level_id < 0:
            return _('<Not on map>')
        if entry.reference_id > -1:
            return f(_('<Uses marker of entry {entry.reference_id}>'))
        return f'({entry.x}, {entry.y})'

    def _get_dungeon_name(self, idx):
        if idx in self._location_names:
            return self._location_names[idx]
        return ''

    # -- Dialog -- #

    def _edit(self):
        tree = self.builder.get_object('tree')
        model, treeiter = tree.get_selection().get_selected()
        if model is not None and treeiter is not None:
            idx = int(model[treeiter][0])
            dialog: Gtk.Dialog = self.builder.get_object('diag_edit')
            dlabel = self._get_dungeon_name(idx)
            if dlabel != '':
                dialog.set_title(f'{_("Edit Marker")} {idx} ({dlabel})')
            else:
                dialog.set_title(f'{_("Edit Marker")} {idx}')
            dialog.set_transient_for(MainController.window())
            dialog.set_attached_to(MainController.window())
            try:
                screen: Gdk.Screen = dialog.get_screen()
                monitor = screen.get_monitor_geometry(screen.get_monitor_at_window(screen.get_active_window()))
                dialog.resize(monitor.width * 0.75, monitor.height * 0.75)
            except BaseException:
                dialog.resize(1015, 865)

            # Map combobox
            cb_map: Gtk.ComboBox = self.builder.get_object('cb_map')
            map_store = cb_map.get_model()
            if map_store is None:
                map_store = Gtk.ListStore(int, str)
                cb_map.set_model(map_store)
                renderer_text = Gtk.CellRendererText()
                cb_map.pack_start(renderer_text, True)
                cb_map.add_attribute(renderer_text, "text", 1)
            else:
                map_store.clear()
            selected_map_iter = map_store.append([-1, _("<Don't show on map>")])
            for level in self._config.script_data.level_list: #TODO: Use the list from the game when available
                iiter = map_store.append([level.id, level.name])
                if level.id == self._markers[idx].level_id:
                    selected_map_iter = iiter
            cb_map.set_active_iter(selected_map_iter)

            # Reference combobox
            cb_reference: Gtk.ComboBox = self.builder.get_object('cb_reference')
            ref_store = cb_reference.get_model()
            if ref_store is None:
                ref_store = Gtk.ListStore(int, str)
                cb_reference.set_model(ref_store)
                renderer_text = Gtk.CellRendererText()
                cb_reference.pack_start(renderer_text, True)
                cb_reference.add_attribute(renderer_text, "text", 1)
            else:
                ref_store.clear()
            selected_ref_iter = None
            for im, marker in enumerate(self._markers):
                if im == idx:
                    continue

                dlabel = self._get_dungeon_name(im)
                if dlabel != '':
                    dlabel = f'{im} ({dlabel})'
                else:
                    dlabel = f'{im}'
                iiter = ref_store.append([im, dlabel])
                if self._markers[idx].reference_id == im:
                    selected_ref_iter = iiter
            if selected_ref_iter is not None:
                cb_reference.set_active_iter(selected_ref_iter)

            if self._markers[idx].reference_id > -1:
                self.builder.get_object('radio_reference').set_active(True)
            else:
                self.builder.get_object('radio_pos').set_active(True)

            # Drawer
            self._change_map_bg(self._markers[idx].level_id, self.builder.get_object('diag_draw'), self.dialog_drawer)

            self._edited_marker = self._markers[idx]
            self._edited_pos = (self._edited_marker.x, self._edited_marker.y)

            self.on_radio_reference_toggled(self.builder.get_object('radio_reference'))

            response = dialog.run()
            dialog.hide()

            if response == Gtk.ResponseType.APPLY:
                marker = self._edited_marker
                cb_map = self.builder.get_object('cb_map')
                model, cbiter = cb_map.get_model(), cb_map.get_active_iter()
                if model is not None and cbiter is not None and cbiter != []:
                    map_id_selected = model[cbiter][0]
                else:
                    display_error(
                        None,
                        _('You need to select a map.')
                    )
                    return
                use_reference = self.builder.get_object('radio_reference').get_active()
                reference_id_selected = -1
                if use_reference:
                    cb_reference = self.builder.get_object('cb_reference')
                    model, cbiter = cb_reference.get_model(), cb_reference.get_active_iter()
                    if model is not None and cbiter is not None and cbiter != []:
                        reference_id_selected = model[cbiter][0]
                    else:
                        display_error(
                            None,
                            _('You need to select a reference.')
                        )
                        return
                if map_id_selected == -1:
                    marker.level_id = -1
                    marker.reference_id = -1
                    marker.x = -1
                    marker.y = -1
                elif use_reference:
                    marker.level_id = map_id_selected
                    marker.reference_id = reference_id_selected
                    marker.x = 0
                    marker.y = 0
                else:
                    marker.level_id = map_id_selected
                    marker.reference_id = -1
                    marker.x = int(self._edited_pos[0])
                    marker.y = int(self._edited_pos[1])

                tree = self.builder.get_object('tree')
                tree.get_model()[self._tree_iters_by_idx[idx]][:] = [
                    str(idx), self._get_map_name(marker),
                    self._get_position(marker), self._get_dungeon_name(idx)
                ]
                if marker.level_id != self._level_id:
                    self._level_id = marker.level_id
                    self._change_map_bg(marker.level_id, self.builder.get_object('draw'), self.drawer)
                else:
                    self.drawer.draw_area.queue_draw()

                self.module.set_world_map_markers(self._markers)

    def on_cb_map_changed(self, cb: Gtk.ComboBox):
        model, cbiter = cb.get_model(), cb.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            self._change_map_bg(model[cbiter][0], self.builder.get_object('diag_draw'), self.dialog_drawer)

    def on_radio_reference_toggled(self, w: Gtk.RadioButton):
        if w.get_active():
            cb_reference = self.builder.get_object('cb_reference')
            cb_reference.set_sensitive(True)
            model, cbiter = cb_reference.get_model(), cb_reference.get_active_iter()
            if model is not None and cbiter is not None and cbiter != []:
                if self.dialog_drawer:
                    self.dialog_drawer.set_editing(self._markers[model[cbiter][0]], hide=self._edited_marker)
        else:
            self.builder.get_object('cb_reference').set_sensitive(False)
            if self.dialog_drawer and self._edited_marker and self._edited_pos:
                self.dialog_drawer.set_editing(self._edited_marker, editing_pos=self._edited_pos)

    def on_cb_reference_changed(self, cb: Gtk.ComboBox):
        model, cbiter = cb.get_model(), cb.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            if self.dialog_drawer:
                self.dialog_drawer.set_editing(self._markers[model[cbiter][0]], hide=self._edited_marker)

    def on_diag_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        if not self.dialog_drawer:
            return
        x = int(button.x / SCALE)
        y = int(button.y / SCALE)
        x = x - x % (BPC_TILE_DIM / 2)
        y = y - y % (BPC_TILE_DIM / 2)

        if button.button == 1:
            self.dialog_drawer.set_mouse_position(x, y)
            self._edited_pos = (x, y)
            self.dialog_drawer.set_editing(self._edited_marker, editing_pos=self._edited_pos)
