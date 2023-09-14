#  Copyright 2020-2023 Capypara and the SkyTemple Contributors
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
import os
import typing
from typing import TYPE_CHECKING, Tuple, List

from gi.repository import Gtk, GLib
from gi.repository.Gtk import Widget
from skytemple.core.ui_utils import builder_get_assert, iter_tree_model
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import open_utf8
from skytemple_files.common.xml_util import prettify
from skytemple_files.data.monster_xml import monster_xml_export

from skytemple.controller.main import MainController as SkyTempleMainController
from skytemple.core.async_tasks.delegator import AsyncTaskDelegator
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.string_provider import StringType
from skytemple.core.module_controller import AbstractController
from skytemple_files.data.tbl_talk import TBL_TALK_SPEC_LEN
from skytemple_files.data.tbl_talk.model import TalkType
from skytemple_files.common.i18n_util import f, _

if TYPE_CHECKING:
    from skytemple.module.monster.module import MonsterModule

MONSTER_NAME = 'Pokémon'
MAP_TALK_TYPE = [StringType.DIALOGUE_HEALTHY,
                 StringType.DIALOGUE_HALF_LIFE,
                 StringType.DIALOGUE_PINCH,
                 StringType.DIALOGUE_LEVEL_UP,
                 StringType.DIALOGUE_WAIT,
                 StringType.DIALOGUE_GROUND_WAIT]

