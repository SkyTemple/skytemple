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
import math
from functools import partial
from typing import TYPE_CHECKING, Optional, List, Union, Callable, Mapping, Tuple

import cairo
from gi.repository import Gtk, Gdk
from gi.repository.Gtk import TreeViewColumn

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import REQUEST_TYPE_MAP_BG, OpenRequest, REQUEST_TYPE_SCENE_SSE, \
    REQUEST_TYPE_SCENE_SSA, REQUEST_TYPE_SCENE_SSS
from skytemple.core.ssb_debugger.ssb_loaded_file_handler import SsbLoadedFileHandler
from skytemple.module.script.controller.ssa_event_dialog import SsaEventDialogController
from skytemple.module.script.drawer import Drawer, InteractionMode
from skytemple_files.common.ppmdu_config.data import Pmd2Data
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptRoutine, Pmd2ScriptLevel
from skytemple_files.common.script_util import SSB_EXT
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.actor import SsaActor
from skytemple_files.script.ssa_sse_sss.event import SsaEvent
from skytemple_files.script.ssa_sse_sss.layer import SsaLayer
from skytemple_files.script.ssa_sse_sss.model import Ssa
from skytemple_files.script.ssa_sse_sss.object import SsaObject
from skytemple_files.script.ssa_sse_sss.performer import SsaPerformer
from skytemple_files.script.ssa_sse_sss.position import SsaPosition
from skytemple_files.script.ssa_sse_sss.trigger import SsaTrigger
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule
    from skytemple.module.map_bg.module import MapBgModule


SIZE_REQUEST_NONE = 500


def resizable(column):
    column.set_resizable(True)
    return column


def cell_renderer_radio():
    renderer_radio = Gtk.CellRendererToggle()
    renderer_radio.set_radio(True)
    return renderer_radio


def column_with_tooltip(label_text, tooltip_text, cell_renderer, attribute, column_id):
    column = Gtk.TreeViewColumn()
    column_header = Gtk.Label(label_text)
    column_header.set_tooltip_text(tooltip_text)
    column_header.show()
    column.set_widget(column_header)
    column.pack_start(cell_renderer, True)
    column.add_attribute(cell_renderer, attribute, column_id)
    return column


def popover_position(x, y, w, h):
    return int(x + w/2), y - BPC_TILE_DIM


