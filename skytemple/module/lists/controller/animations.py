#  Copyright 2020-2021 Capypara and the SkyTemple Contributors
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
import sys
import webbrowser
from typing import TYPE_CHECKING, Optional, List

from skytemple_files.common.i18n_util import _, f

from gi.repository import Gtk

from skytemple_files.data.anim import *
from skytemple_files.data.anim.model import *
from skytemple.core.ui_utils import glib_async
from skytemple.core.error_handler import display_error
from skytemple.controller.main import MainController
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple_files.common.util import open_utf8
from skytemple.module.lists.controller.base import PATTERN_MD_ENTRY

if TYPE_CHECKING:
    from skytemple.module.moves_items.module import MovesItemsModule
from skytemple_files.common.i18n_util import _

logger = logging.getLogger(__name__)

mapping = {"traps_store":"trap_table",
           "items_store":"item_table",
           "general_store":"general_table",
           "moves_store":"move_table",
           "spec_store":"special_move_table"}
class AnimationsController(AbstractController):
    def __init__(self, module: 'ListsModule', *args):
        super().__init__(module, *args)
        self.module = module
        self.sp_effects = None
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'animations.glade')
        stack: Gtk.Stack = self.builder.get_object('list_stack')

        if not self.module.has_animations():
            stack.set_visible_child(self.builder.get_object('box_na'))
            return stack
        self.animations = self.module.get_animations()

        self._ent_names = dict()
        self._init_monster_store()
        self._init_combos()
        self._init_trees()
        
        stack.set_visible_child(self.builder.get_object('box_list'))
        self.builder.connect_signals(self)
        
        return stack

    def _init_combos(self):
        # Init available menus
        cb_store: Gtk.ListStore = self.builder.get_object('move_filter')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_filter_move')
        # Init combobox
        cb_store.clear()
        cb_store.append([-1, _("Show All")])
        for i,v in enumerate(self.animations.move_table):
            cb_store.append([i, f'{i}: {self._string_provider.get_value(StringType.MOVE_NAMES, i)}'])
        cb.set_active(0)
    
    def _init_trees(self) -> Optional[int]:
        store: Gtk.ListStore = self.builder.get_object('type_store')
        store.clear()
        for v in AnimType:
            store.append([v.value, v.description])

        
        store: Gtk.ListStore = self.builder.get_object('point_store')
        store.clear()
        for v in AnimPointType:
            store.append([v.value, v.description])
        
        tree_store: Gtk.ListStore = self.builder.get_object('traps_store')
        tree_store.clear()
        tmp_view = []
        for i, e in enumerate(self.animations.trap_table):
            tmp_view.append([i,self._string_provider.get_value(StringType.TRAP_NAMES, i),e.anim])
        for x in sorted(tmp_view,key=lambda x:x[1]):
            tree_store.append(x)
        
        tree_store: Gtk.ListStore = self.builder.get_object('items_store')
        tree_store.clear()
        tmp_view = []
        for i, e in enumerate(self.animations.item_table):
            tmp_view.append([i,self._string_provider.get_value(StringType.ITEM_NAMES, i),e.anim1,e.anim2])
        for x in sorted(tmp_view,key=lambda x:x[1]):
            tree_store.append(x)

        self._update_general()
        
        self._update_moves()
        
        self.on_cb_filter_move_changed()

    def _get_move_filter_id(self):
        cb_store: Gtk.ListStore = self.builder.get_object('move_filter')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_filter_move')
        return cb_store[cb.get_active_iter()][0]
    
    def _update_moves(self, *args):
        tree_store: Gtk.ListStore = self.builder.get_object('moves_store')
        tree_store.clear()
        for i, e in enumerate(self.animations.move_table):
            tree_store.append([i,self._string_provider.get_value(StringType.MOVE_NAMES, i), \
                             e.anim1,e.anim2,e.anim3,e.anim4,e.dir,e.flag1,e.flag2,e.flag3,e.flag4,\
                             e.speed,e.animation,e.point.value,e.sfx,e.spec_entries,e.spec_start,e.point.description])
        
    def _update_general(self, *args):
        tree_store: Gtk.ListStore = self.builder.get_object('general_store')
        tree_store.clear()
        for i, e in enumerate(self.animations.general_table):
            tree_store.append([i, e.anim_type.value,e.anim_file,e.unk1,e.unk2,e.sfx,e.unk3,e.unk4, \
                               e.point.value,e.unk5,e.loop,e.anim_type.description,e.point.description])
        
    def _get_pkmn_name(self, pkmn_id):
        pkmn_name = f"??? (${pkmn_id:04})"
        if pkmn_id in self._ent_names:
            pkmn_name = self._ent_names[pkmn_id]
        return pkmn_name
    
    def on_cb_filter_move_changed(self, *args):
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_filter_move')
        if cb.get_active_iter()==None:
            return
        tree_store: Gtk.ListStore = self.builder.get_object('spec_store')
        tree_store.clear()
        move_id = self._get_move_filter_id()
        if move_id<0:
            data = self.animations.special_move_table
            delta = 0
        else:
            mv = self.animations.move_table[move_id]
            delta = mv.spec_start
            data = self.animations.special_move_table[mv.spec_start:mv.spec_start+mv.spec_entries]
        for i, e in enumerate(data):
            tree_store.append([delta+i,e.pkmn_id,e.animation,e.point.value,e.sfx,self._get_pkmn_name(e.pkmn_id),e.point.description])

        
    def on_spec_entity_editing_started(self, renderer, editable, path):
        editable.set_completion(self.builder.get_object('completion_entities'))

    def _init_monster_store(self):
        monster_md = self.module.get_monster_md()
        monster_store: Gtk.ListStore = self.builder.get_object('monster_store')
        for idx, entry in enumerate(monster_md.entries):
            midx = entry.md_index_base
            if self.module.project.is_patch_applied("ExpandPokeList"):
                midx = entry.entid
            if not midx in self._ent_names:
                name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, entry.md_index_base)
                self._ent_names[midx] = f'{name} (${midx:04})'
                monster_store.append([self._ent_names[midx]])
    
    def set_tree_attr(self, path, text, store_name, attr_name, attr_pos):
        try:
            v = int(text)
            tree_store: Gtk.ListStore = self.builder.get_object(store_name)
            tree_store[path][attr_pos] = v
            i = tree_store[path][0]
            setattr(getattr(self.animations, mapping[store_name])[i], attr_name, v)
            self.module.mark_animations_as_modified()
        except ValueError:
            return
    
    def set_tree_bool(self, path, v, store_name, attr_name, attr_pos):
        try:
            tree_store: Gtk.ListStore = self.builder.get_object(store_name)
            tree_store[path][attr_pos] = v
            i = tree_store[path][0]
            setattr(getattr(self.animations, mapping[store_name])[i], attr_name, v)
            self.module.mark_animations_as_modified()
        except ValueError:
            return
        
    def on_trap_anim_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'traps_store', 'anim', 2)
    
    def on_item_anim1_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'items_store', 'anim1', 2)
        
    def on_item_anim2_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'items_store', 'anim2', 3)

    def on_spec_entity_edited(self, widget, path, text):
        match = PATTERN_MD_ENTRY.match(text)
        if match is None:
            return
        entid = match.group(1)
        self.set_tree_attr(path, entid, 'spec_store', 'pkmn_id', 1)
        try:
            v = int(entid)
            tree_store: Gtk.ListStore = self.builder.get_object('spec_store')
            tree_store[path][5] = self._get_pkmn_name(v)
        except ValueError:
            return
        
    def on_spec_anim_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'spec_store', 'animation', 2)

    def on_spec_sfx_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'spec_store', 'sfx', 4)
    
    @glib_async
    def on_spec_point_changed(self, w, treepath, treeiter):
        store_spec: Gtk.ListStore = self.builder.get_object('spec_store')
        store_type: Gtk.ListStore = self.builder.get_object('point_store')
        store_spec[treepath][3] = store_type[treeiter][0]
        store_spec[treepath][6] = store_type[treeiter][1]
        self.animations.special_move_table[store_spec[treepath][0]].point = AnimPointType(store_type[treeiter][0])
        self.module.mark_animations_as_modified()

    def on_btn_remove_spec_clicked(self, *args):
        # Deletes all selected entries
        # Allows multiple deletion
        move_id = self._get_move_filter_id()
        active_rows : List[Gtk.TreePath] = self.builder.get_object('spec_tree').get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = self.builder.get_object('spec_store')
        for v in reversed(sorted(active_rows, key=lambda x:x.get_indices())):
            delta = store[v.get_indices()[0]][0]
            for i,x in enumerate(self.animations.move_table):
                new_spec_end = x.spec_start+x.spec_entries
                new_spec_start = x.spec_start
                if new_spec_end>delta:
                    new_spec_end -= 1
                if new_spec_start>delta:
                    new_spec_start -= 1
                x.spec_start = new_spec_start
                x.spec_entries = new_spec_end-new_spec_start
            del self.animations.special_move_table[delta]
            del store[v.get_indices()[0]]
        self.on_cb_filter_move_changed()
        self._update_moves()
        self.module.mark_animations_as_modified()
        
    def on_btn_add_spec_clicked(self, *args):
        move_id = self._get_move_filter_id()
        if move_id<0:
            delta = len(self.animations.special_move_table)
        else:
            mv = self.animations.move_table[move_id]
            delta = mv.spec_start+mv.spec_entries
            for i,x in enumerate(self.animations.move_table):
                if move_id==i:
                    x.spec_entries+=1
                else:
                    new_spec_end = x.spec_start+x.spec_entries
                    new_spec_start = x.spec_start
                    if new_spec_end>=delta:
                        new_spec_end += 1
                    if new_spec_start>=delta:
                        new_spec_start += 1
                    x.spec_start = new_spec_start
                    x.spec_entries = new_spec_end-new_spec_start
        e = SpecMoveAnim(bytes(SPECIAL_MOVE_DATA_SIZE))
        self.animations.special_move_table.insert(delta, e)
        tree_store: Gtk.ListStore = self.builder.get_object('spec_store')
        tree_store.append([delta,e.pkmn_id,e.animation,e.point.value,e.sfx,self._get_pkmn_name(e.pkmn_id),e.point.description])
        self._update_moves()
        self.module.mark_animations_as_modified()

    def on_move_anim1_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'anim1', 2)
        
    def on_move_anim2_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'anim2', 3)
        
    def on_move_anim3_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'anim3', 4)
        
    def on_move_anim4_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'anim4', 5)
        
    def on_move_dir_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'dir', 6)
        
    def on_move_flag1_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'moves_store', 'flag1', 7)
        
    def on_move_flag2_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'moves_store', 'flag2', 8)
        
    def on_move_flag3_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'moves_store', 'flag3', 9)
        
    def on_move_flag4_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'moves_store', 'flag4', 10)
        
    def on_move_speed_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'speed', 11)
        
    def on_move_anim_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'animation', 12)
    
    @glib_async
    def on_move_point_changed(self, w, treepath, treeiter):
        store_move: Gtk.ListStore = self.builder.get_object('moves_store')
        store_type: Gtk.ListStore = self.builder.get_object('point_store')
        store_move[treepath][13] = store_type[treeiter][0]
        store_move[treepath][17] = store_type[treeiter][1]
        self.animations.move_table[store_move[treepath][0]].point = AnimPointType(store_type[treeiter][0])
        self.module.mark_animations_as_modified()
        
    def on_move_sfx_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'sfx', 14)
        
    def on_move_spec_start_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'spec_start', 16)
        
    def on_move_spec_entries_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'moves_store', 'spec_entries', 15)

    def on_btn_remove_move_clicked(self, *args):
        # Deletes all selected entries
        # Allows multiple deletion
        active_rows : List[Gtk.TreePath] = self.builder.get_object('moves_tree').get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = self.builder.get_object('moves_store')
        for v in reversed(sorted(active_rows, key=lambda x:x.get_indices())):
            move_id = store[v.get_indices()[0]][0]
            del self.animations.move_table[move_id]
            del store[v.get_indices()[0]]
        self._update_moves()
        self._init_combos()
        self.module.mark_animations_as_modified()
        
    def on_btn_add_move_clicked(self, *args):
        e = MoveAnim(bytes(MOVE_DATA_SIZE))
        self.animations.move_table.append(e)
        tree_store: Gtk.ListStore = self.builder.get_object('moves_store')
        i = len(self.animations.move_table)-1
        tree_store.append([i,self._string_provider.get_value(StringType.MOVE_NAMES, i), \
                         e.anim1,e.anim2,e.anim3,e.anim4,e.dir,e.flag1,e.flag2,e.flag3,e.flag4,\
                         e.speed,e.animation,e.point.value,e.sfx,e.spec_entries,e.spec_start,e.point.description])
        self.module.mark_animations_as_modified()
    
    @glib_async
    def on_gen_file_type_changed(self, w, treepath, treeiter):
        store_gen: Gtk.ListStore = self.builder.get_object('general_store')
        store_type: Gtk.ListStore = self.builder.get_object('type_store')
        store_gen[treepath][1] = store_type[treeiter][0]
        store_gen[treepath][11] = store_type[treeiter][1]
        self.animations.general_table[store_gen[treepath][0]].anim_type = AnimType(store_type[treeiter][0])
        self.module.mark_animations_as_modified()
    
    def on_gen_file_id_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'general_store', 'anim_file', 2)
    
    def on_gen_unk1_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'general_store', 'unk1', 3)
    
    def on_gen_unk2_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'general_store', 'unk2', 4)
    
    def on_gen_sfx_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'general_store', 'sfx', 5)
    
    def on_gen_unk3_edited(self, widget, path, text):
        self.set_tree_attr(path, text, 'general_store', 'unk3', 6)
        
    def on_gen_unk4_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'general_store', 'unk4', 7)
    
    @glib_async
    def on_gen_point_changed(self, w, treepath, treeiter):
        store_gen: Gtk.ListStore = self.builder.get_object('general_store')
        store_type: Gtk.ListStore = self.builder.get_object('point_store')
        store_gen[treepath][8] = store_type[treeiter][0]
        store_gen[treepath][12] = store_type[treeiter][1]
        self.animations.general_table[store_gen[treepath][0]].point = AnimPointType(store_type[treeiter][0])
        self.module.mark_animations_as_modified()
        
    def on_gen_unk5_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'general_store', 'unk5', 9)
        
    def on_gen_loop_toggled(self, widget, path):
        self.set_tree_bool(path, not widget.get_active(), 'general_store', 'loop', 10)

    def on_btn_remove_general_clicked(self, *args):
        # Deletes all selected entries
        # Allows multiple deletion
        active_rows : List[Gtk.TreePath] = self.builder.get_object('general_tree').get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = self.builder.get_object('general_store')
        for v in reversed(sorted(active_rows, key=lambda x:x.get_indices())):
            gen_id = store[v.get_indices()[0]][0]
            del self.animations.general_table[gen_id]
            del store[v.get_indices()[0]]
        self._update_general()
        self.module.mark_animations_as_modified()
        
    def on_btn_add_general_clicked(self, *args):
        e = GeneralAnim(bytes(GENERAL_DATA_SIZE))
        self.animations.general_table.append(e)
        tree_store: Gtk.ListStore = self.builder.get_object('general_store')
        i = len(self.animations.general_table)-1
        tree_store.append([i, e.anim_type.value,e.anim_file,e.unk1,e.unk2,e.sfx,e.unk3,e.unk4, \
                            e.point.value,e.unk5,e.loop,e.anim_type.description,e.point.description])
        self.module.mark_animations_as_modified()