# TODO: Static list of actors
UNIQUE_ACTORS = [_("Partner 1"),
                 _("Partner 2"),
                 _("Partner 3"),
                 _("Grovyle"),
                 _("Chatot"),
                 _("Bidoof"),
                 _("Celebi"),
                 _("Cresselia")]+[_("Unknown Actor %02d") % i for i in range(8, 13)]+[_("Shaymin"),
                 _("Snover"),
                 _("Armaldo"),
                 _("Banette"), #Not sure about those two (I could have swapped them)
                 _("Skorupi"), #With this
                 _("Medicham"),
                 _("Gardevoir"),
                 _("Unknown Actor 20"),
                 _("Celebi"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir"),
                 _("Dusknoir")]+[_("Unknown Actor %02d") % i for i in range(29, 34)]+[_("Loudred"), _("Unknown Actor 35")]
class MainController(AbstractController):
    def __init__(self, module: 'MonsterModule', item_id: int):
        self.module = module
        self._string_provider = module.project.get_string_provider()

    def get_view(self) -> Widget:
        self.builder = self._get_builder(__file__, 'main.glade')
        self._init_combos()
        self._init_groups()
        self._init_spec_personalities()
        
        self.on_lang_changed()
        self.builder.connect_signals(self)
        return builder_get_assert(self.builder, Gtk.Widget, 'box_list')

    def _init_groups(self):
        builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').set_text(str(0))
        builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').set_increments(1,1)
        builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').set_range(0, self.module.get_nb_personality_groups()-1)
        
    def _init_combos(self):
        # Init available types
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_store_types')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_types')
        # Init combobox
        cb_store.clear()
        for v in TalkType:
            cb_store.append([v.value, v.description])
        cb.set_active(0)
        
        # Init available languages
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_store_lang')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_lang')
        # Init combobox
        cb_store.clear()
        for lang in self._string_provider.get_languages():
            cb_store.append([lang.locale, lang.name])
        cb.set_active(0)

    def on_lang_changed(self, *args):
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_store_lang')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_lang')
        active_iter = cb.get_active_iter()
        assert active_iter is not None
        self._current_lang = cb_store[active_iter][0]
        self._refresh_list()


    def _init_spec_personalities(self):
        tree_store = builder_get_assert(self.builder, Gtk.ListStore, 'special_personalities_tree_store')
        tree_store.clear()
        for i in range(TBL_TALK_SPEC_LEN):
            tree_store.append([UNIQUE_ACTORS[i], self.module.get_special_personality(i)])
        
    def on_value_changed(self, *args):
        self._refresh_list()

    def _get_current_settings(self) -> Tuple[int, TalkType]:
        cb_store = builder_get_assert(self.builder, Gtk.ListStore, 'cb_store_types')
        cb = builder_get_assert(self.builder, Gtk.ComboBox, 'cb_types')

        active_iter = cb.get_active_iter()
        assert active_iter is not None
        talk_type: TalkType = TalkType(cb_store[active_iter][0])  # type: ignore
        group: int = int(builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').get_text())
        return group, talk_type
        
    def _regenerate_list(self):
        group, talk_type = self._get_current_settings()
        
        tree_store: Gtk.ListStore = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
        new_list = []
        for row in iter_tree_model(tree_store):
            new_list.append(row[0])
        self.module.set_personality_dialogues(group, talk_type, new_list)
        self.module.mark_tbl_talk_as_modified()
        self._refresh_list()
        
    def on_spec_personality_edited(self, widget, path, text):
        try:
            tree_store = builder_get_assert(self.builder, Gtk.ListStore, 'special_personalities_tree_store')
            tree_store[path][1] = int(text)
            self.module.set_special_personality(int(path), int(text))
        except ValueError:
            return
        
    def on_id_text_edited(self, widget, path, text):
        try:
            tree_store = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
            tree_store[path][0] = int(text)
        except ValueError:
            return
        
        self._regenerate_list()
    
    def on_string_text_edited(self, widget, path, text):
        _, talk_type = self._get_current_settings()
        
        tree_store = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
        self._string_provider.get_model(self._current_lang).strings[
            self._string_provider.get_index(MAP_TALK_TYPE[talk_type.value], int(tree_store[path][0]))
        ] = text
        self._regenerate_list()
        self.module.mark_string_as_modified()

    def on_btn_add_dialogue_clicked(self, *args):
        store = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
        store.append([0, ""])
        self._regenerate_list()

    def on_btn_remove_dialogue_clicked(self, *args):
        # Deletes all selected dialogue entries
        # Allows multiple deletions
        active_rows = builder_get_assert(self.builder, Gtk.TreeView, 'group_text_tree').get_selection().get_selected_rows()[1]
        store = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
        for x in reversed(sorted(active_rows, key=lambda x: x.get_indices())):
            del store[x.get_indices()[0]]
        self._regenerate_list()
        
    def on_btn_add_group_clicked(self, *args):
        self.module.add_personality_group()
        self._init_groups()
        builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').set_text(str(self.module.get_nb_personality_groups()-1))
        self.module.mark_tbl_talk_as_modified()
        self._refresh_list()

    def on_btn_remove_group_clicked(self, *args):
        # Deletes current group
        if self.module.get_nb_personality_groups()>1:
            group, _ = self._get_current_settings()
            self.module.remove_personality_group(group)
            self._init_groups()
            builder_get_assert(self.builder, Gtk.SpinButton, 'spin_group_nb').set_text(str(max(group-1, 0)))
            self.module.mark_tbl_talk_as_modified()
            self._refresh_list()

    def _refresh_list(self):
        group, talk_type = self._get_current_settings()
        dialogues: List[int] = self.module.get_personality_dialogues(group, talk_type)
        tree_store = builder_get_assert(self.builder, Gtk.ListStore, 'group_text_tree_store')
        tree_store.clear()
        for d in dialogues:
            tree_store.append([d, self._string_provider.get_value(MAP_TALK_TYPE[talk_type.value], d, self._current_lang)])

    def on_btn_export_clicked(self, *args):
        dialog = builder_get_assert(self.builder, Gtk.Dialog, 'export_dialog')
        dialog.resize(640, 320)
        dialog.set_attached_to(SkyTempleMainController.window())
        dialog.set_transient_for(SkyTempleMainController.window())
        export_progress = builder_get_assert(self.builder, Gtk.ProgressBar, 'export_progress')

        resp = dialog.run()
        dialog.hide()

        if resp == Gtk.ResponseType.APPLY:
            # Create output XML
            export_names = builder_get_assert(self.builder, Gtk.Switch, 'export_type_names').get_active()
            export_stats = builder_get_assert(self.builder, Gtk.Switch, 'export_type_stats').get_active()
            export_moveset = builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset1').get_active()
            export_moveset2 = builder_get_assert(self.builder, Gtk.Switch, 'export_type_moveset2').get_active()
            export_portraits = builder_get_assert(self.builder, Gtk.Switch, 'export_type_portraits').get_active()
            expand_poke_list_applied = self.module.project.is_patch_applied('ExpandPokeList')
            num_entities = FileType.MD.properties().num_entities

            save_diag = Gtk.FileChooserNative.new(
                _("Export Pokémon at..."),
                SkyTempleMainController.window(),
                Gtk.FileChooserAction.SELECT_FOLDER,
                None, None
            )

            response = save_diag.run()
            directory = save_diag.get_filename()
            save_diag.destroy()

            if response == Gtk.ResponseType.ACCEPT and directory is not None:
                async def export():
                    assert directory is not None
                    max_progress = num_entities
                    if expand_poke_list_applied:
                        max_progress = len(self.module.monster_md.entries)
                    for i, entry in enumerate(self.module.monster_md.entries):
                        if entry.md_index >= num_entities and not expand_poke_list_applied:
                            break

                        names, md_gender1, md_gender2, moveset, moveset2, stats, portraits, portraits2, personality1, personality2, idle_anim1, idle_anim2 = self.module.get_export_data(
                            entry
                        )

                        main_name = names.get("English")[0]
                        if main_name is None:
                            name_vals = list(names.values())
                            if len(name_vals) > 0:
                                main_name = name_vals[0][0]
                            else:
                                main_name = ""
                        if expand_poke_list_applied:
                            # We do not support multi gender export for now with this patch, too many edge cases.
                            md_gender2 = None
                            portraits2 = None
                            personality2 = None
                            idle_anim2 = None
                        if not export_names:
                            names = None
                        if not export_stats:
                            stats = None
                        if not export_moveset:
                            moveset = None
                        if not export_moveset2:
                            moveset2 = None
                        if not export_portraits:
                            portraits = None
                            portraits2 = None

                        xml = monster_xml_export(
                            self.module.project.get_rom_module().get_static_data().game_version,
                            md_gender1, md_gender2, names, moveset, moveset2, stats, portraits, portraits2,
                            personality1, personality2, idle_anim1, idle_anim2
                        )

                        fn = os.path.join(directory, f"{entry.md_index:04}_{main_name}.xml")

                        with open_utf8(fn, 'w') as file:
                            file.write(prettify(xml))

                        GLib.idle_add(lambda: export_progress.set_fraction(i / max_progress))
                    GLib.idle_add(progress_dialog.hide)


                progress_dialog = builder_get_assert(self.builder, Gtk.Dialog, 'progress_dialog')
                progress_dialog.set_attached_to(SkyTempleMainController.window())
                progress_dialog.set_transient_for(SkyTempleMainController.window())
                AsyncTaskDelegator.run_task(export())
                progress_dialog.run()

            else:
                md = SkyTempleMessageDialog(SkyTempleMainController.window(),
                                            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.WARNING,
                                            Gtk.ButtonsType.OK, "Export was canceled.")
                md.set_position(Gtk.WindowPosition.CENTER)
                md.run()
                md.destroy()
                return

    @typing.no_type_check
    def unload(self):
        builder_get_assert(self.builder, Gtk.Dialog, 'export_dialog').destroy()
        builder_get_assert(self.builder, Gtk.Dialog, 'progress_dialog').destroy()
        super().unload()