class SsaController(AbstractController):
    _last_open_tab = None
    _paned_pos = None
    _last_scale_factor = None
    # Cache for map backgrounds, for faster scene view transitions in the same map context
    # Should be set to (None, ) when loading a map BG context.
    map_bg_surface_cache = (None, )

    def __init__(self, module: 'ScriptModule', item: dict):
        self.module = module
        self.map_bg_module: 'MapBgModule' = module.project.get_module('map_bg')
        self.static_data: Pmd2Data = module.project.get_rom_module().get_static_data()
        self.mapname = item['map']
        self.filename = item['file']
        self.type = item['type']
        self.scripts = item['scripts']
        self.level: Optional[Pmd2ScriptLevel] = None
        self.mapbg_id = -1
        if self.mapname in self.static_data.script_data.level_list__by_name:
            self.level = self.static_data.script_data.level_list__by_name[self.mapname]
            self.mapbg_id = self.level.mapid

        self.builder = None

        if self.__class__._last_scale_factor is not None:
            self._scale_factor = self.__class__._last_scale_factor
        else:
            self._scale_factor = 1
        self._bg_draw_is_clicked__location: Optional[Tuple[int, int]] = None
        self._bg_draw_is_clicked__drag_active = False
        self._map_bg_width = SIZE_REQUEST_NONE
        self._map_bg_height = SIZE_REQUEST_NONE
        self._map_bg_surface = None
        self._suppress_events = False

        self._currently_open_popover = None
        self._currently_selected_entity: Optional[SsaActor, SsaObject, SsaEvent, SsaPerformer] = None
        self._currently_selected_entity_layer: Optional[int] = None
        self._selected_by_map_click = False

        self._w_ssa_draw: Optional[Gtk.DrawingArea] = None
        self._w_po_actors: Optional[Gtk.Popover] = None
        self._w_po_objects: Optional[Gtk.Popover] = None
        self._w_po_performers: Optional[Gtk.Popover] = None
        self._w_po_triggers: Optional[Gtk.Popover] = None

        self.ssa: Optional[Ssa] = None

        self.drawer: Optional[Drawer] = None

    def get_view(self) -> Gtk.Widget:
        self.module.get_sprite_provider().reset()
        self.builder = self._get_builder(__file__, 'ssa.glade')
        self._w_ssa_draw = self.builder.get_object('ssa_draw')
        self._w_po_actors: Optional[Gtk.Popover] = self.builder.get_object('po_actor')
        self._w_po_objects: Optional[Gtk.Popover] = self.builder.get_object('po_object')
        self._w_po_performers: Optional[Gtk.Popover] = self.builder.get_object('po_performer')
        self._w_po_triggers: Optional[Gtk.Popover] = self.builder.get_object('po_trigger')

        paned: Gtk.Paned = self.builder.get_object('ssa_paned')
        if self.__class__._paned_pos is not None:
            paned.set_position(self._paned_pos)
        else:
            paned.set_position(800)
        util_notebook: Gtk.Notebook = self.builder.get_object('ssa_utility')
        if self.__class__._last_open_tab is not None:
            util_notebook.set_current_page(self._last_open_tab)
        self.builder.connect_signals(self)

        self._init_ssa()
        self._init_drawer()
        self._init_all_the_stores()
        self._update_scales()

        return self.builder.get_object('editor_ssa')

    def on_ssa_utility_switch_page(self, util_notebook: Gtk.Notebook, p, pnum, *args):
        self.__class__._last_open_tab = pnum

    def on_ssa_paned_position_notify(self, paned: Gtk.Paned, *args):
        self.__class__._paned_pos = paned.get_position()

    def on_ssa_draw_event_button_press_event(self, box, button: Gdk.EventButton):
        if not self.drawer or self.drawer.interaction_mode != InteractionMode.SELECT:
            return
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            self._bg_draw_is_clicked__drag_active = False
            self._bg_draw_is_clicked__location = (int(button.x), int(button.y))
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            # Select.
            self.drawer.end_drag()
            layer, selected = self.drawer.get_under_mouse()
            self._select(selected, layer,
                         open_popover=False)
            if selected is not None:
                tree, l_iter = self._get_list_tree_and_iter_for(selected)
                self._selected_by_map_click = True
                if l_iter is not None:
                    # This really shouldn't be None but okay?
                    tree.get_selection().select_iter(l_iter)
                self._selected_by_map_click = False

        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_button_release_event(self, box, button: Gdk.EventButton):
        if button.button == 1 and self.drawer is not None:
            # PLACE
            place_layer = 0
            new_entity = None
            if self.drawer.get_sector_highlighted() is not None:
                place_layer = self.drawer.get_sector_highlighted()

            if self.drawer.interaction_mode == InteractionMode.PLACE_ACTOR:
                new_entity = SsaActor(
                    self.static_data.script_data, 0, self._build_pos(*self.drawer.get_pos_place_actor()), -1, -1
                )
                self.ssa.layer_list[place_layer].actors.append(new_entity)
            elif self.drawer.interaction_mode == InteractionMode.PLACE_OBJECT:
                new_entity = SsaObject(
                    self.static_data.script_data, 0, 2, 2, self._build_pos(*self.drawer.get_pos_place_object()), -1, -1
                )
                self.ssa.layer_list[place_layer].objects.append(new_entity)
            elif self.drawer.interaction_mode == InteractionMode.PLACE_PERFORMER:
                new_entity = SsaPerformer(
                    0, 1, 1, self._build_pos(*self.drawer.get_pos_place_performer()), -1, -1
                )
                self.ssa.layer_list[place_layer].performers.append(new_entity)
            elif self.drawer.interaction_mode == InteractionMode.PLACE_TRIGGER:
                new_entity = SsaEvent(
                    2, 2, 0, 0, self._build_pos(*self.drawer.get_pos_place_trigger(), dir=False), 65535
                )
                self.ssa.layer_list[place_layer].events.append(new_entity)
            if new_entity is not None:
                # Switch back to move/select mode
                self.builder.get_object('tool_scene_move').set_active(True)
                self._select(new_entity, place_layer)
                self._add_entity_to_list(new_entity, place_layer)
                self.module.mark_as_modified(self.mapname, self.type, self.filename)

            # SELECT / DRAG
            elif self._currently_selected_entity is not None:
                if not self._bg_draw_is_clicked__drag_active:
                    # Open popover
                    self._select(self._currently_selected_entity, self._currently_selected_entity_layer,
                                 open_popover=True)
                else:
                    # END DRAG / UPDATE POSITION
                    tile_x, tile_y = self.drawer.get_current_drag_entity_pos()
                    tile_x /= BPC_TILE_DIM
                    tile_y /= BPC_TILE_DIM
                    # Out of bounds failsafe:
                    if tile_x < 0:
                        tile_x = 0
                    if tile_y < 0:
                        tile_y = 0
                    self.drawer.end_drag()
                    self.module.mark_as_modified(self.mapname, self.type, self.filename)
                    self._currently_selected_entity.pos.x_relative = math.floor(tile_x)
                    self._currently_selected_entity.pos.y_relative = math.floor(tile_y)
                    if tile_x % 1 != 0:
                        self._currently_selected_entity.pos.x_offset = 2
                    else:
                        self._currently_selected_entity.pos.x_offset = 0
                    if tile_y % 1 != 0:
                        self._currently_selected_entity.pos.y_offset = 2
                    else:
                        self._currently_selected_entity.pos.y_offset = 0
                    self._bg_draw_is_clicked__drag_active = False
                    self._bg_draw_is_clicked__location = None
        self._bg_draw_is_clicked__location = None
        self._bg_draw_is_clicked__drag_active = False
        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            self.drawer.set_mouse_position(correct_mouse_x, correct_mouse_y)

            if self._currently_selected_entity is not None:
                this_x, this_y = motion.get_coords()
                if self._bg_draw_is_clicked__location is not None:
                    start_x, start_y = self._bg_draw_is_clicked__location
                    # Start drag & drop if mouse moved at least one tile.
                    if not self._bg_draw_is_clicked__drag_active and (
                            abs(start_x - this_x) > BPC_TILE_DIM / 2 * self._scale_factor
                            or abs(start_y - this_y) > BPC_TILE_DIM / 2 * self._scale_factor
                    ):
                        self._bg_draw_is_clicked__drag_active = True
                        self.drawer.set_drag_position(
                            int((start_x - 4) / self._scale_factor) - self._currently_selected_entity.pos.x_absolute,
                            int((start_y - 4) / self._scale_factor) - self._currently_selected_entity.pos.y_absolute
                        )

            self._w_ssa_draw.queue_draw()

    # SCENE TOOLBAR #
    def on_tool_scene_zoom_in_clicked(self, *args):
        self._scale_factor *= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    def on_tool_scene_zoom_out_clicked(self, *args):
        self._scale_factor /= 2
        self.__class__._last_scale_factor = self._scale_factor
        self._update_scales()

    def on_tool_scene_grid_toggled(self, w, *args):
        if self.drawer:
            self.drawer.set_draw_tile_grid(w.get_active())
            self._w_ssa_draw.queue_draw()

    def on_tool_scene_move_toggled(self, *args):
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.SELECT

    def on_tool_scene_add_actor_toggled(self, *args):
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_ACTOR
            self._select(None, None)

    def on_tool_scene_add_object_toggled(self, *args):
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_OBJECT
            self._select(None, None)

    def on_tool_scene_add_performer_toggled(self, *args):
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_PERFORMER
            self._select(None, None)

    def on_tool_scene_add_trigger_toggled(self, *args):
        if self.drawer:
            self.drawer.interaction_mode = InteractionMode.PLACE_TRIGGER
            self._select(None, None)

    def on_tool_choose_map_bg_cb_changed(self, w: Gtk.ComboBox):
        model, cbiter = w.get_model(), w.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            item_id = model[cbiter][0]
            self.mapbg_id = item_id
            if self.__class__.map_bg_surface_cache[0] == item_id:
                self._map_bg_surface, bma_width, bma_height = self.__class__.map_bg_surface_cache[1:]
            else:
                bma = self.map_bg_module.get_bma(item_id)
                bpl = self.map_bg_module.get_bpl(item_id)
                bpc = self.map_bg_module.get_bpc(item_id)
                bpas = self.map_bg_module.get_bpas(item_id)
                self._map_bg_surface = pil_to_cairo_surface(
                    bma.to_pil(bpc, bpl, bpas, False, False, single_frame=True)[0].convert('RGBA')
                )
                bma_width = bma.map_width_camera * BPC_TILE_DIM
                bma_height = bma.map_height_camera * BPC_TILE_DIM
                self.__class__.map_bg_surface_cache = (item_id, self._map_bg_surface, bma_width, bma_height)
            if self.drawer:
                self._set_drawer_bg(self._map_bg_surface, bma_width, bma_height)

    def on_tool_scene_goto_bg_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_MAP_BG, self.mapbg_id
        ))

    # EVENTS TOOLBAR #
    def on_tool_events_add_clicked(self, *args):
        dialog = SsaEventDialogController(
            self.builder, MainController.window(),
            self._get_event_dialog_script_names(),
            self.static_data.script_data
        )
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            new_event = dialog.get_event()
            self.ssa.triggers.append(new_event)
            self.builder.get_object('ssa_events').get_model().append(
                self._list_entry_generate_event(new_event)
            )
            # Update popovers for events
            po_trigger_id: Gtk.ComboBox = self.builder.get_object('po_trigger_id')
            po_trigger_id.get_model().append([new_event,
                                              f"{self._get_talk_script_name(new_event.script_id)} "
                                              f"/ {self._get_coroutine_name(new_event.coroutine)}"])
            # Update lists for triggers
            for layer_id, layer in enumerate(self.ssa.layer_list):
                for trigger in layer.events:
                    self._refresh_list_entry_for(trigger, layer_id)

            self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def on_tool_events_remove_clicked(self, *args):
        widget: Gtk.TreeView = self.builder.get_object('ssa_events')
        model: Gtk.ListStore
        model, treeiter = widget.get_selection().get_selected()
        if treeiter is not None and model is not None:
            row = model[treeiter][:]
            # Remove from list
            model.remove(treeiter)
            # Remove from model
            trigger_id = self.ssa.triggers.index(row[0])
            self.ssa.triggers.remove(row[0])
            # Update popovers combobox for events
            po_trigger_id: Gtk.ComboBox = self.builder.get_object('po_trigger_id')
            po_store: Gtk.ListStore = po_trigger_id.get_model()
            po_iter = po_store.get_iter_first()
            while po_iter:
                if po_store[po_iter][0] == row[0]:
                    po_store.remove(po_iter)
                    break
                po_iter = po_store.iter_next(po_iter)
            # Update triggers ( set to 0 if removed, if bigger than index, decrease by 1 )
            for layer_id, layer in enumerate(self.ssa.layer_list):
                for trigger in layer.events:
                    if trigger.trigger_id == trigger_id:
                        trigger.trigger_id = 0
                    elif trigger.trigger_id > trigger_id:
                        trigger.trigger_id -= 1
                    self._refresh_list_entry_for(trigger, layer_id)
            # Mark as modified
            self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def on_tool_events_edit_clicked(self, *args):
        widget: Gtk.TreeView = self.builder.get_object('ssa_events')
        model: Gtk.ListStore
        model, treeiter = widget.get_selection().get_selected()
        if treeiter is not None and model is not None:
            edit_model: SsaTrigger = model[treeiter][0]
            dialog = SsaEventDialogController(
                self.builder, MainController.window(),
                self._get_event_dialog_script_names(),
                self.static_data.script_data,
                edit=edit_model
            )
            response = dialog.run()
            if response == Gtk.ResponseType.OK:
                new_event = dialog.get_event()
                edit_model.coroutine = new_event.coroutine
                edit_model.script_id = new_event.script_id
                edit_model.unk2 = new_event.unk2
                edit_model.unk3 = new_event.unk3
                # Update popovers for events
                po_trigger_id: Gtk.ComboBox = self.builder.get_object('po_trigger_id')
                po_store: Gtk.ListStore = po_trigger_id.get_model()
                po_iter = po_store.get_iter_first()
                while po_iter:
                    if po_store[po_iter][0] == edit_model:
                        po_store[po_iter][:] = [
                            edit_model,
                            f"{self._get_talk_script_name(edit_model.script_id)} "
                            f"/ {self._get_coroutine_name(edit_model.coroutine)}"
                        ]
                        break
                    po_iter = po_store.iter_next(po_iter)
                # Update lists for triggers
                for layer_id, layer in enumerate(self.ssa.layer_list):
                    for trigger in layer.events:
                        self._refresh_list_entry_for(trigger, layer_id)
                # Update event list
                l_iter = model.get_iter_first()
                while l_iter:
                    if model[l_iter][0] == edit_model:
                        model[l_iter][:] = self._list_entry_generate_event(edit_model)
                        break
                    l_iter = model.iter_next(l_iter)

                self.module.mark_as_modified(self.mapname, self.type, self.filename)

    # SECTOR TOOLBAR #
    def on_tool_sector_add_clicked(self, *args):
        # Create
        new_index = len(self.ssa.layer_list)
        new_layer = SsaLayer()
        # Add to ssa_layers
        ssa_layers = self.builder.get_object('ssa_layers')
        ssa_layers.get_model().append(self._list_entry_generate_layer(new_index, new_layer))
        self.ssa.layer_list.append(new_layer)
        # Add to popover comboboxes
        po_actor_sector: Gtk.ComboBox = self.builder.get_object('po_actor_sector')
        po_actor_sector.get_model().append([new_index, f(_('Sector {new_index}'))])
        # Tell drawer
        self.drawer.sector_added()
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def on_tool_sector_remove_clicked(self, *args):
        # Confirmation dialog
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
            Gtk.ButtonsType.YES_NO,
            _("Are you sure you want to remove this sector?\n"
              "Removing the sector will re-number all following sectors (eg. if you remove Sector 70, sector 71 will become 70, 72 -> 71, etc.)\n"
              "Removing a sector may cause serious issues when the game tries to load the scene."),
            title=_("Warning!")
        )

        response = md.run()
        md.destroy()

        if response == Gtk.ResponseType.YES:
            # Okay, delete the layer/sector
            widget: Gtk.TreeView = self.builder.get_object('ssa_layers')
            model: Gtk.ListStore
            model, treeiter = widget.get_selection().get_selected()
            if treeiter is not None and model is not None:
                layer_id = model[treeiter][0]
                # UPDATE ALL LAYERS LIST ENTRIES AFTER THIS ONE!
                after_iter = model.iter_next(treeiter)
                after_inc = 0
                while after_iter:
                    model[after_iter][0:2] = self._list_entry_generate_layer(
                        layer_id + after_inc, self.ssa.layer_list[layer_id + after_inc + 1]
                    )[0:2]
                    after_iter = model.iter_next(after_iter)
                    after_inc += 1
                # REMOVE ALL ENTITIES THAT NO LONGER EXIST FROM THE LISTS
                layer = self.ssa.layer_list[layer_id]
                for actor in layer.actors:
                    tree, l_iter = self._get_list_tree_and_iter_for(actor)
                    tree.get_model().remove(l_iter)
                for object in layer.objects:
                    tree, l_iter = self._get_list_tree_and_iter_for(object)
                    tree.get_model().remove(l_iter)
                for performer in layer.performers:
                    tree, l_iter = self._get_list_tree_and_iter_for(performer)
                    tree.get_model().remove(l_iter)
                for trigger in layer.events:
                    tree, l_iter = self._get_list_tree_and_iter_for(trigger)
                    tree.get_model().remove(l_iter)
                # UPDATE ALL ENTITY LIST LAYER INDICES AFTER THIS ONE!
                for after_inc, layer in enumerate(self.ssa.layer_list[layer_id + 1:]):
                    for actor in layer.actors:
                        self._refresh_list_entry_for(actor, layer_id + after_inc)
                    for object in layer.objects:
                        self._refresh_list_entry_for(object, layer_id + after_inc)
                    for performer in layer.performers:
                        self._refresh_list_entry_for(performer, layer_id + after_inc)
                    for trigger in layer.events:
                        self._refresh_list_entry_for(trigger, layer_id + after_inc)
                # Remove layer
                del self.ssa.layer_list[layer_id]
                # Remove from ssa_layers
                model.remove(treeiter)
                # Tell drawer
                self.drawer.sector_removed(layer_id)
                # Get iter in popover combo box
                po_store: Gtk.ListStore = self.builder.get_object('po_actor_sector').get_model()
                po_iter = po_store.get_iter_first()
                found_in_po = False
                while po_iter:
                    if po_store[po_iter][0] == layer_id:
                        found_in_po = True
                        break
                    po_iter = po_store.iter_next(po_iter)
                if found_in_po:
                    # Update all popover entries after this one
                    after_iter = po_store.iter_next(po_iter)
                    after_inc = 0
                    while after_iter:
                        po_store[after_iter] = [layer_id + after_inc, f'Sector {layer_id + after_inc}']
                        after_iter = po_store.iter_next(after_iter)
                        after_inc += 1
                    # Remove from popover combo box
                    po_store.remove(po_iter)
                # Remove now invalid references:
                if self._currently_selected_entity_layer == layer_id:
                    self._currently_selected_entity_layer = None
                    self._currently_selected_entity = None
                    self._bg_draw_is_clicked__drag_active = False
                    self._bg_draw_is_clicked__location = None
                # Mark as modified
                self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def on_ssa_layers_visible_toggled(self, model, widget, path):
        model[path][2] = not model[path][2]
        if self.drawer:
            self.drawer.set_sector_visible(model[path][0], model[path][2])

    def on_ssa_layers_solo_toggled(self, model, widget, path):
        model[path][3] = not model[path][3]
        if self.drawer:
            self.drawer.set_sector_solo(model[path][0], model[path][3])

    # SCRIPT TOOLBAR #
    def on_tool_script_edit_clicked(self, *args):
        tree: Gtk.TreeView = self.builder.get_object('ssa_scripts')
        model, treeiter = tree.get_selection().get_selected()
        if treeiter is not None and model is not None:
            manager = MainController.debugger_manager()
            manager.open_ssb(f'SCRIPT/{self.mapname}/{model[treeiter][0]}', MainController.window())

    def on_tool_script_add_clicked(self, *args):
        if self.type == 'ssa':
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                f"Acting scenes must have exactly one script assigned to them."
            )
            md.run()
            md.destroy()
            return
        # Ask for number to add
        response, number = self._show_generic_input(_('Script Number'), _('Create Script'))
        if response != Gtk.ResponseType.OK:
            return
        try:
            number = int(number)
        except ValueError:
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("Please enter a valid number.")
            )
            md.run()
            md.destroy()
            return
        # Calculate name
        ssb_path = f'{self.filename[:-4]}{number:02d}{SSB_EXT}'
        # Check if already exists
        if self.module.project.file_exists(ssb_path):
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("This script already exists.")
            )
            md.run()
            md.destroy()
            return
        # Write to ROM
        save_kwargs = {
            'filename': ssb_path,
            'static_data': self.static_data,
            'project_fm': self.module.project.get_project_file_manager()
        }
        self.module.project.create_new_file(
            ssb_path, SsbLoadedFileHandler.create(**save_kwargs), SsbLoadedFileHandler, **save_kwargs
        )
        # Update script list
        short_name = self._get_file_shortname(ssb_path)
        ssa_scripts_store: Gtk.ListStore = self.builder.get_object('ssa_scripts').get_model()
        # The reason this is the same is because I screwed up when building self.scripts...
        ssa_scripts_store.append([short_name, short_name])
        # Update debugger
        MainController.debugger_manager().on_script_added(
            ssb_path, self.mapname, self.type, self.filename.split('/')[-1]
        )
        # Update popovers actors / objects
        po_actor_script: Gtk.ComboBox = self.builder.get_object('po_actor_script')
        po_actor_script.get_model().append([number, short_name])
        # Add to object script list
        self.scripts.append(short_name)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def on_tool_script_remove_clicked(self, *args):
        if self.type == 'ssa':
            md = SkyTempleMessageDialog(
                MainController.window(),
                Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.OK,
                _("Acting scenes must have exactly one script assigned to them.")
            )
            md.run()
            md.destroy()
            return
        # TODO
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.MODAL, Gtk.MessageType.ERROR,
            Gtk.ButtonsType.OK,
            _("Not implemented.")
        )
        md.run()
        md.destroy()
        # Ask.
        # Calculate number
        # Check if assigned to event
        # Check if assigned to actor or object
        # Remove rom ROM
        # Update script list
        # Update debugger
        #MainController.debugger_manager().on_script_removed(ssb_path)
        # Update popovers actors / objects
        # Remove from object script list
        # Mark as modified

    def on_ssa_scripts_button_press_event(self, tree, event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            self.on_tool_script_edit_clicked()

    # ACTOR OVERLAY #
    def on_po_actor_sector_changed(self, widget: Gtk.ComboBox, *args):
        self._on_po_sector_changed(widget)

    def on_po_actor_kind_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            kind_id = model[cbiter][0]
            self._currently_selected_entity.actor = self.static_data.script_data.level_entities__by_id[kind_id]
            self._refresh_for_selected()

    def on_po_actor_script_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.script_id = model[cbiter][0]
            self._refresh_for_selected()

    def on_po_actor_dir_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.pos.direction = self.static_data.script_data.directions__by_ssa_id[model[cbiter][0]]
            self._refresh_for_selected()

    def on_po_actor_delete_clicked(self, widget: Gtk.ComboBox, *args):
        # Remove from list
        tree, l_iter = self._get_list_tree_and_iter_for(self._currently_selected_entity)
        tree.get_model().remove(l_iter)
        # Remove from model
        self.ssa.layer_list[self._currently_selected_entity_layer].actors.remove(self._currently_selected_entity)
        # Remove now invalid references:
        self._currently_selected_entity = None
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location = None
        if self._currently_open_popover is not None:
            self._currently_open_popover.popdown()
        self._w_ssa_draw.queue_draw()
        # Refresh layer list entry for current layer
        self._refresh_layer(self._currently_selected_entity_layer)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    # OBJECT OVERLAY #
    def on_po_object_sector_changed(self, widget: Gtk.ComboBox, *args):
        self._on_po_sector_changed(widget)

    def on_po_object_kind_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            kind_id = model[cbiter][0]
            self._currently_selected_entity.object = self.static_data.script_data.objects__by_id[kind_id]
            self._refresh_for_selected()

    def on_po_object_script_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.script_id = model[cbiter][0]
            self._refresh_for_selected()

    def on_po_object_width_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.hitbox_w = size
                self._refresh_for_selected()

    def on_po_object_height_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.hitbox_h = size
                self._refresh_for_selected()

    def on_po_object_dir_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.pos.direction = self.static_data.script_data.directions__by_ssa_id[model[cbiter][0]]
            self._refresh_for_selected()

    def on_po_object_delete_clicked(self, widget: Gtk.ComboBox, *args):
        # Remove from list
        tree, l_iter = self._get_list_tree_and_iter_for(self._currently_selected_entity)
        tree.get_model().remove(l_iter)
        # Remove from model
        self.ssa.layer_list[self._currently_selected_entity_layer].objects.remove(self._currently_selected_entity)
        # Remove now invalid references:
        self._currently_selected_entity = None
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location = None
        if self._currently_open_popover is not None:
            self._currently_open_popover.popdown()
        self._w_ssa_draw.queue_draw()
        # Refresh layer list entry for current layer
        self._refresh_layer(self._currently_selected_entity_layer)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    # PERFORMER OVERLAY #
    def on_po_performer_sector_changed(self, widget: Gtk.ComboBox, *args):
        self._on_po_sector_changed(widget)

    def on_po_performer_kind_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.type = model[cbiter][0]
            self._refresh_for_selected()

    def on_po_performer_width_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.hitbox_w = size
                self._refresh_for_selected()

    def on_po_performer_height_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.hitbox_h = size
                self._refresh_for_selected()

    def on_po_performer_dir_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.pos.direction = self.static_data.script_data.directions__by_ssa_id[model[cbiter][0]]
            self._refresh_for_selected()

    def on_po_performer_delete_clicked(self, widget: Gtk.ComboBox, *args):
        # Remove from list
        tree, l_iter = self._get_list_tree_and_iter_for(self._currently_selected_entity)
        tree.get_model().remove(l_iter)
        # Remove from model
        self.ssa.layer_list[self._currently_selected_entity_layer].performers.remove(self._currently_selected_entity)
        # Remove now invalid references:
        self._currently_selected_entity = None
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location = None
        if self._currently_open_popover is not None:
            self._currently_open_popover.popdown()
        self._w_ssa_draw.queue_draw()
        # Refresh layer list entry for current layer
        self._refresh_layer(self._currently_selected_entity_layer)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    # TRIGGER OVERLAY #
    def on_po_trigger_sector_changed(self, widget: Gtk.ComboBox, *args):
        self._on_po_sector_changed(widget)

    def on_po_trigger_id_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            self._currently_selected_entity.trigger_id = self.ssa.triggers.index(model[cbiter][0])
            self._refresh_for_selected()

    def on_po_trigger_width_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.trigger_width = size
                self._refresh_for_selected()

    def on_po_trigger_height_changed(self, widget: Gtk.Entry, *args):
        try:
            size = int(widget.get_text())
        except ValueError:
            pass  # Ignore errors
        else:
            if self._currently_selected_entity is not None:
                self._currently_selected_entity.trigger_height = size
                self._refresh_for_selected()

    def on_po_trigger_delete_clicked(self, widget: Gtk.ComboBox, *args):
        # Remove from list
        tree, l_iter = self._get_list_tree_and_iter_for(self._currently_selected_entity)
        tree.get_model().remove(l_iter)
        # Remove from model
        self.ssa.layer_list[self._currently_selected_entity_layer].events.remove(self._currently_selected_entity)
        # Remove now invalid references:
        self._currently_selected_entity = None
        self._bg_draw_is_clicked__drag_active = False
        self._bg_draw_is_clicked__location = None
        if self._currently_open_popover is not None:
            self._currently_open_popover.popdown()
        self._w_ssa_draw.queue_draw()
        # Refresh layer list entry for current layer
        self._refresh_layer(self._currently_selected_entity_layer)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    # OVERLAY COMMON #
    def _on_po_sector_changed(self, widget: Gtk.ComboBox, *args):
        model, cbiter = widget.get_model(), widget.get_active_iter()
        if model is not None and cbiter is not None and cbiter != [] and self._currently_selected_entity is not None:
            new_layer_id = model[cbiter][0]
            if self._currently_selected_entity is not None:
                if isinstance(self._currently_selected_entity, SsaActor):
                    index = self.ssa.layer_list[self._currently_selected_entity_layer].actors.index(self._currently_selected_entity)
                    del self.ssa.layer_list[self._currently_selected_entity_layer].actors[index]
                    self.ssa.layer_list[new_layer_id].actors.append(self._currently_selected_entity)
                elif isinstance(self._currently_selected_entity, SsaObject):
                    index = self.ssa.layer_list[self._currently_selected_entity_layer].objects.index(self._currently_selected_entity)
                    del self.ssa.layer_list[self._currently_selected_entity_layer].objects[index]
                    self.ssa.layer_list[new_layer_id].objects.append(self._currently_selected_entity)
                elif isinstance(self._currently_selected_entity, SsaPerformer):
                    index = self.ssa.layer_list[self._currently_selected_entity_layer].performers.index(self._currently_selected_entity)
                    del self.ssa.layer_list[self._currently_selected_entity_layer].performers[index]
                    self.ssa.layer_list[new_layer_id].performers.append(self._currently_selected_entity)
                elif isinstance(self._currently_selected_entity, SsaEvent):
                    index = self.ssa.layer_list[self._currently_selected_entity_layer].events.index(self._currently_selected_entity)
                    del self.ssa.layer_list[self._currently_selected_entity_layer].events[index]
                    self.ssa.layer_list[new_layer_id].events.append(self._currently_selected_entity)

                # Also update the layer list entry for old and new layer
                self._refresh_layer(self._currently_selected_entity_layer)
                new_layer_iter = self._refresh_layer(new_layer_id)

                # Select the layer:
                ssa_layers = self.builder.get_object('ssa_layers')
                self._currently_selected_entity_layer = new_layer_id
                ssa_layers.get_selection().select_iter(new_layer_iter)
                
                self._refresh_for_selected()

    def _refresh_layer(self, layer_id):
        ssa_layers = self.builder.get_object('ssa_layers')
        l_iter = self._find_list_iter(ssa_layers, lambda row: layer_id == row[0])
        for i, f in enumerate(self._list_entry_generate_layer(layer_id, self.ssa.layer_list[layer_id])[0:2]):
            ssa_layers.get_model()[l_iter][i] = f
        return l_iter

    def _refresh_for_selected(self):
        # Refresh drawing
        self._w_ssa_draw.queue_draw()
        # Refresh list entries
        self._refresh_list_entry_for(self._currently_selected_entity, self._currently_selected_entity_layer)
        # Mark as modified
        self.module.mark_as_modified(self.mapname, self.type, self.filename)

    def _refresh_list_entry_for(self, entity, layer):
        tree, l_iter = self._get_list_tree_and_iter_for(entity)
        if isinstance(entity, SsaActor):
            for i, f in enumerate(self._list_entry_generate_actor(layer, entity)):
                tree.get_model()[l_iter][i] = f
        elif isinstance(entity, SsaObject):
            for i, f in enumerate(self._list_entry_generate_object(layer, entity)):
                tree.get_model()[l_iter][i] = f
        elif isinstance(entity, SsaPerformer):
            for i, f in enumerate(self._list_entry_generate_performer(layer, entity)):
                tree.get_model()[l_iter][i] = f
        elif isinstance(entity, SsaEvent):
            for i, f in enumerate(self._list_entry_generate_trigger(layer, entity)):
                tree.get_model()[l_iter][i] = f

    def _get_list_for(self, entity) -> Gtk.TreeView:
        tree = None
        if isinstance(entity, SsaActor):
            tree: Gtk.TreeView = self.builder.get_object("ssa_actors")
        elif isinstance(entity, SsaObject):
            tree: Gtk.TreeView = self.builder.get_object("ssa_objects")
        elif isinstance(entity, SsaPerformer):
            tree: Gtk.TreeView = self.builder.get_object("ssa_performers")
        elif isinstance(entity, SsaEvent):
            tree: Gtk.TreeView = self.builder.get_object("ssa_triggers")
        return tree

    def _get_list_tree_and_iter_for(self, selected) -> Tuple[Gtk.TreeView, Optional[Gtk.TreeIter]]:
        tree = self._get_list_for(selected)
        return tree, self._find_list_iter(tree, lambda row: selected is row[1])

    def _find_list_iter(self, tree, condition_cb):
        if tree is not None:
            l_iter: Gtk.TreeIter = tree.get_model().get_iter_first()
            while l_iter:
                row = tree.get_model()[l_iter]
                if condition_cb(row):
                    return l_iter
                l_iter = tree.get_model().iter_next(l_iter)
        return None

    # TREE VIEWS #
    def on_ssa_scenes_selection_changed(self, selection: Gtk.TreeSelection, *args):
        if not self._suppress_events:
            model, treeiter = selection.get_selected()
            if treeiter is not None and model is not None:
                filename = model[treeiter][0]
                if filename[-3:] == 'sse':
                    self.module.project.request_open(OpenRequest(
                        REQUEST_TYPE_SCENE_SSE, self.mapname
                    ))
                elif filename[-3:] == 'ssa':
                    self.module.project.request_open(OpenRequest(
                        REQUEST_TYPE_SCENE_SSA, (self.mapname, filename)
                    ))
                elif filename[-3:] == 'sss':
                    self.module.project.request_open(OpenRequest(
                        REQUEST_TYPE_SCENE_SSS, (self.mapname, filename)
                    ))

    def on_ssa_layers_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        target = None
        if treeiter is not None and model is not None:
            target = model[treeiter][0]
        if self.drawer:
            self.drawer.set_sector_highlighted(target)

    def on_ssa_actors_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            entry = model[treeiter]
            self._deselect("ssa_objects")
            self._deselect("ssa_performers")
            self._deselect("ssa_triggers")
            if not self._selected_by_map_click:
                self._select(entry[1], entry[0], False)

    def on_ssa_objects_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            entry = model[treeiter]
            self._deselect("ssa_actors")
            self._deselect("ssa_performers")
            self._deselect("ssa_triggers")
            if not self._selected_by_map_click:
                self._select(entry[1], entry[0], False)

    def on_ssa_performers_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            entry = model[treeiter]
            self._deselect("ssa_actors")
            self._deselect("ssa_objects")
            self._deselect("ssa_triggers")
            if not self._selected_by_map_click:
                self._select(entry[1], entry[0], False)

    def on_ssa_triggers_selection_changed(self, selection: Gtk.TreeSelection, *args):
        model, treeiter = selection.get_selected()
        if treeiter is not None and model is not None:
            entry = model[treeiter]
            self._deselect("ssa_actors")
            self._deselect("ssa_objects")
            self._deselect("ssa_performers")
            if not self._selected_by_map_click:
                self._select(entry[1], entry[0], False)

    def on_ssa_actors_button_press_event(self, tree: Gtk.TreeView, event: Gdk.Event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            model, treeiter = tree.get_selection().get_selected()
            if treeiter is not None and model is not None:
                entry = model[treeiter]
                self._select(entry[1], entry[0], True)

    def on_ssa_objects_button_press_event(self, tree: Gtk.TreeView, event: Gdk.Event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            model, treeiter = tree.get_selection().get_selected()
            if treeiter is not None and model is not None:
                entry = model[treeiter]
                self._select(entry[1], entry[0], True)

    def on_ssa_performers_button_press_event(self, tree: Gtk.TreeView, event: Gdk.Event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            model, treeiter = tree.get_selection().get_selected()
            if treeiter is not None and model is not None:
                entry = model[treeiter]
                self._select(entry[1], entry[0], True)

    def on_ssa_triggers_button_press_event(self, tree: Gtk.TreeView, event: Gdk.Event):
        if event.type == Gdk.EventType.DOUBLE_BUTTON_PRESS:
            model, treeiter = tree.get_selection().get_selected()
            if treeiter is not None and model is not None:
                entry = model[treeiter]
                self._select(entry[1], entry[0], True)

    def on_po_closed(self, *args):
        self._currently_open_popover = None

    def _deselect(self, list_name):
        self.builder.get_object(list_name).get_selection().unselect_all()

    def _select(self, selected: Optional[Union[SsaActor, SsaObject, SsaPerformer, SsaEvent]], selected_layer: Optional[int],
                open_popover=True, popup_x=None, popup_y=None):
        if self._currently_open_popover is not None:
            self._currently_open_popover.popdown()
        # Also select the layer back.
        if selected_layer is not None:
            ssa_layers: Gtk.TreeView = self.builder.get_object('ssa_layers')
            ssa_layers.get_selection().select_iter(self._find_list_iter(ssa_layers, lambda row: row[0] == selected_layer))

        # this will prevent the updating events from firing, when selecting below.
        self._currently_selected_entity = None
        self._currently_selected_entity_layer = None
        self.drawer.set_selected(selected)
        if open_popover:
            popover = None
            if isinstance(selected, SsaActor):
                popover: Gtk.Popover = self._w_po_actors
                if popup_x is None or popup_y is None:
                    popup_x, popup_y = popover_position(*tuple(x * self._scale_factor for x in self.drawer.get_bb_actor(selected)))
                self._select_in_combobox_where_callback('po_actor_kind', lambda r: selected.actor.id == r[0])
                self._select_in_combobox_where_callback('po_actor_sector', lambda r: selected_layer == r[0])
                self._select_in_combobox_where_callback('po_actor_script', lambda r: selected.script_id == r[0])
                self._select_in_combobox_where_callback('po_actor_dir', lambda r: selected.pos.direction.id == r[0])

                popover.set_relative_to(self._w_ssa_draw)
                rect = Gdk.Rectangle()
                rect.x = popup_x
                rect.y = popup_y
                popover.set_pointing_to(rect)
                popover.popup()
            elif isinstance(selected, SsaObject):
                popover: Gtk.Popover = self._w_po_objects
                if popup_x is None or popup_y is None:
                    popup_x, popup_y = popover_position(*tuple(x * self._scale_factor for x in self.drawer.get_bb_object(selected)))
                self._select_in_combobox_where_callback('po_object_kind', lambda r: selected.object.id == r[0])
                self._select_in_combobox_where_callback('po_object_sector', lambda r: selected_layer == r[0])
                self._select_in_combobox_where_callback('po_object_script', lambda r: selected.script_id == r[0])
                self._select_in_combobox_where_callback('po_object_dir', lambda r: selected.pos.direction.id == r[0])
                self.builder.get_object('po_object_width').set_text(str(selected.hitbox_w))
                self.builder.get_object('po_object_height').set_text(str(selected.hitbox_h))

                popover.set_relative_to(self._w_ssa_draw)
                rect = Gdk.Rectangle()
                rect.x = popup_x
                rect.y = popup_y
                popover.set_pointing_to(rect)
                popover.popup()
            elif isinstance(selected, SsaPerformer):
                popover: Gtk.Popover = self._w_po_performers
                if popup_x is None or popup_y is None:
                    popup_x, popup_y = popover_position(*tuple(x * self._scale_factor for x in self.drawer.get_bb_performer(selected)))
                self._select_in_combobox_where_callback('po_performer_kind', lambda r: selected.type == r[0])
                self._select_in_combobox_where_callback('po_performer_sector', lambda r: selected_layer == r[0])
                self._select_in_combobox_where_callback('po_performer_dir', lambda r: selected.pos.direction.id == r[0])
                self.builder.get_object('po_performer_width').set_text(str(selected.hitbox_w))
                self.builder.get_object('po_performer_height').set_text(str(selected.hitbox_h))

                popover.set_relative_to(self._w_ssa_draw)
                rect = Gdk.Rectangle()
                rect.x = popup_x
                rect.y = popup_y
                popover.set_pointing_to(rect)
                popover.popup()
            elif isinstance(selected, SsaEvent):
                popover: Gtk.Popover = self._w_po_triggers
                if popup_x is None or popup_y is None:
                    popup_x, popup_y = popover_position(*tuple(x * self._scale_factor for x in self.drawer.get_bb_trigger(selected)))
                self._select_in_combobox_where_callback('po_trigger_id', lambda r: selected.trigger_id == self.ssa.triggers.index(r[0]))
                self._select_in_combobox_where_callback('po_trigger_sector', lambda r: selected_layer == r[0])
                self.builder.get_object('po_trigger_width').set_text(str(selected.trigger_width))
                self.builder.get_object('po_trigger_height').set_text(str(selected.trigger_height))

                popover.set_relative_to(self._w_ssa_draw)
                rect = Gdk.Rectangle()
                rect.x = popup_x
                rect.y = popup_y
                popover.set_pointing_to(rect)
                popover.popup()
            if popover is not None:
                self._currently_open_popover = popover
        self._currently_selected_entity = selected
        self._currently_selected_entity_layer = selected_layer

    def _add_entity_to_list(self, entity: Union[SsaActor, SsaObject, SsaPerformer, SsaEvent], layer: int):
        tree = self._get_list_for(entity)
        if isinstance(entity, SsaActor):
            tree.get_model().append(self._list_entry_generate_actor(layer, entity))
        elif isinstance(entity, SsaObject):
            tree.get_model().append(self._list_entry_generate_object(layer, entity))
        elif isinstance(entity, SsaPerformer):
            tree.get_model().append(self._list_entry_generate_performer(layer, entity))
        elif isinstance(entity, SsaEvent):
            tree.get_model().append(self._list_entry_generate_trigger(layer, entity))

    def _select_in_combobox_where_callback(self, cb_name: str, callback: Callable[[Mapping], bool]):
        cb: Gtk.ComboBox = self.builder.get_object(cb_name)
        l_iter = cb.get_model().get_iter_first()
        while l_iter is not None:
            if callback(cb.get_model()[l_iter]):
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)

    def _init_ssa(self):
        self.ssa = self.module.get_ssa(self.filename)

    def _init_all_the_stores(self):
        self._suppress_events = True
        # MAP BGS
        map_bg_list: BgList = self.map_bg_module.bgs
        tool_choose_map_bg_cb: Gtk.ComboBox = self.builder.get_object('tool_choose_map_bg_cb')
        map_bg_store = Gtk.ListStore(int, str)  # ID, BMA name
        default_bg = map_bg_store.append([-1, _("None")])
        for i, entry in enumerate(map_bg_list.level):
            bg_iter = map_bg_store.append([i, entry.bma_name])
            if i == self.mapbg_id:
                default_bg = bg_iter
        self._fast_set_comboxbox_store(tool_choose_map_bg_cb, map_bg_store, 1)
        tool_choose_map_bg_cb.set_active_iter(default_bg)

        # EVENTS - TODO: Unify naming of SSA events/triggers with the UI!
        ssa_events: Gtk.TreeView = self.builder.get_object('ssa_events')
        # (obj, coroutine name, script name, unk2, unk3)
        events_list_store = Gtk.ListStore(object, str, str, int, int)
        ssa_events.append_column(resizable(TreeViewColumn(_("Triggered Script"), Gtk.CellRendererText(), text=2)))
        ssa_events.append_column(resizable(TreeViewColumn(_("Coroutine"), Gtk.CellRendererText(), text=1)))
        ssa_events.append_column(resizable(TreeViewColumn(_("Unk2"), Gtk.CellRendererText(), text=3)))
        ssa_events.append_column(resizable(TreeViewColumn(_("Unk3"), Gtk.CellRendererText(), text=4)))
        ssa_events.set_model(events_list_store)
        for event in self.ssa.triggers:
            events_list_store.append(self._list_entry_generate_event(event))

        # SCRIPTS
        ssa_scripts: Gtk.TreeView = self.builder.get_object('ssa_scripts')
        # (short path (relative to scene), display name)
        scripts_list_store = Gtk.ListStore(str, str)
        ssa_scripts.append_column(resizable(TreeViewColumn(_("Name"), Gtk.CellRendererText(), text=1)))
        ssa_scripts.set_model(scripts_list_store)
        for script in self.scripts:
            scripts_list_store.append([
                script,
                self._get_file_shortname(script)
            ])

        # SCENES FOR MAP
        ssa_scenes: Gtk.TreeView = self.builder.get_object('ssa_scenes')
        # (filename)
        scenes_list_store = Gtk.ListStore(str)
        ssa_scenes.append_column(resizable(TreeViewColumn(_("Name"), Gtk.CellRendererText(), text=0)))
        ssa_scenes.set_model(scenes_list_store)
        select_iter_current_scene = None
        for scene in self.module.get_scenes_for_map(self.mapname):
            it = scenes_list_store.append(self._list_entry_generate_scene(scene))
            if scene == self.filename.split('/')[-1]:
                select_iter_current_scene = it
        if select_iter_current_scene is not None:
            ssa_scenes.get_selection().select_iter(select_iter_current_scene)

        # ENTITY LISTS (STORE SETUP)
        # Are filled later (under layers; with the layer data)
        # ssa_actors
        ssa_actors: Gtk.TreeView = self.builder.get_object('ssa_actors')
        # (layer, entity, kind, script name)
        actors_list_store = Gtk.ListStore(int, object, str, str)
        ssa_actors.append_column(resizable(TreeViewColumn(_("Sector"), Gtk.CellRendererText(), text=0)))
        ssa_actors.append_column(resizable(TreeViewColumn(_("Kind"), Gtk.CellRendererText(), text=2)))
        ssa_actors.append_column(resizable(TreeViewColumn(_("Talk Script"), Gtk.CellRendererText(), text=3)))
        ssa_actors.set_model(actors_list_store)

        # ssa_objects
        ssa_objects: Gtk.TreeView = self.builder.get_object('ssa_objects')
        # (layer, entity, kind, script name)
        objects_list_store = Gtk.ListStore(int, object, str, str)
        ssa_objects.append_column(resizable(TreeViewColumn(_("Sector"), Gtk.CellRendererText(), text=0)))
        ssa_objects.append_column(resizable(TreeViewColumn(_("Kind"), Gtk.CellRendererText(), text=2)))
        ssa_objects.append_column(resizable(TreeViewColumn(_("Talk Script"), Gtk.CellRendererText(), text=3)))
        ssa_objects.set_model(objects_list_store)

        # ssa_performers
        ssa_performers: Gtk.TreeView = self.builder.get_object('ssa_performers')
        # (layer, entity, kind)
        performers_list_store = Gtk.ListStore(int, object, str)
        ssa_performers.append_column(resizable(TreeViewColumn(_("Sector"), Gtk.CellRendererText(), text=0)))
        ssa_performers.append_column(resizable(TreeViewColumn(_("Type"), Gtk.CellRendererText(), text=2)))
        ssa_performers.set_model(performers_list_store)

        # ssa_triggers
        ssa_triggers: Gtk.TreeView = self.builder.get_object('ssa_triggers')
        # (layer, entity, event coroutine name)
        triggers_list_store = Gtk.ListStore(int, object, str)
        ssa_triggers.append_column(resizable(TreeViewColumn(_("Sector"), Gtk.CellRendererText(), text=0)))
        ssa_triggers.append_column(resizable(TreeViewColumn(_("Event Script"), Gtk.CellRendererText(), text=2)))
        ssa_triggers.set_model(triggers_list_store)
        
        # POPOVERS
        # > PO - Sectors [STORE SETUP]
        po_sector_store = Gtk.ListStore(int, str)  # ID, name
        
        po_actor_sector: Gtk.ComboBox = self.builder.get_object('po_actor_sector')
        self._fast_set_comboxbox_store(po_actor_sector, po_sector_store, 1)
        
        po_object_sector: Gtk.ComboBox = self.builder.get_object('po_object_sector')
        self._fast_set_comboxbox_store(po_object_sector, po_sector_store, 1)
        
        po_performer_sector: Gtk.ComboBox = self.builder.get_object('po_performer_sector')
        self._fast_set_comboxbox_store(po_performer_sector, po_sector_store, 1)
        
        po_trigger_sector: Gtk.ComboBox = self.builder.get_object('po_trigger_sector')
        self._fast_set_comboxbox_store(po_trigger_sector, po_sector_store, 1)

        # > PO - Directions
        po_direction_store = Gtk.ListStore(int, str)  # ID, name
        for direction in self.static_data.script_data.directions.values():
            po_direction_store.append([direction.id, direction.print_name])
        
        po_actor_direction: Gtk.ComboBox = self.builder.get_object('po_actor_dir')
        self._fast_set_comboxbox_store(po_actor_direction, po_direction_store, 1)
        
        po_object_direction: Gtk.ComboBox = self.builder.get_object('po_object_dir')
        self._fast_set_comboxbox_store(po_object_direction, po_direction_store, 1)
        
        po_performer_direction: Gtk.ComboBox = self.builder.get_object('po_performer_dir')
        self._fast_set_comboxbox_store(po_performer_direction, po_direction_store, 1)

        # > PO - Talk Script
        po_script_store = Gtk.ListStore(int, str)  # ID, name
        po_script_store.append([-1, _('None')])
        for s_i, script in [(self._script_id(script, as_int=True), self._get_file_shortname(script)) for script in self.scripts]:
            po_script_store.append([s_i, script])
        
        po_actor_script: Gtk.ComboBox = self.builder.get_object('po_actor_script')
        self._fast_set_comboxbox_store(po_actor_script, po_script_store, 1)
        
        po_object_script: Gtk.ComboBox = self.builder.get_object('po_object_script')
        self._fast_set_comboxbox_store(po_object_script, po_script_store, 1)

        # > PO - Kinds
        # Actors
        po_actor_kind_store = Gtk.ListStore(int, str)  # ID, name
        for actor_kind in self.static_data.script_data.level_entities:
            po_actor_kind_store.append([actor_kind.id, actor_kind.name])
        
        po_actor_kind: Gtk.ComboBox = self.builder.get_object('po_actor_kind')
        self._fast_set_comboxbox_store(po_actor_kind, po_actor_kind_store, 1)
        
        # Objects
        po_object_kind_store = Gtk.ListStore(int, str)  # ID, name
        for object_kind in self.static_data.script_data.objects:
            po_object_kind_store.append([object_kind.id, object_kind.unique_name])
        
        po_object_kind: Gtk.ComboBox = self.builder.get_object('po_object_kind')
        self._fast_set_comboxbox_store(po_object_kind, po_object_kind_store, 1)
        
        # Performer
        po_performer_kind_store = Gtk.ListStore(int, str)  # ID, name
        # TODO: Put into scriptdata when knowing what they do, also
        #       see SsaPerformer model.
        for performer_type in [0, 1, 2, 3, 4, 5]:
            po_performer_kind_store.append([performer_type, f(_('Type {performer_type}'))])

        po_performer_kind: Gtk.ComboBox = self.builder.get_object('po_performer_kind')
        self._fast_set_comboxbox_store(po_performer_kind, po_performer_kind_store, 1)
        
        # Trigger
        po_trigger_id_store = Gtk.ListStore(object, str)  # event object, name
        for e_i, event in enumerate(self.ssa.triggers):
            po_trigger_id_store.append([event, f"{self._get_talk_script_name(event.script_id)} "
                                             f"/ {self._get_coroutine_name(event.coroutine)}"])

        po_trigger_id: Gtk.ComboBox = self.builder.get_object('po_trigger_id')
        self._fast_set_comboxbox_store(po_trigger_id, po_trigger_id_store, 1)

        # LAYERS
        ssa_layers: Gtk.TreeView = self.builder.get_object('ssa_layers')
        # (index, display_name, visible, solo)
        layer_list_store = Gtk.ListStore(int, str, bool, bool)
        renderer_visible = Gtk.CellRendererToggle()
        renderer_visible.connect("toggled", partial(self.on_ssa_layers_visible_toggled, layer_list_store))
        ssa_layers.append_column(column_with_tooltip(_("V"),  # TRANSLATOR: First letter of 'Visible'
                                                     _("Visible"), renderer_visible, "active", 2))
        renderer_solo = Gtk.CellRendererToggle()
        renderer_solo.connect("toggled", partial(self.on_ssa_layers_solo_toggled, layer_list_store))
        ssa_layers.append_column(column_with_tooltip(_("S"),  # TRANSLATOR: First letter of 'Solo'
                                                     _("Solo"), renderer_solo, "active", 3))
        ssa_layers.append_column(resizable(TreeViewColumn(_("Name"), Gtk.CellRendererText(), text=1)))
        ssa_layers.set_model(layer_list_store)
        for i, layer in enumerate(self.ssa.layer_list):
            layer_list_store.append(self._list_entry_generate_layer(i, layer))

            # ENTITY LISTS (DATA)
            # ssa_actors
            for actor in layer.actors:
                # (layer, entity, kind, script name)
                actors_list_store.append(self._list_entry_generate_actor(i, actor))
            # ssa_objects
            for obj in layer.objects:
                # (layer, entity, kind, script name)
                objects_list_store.append(self._list_entry_generate_object(i, obj))
            # ssa_performers
            for performer in layer.performers:
                # (layer, entity, kind, script name)
                performers_list_store.append(self._list_entry_generate_performer(i, performer))
            # ssa_triggers
            for trigger in layer.events:
                # (layer, entity, event coroutine name)
                triggers_list_store.append(self._list_entry_generate_trigger(i, trigger))
                
            # > PO - Sectors [DATA]
            po_sector_store.append([i, f(_('Sector {i}'))])

        self._suppress_events = False

    def _init_drawer(self):
        self.drawer = Drawer(self._w_ssa_draw, self.ssa,
                             partial(self._get_event_script_name, self.ssa.triggers, short=True),
                             self.module.get_sprite_provider())
        self.drawer.start()

        self.drawer.set_draw_tile_grid(self.builder.get_object(f'tool_scene_grid').get_active())

    def _set_drawer_bg(self, surface: cairo.Surface, w: int, h: int):
        self._map_bg_width = w
        self._map_bg_height = h
        self._w_ssa_draw.set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        self.drawer.map_bg = surface
        self._w_ssa_draw.queue_draw()

    def _update_scales(self):
        self._w_ssa_draw.set_size_request(
            self._map_bg_width * self._scale_factor, self._map_bg_height * self._scale_factor
        )
        if self.drawer:
            self.drawer.set_scale(self._scale_factor)

        self._w_ssa_draw.queue_draw()

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _list_entry_generate_event(self, event: SsaTrigger):
        return [
            event,
            self._get_coroutine_name(event.coroutine),
            self._get_talk_script_name(event.script_id),
            event.unk2,
            event.unk3
        ]

    def _list_entry_generate_scene(self, scene):
        return [
            self._get_file_shortname(scene)
        ]

    def _list_entry_generate_actor(self, layer_id, actor: SsaActor):
        return [
            layer_id, actor,
            self._get_actor_name(actor),
            self._get_talk_script_name(actor.script_id)
        ]

    def _list_entry_generate_object(self, layer_id, obj: SsaObject):
        return [
            layer_id, obj,
            self._get_object_name(obj),
            self._get_talk_script_name(obj.script_id)
        ]

    def _list_entry_generate_performer(self, layer_id, performer: SsaPerformer):
        return [
            layer_id, performer,
            self._get_performer_name(performer)
        ]

    def _list_entry_generate_trigger(self, layer_id, trigger: SsaEvent):
        return [
            layer_id, trigger,
            self._get_event_script_name(self.ssa.triggers, trigger.trigger_id)
        ]

    def _list_entry_generate_layer(self, i, layer):
        return [
            i, f'Sector {i} ({self._get_layer_content_string(layer)})', True, False
        ]

    def _get_coroutine_name(self, coroutine: Pmd2ScriptRoutine):
        return coroutine.name

    def _get_talk_script_name(self, script_id: int):
        if script_id == -1:
            return _('None')
        if self.type == 'ssa':
            if len(self.scripts) < 1:
                return '???'
            if script_id > 0:
                return f(_('?INVALID? {script_id}'))
            return self.scripts[script_id]
        for script_name in self.scripts:
            if self._talk_script_matches(script_name, script_id):
                return script_name
        return self.scripts[script_id]

    @staticmethod
    def _get_file_shortname(path: str):
        return path.split('/')[-1]

    @staticmethod
    def _get_layer_content_string(layer: SsaLayer):
        len_actors = len(layer.actors)
        len_objects = len(layer.objects)
        len_performers = len(layer.performers)
        len_triggers = len(layer.events)
        if len_actors + len_objects + len_performers + len_triggers < 1:
            return 'empty'
        ret_str = ''
        if len_actors > 0:
            ret_str += f(_('{len_actors} acts, '))  # TRANSLATOR: actors
        if len_objects > 0:
            ret_str += f(_('{len_objects} objs, '))  # TRANSLATOR: objects
        if len_performers > 0:
            ret_str += f(_('{len_performers} prfs, '))  # TRANSLATOR: performers
        if len_triggers > 0:
            ret_str += f(_('{len_triggers} trgs'))  # TRANSLATOR: triggers

        return ret_str.rstrip(', ')

    @staticmethod
    def _get_actor_name(actor: SsaActor):
        return actor.actor.name

    @staticmethod
    def _get_object_name(object: SsaObject):
        return object.object.unique_name

    def _get_performer_name(self, performer: SsaPerformer):
        return f(_('Type {performer.type}'))

    def _get_event_script_name(self, events: List[SsaTrigger], event_id: int, short=False) -> str:
        if len(events) < event_id + 1:
            return f'??? {event_id}'
        name = self._get_talk_script_name(events[event_id].script_id)
        if short:
            return self._script_id(name)
        return name

    def _script_id(self, name, as_int=False) -> Union[str, int]:
        if not as_int:
            return name[-6:-4]
        try:
            return int(name[-6:-4])
        except ValueError:
            return 0

    def _talk_script_matches(self, script_name, script_id):
        try:
            suffix = self._script_id(script_name, as_int=True)
            if suffix == script_id:
                return True
        except ValueError:
            return False
        return False

    def _get_event_dialog_script_names(self):
        return {self._script_id(script, as_int=True): self._get_file_shortname(script) for script in self.scripts}

    def _build_pos(self, x: float, y: float, dir=True) -> SsaPosition:
        direction = 1 if dir else None
        x /= BPC_TILE_DIM
        y /= BPC_TILE_DIM
        x_relative = math.floor(x)
        y_relative = math.floor(y)
        x_offset = 2 if x % 1 != 0 else 0
        y_offset = 2 if y % 1 != 0 else 0
        return SsaPosition(self.static_data.script_data, x_relative, y_relative, x_offset, y_offset, direction)

    def _show_generic_input(self, label_text, ok_text):
        dialog: Gtk.Dialog = self.builder.get_object('generic_input_dialog')
        entry: Gtk.Entry = self.builder.get_object('generic_input_dialog_entry')
        label: Gtk.Label = self.builder.get_object('generic_input_dialog_label')
        label.set_text(label_text)
        btn_cancel = dialog.add_button(_("Cancel"), Gtk.ResponseType.CANCEL)
        btn = dialog.add_button(ok_text, Gtk.ResponseType.OK)
        btn.set_can_default(True)
        btn.grab_default()
        entry.set_activates_default(True)
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())
        response = dialog.run()
        dialog.hide()
        btn.get_parent().remove(btn)
        btn_cancel.get_parent().remove(btn_cancel)
        return response, entry.get_text()
