#  Copyright 2020 Parakoopa
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
from functools import partial
from typing import TYPE_CHECKING, Optional, List

import cairo
from gi.repository import Gtk, Gdk
from gi.repository.Gtk import TreeViewColumn

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple.core.open_request import REQUEST_TYPE_MAP_BG, OpenRequest, REQUEST_TYPE_SCENE_SSE, \
    REQUEST_TYPE_SCENE_SSA, REQUEST_TYPE_SCENE_SSS
from skytemple.module.script.drawer import Drawer
from skytemple_files.common.ppmdu_config.data import Pmd2Data
from skytemple_files.common.ppmdu_config.script_data import Pmd2ScriptRoutine
from skytemple_files.graphics.bg_list_dat.model import BgList
from skytemple_files.graphics.bpc.model import BPC_TILE_DIM
from skytemple_files.script.ssa_sse_sss.actor import SsaActor
from skytemple_files.script.ssa_sse_sss.layer import SsaLayer
from skytemple_files.script.ssa_sse_sss.model import Ssa
from skytemple_files.script.ssa_sse_sss.object import SsaObject
from skytemple_files.script.ssa_sse_sss.performer import SsaPerformer
from skytemple_files.script.ssa_sse_sss.trigger import SsaTrigger

if TYPE_CHECKING:
    from skytemple.module.script.module import ScriptModule
    from skytemple.module.map_bg.module import MapBgModule


SIZE_REQUEST_NONE = 500


