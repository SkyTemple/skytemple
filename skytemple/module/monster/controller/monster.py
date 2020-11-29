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
import math
import re
from enum import Enum
from typing import TYPE_CHECKING, Type, List, Optional, Dict
from xml.etree import ElementTree

import cairo
from gi.repository import Gtk, GLib

from skytemple.controller.main import MainController
from skytemple.core.module_controller import AbstractController
from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import add_dialog_xml_filter
from skytemple.module.monster.controller.level_up import LevelUpController
from skytemple.module.portrait.portrait_provider import IMG_DIM
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.xml_util import prettify
from skytemple_files.data.md.model import Gender, PokeType, MovementType, IQGroup, Ability, EvolutionMethod, \
    NUM_ENTITIES, ShadowSize, MONSTER_BIN, MdEntry
from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple_files.data.monster_xml import monster_xml_export

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule
MAX_ITEMS = 1352
PATTERN = re.compile(r'.*\(#(\d+)\).*')


class MonsterController(AbstractController):
    _last_open_tab_id = 0

    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self.item_id = item_id
        self.entry = self.module.get_entry(self.item_id)

        self._monster_bin = self.module.project.open_file_in_rom(MONSTER_BIN, FileType.BIN_PACK, threadsafe=True)

        self.builder = None
        self._is_loading = False
        self._string_provider = module.project.get_string_provider()
        self._sprite_provider = module.project.get_sprite_provider()
        self._portrait_provider = module.project.get_module('portrait').get_portrait_provider()
        self._level_up_controller: Optional[LevelUpController] = None

        self._render_graph_on_tab_change = True

        self.item_names = {}
        for i in range(0, MAX_ITEMS):
            name = self.module.project.get_string_provider().get_value(StringType.ITEM_NAMES, i)
            self.item_names[i] = f'{name} (#{i:04})'

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'monster.glade')

        self._sprite_provider.reset()
        self._portrait_provider.reset()

        self._init_language_labels()
        self._init_entid()
        self._init_stores()
        self._init_sub_pages()

        # Init Items Completion
        store: Gtk.ListStore = self.builder.get_object('store_completion_items')

        for item in self.item_names.values():
            store.append([item])

        self._is_loading = True
        self._init_values()
        self._is_loading = False

        self._update_pre_evo_label()
        self._update_base_form_label()

        self.builder.connect_signals(self)
        self.builder.get_object('draw_sprite').queue_draw()

        notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
        notebook.set_current_page(self.__class__._last_open_tab_id)

        self.builder.get_object('settings_grid').check_resize()

        self._check_sprite_size(True)

        return self.builder.get_object('box_main')

    def on_main_notebook_switch_page(self, notebook, page, page_num):
        self.__class__._last_open_tab_id = page_num
        if self._render_graph_on_tab_change:
            self._render_graph_on_tab_change = False
            self._level_up_controller.render_graph()

    def on_draw_portrait_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        scale = 2
        portrait = self._portrait_provider.get(self.entry.md_index - 1, 0,
                                               lambda: GLib.idle_add(widget.queue_draw), True)
        ctx.scale(scale, scale)
        ctx.set_source_surface(portrait)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ctx.scale(1 / scale, 1 / scale)
        if widget.get_size_request() != (IMG_DIM * scale, IMG_DIM * scale):
            widget.set_size_request(IMG_DIM * scale, IMG_DIM * scale)
        return True

    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        if self.entry.entid > 0:
            sprite, x, y, w, h = self._sprite_provider.get_monster(self.entry.md_index, 0,
                                                                   lambda: GLib.idle_add(widget.queue_draw))
        else:
            sprite, x, y, w, h = self._sprite_provider.get_error()
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        if widget.get_size_request() != (w, h):
            widget.set_size_request(w, h)
        return True

    def on_cb_type_primary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_type_secondary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_national_pokedex_number_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_entid_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_sprite_index_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()
        self._sprite_provider.reset()
        self._check_sprite_size(False)
        self.builder.get_object('draw_sprite').queue_draw()

    def on_cb_gender_changed(self, w, *args):
        self._update_from_cb(w)
        #Changing the gender should also refresh the tree, as the gender is marked here.
        self.module.refresh(self.item_id)
        self.mark_as_modified()

    def on_entry_lang1_changed(self, w, *args):
        self.builder.get_object('label_id_name').set_text(f'${self.entry.md_index:04d}: {w.get_text()}')
        self._update_lang_from_entry(w, 0)
        self.module.refresh(self.item_id)
        self.mark_as_modified()

    def on_entry_lang2_changed(self, w, *args):
        self._update_lang_from_entry(w, 1)
        self.mark_as_modified()

    def on_entry_lang3_changed(self, w, *args):
        self._update_lang_from_entry(w, 2)
        self.mark_as_modified()

    def on_entry_lang4_changed(self, w, *args):
        self._update_lang_from_entry(w, 3)
        self.mark_as_modified()

    def on_entry_lang5_changed(self, w, *args):
        self._update_lang_from_entry(w, 4)
        self.mark_as_modified()

    def on_entry_body_size_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_movement_type_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_iq_group_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_ability_primary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_cb_ability_secondary_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_exp_yield_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_recruit_rate1_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_recruit_rate2_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_hp_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_weight_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_atk_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_sp_atk_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_def_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_base_sp_def_changed(self, w, *args):
        self._update_from_entry(w)
        if self._level_up_controller is not None:
            self._level_up_controller.queue_render_graph()
            self._render_graph_on_tab_change = True
        self.mark_as_modified()

    def on_entry_size_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_evo_param1_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_evo_param2_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_pre_evo_index_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_pre_evo_label()
        self.mark_as_modified()

    def on_cb_evo_method_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_btn_help_evo_params_clicked(self, w, *args):
        md = Gtk.MessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            f"Values depend on Evolution Type:\n"
            f"- None: n/a - n/a\n"
            f"- Level: Level required to evolve - Optional evolutionary item ID\n"
            f"- IQ: IQ required - Optional evolutionary item ID\n"
            f"- Items: Regular Item ID - Optional evolutionary item ID\n"
            f"- Unknown: ? - ?\n"
            f"- Link Cable: 0 - 1",
            title="Evolution Parameters"
        )
        md.run()
        md.destroy()

    def on_btn_help_hp_regeneration_clicked(self, w, *args):
        md = Gtk.MessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            f"The % of HP that this Pokémon regenerates at the end of "
            f"each turn is equal to 1/(value * 2), before applying any modifiers.\n"
            f"The final value is capped between 1/30 and 1/500",
            title="HP Regeneration"
        )
        md.run()
        md.destroy()

    def on_entry_exclusive_item1_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item1', val)
        self.mark_as_modified()

    def on_entry_exclusive_item2_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item2', val)
        self.mark_as_modified()

    def on_entry_exclusive_item3_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item3', val)
        self.mark_as_modified()

    def on_entry_exclusive_item4_changed(self, w, *args):
        match = PATTERN.match(w.get_text())
        if match is None:
            return
        try:
            val = int(match.group(1))
        except ValueError:
            return
        setattr(self.entry, 'exclusive_item4', val)
        self.mark_as_modified()

    def on_entry_bitflag1_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk31_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_movement_speed_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk17_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk18_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_cb_shadow_size_changed(self, w, *args):
        self._update_from_cb(w)
        self.mark_as_modified()

    def on_entry_hp_regeneration_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk21_h_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_chance_spawn_asleep_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk27_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk29_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk28_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_unk30_changed(self, w, *args):
        self._update_from_entry(w)
        self.mark_as_modified()

    def on_entry_base_form_index_changed(self, w, *args):
        self._update_from_entry(w)
        self._update_base_form_label()
        self.mark_as_modified()

    def on_btn_export_clicked(self, *args):
        dialog: Gtk.Dialog = self.builder.get_object('export_dialog')
        dialog.resize(640, 560)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())

        # Fill Pokémon tree
        store: Gtk.TreeStore = self.builder.get_object('export_dialog_store')
        store.clear()
        monster_entries_by_base_id: Dict[int, List[MdEntry]] = {}
        for entry in self.module.monster_md.entries:
            if entry.md_index_base not in monster_entries_by_base_id:
                monster_entries_by_base_id[entry.md_index_base] = []
            monster_entries_by_base_id[entry.md_index_base].append(entry)

        for baseid, entry_list in monster_entries_by_base_id.items():
            name = self.module.project.get_string_provider().get_value(StringType.POKEMON_NAMES, baseid)
            entry_main_tree = self.module.generate_entry__entity_root(baseid, name)
            ent_root = store.append(None, [
                -1, -1, False, entry_main_tree[0],
                entry_main_tree[1], False, False
            ])

            for entry in entry_list:
                entry_main_tree = self.module.generate_entry__entry(entry.md_index, entry.gender)
                store.append(
                    ent_root, [
                        entry_main_tree[4], -1, True, entry_main_tree[0],
                        entry_main_tree[1], False, False
                    ]
                )

        names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2 = self.module.get_export_data(self.entry)
        we_are_gender1 = md_gender1 == self.entry

        if md_gender2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_portraits_current_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if portraits2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_portraits_other_gender')
            sw.set_active(False)
            sw.set_sensitive(False)

        if stats is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_stats')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_moveset1')
            sw.set_active(False)
            sw.set_sensitive(False)

        if moveset2 is None:
            sw: Gtk.Switch = self.builder.get_object('export_type_moveset2')
            sw.set_active(False)
            sw.set_sensitive(False)

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.APPLY:
            # Create output XML

            if not self.builder.get_object('export_type_current_gender').get_active():
                if we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not self.builder.get_object('export_type_other_gender').get_active():
                if not we_are_gender1:
                    md_gender1 = None
                else:
                    md_gender2 = None
            if not self.builder.get_object('export_type_names').get_active():
                names = None
            if not self.builder.get_object('export_type_stats').get_active():
                stats = None
            if not self.builder.get_object('export_type_moveset1').get_active():
                moveset = None
            if not self.builder.get_object('export_type_moveset2').get_active():
                moveset2 = None
            if not self.builder.get_object('export_type_portraits_current_gender').get_active():
                if we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None
            if not self.builder.get_object('export_type_portraits_other_gender').get_active():
                if not we_are_gender1:
                    portraits = None
                else:
                    portraits2 = None

            xml = monster_xml_export(
                self.module.project.get_rom_module().get_static_data().game_version,
                md_gender1, md_gender2, names, moveset, moveset2, stats, portraits, portraits2
            )

            # 1. Export to file
            if self.builder.get_object('export_file_switch').get_active():
                save_diag = Gtk.FileChooserDialog(
                    "Export Pokémon as...",
                    SkyTempleMainController.window(),
                    Gtk.FileChooserAction.SAVE,
                    (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
                )

                add_dialog_xml_filter(save_diag)
                response = save_diag.run()
                fn = save_diag.get_filename()
                if '.' not in fn:
                    fn += '.xml'
                save_diag.destroy()

                if response == Gtk.ResponseType.OK:
                    with open(fn, 'w') as f:
                        f.write(prettify(xml))
                else:
                    md = Gtk.MessageDialog(SkyTempleMainController.window(),
                                           Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                           Gtk.ButtonsType.OK, "Export was canceled.")
                    md.set_position(Gtk.WindowPosition.CENTER)
                    md.run()
                    md.destroy()
                    return

            # 2. Import to selected Pokémon
            selected_monsters: List[int] = []
            def collect_monsters_recurse(titer: Optional[Gtk.TreeIter]):
                for i in range(store.iter_n_children(titer)):
                    child = store.iter_nth_child(titer, i)
                    if store[child][2] and store[child][5]:  # is floor and is selected
                        selected_monsters.append(store[child][0])
                    collect_monsters_recurse(child)

            collect_monsters_recurse(None)
            self.module.import_from_xml(selected_monsters, xml)

    def on_btn_import_clicked(self, *args):
        save_diag = Gtk.FileChooserDialog(
            "Import Pokémon from...",
            SkyTempleMainController.window(),
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        )

        add_dialog_xml_filter(save_diag)
        response = save_diag.run()
        fn = save_diag.get_filename()
        save_diag.destroy()

        if response == Gtk.ResponseType.OK:
            self.module.import_from_xml([self.entry.md_index], ElementTree.parse(fn).getroot())
            SkyTempleMainController.reload_view()

    def on_cr_export_selected_toggled(self, w: Gtk.CellRendererToggle, path, *args):
        store: Gtk.TreeStore = self.builder.get_object('export_dialog_store')
        is_active = not w.get_active()
        store[path][5] = is_active
        store[path][6] = False
        # Update inconsistent state for all parents
        def mark_inconsistent_recurse(titer: Gtk.TreeIter, force_inconstent=False):
            parent = store.iter_parent(titer)
            if parent is not None:
                should_be_inconsistent = force_inconstent
                if not should_be_inconsistent:
                    # Look at children to see if should be marked inconsistent
                    children = []
                    for i in range(store.iter_n_children(parent)):
                        child = store.iter_nth_child(parent, i)
                        children.append(child)
                    states = [store[child][5] for child in children]
                    should_be_inconsistent = any([store[child][6] for child in children]) or not states.count(states[0]) == len(states)
                store[parent][6] = should_be_inconsistent
                if should_be_inconsistent:
                    store[parent][5] = False
                else:
                    store[parent][5] = states[0]
                mark_inconsistent_recurse(parent, should_be_inconsistent)

        mark_inconsistent_recurse(store.get_iter(path))
        # Update state for all children
        def mark_active_recurse(titer: Gtk.TreeIter):
            for i in range(store.iter_n_children(titer)):
                child = store.iter_nth_child(titer, i)
                store[child][5] = is_active
                store[child][6] = False
                mark_active_recurse(child)
        mark_active_recurse(store.get_iter(path))

    def _init_language_labels(self):
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_label: Gtk.Label = self.builder.get_object(f'label_lang{gui_id}')
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            if lang_id < len(langs):
                # We have this language
                gui_label.set_text(langs[lang_id].name + ':')
            else:
                # We don't.
                gui_label.set_text("")
                gui_entry.set_sensitive(False)

    def _init_entid(self):
        self.builder.get_object(f'label_base_id').set_text(f'#{self.entry.md_index_base:03}')
        name = self._string_provider.get_value(StringType.POKEMON_NAMES, self.entry.md_index_base)
        self.builder.get_object('label_id_name').set_text(f'${self.entry.md_index:04d}: {name}')

    def _init_stores(self):
        # Genders
        self._comboxbox_for_enum(['cb_gender'], Gender)
        # Types
        self._comboxbox_for_enum(['cb_type_primary', 'cb_type_secondary'], PokeType)
        # Movement Types
        self._comboxbox_for_enum(['cb_movement_type'], MovementType)
        # IQ Groups
        self._comboxbox_for_enum(['cb_iq_group'], IQGroup)
        # Abilities
        self._comboxbox_for_enum(['cb_ability_primary', 'cb_ability_secondary'], Ability)
        # Evolution Methods
        self._comboxbox_for_enum(['cb_evo_method'], EvolutionMethod)
        # Shadow Size
        self._comboxbox_for_enum(['cb_shadow_size'], ShadowSize)

    def _init_values(self):
        # Names
        langs = self._string_provider.get_languages()
        for lang_id in range(0, 5):
            gui_id = lang_id + 1
            gui_entry: Gtk.Entry = self.builder.get_object(f'entry_lang{gui_id}')
            if lang_id < len(langs):
                # We have this language
                gui_entry.set_text(self._string_provider.get_value(StringType.POKEMON_NAMES,
                                                                   self.entry.md_index_base,
                                                                   langs[lang_id]))

        # Stats
        self._set_entry('entry_unk31', self.entry.unk31)
        self._set_entry('entry_national_pokedex_number', self.entry.national_pokedex_number)
        self._set_entry('entry_entid', self.entry.entid)
        self._set_entry('entry_sprite_index', self.entry.sprite_index)
        self._set_entry('entry_base_movement_speed', self.entry.base_movement_speed)
        self._set_entry('entry_pre_evo_index', self.entry.pre_evo_index)
        self._set_entry('entry_base_form_index', self.entry.base_form_index)
        self._set_cb('cb_evo_method', self.entry.evo_method.value)
        self._set_entry('entry_evo_param1', self.entry.evo_param1)
        self._set_entry('entry_evo_param2', self.entry.evo_param2)
        self._set_cb('cb_gender', self.entry.gender.value)
        self._set_entry('entry_body_size', self.entry.body_size)
        self._set_cb('cb_type_primary', self.entry.type_primary.value)
        self._set_cb('cb_type_secondary', self.entry.type_secondary.value)
        self._set_cb('cb_movement_type', self.entry.movement_type.value)
        self._set_cb('cb_iq_group', self.entry.iq_group.value)
        self._set_cb('cb_ability_primary', self.entry.ability_primary.value)
        self._set_cb('cb_ability_secondary', self.entry.ability_secondary.value)
        self._set_entry('entry_bitflag1', self.entry.bitflag1)
        self._set_entry('entry_exp_yield', self.entry.exp_yield)
        self._set_entry('entry_recruit_rate1', self.entry.recruit_rate1)
        self._set_entry('entry_base_hp', self.entry.base_hp)
        self._set_entry('entry_recruit_rate2', self.entry.recruit_rate2)
        self._set_entry('entry_base_atk', self.entry.base_atk)
        self._set_entry('entry_base_sp_atk', self.entry.base_sp_atk)
        self._set_entry('entry_base_def', self.entry.base_def)
        self._set_entry('entry_base_sp_def', self.entry.base_sp_def)
        self._set_entry('entry_weight', self.entry.weight)
        self._set_entry('entry_size', self.entry.size)
        self._set_entry('entry_unk17', self.entry.unk17)
        self._set_entry('entry_unk18', self.entry.unk18)
        self._set_cb('cb_shadow_size', self.entry.shadow_size.value)
        self._set_entry('entry_chance_spawn_asleep', self.entry.chance_spawn_asleep)
        self._set_entry('entry_hp_regeneration', self.entry.hp_regeneration)
        self._set_entry('entry_unk21_h', self.entry.unk21_h)
        self._set_entry('entry_exclusive_item1', self.item_names[self.entry.exclusive_item1])
        self._set_entry('entry_exclusive_item2', self.item_names[self.entry.exclusive_item2])
        self._set_entry('entry_exclusive_item3', self.item_names[self.entry.exclusive_item3])
        self._set_entry('entry_exclusive_item4', self.item_names[self.entry.exclusive_item4])
        self._set_entry('entry_unk27', self.entry.unk27)
        self._set_entry('entry_unk28', self.entry.unk28)
        self._set_entry('entry_unk29', self.entry.unk29)
        self._set_entry('entry_unk30', self.entry.unk30)

    def mark_as_modified(self):
        if not self._is_loading:
            self.module.mark_md_as_modified(self.item_id)

    def _comboxbox_for_enum(self, names: List[str], enum: Type[Enum]):
        store = Gtk.ListStore(int, str)  # id, name
        for entry in enum:
            store.append([entry.value, self._enum_entry_to_str(entry)])
        for name in names:
            self._fast_set_comboxbox_store(self.builder.get_object(name), store, 1)

    @staticmethod
    def _fast_set_comboxbox_store(cb: Gtk.ComboBox, store: Gtk.ListStore, col):
        cb.set_model(store)
        renderer_text = Gtk.CellRendererText()
        cb.pack_start(renderer_text, True)
        cb.add_attribute(renderer_text, "text", col)

    def _enum_entry_to_str(self, entry):
        if hasattr(entry, 'print_name'):
            return entry.print_name
        return entry.name.capitalize().replace('_', ' ')

    def _set_entry(self, entry_name, text):
        self.builder.get_object(entry_name).set_text(str(text))

    def _set_cb(self, cb_name, value):
        cb: Gtk.ComboBox = self.builder.get_object(cb_name)
        l_iter: Gtk.TreeIter = cb.get_model().get_iter_first()
        while l_iter:
            row = cb.get_model()[l_iter]
            if row[0] == value:
                cb.set_active_iter(l_iter)
                return
            l_iter = cb.get_model().iter_next(l_iter)

    def _update_from_entry(self, w: Gtk.Entry):
        attr_name = Gtk.Buildable.get_name(w)[6:]
        try:
            val = int(w.get_text())
        except ValueError:
            return
        setattr(self.entry, attr_name, val)

    def _update_from_cb(self, w: Gtk.ComboBox):
        attr_name = Gtk.Buildable.get_name(w)[3:]
        val = w.get_model()[w.get_active_iter()][0]
        current_val = getattr(self.entry, attr_name)
        if isinstance(current_val, Enum):
            enum_class = current_val.__class__
            val = enum_class(val)
        setattr(self.entry, attr_name, val)

    def _update_lang_from_entry(self, w: Gtk.Entry, lang_index):
        lang = self._string_provider.get_languages()[lang_index]
        self._string_provider.get_model(lang).strings[
            self._string_provider.get_index(StringType.POKEMON_NAMES, self.entry.md_index_base)
        ] = w.get_text()

    def _init_sub_pages(self):
        notebook: Gtk.Notebook = self.builder.get_object('main_notebook')
        tab_label: Gtk.Label = Gtk.Label.new('Stats and Moves')
        level_up_view, self._level_up_controller = self.module.get_level_up_view(self.item_id)
        notebook.append_page(level_up_view, tab_label)
        tab_label: Gtk.Label = Gtk.Label.new('Portraits')
        notebook.append_page(self.module.get_portrait_view(self.item_id), tab_label)

    def _update_base_form_label(self):
        label: Gtk.Label = self.builder.get_object('label_base_form_index')
        entry: Gtk.Entry = self.builder.get_object('entry_base_form_index')
        try:
            entry_id = int(entry.get_text())
            if entry_id > NUM_ENTITIES:
                raise ValueError()
            entry = self.module.monster_md[entry_id]
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            label.set_text(f'#{entry.md_index_base:03d}: {name}')
        except BaseException:
            label.set_text(f'??? Enter a valid Base ID (#)')

    def _update_pre_evo_label(self):
        label: Gtk.Label = self.builder.get_object('label_pre_evo_index')
        entry: Gtk.Entry = self.builder.get_object('entry_pre_evo_index')
        try:
            entry_id = int(entry.get_text())
            entry = self.module.monster_md[entry_id]
            name = self._string_provider.get_value(StringType.POKEMON_NAMES, entry.md_index_base)
            label.set_text(f'${entry.md_index:04d}: {name} ({entry.gender.name[0]})')
        except BaseException:
            label.set_text(f'??? Enter a valid Entry ID ($)')

    def _check_sprite_size(self, show_warning):
        """
        Check that the data in the unknown Pokémon sprite-related metadata
        table matches the currently selected sprite of the Pokémon. If not, change
        the value and save it.
        """
        with self._monster_bin as sprites:
            sprite_bin = sprites[self.entry.sprite_index]
            sprite = FileType.WAN.deserialize(FileType.PKDPX.deserialize(sprite_bin).decompress())
        sprite_size_table = self.module.get_pokemon_sprite_data_table()
        check_value = sprite_size_table[self.entry.md_index_base].sprite_tile_slots
        max_tile_slots_needed = max(
            (f.unk2 & 0x3FF) + math.ceil(f.resolution.x * f.resolution.y / 256)
            for f in sprite.model.meta_frame_store.meta_frames
        )
        # There isn't those 2 blocks buffer! Doing this would cause some problems in the long term.
        # Also, this should use the Unk#6 field in the animation info block (see psy's docs about wan files)
        # instead of the calculation above, as it's exactly the result of that
        max_tile_slots_needed = max((6, max_tile_slots_needed))
        if check_value != max_tile_slots_needed:
            sprite_size_table[self.entry.md_index_base].sprite_tile_slots = max_tile_slots_needed
            self.module.set_pokemon_sprite_data_table(sprite_size_table)

            if show_warning:
                md = Gtk.MessageDialog(MainController.window(),
                                       Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                       Gtk.ButtonsType.OK,
                                       "The sprite memory size of this Pokémon was too low "
                                       "for this Pokémon's assigned sprite.\n"
                                       "SkyTemple automatically corrected it.")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()

            self.mark_as_modified()
