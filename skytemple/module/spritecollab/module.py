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
import asyncio
import os
from tempfile import NamedTemporaryFile
from typing import Optional, Tuple

from PIL import Image
from gi.repository import Gtk, GLib, Pango
from range_typed_integers import i16
from skytemple_files.common.i18n_util import _
from skytemple_files.common.ppmdu_config.data import Pmd2Sprite
from skytemple_files.common.spritecollab.client import MonsterFormDetails, SpriteCollabClient
from skytemple_files.data.md.protocol import ShadowSize
from skytemple_files.graphics.chara_wan.model import WanFile

from skytemple.controller.main import MainController
from skytemple.core.abstract_module import AbstractModule
from skytemple.core.error_handler import display_error
from skytemple.core.item_tree import ItemTree
from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple.core.rom_project import RomProject
from skytemple.module.spritecollab.controller.browser import BrowserController


class SpritecollabModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return ['sprite', 'portrait']

    @classmethod
    def sort_order(cls):
        return 0  # n/a

    def __init__(self, rom_project: RomProject):
        pass

    def load_tree_items(self, item_tree: ItemTree):
        pass  # n/a

    def show_spritecollab_browser(self):
        return BrowserController.get_instance(self).show()

    def apply_portraits(self, window: Gtk.Window, portraits: Image.Image):
        project = RomProject.get_current()
        monster_idx = self._check_opened(window)
        if monster_idx is None:
            return
        assert project is not None
        portrait_module = project.get_module('portrait')
        prt_idx = monster_idx - 1
        if not portrait_module.is_idx_supported(prt_idx):
            self._msg_not_supported(window)
            return
        fname: Optional[str] = None
        try:
            with NamedTemporaryFile('w+b', delete=False, suffix='.png') as f:
                fname = f.name
                portraits.save(f)
            portrait_module.import_sheet(prt_idx, fname)
            GLib.idle_add(lambda: MainController.reload_view())
            GLib.idle_add(lambda: self._msg_success(window, _("Portraits successfully imported.")))
        finally:
            try:
                if fname is not None:
                    os.remove(fname)
            except Exception:
                pass

    def apply_sprites(self, window: Gtk.Window, client: SpriteCollabClient, form: MonsterFormDetails):
        project = RomProject.get_current()
        monster_idx = self._check_opened(window)
        if monster_idx is None:
            return
        assert project is not None

        # TODO: Message asking about EventSleep and also ask about new sprite ID or not
        show_sprite_diag = self._show_sprite_diag(window)
        if show_sprite_diag is None:
            return
        copy_event_sleep, new = show_sprite_diag

        sprite_module = project.get_module('sprite')
        monster_module = project.get_module('monster')
        if new:
            sprite_idx = i16(sprite_module.get_monster_sprite_count())
        else:
            sprite_idx = monster_module.get_sprite_idx(monster_idx)
        if not sprite_module.is_idx_supported(sprite_idx):
            self._msg_not_supported(window)
            return

        spr_result = asyncio.run(get_sprites(client, (form.monster_id, form.form_path), copy_event_sleep))
        if spr_result is not None:
            wan_file, pmd2_sprite, shadow_size_id = spr_result
            # update sprite
            sprite_module.save_monster_sprite(sprite_idx, wan_file)

            monster_module.set_sprite_idx(monster_idx, sprite_idx)
            monster_module.set_shadow_size(
                monster_idx,
                ShadowSize(shadow_size_id)  # type: ignore
            )
            sprite_module.update_sprconf(pmd2_sprite)
        else:
            self._msg_no_data(window)
            return

        GLib.idle_add(lambda: MainController.reload_view())
        GLib.idle_add(lambda: self._msg_success(window, _("Sprites successfully imported.")))

    def _check_opened(self, window: Gtk.Window) -> Optional[int]:
        project = RomProject.get_current()
        if project is None:
            self._msg_not_opened(window)
            return None
        monster_module = project.get_module('monster')
        monster_idx = monster_module.get_opened_id()
        if monster_idx is None:
            self._msg_not_opened(window)
            return None
        return monster_idx

    def _msg_success(self, window: Gtk.Window, msg: str):
        self._msg(msg, window, Gtk.MessageType.INFO, is_success=True)

    def _msg_not_opened(self, window: Gtk.Window):
        self._msg(_("Open a Pokémon in the main window to apply the assets to."), window, Gtk.MessageType.INFO)

    def _msg_no_data(self, window: Gtk.Window):
        self._msg(_("Could not apply the sprites, since no sprite data is available."), window, Gtk.MessageType.ERROR)

    def _msg_not_supported(self, window: Gtk.Window):
        self._msg(_("This Pokémon does not support portraits and/or sprites."), window, Gtk.MessageType.ERROR)

    def _show_sprite_diag(self, window: Gtk.Window) -> Optional[Tuple[bool, bool]]:
        diag: Gtk.Dialog = Gtk.Dialog()
        diag.set_parent(window)
        diag.set_transient_for(window)
        diag.set_modal(True)
        diag.add_buttons(_("Cancel"), Gtk.ResponseType.CLOSE, _("Apply"), Gtk.ResponseType.APPLY)
        content: Gtk.Box = diag.get_content_area()
        content.set_spacing(10)
        content.set_margin_start(5)
        content.set_margin_end(5)
        content.set_margin_left(5)
        content.set_margin_right(5)
        content_label: Gtk.Label = Gtk.Label.new(_(
            "This will replace the sprite of this Pokémon with the one from the repository.\n"
            "You can also choose to create a new sprite instead, it will be assigned to the Pokémon.\n\n"
            "Additionally you can choose to copy the Sleep animation to the EventSleep/Laying/Waking\n"
            "animations (if they aren't available for this Pokémon otherwise).\n"
            "This will fix Pokémon using weird animations instead of sleeping on the overworld, \n"
            "when choosing them as a starter or partner."
        ))
        content_label.set_line_wrap(True)
        content_label.set_line_wrap_mode(Pango.WrapMode.WORD)
        content.pack_start(content_label, True, True, 0)
        new_sprite_id: Gtk.CheckButton = Gtk.CheckButton.new_with_label(_("Create a new sprite instead of replacing the existing one."))
        new_sprite_id.set_active(False)
        content.pack_start(new_sprite_id, True, True, 0)
        copy_event_sleep: Gtk.CheckButton = Gtk.CheckButton.new_with_label(_("Copy the Sleep animation to EventSleep/Laying/Waking."))
        copy_event_sleep.set_active(True)
        content.pack_start(copy_event_sleep, True, True, 0)
        content.show_all()
        response = diag.run()
        diag.hide()
        diag.destroy()
        if response == Gtk.ResponseType.APPLY:
            return copy_event_sleep.get_active(), new_sprite_id.get_active()
        return None

    def _msg(self, msg: str, window: Gtk.Window, typ=Gtk.MessageType.ERROR, is_success=False):
        if typ == Gtk.MessageType.ERROR:
            display_error(
                None,
                msg,
                should_report=False,
                window=window
            )
        else:
            md = SkyTempleMessageDialog(window,
                                        Gtk.DialogFlags.DESTROY_WITH_PARENT, typ,
                                        Gtk.ButtonsType.OK, msg, is_success=is_success)
            md.set_position(Gtk.WindowPosition.CENTER)
            md.run()
            md.destroy()


async def get_sprites(
        client: SpriteCollabClient,
        form: Tuple[int, str],
        copy_to_event_sleep_if_missing: bool
) -> Optional[Tuple[WanFile, Pmd2Sprite, int]]:
    async with client as session:
        sprites = await session.fetch_sprites(
            [form],
            [None],
            copy_to_event_sleep_if_missing=copy_to_event_sleep_if_missing
        )
        return sprites[0]