def resizable(column):
    column.set_resizable(True)
    return column


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

        self.builder = None

        if self.__class__._last_scale_factor is not None:
            self._scale_factor = self.__class__._last_scale_factor
        else:
            self._scale_factor = 1
        self._bg_draw_is_clicked = False
        self._map_bg_width = SIZE_REQUEST_NONE
        self._map_bg_height = SIZE_REQUEST_NONE
        self._map_bg_surface = None
        self._suppress_events = False

        self._w_ssa_draw: Optional[Gtk.DrawingArea] = None

        self.ssa: Optional[Ssa] = None

        self.drawer: Optional[Drawer] = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'ssa.glade')
        self._w_ssa_draw = self.builder.get_object('ssa_draw')

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
        correct_mouse_x = int((button.x - 4) / self._scale_factor)
        correct_mouse_y = int((button.y - 4) / self._scale_factor)
        if button.button == 1:
            self._bg_draw_is_clicked = True
            # Snap to 0,5 tiles
            snap_x = correct_mouse_x - correct_mouse_x % (BPC_TILE_DIM / 2)
            snap_y = correct_mouse_y - correct_mouse_y % (BPC_TILE_DIM / 2)
            self.drawer.set_mouse_position(snap_x, snap_y)
        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_button_release_event(self, box, button: Gdk.EventButton):
        if button.button == 1:
            self._bg_draw_is_clicked = False
        self._w_ssa_draw.queue_draw()

    def on_ssa_draw_event_motion_notify_event(self, box, motion: Gdk.EventMotion):
        correct_mouse_x = int((motion.x - 4) / self._scale_factor)
        correct_mouse_y = int((motion.y - 4) / self._scale_factor)
        if self.drawer:
            # Snap to 0,5 tiles
            snap_x = correct_mouse_x - correct_mouse_x % (BPC_TILE_DIM / 2)
            snap_y = correct_mouse_y - correct_mouse_y % (BPC_TILE_DIM / 2)
            self.drawer.set_mouse_position(snap_x, snap_y)
            # TODO:
            #if self.bg_draw_is_clicked:
            #    self._set_col_at_pos(snap_x, snap_y)
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
        pass

    def on_tool_scene_add_actor_toggled(self, *args):
        pass

    def on_tool_scene_add_object_toggled(self, *args):
        pass

    def on_tool_scene_add_performer_toggled(self, *args):
        pass

    def on_tool_scene_add_trigger_toggled(self, *args):
        pass

    def on_tool_choose_map_bg_cb_changed(self, w: Gtk.ComboBox):
        model, cbiter = w.get_model(), w.get_active_iter()
        if model is not None and cbiter is not None and cbiter != []:
            item_id = model[cbiter][0]
            if self.__class__.map_bg_surface_cache[0] == item_id:
                self._map_bg_surface, bma_width, bma_height = self.__class__.map_bg_surface_cache[1:]
            else:
                bma = self.map_bg_module.get_bma(item_id)
                bpl = self.map_bg_module.get_bpl(item_id)
                bpc = self.map_bg_module.get_bpc(item_id)
                bpas = self.map_bg_module.get_bpas(item_id)
                self._map_bg_surface = pil_to_cairo_surface(
                    bma.to_pil(bpc, bpl.palettes, bpas, False, False)[0].convert('RGBA')
                )
                bma_width = bma.map_width_camera * BPC_TILE_DIM
                bma_height = bma.map_height_camera * BPC_TILE_DIM
                self.__class__.map_bg_surface_cache = (item_id, self._map_bg_surface, bma_width, bma_height)
            if self.drawer:
                self._set_drawer_bg(self._map_bg_surface, bma_width, bma_height)

    def on_tool_scene_goto_bg_clicked(self, *args):
        self.module.project.request_open(OpenRequest(
            REQUEST_TYPE_MAP_BG, self.mapname
        ))

    # EVENTS TOOLBAR #
    def on_tool_events_add_clicked(self, *args):
        pass

    def on_tool_events_remove_clicked(self, *args):
        pass

    def on_tool_events_edit_clicked(self, *args):
        pass

    # SECTOR TOOLBAR #
    def on_tool_sector_add_clicked(self, *args):
        pass

    def on_tool_sector_remove_clicked(self, *args):
        pass

    # SCRIPT TOOLBAR #
    def on_tool_script_edit_clicked(self, *args):
        pass

    def on_tool_script_add_clicked(self, *args):
        pass

    def on_tool_script_remove_clicked(self, *args):
        pass

    # ACTOR OVERLAY #
    def on_po_actor_sector_changed(self, *args):
        pass

    def on_po_actor_kind_changed(self, *args):
        pass

    def on_po_actor_script_changed(self, *args):
        pass

    def on_po_actor_delete_clicked(self, *args):
        pass

    # OBJECT OVERLAY #
    def on_po_object_sector_changed(self, *args):
        pass

    def on_po_object_kind_changed(self, *args):
        pass

    def on_po_object_script_changed(self, *args):
        pass

    def on_po_object_width_changed(self, *args):
        pass

    def on_po_object_height_changed(self, *args):
        pass

    def on_po_object_delete_clicked(self, *args):
        pass

    # PERFORMER OVERLAY #
    def on_po_performer_sector_changed(self, *args):
        pass

    def on_po_performer_kind_changed(self, *args):
        pass

    def on_po_performer_width_changed(self, *args):
        pass

    def on_po_performer_height_changed(self, *args):
        pass

    def on_po_performer_delete_clicked(self, *args):
        pass

    # TRIGGER OVERLAY #
    def on_po_trigger_sector_changed(self, *args):
        pass

    def on_po_trigger_id_changed(self, *args):
        pass

    def on_po_trigger_width_changed(self, *args):
        pass

    def on_po_trigger_height_changed(self, *args):
        pass

    def on_po_trigger_delete_clicked(self, *args):
        pass

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

    def _init_ssa(self):
        self.ssa = self.module.get_ssa(self.filename)

    def _init_all_the_stores(self):
        self._suppress_events = True
        # MAP BGS
        map_bg_list: BgList = self.map_bg_module.bgs
        tool_choose_map_bg_cb: Gtk.ComboBox = self.builder.get_object('tool_choose_map_bg_cb')
        map_bg_store = Gtk.ListStore(int, str)  # ID, BPL name
        default_bg = map_bg_store.append([-1, "None"])
        for i, entry in enumerate(map_bg_list.level):
            bg_iter = map_bg_store.append([i, entry.bpl_name])
            if entry.bpl_name == self.mapname:
                default_bg = bg_iter
        self._fast_set_comboxbox_store(tool_choose_map_bg_cb, map_bg_store, 1)
        tool_choose_map_bg_cb.set_active_iter(default_bg)

        # EVENTS - TODO: Unify naming of SSA events/triggers with the UI!
        ssa_events: Gtk.TreeView = self.builder.get_object('ssa_events')
        # ID is index; (obj, coroutine name, script name, unk2, unk3)
        events_list_store = Gtk.ListStore(object, str, str, int, int)
        ssa_events.append_column(resizable(TreeViewColumn("Triggered Script", Gtk.CellRendererText(), text=2)))
        ssa_events.append_column(resizable(TreeViewColumn("Coroutine", Gtk.CellRendererText(), text=1)))
        ssa_events.append_column(resizable(TreeViewColumn("Unk2", Gtk.CellRendererText(), text=3)))
        ssa_events.append_column(resizable(TreeViewColumn("Unk3", Gtk.CellRendererText(), text=4)))
        ssa_events.set_model(events_list_store)
        for event in self.ssa.triggers:
            events_list_store.append(self._list_entry_generate_event(event))

        # SCRIPTS
        ssa_scripts: Gtk.TreeView = self.builder.get_object('ssa_scripts')
        # (full path, display name)
        scripts_list_store = Gtk.ListStore(str, str)
        ssa_scripts.append_column(resizable(TreeViewColumn("Name", Gtk.CellRendererText(), text=1)))
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
        ssa_scenes.append_column(resizable(TreeViewColumn("Name", Gtk.CellRendererText(), text=0)))
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
        # (layer, index in layer, kind, script name)
        actors_list_store = Gtk.ListStore(int, int, str, str)
        ssa_actors.append_column(resizable(TreeViewColumn("Sector", Gtk.CellRendererText(), text=0)))
        ssa_actors.append_column(resizable(TreeViewColumn("Kind", Gtk.CellRendererText(), text=2)))
        ssa_actors.append_column(resizable(TreeViewColumn("Talk Script", Gtk.CellRendererText(), text=3)))
        ssa_actors.set_model(actors_list_store)

        # ssa_objects
        ssa_objects: Gtk.TreeView = self.builder.get_object('ssa_objects')
        # (layer, index in layer, kind, script name)
        objects_list_store = Gtk.ListStore(int, int, str, str)
        ssa_objects.append_column(resizable(TreeViewColumn("Sector", Gtk.CellRendererText(), text=0)))
        ssa_objects.append_column(resizable(TreeViewColumn("Kind", Gtk.CellRendererText(), text=2)))
        ssa_objects.append_column(resizable(TreeViewColumn("Talk Script", Gtk.CellRendererText(), text=3)))
        ssa_objects.set_model(objects_list_store)

        # ssa_performers
        ssa_performers: Gtk.TreeView = self.builder.get_object('ssa_performers')
        # (layer, index in layer, kind)
        performers_list_store = Gtk.ListStore(int, int, str)
        ssa_performers.append_column(resizable(TreeViewColumn("Sector", Gtk.CellRendererText(), text=0)))
        ssa_performers.append_column(resizable(TreeViewColumn("Type", Gtk.CellRendererText(), text=2)))
        ssa_performers.set_model(performers_list_store)

        # ssa_triggers
        ssa_triggers: Gtk.TreeView = self.builder.get_object('ssa_triggers')
        # (layer, index in layer, event coroutine name)
        triggers_list_store = Gtk.ListStore(int, int, str)
        ssa_triggers.append_column(resizable(TreeViewColumn("Sector", Gtk.CellRendererText(), text=0)))
        ssa_triggers.append_column(resizable(TreeViewColumn("Event Script", Gtk.CellRendererText(), text=2)))
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
            po_direction_store.append([direction.id, direction.name])
        
        po_actor_direction: Gtk.ComboBox = self.builder.get_object('po_actor_dir')
        self._fast_set_comboxbox_store(po_actor_direction, po_direction_store, 1)
        
        po_object_direction: Gtk.ComboBox = self.builder.get_object('po_object_dir')
        self._fast_set_comboxbox_store(po_object_direction, po_direction_store, 1)
        
        po_performer_direction: Gtk.ComboBox = self.builder.get_object('po_performer_dir')
        self._fast_set_comboxbox_store(po_performer_direction, po_direction_store, 1)

        # > PO - Talk Script
        po_script_store = Gtk.ListStore(int, str)  # ID, name
        for s_i, script in enumerate([self._get_file_shortname(script) for script in self.scripts]):
            po_script_store.append([s_i, script])
        
        po_actor_script: Gtk.ComboBox = self.builder.get_object('po_actor_script')
        self._fast_set_comboxbox_store(po_actor_script, po_script_store, 1)
        
        po_object_script: Gtk.ComboBox = self.builder.get_object('po_object_script')
        self._fast_set_comboxbox_store(po_object_script, po_script_store, 1)

        # > PO - Kinds
        # Actors
        po_actor_kind_store = Gtk.ListStore(int, str)  # ID, name
        for actor_kind in self.static_data.script_data.level_entities:
            po_script_store.append([actor_kind.id, actor_kind.name])
        
        po_actor_kind: Gtk.ComboBox = self.builder.get_object('po_actor_kind')
        self._fast_set_comboxbox_store(po_actor_kind, po_actor_kind_store, 1)
        
        # Objects
        po_object_kind_store = Gtk.ListStore(int, str)  # ID, name
        for object_kind in self.static_data.script_data.objects:
            po_script_store.append([object_kind.id, object_kind.name])
        
        po_object_kind: Gtk.ComboBox = self.builder.get_object('po_object_kind')
        self._fast_set_comboxbox_store(po_object_kind, po_object_kind_store, 1)
        
        # Performer
        po_performer_kind_store = Gtk.ListStore(int, str)  # ID, name
        # TODO: Put into scriptdata when knowing what they do, also
        #       see SsaPerformer model.
        for performer_type in [0, 1, 2, 3, 4, 5]:
            po_script_store.append([performer_type, f'Type {performer_type}'])

        po_performer_kind: Gtk.ComboBox = self.builder.get_object('po_performer_kind')
        self._fast_set_comboxbox_store(po_performer_kind, po_performer_kind_store, 1)
        
        # Trigger
        po_trigger_id_store = Gtk.ListStore(int, str)  # ID, name
        # TODO: This store must be synced with the event list updating!
        for e_i, event in enumerate(self.ssa.triggers):
            po_script_store.append([e_i, self._get_talk_script_name(event.script_id)])

        po_trigger_id: Gtk.ComboBox = self.builder.get_object('po_trigger_id')
        self._fast_set_comboxbox_store(po_trigger_id, po_trigger_id_store, 1)

        # LAYERS
        ssa_layers: Gtk.TreeView = self.builder.get_object('ssa_layers')
        # ID is index; (display_name)
        layer_list_store = Gtk.ListStore(str)
        ssa_layers.append_column(resizable(TreeViewColumn("Name", Gtk.CellRendererText(), text=0)))
        ssa_layers.set_model(layer_list_store)
        for i, layer in enumerate(self.ssa.layer_list):
            layer_list_store.append([
                # TODO: Don't forget to update this, when adding / removing
                f'Sector {i} ({self._get_layer_content_string(layer)})'
            ])

            # ENTITY LISTS (DATA)
            # ssa_actors
            for e_i, actor in enumerate(layer.actors):
                # (layer, index in layer, kind, script name)
                actors_list_store.append(self._list_entry_generate_actor(i, e_i, actor))
            # ssa_objects
            for e_i, obj in enumerate(layer.objects):
                # (layer, index in layer, kind, script name)
                objects_list_store.append(self._list_entry_generate_object(i, e_i, obj))
            # ssa_performers
            for e_i, performer in enumerate(layer.performers):
                # (layer, index in layer, kind, script name)
                performers_list_store.append(self._list_entry_generate_performer(i, e_i, performer))
            # ssa_triggers
            for e_i, trigger in enumerate(layer.events):
                # (layer, index in layer, event coroutine name)
                triggers_list_store.append(self._list_entry_generate_trigger(i, e_i, trigger))
                
            # > PO - Sectors [DATA]
            po_sector_store.append([i, f'Sector {i}'])

        self._suppress_events = False

    def _init_drawer(self):
        self.drawer = Drawer(self._w_ssa_draw, self.ssa, partial(self._get_event_script_name, self.ssa.triggers, short=True))
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

    def _list_entry_generate_event(self, event):
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

    def _list_entry_generate_actor(self, layer_id, idx_in_layer, actor):
        return [
            layer_id, idx_in_layer, 
            self._get_actor_name(actor),
            self._get_talk_script_name(actor.script_id)
        ]

    def _list_entry_generate_object(self, layer_id, idx_in_layer, obj):
        return [
            layer_id, idx_in_layer,
            self._get_object_name(obj),
            self._get_talk_script_name(obj.script_id)
        ]

    def _list_entry_generate_performer(self, layer_id, idx_in_layer, performer):
        return [
            layer_id, idx_in_layer,
            self._get_performer_name(performer)
        ]

    def _list_entry_generate_trigger(self, layer_id, idx_in_layer, trigger):
        return [
            layer_id, idx_in_layer,
            self._get_event_script_name(self.ssa.triggers, trigger.trigger_id)
        ]

    def _get_coroutine_name(self, coroutine: Pmd2ScriptRoutine):
        return coroutine.name

    def _get_talk_script_name(self, script_id: int):
        if self.type == 'ssa':
            if len(self.scripts) < 1:
                return '???'
            if script_id > 0:
                return f'?INVALID? {script_id}'
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
            ret_str += f'{len_actors} acts, '
        if len_objects > 0:
            ret_str += f'{len_objects} objs, '
        if len_performers > 0:
            ret_str += f'{len_performers} prfs, '
        if len_triggers > 0:
            ret_str += f'{len_triggers} trgs'

        return ret_str.rstrip(', ')

    @staticmethod
    def _get_actor_name(actor: SsaActor):
        return actor.actor.name

    @staticmethod
    def _get_object_name(object: SsaObject):
        return object.object.unique_name

    def _get_performer_name(self, performer: SsaPerformer):
        return f'Type {performer.type}'

    def _get_event_script_name(self, events: List[SsaTrigger], event_id: int, short=False) -> str:
        if len(events) < event_id + 1:
            return f'??? {event_id}'
        name = self._get_talk_script_name(events[event_id].script_id)
        if short:
            return name[-6:-4]
        return name

    def _talk_script_matches(self, script_name, script_id):
        try:
            suffix = int(script_name[-6:-4])
            if suffix == script_id:
                return True
        except ValueError:
            return False
        return False
