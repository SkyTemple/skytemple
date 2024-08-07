#  Copyright 2020-2024 Capypara and the SkyTemple Contributors
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
import logging
import os
import sys
from typing import TYPE_CHECKING, cast
from xml.etree import ElementTree
from xml.etree.ElementTree import Element
from zipfile import ZipFile
import cairo
from skytemple.core.ui_utils import assert_not_none, data_dir
from skytemple_files.common.ppmdu_config.data import Pmd2Sprite, Pmd2Index
from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.events.manager import EventManager
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.model_context import ModelContext
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.bin_pack.model import BinPack
from skytemple_files.graphics.chara_wan.model import WanFile
from skytemple_files.graphics.wan_wat.model import Wan
from skytemple_files.common.i18n_util import _
from gi.repository import Gtk, GLib

from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.sprite.module import SpriteModule
logger = logging.getLogger(__name__)
FPS = 30


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "sprite", "monster_sprite.ui"))
class StSpriteMonsterSpritePage(Gtk.Box):
    __gtype_name__ = "StSpriteMonsterSpritePage"
    module: SpriteModule
    item_data: int
    draw_sprite: Gtk.DrawingArea = cast(Gtk.DrawingArea, Gtk.Template.Child())
    spritecollab_browser: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    explanation_text2: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    export_ground: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_ground: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_attack: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    export_attack: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    export_dungeon: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_dungeon: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    explanation_text: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    button_import: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    export: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_new: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    import_export_zip: Gtk.CheckButton = cast(Gtk.CheckButton, Gtk.Template.Child())
    explanation_text1: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())
    sprite_warning: Gtk.Label = cast(Gtk.Label, Gtk.Template.Child())

    def __init__(
        self,
        module: SpriteModule,
        item_data: int,
        mark_as_modified_cb,
        assign_new_sprite_id_cb,
        get_shadow_size_cb,
        set_shadow_size_cb,
    ):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self._sprite_provider = self.module.get_sprite_provider()
        self._mark_as_modified_cb = mark_as_modified_cb
        self._assign_new_sprite_id_cb = assign_new_sprite_id_cb
        self._get_shadow_size_cb = get_shadow_size_cb
        self._set_shadow_size_cb = set_shadow_size_cb
        self._frame_counter = 0
        self._anim_counter = 0
        self._drawing_is_active = 0
        self._draw_area: Gtk.DrawingArea | None = None
        self._monster_bin: ModelContext[BinPack] = self.module.get_monster_bin_ctx()
        self._rendered_frame_info: list[tuple[int, tuple[cairo.Surface, int, int, int, int]]] = []
        assert self.module.is_idx_supported(self.item_data)
        self._draw_area = self.draw_sprite
        if self.module.get_gfxcrunch().is_available():  # noqa: W291
            self.explanation_text2.set_markup(
                _(
                    "Alternatively you can export the sprite files \nin the gfxcrunch format and edit them manually.\nWarning: SkyTemple does not validate the files you import."
                )
            )
        try:
            self._load_frames()
            self.start_sprite_drawing()
        except BaseException as ex:
            logger.error("Failed rendering sprite preview", exc_info=ex)
        # Disable import/export if sprite ID higher than available IDs
        if self.item_data >= self.module.get_monster_sprite_count():
            self.button_import.set_sensitive(False)
            self.export.set_sensitive(False)
            self.import_ground.set_sensitive(False)
            self.export_ground.set_sensitive(False)
            self.import_attack.set_sensitive(False)
            self.export_attack.set_sensitive(False)
            self.import_dungeon.set_sensitive(False)
            self.export_dungeon.set_sensitive(False)

    def start_sprite_drawing(self):
        """Start drawing on the DrawingArea"""
        self._drawing_is_active = True
        assert self._draw_area is not None
        self._draw_area.queue_draw()
        GLib.timeout_add(int(1000 / FPS), self._tick)

    def stop_sprite_drawing(self):
        self._drawing_is_active = False

    def _tick(self):
        if self._draw_area is None:
            return False
        if self._draw_area is not None and self._draw_area.get_parent() is None:
            # XXX: Gtk doesn't remove the widget on switch sometimes...
            self._draw_area.destroy()
            return False
        if EventManager.instance().get_if_main_window_has_fous():
            self._draw_area.queue_draw()
        self._frame_counter += 1
        return self._drawing_is_active

    @Gtk.Template.Callback()
    def on_draw_sprite_draw(self, widget: Gtk.DrawingArea, ctx: cairo.Context):
        if not self._drawing_is_active:
            return True
        scale = 4
        sprite, x, y, w, h = self._get_sprite_anim()
        ctx.scale(scale, scale)
        ctx.set_source_surface(sprite)
        ctx.get_source().set_filter(cairo.Filter.NEAREST)
        ctx.paint()
        ww, wh = widget.get_size_request()
        if ww < w or wh < h:
            widget.set_size_request(w * scale, h * scale)
        ctx.scale(1 / scale, 1 / scale)
        return True

    def _zip_is_active(self):
        return self.import_export_zip.get_active()

    def _add_zip_filter_to_dialog(self, dialog: Gtk.FileChooserNative):
        filter_zip = Gtk.FileFilter()
        filter_zip.set_name("Zip archives")
        filter_zip.add_pattern("*.zip")
        dialog.add_filter(filter_zip)
        dialog.set_current_name("spritesheet.zip")

    @Gtk.Template.Callback()
    def on_export_clicked(self, w: Gtk.MenuToolButton):
        is_zip = self._zip_is_active()
        dialog = Gtk.FileChooserNative.new(
            _("Export spritesheet..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER if not is_zip else Gtk.FileChooserAction.SAVE,
            _("_Save"),
            None,
        )
        if is_zip:
            self._add_zip_filter_to_dialog(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                monster: WanFile = self.module.get_monster_monster_sprite_chara(self.item_data)
                ground: WanFile = self.module.get_monster_ground_sprite_chara(self.item_data)
                attack: WanFile = self.module.get_monster_attack_sprite_chara(self.item_data)
                merged = FileType.WAN.CHARA.merge_wan(monster, ground, attack)
                merged.sdwSize = self._get_shadow_size_cb()
                try:
                    animation_names = (
                        self.module.project.get_rom_module().get_static_data().animation_names[self.item_data]
                    )
                except KeyError:
                    # Fall back to Bulbasaur
                    animation_names = self.module.project.get_rom_module().get_static_data().animation_names[0]
                if not is_zip:
                    FileType.WAN.CHARA.export_sheets(fn, merged, animation_names)
                else:
                    FileType.WAN.CHARA.export_sheets_as_zip(fn, merged, animation_names)
                md = SkyTempleMessageDialog(
                    MainController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("The spritesheet was successfully exported."),
                    title=_("Success!"),
                    is_success=True,
                )
                md.run()
                md.destroy()
            except BaseException as e:
                display_error(sys.exc_info(), str(e), _("Error exporting the spritesheet."))

    @Gtk.Template.Callback()
    def on_button_import_clicked(self, w: Gtk.MenuToolButton):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("To import select the archive that contains the spritesheets.")
            if self._zip_is_active()
            else _("To import select the directory of the spritesheets. If it is still zipped, unzip it first."),
            title="SkyTemple",
        )
        md.run()
        md.destroy()
        self.do_import(self.item_data)

    @Gtk.Template.Callback()
    def on_import_new_clicked(self, w: Gtk.MenuToolButton):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT,
            Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK_CANCEL,
            _(
                "This will insert a completely new sprite into the game's sprite file and assign the new ID to the Pokémon.\nIf you want to instead replace the currently assigned sprite, choose 'Import'.\n"
            )
            + _("To import select the archive that contains the spritesheets.")
            if self._zip_is_active()
            else _("To import select the directory of the spritesheets. If it is still zipped, unzip it first."),
            title="SkyTemple",
        )
        response = md.run()
        md.destroy()
        if response == Gtk.ResponseType.OK:
            new_sprite_id = self.module.get_monster_sprite_count()
            if new_sprite_id > -1:
                self.do_import(new_sprite_id, lambda: self._assign_new_sprite_id_cb(new_sprite_id))

    def do_import(self, sprite_id: int, cb=lambda: None):
        is_zip = self._zip_is_active()
        dialog = Gtk.FileChooserNative.new(
            _("Import spritesheet..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER if not is_zip else Gtk.FileChooserAction.OPEN,
            None,
            None,
        )
        if is_zip:
            self._add_zip_filter_to_dialog(dialog)
        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        if response == Gtk.ResponseType.ACCEPT and fn is not None:
            try:
                wan = (
                    FileType.WAN.CHARA.import_sheets(fn)
                    if not is_zip
                    else FileType.WAN.CHARA.import_sheets_from_zip(fn)
                )
                self.module.save_monster_sprite(sprite_id, wan)
                md = SkyTempleMessageDialog(
                    MainController.window(),
                    Gtk.DialogFlags.DESTROY_WITH_PARENT,
                    Gtk.MessageType.INFO,
                    Gtk.ButtonsType.OK,
                    _("The spritesheet was successfully imported."),
                    title=_("Success!"),
                    is_success=True,
                )
                md.run()
                md.destroy()
                # Shadow size
                if not is_zip:
                    tree = ElementTree.parse(os.path.join(fn, "AnimData.xml")).getroot()
                else:
                    with ZipFile(fn, "r") as ZipObj:
                        tree = ElementTree.fromstring(ZipObj.read("AnimData.xml"))
                self._set_shadow_size_cb(int(assert_not_none(assert_not_none(tree.find("ShadowSize")).text)))
                # Update/create sprconf.json:
                anims: Element = assert_not_none(tree.find("Anims"))
                action_indices = {}
                for action in anims:
                    name_normal: str = assert_not_none(assert_not_none(action.find("Name")).text)
                    action_index = action.find("Index")
                    if action_index is not None:
                        idx = int(assert_not_none(action_index.text))
                        action_indices[idx] = Pmd2Index(idx, [name_normal])
                self.module.update_sprconf(Pmd2Sprite(sprite_id, action_indices))
                cb()
                self._mark_as_modified_cb()
                MainController.reload_view()
            except BaseException as e:
                display_error(sys.exc_info(), str(e), _("Error importing the spritesheet."))

    @Gtk.Template.Callback()
    def on_export_ground_clicked(self, w: Gtk.MenuToolButton):
        self.module.export_a_sprite(self.module.get_monster_ground_sprite_chara(self.item_data, raw=True))

    @Gtk.Template.Callback()
    def on_import_ground_clicked(self, w: Gtk.MenuToolButton):
        sprite = self.module.import_a_sprite()
        if sprite is None:
            return
        self.module.save_monster_ground_sprite(self.item_data, sprite, raw=True)
        self._mark_as_modified_cb()
        MainController.reload_view()

    @Gtk.Template.Callback()
    def on_export_dungeon_clicked(self, w: Gtk.MenuToolButton):
        self.module.export_a_sprite(self.module.get_monster_monster_sprite_chara(self.item_data, raw=True))

    @Gtk.Template.Callback()
    def on_import_dungeon_clicked(self, w: Gtk.MenuToolButton):
        sprite = self.module.import_a_sprite()
        if sprite is None:
            return
        self.module.save_monster_monster_sprite(self.item_data, sprite, raw=True)
        self._mark_as_modified_cb()
        MainController.reload_view()

    @Gtk.Template.Callback()
    def on_export_attack_clicked(self, w: Gtk.MenuToolButton):
        self.module.export_a_sprite(self.module.get_monster_attack_sprite_chara(self.item_data, raw=True))

    @Gtk.Template.Callback()
    def on_import_attack_clicked(self, w: Gtk.MenuToolButton):
        sprite = self.module.import_a_sprite()
        if sprite is None:
            return
        self.module.save_monster_attack_sprite(self.item_data, sprite, raw=True)
        self._mark_as_modified_cb()
        MainController.reload_view()

    @Gtk.Template.Callback()
    def on_explanation_text_activate_link(self, *args):
        self.module.open_spritebot_explanation()

    @Gtk.Template.Callback()
    def on_explanation_text2_activate_link(self, *args):
        self.module.open_gfxcrunch_page()

    @Gtk.Template.Callback()
    def on_spritecollab_browser_clicked(self, *args):
        MainController.show_spritecollab_browser()

    def _get_sprite_anim(self):
        current = self._rendered_frame_info[self._anim_counter]
        self._frame_counter += 1
        if self._frame_counter > current[0]:
            self._frame_counter = 0
            self._anim_counter += 1
            if self._anim_counter >= len(self._rendered_frame_info):
                self._anim_counter = 0
        return current[1]

    def _load_frames(self):
        with self._monster_bin as monster_bin:
            sprite = self._load_sprite_from_bin_pack(monster_bin, self.item_data)
            ani_group = sprite.anim_groups[0]
            frame_id = 2
            for frame in ani_group[frame_id].frames:
                mfg_id = frame.frame_id
                sprite_img, (cx, cy) = sprite.render_frame(sprite.frames[mfg_id])
                self._rendered_frame_info.append(
                    (
                        frame.duration,
                        (
                            pil_to_cairo_surface(sprite_img),
                            cx,
                            cy,
                            sprite_img.width,
                            sprite_img.height,
                        ),
                    )
                )

    def _load_sprite_from_bin_pack(self, bin_pack: BinPack, file_id) -> Wan:
        # TODO: Support of bin_pack item management via the RomProject instead?
        return FileType.WAN.deserialize(FileType.PKDPX.deserialize(bin_pack[file_id]).decompress())
