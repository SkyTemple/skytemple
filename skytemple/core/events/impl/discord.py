"""
Discord presence module.
If the extra dependencies are not installed, importing this module will raise an ImportError.
"""

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
import asyncio
import inspect
import logging
import os
from collections.abc import Callable

from gi.repository import GLib, Gtk
from skytemple_files.common.i18n_util import _
from skytemple_files.common.types.file_types import FileType

from skytemple.core.abstract_module import AbstractModule
from skytemple.core.async_tasks.delegator import AsyncTaskDelegator
from skytemple.core.events.abstract_listener import AbstractListener
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject
from pypresence import Presence, BaseClient, AioPresence
import time

from skytemple.core.string_provider import StringType
from skytemple.core.ui_utils import version
from skytemple.core.widget.status_page import StStatusPage

CLIENT_ID = "736538698719690814"
IDLE_TIMEOUT = 5 * 60
logger = logging.getLogger(__name__)
SHOW_ROM_NAME = False


class DiscordPresence(AbstractListener):
    def __init__(self):
        """
        Tries to initialize the connection with Discord.
        :raises: ConnectionRefusedError
        """
        self.rpc: BaseClient
        if AsyncTaskDelegator.support_aio():
            self.rpc = AioPresence(CLIENT_ID)
        else:
            self.rpc = Presence(CLIENT_ID)
            self.rpc.connect()
        self._idle_timeout_id = None

        self.start = None
        self._reset_playtime()
        self.current_presence = "main"
        self.module_info = None
        self.module_state = None
        self.rom_name = None
        self.debugger_script_name = None
        self.project: RomProject | None = None

    async def on_event_loop_started(self):
        await self.rpc.connect()

    def on_main_window_focus(self):
        if self._idle_timeout_id is not None:
            GLib.source_remove(self._idle_timeout_id)
            self._idle_timeout_id = None
        if self.current_presence == "idle":
            self._reset_playtime()
        self.current_presence = "main"
        self._update_current_presence()

    def on_debugger_window_focus(self):
        if self._idle_timeout_id is not None:
            GLib.source_remove(self._idle_timeout_id)
            self._idle_timeout_id = None
        self.current_presence = "debugger"
        if self.current_presence == "idle":
            self._reset_playtime()
        self._update_current_presence()

    def on_idle(self):
        self._idle_timeout_id = None
        self.current_presence = "idle"
        self._update_current_presence()

    def on_focus_lost(self):
        if self._idle_timeout_id is None:
            self._idle_timeout_id = GLib.timeout_add_seconds(IDLE_TIMEOUT, self.on_idle)

    def on_project_open(self, project: RomProject):
        self.project = project
        if SHOW_ROM_NAME:
            self.rom_name = os.path.basename(project.filename)
        else:
            self.rom_name = "Version " + version()
        self._update_current_presence()

    def on_view_switch(
        self,
        module: AbstractModule,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        mod_handler = getattr(self, f"on_view_switch__{module.__class__.__name__}", None)
        if mod_handler and callable(mod_handler):
            mod_handler(module, view, breadcrumbs)
        else:
            self.module_info = f'Editing in module "{module.__class__.__name__}"'
            self.module_state = self.rom_name
        self._update_current_presence()

    def on_view_switch__MiscGraphicsModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.misc_graphics.widget.w16 import StMiscGraphicsW16Page
        from skytemple.module.misc_graphics.widget.wte_wtu import (
            StMiscGraphicsWteWtuPage,
        )

        self.module_info = "Editing graphics"
        self.module_state = self.rom_name
        if isinstance(view, StMiscGraphicsW16Page):
            self.module_state = module.list_of_w16s[view.item_data]
        if isinstance(view, StMiscGraphicsWteWtuPage):
            self.module_state = view.item_data.wte_filename

    def on_view_switch__DungeonGraphicsModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.dungeon_graphics.module import (
            NUMBER_OF_TILESETS,
        )
        from skytemple.module.dungeon_graphics.widget.tileset import (
            StDungeonGraphicsTilesetPage,
        )
        from skytemple.module.dungeon_graphics.widget.dungeon_bg import (
            StDungeonGraphicsDungeonBgPage,
        )

        self.module_info = "Editing dungeon tilesets"
        self.module_state = self.rom_name
        if isinstance(view, StDungeonGraphicsTilesetPage):
            self.module_state = f"Tileset {view.item_data}"
        if isinstance(view, StDungeonGraphicsDungeonBgPage):
            self.module_state = f"Background {NUMBER_OF_TILESETS + view.item_data}"

    def on_view_switch__BgpModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.bgp.widget.bgp import StBgpBgpPage

        self.module_info = "Editing background images"
        self.module_state = self.rom_name
        if isinstance(view, StBgpBgpPage):
            self.module_state = module.list_of_bgps[view.item_data]

    def on_view_switch__RomModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        self.module_info = "Editing the ROM"
        self.module_state = self.rom_name

    def on_view_switch__ListsModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.lists.controller.actor_list import ActorListController
        from skytemple.module.lists.controller.starters_list import (
            StartersListController,
        )
        from skytemple.module.lists.controller.recruitment_list import (
            RecruitmentListController,
        )
        from skytemple.module.lists.widget.world_map import StListsWorldMapPage

        self.module_info = "Editing lists"
        self.module_state = self.rom_name
        if isinstance(view, ActorListController):
            self.module_info = "Editing the actor list"
        if isinstance(view, StartersListController):
            self.module_info = "Editing the starters list"
        if isinstance(view, RecruitmentListController):
            self.module_info = "Editing the recruitment list"
        if isinstance(view, StListsWorldMapPage):
            self.module_info = "Editing the world map"

    def on_view_switch__PatchModule(
        self,
        module: AbstractModule,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.patch.widget.item_effects import StPatchItemEffectsPage
        from skytemple.module.patch.widget.move_effects import StPatchMoveEffectsPage
        from skytemple.module.patch.widget.sp_effects import StPatchSPEffectsPage

        if isinstance(view, StPatchItemEffectsPage):
            self.module_info = "Editing item effects"
            self.module_state = self.rom_name
        elif isinstance(view, StPatchMoveEffectsPage):
            self.module_info = "Editing move effects"
            self.module_state = self.rom_name
        elif isinstance(view, StPatchSPEffectsPage):
            self.module_info = "Editing special processes"
            self.module_state = self.rom_name
        else:
            self.module_info = "Editing patches"
            self.module_state = self.rom_name

    def on_view_switch__MapBgModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.map_bg.widget.bg import StMapBgBgPage

        self.module_info = "Editing map backgrounds"
        self.module_state = self.rom_name
        if isinstance(view, StMapBgBgPage):
            self.module_state = breadcrumbs[0]

    def on_view_switch__ScriptModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.script.widget.ssa import StScriptSsaPage

        self.module_info = "Editing scenes"
        self.module_state = self.rom_name
        if isinstance(view, StScriptSsaPage):
            if view.type == "sse":
                self.module_state = f"{breadcrumbs[1]} / {breadcrumbs[0]}"
            else:
                self.module_state = f"{breadcrumbs[2]} / {breadcrumbs[0]}"

    def on_view_switch__DungeonModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.dungeon.widget.dungeon import StDungeonDungeonPage
        from skytemple.module.dungeon.widget.floor import StDungeonFloorPage
        from skytemple.module.dungeon.widget.fixed_rooms import StDungeonFixedRoomsPage
        from skytemple.module.dungeon.widget.fixed import StDungeonFixedPage

        self.module_state = self.rom_name
        if isinstance(view, StDungeonDungeonPage):
            self.module_info = "Editing Dungeons"
            self.module_state = view.dungeon_name
        elif isinstance(view, StDungeonFloorPage):
            self.module_info = "Editing Dungeons"
            dungeon_name = module.project.get_string_provider().get_value(
                StringType.DUNGEON_NAMES_MAIN, view.item_data.dungeon.dungeon_id
            )
            self.module_state = f"{dungeon_name} - Floor {view.item_data.floor_id + 1}"
        elif isinstance(view, StDungeonFixedRoomsPage):
            self.module_info = "Editing Fixed Rooms"
        elif isinstance(view, StDungeonFixedPage):
            self.module_info = "Editing Fixed Rooms"
            self.module_state = f"Fixed Room {view.item_data}"

    def on_view_switch__MonsterModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.monster.widget.monster import StMonsterMonsterPage

        self.module_info = "Editing Pokémon"
        self.module_state = self.rom_name
        if isinstance(view, StMonsterMonsterPage):
            self.module_state = module.project.get_string_provider().get_value(
                StringType.POKEMON_NAMES,
                view.item_data % FileType.MD.properties().num_entities,
            )

    def on_view_switch__StringsModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.strings.widget.strings import StStringsStringsPage

        self.module_info = "Editing Text Strings"
        self.module_state = self.rom_name
        if isinstance(view, StStringsStringsPage):
            self.module_state = view.langname

    def on_view_switch__SpriteModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.sprite.widget.object import StSpriteObjectPage

        self.module_info = "Editing sprites"
        self.module_state = self.rom_name
        if isinstance(view, StSpriteObjectPage):
            self.module_state = breadcrumbs[0]

    def on_view_switch__MovesItemsModule(
        self,
        module,
        view: AbstractController | Gtk.Widget,
        breadcrumbs: list[str],
    ):
        from skytemple.module.moves_items.widget.item import StMovesItemsItemPage
        from skytemple.module.moves_items.widget.item_lists import (
            StMovesItemsItemListsPage,
        )
        from skytemple.module.moves_items.widget.move import StMovesItemsMovePage

        if isinstance(view, StStatusPage):
            if view.item_data.title == _("Items"):
                self.module_info = "Editing Items"
            else:
                self.module_info = "Editing Moves"
            self.module_state = self.rom_name
        elif isinstance(view, StMovesItemsItemPage):
            self.module_info = "Editing Items"
            self.module_state = breadcrumbs[0]
        elif isinstance(view, StMovesItemsMovePage):
            self.module_info = "Editing Moves"
            self.module_state = breadcrumbs[0]
        elif isinstance(view, StMovesItemsItemListsPage):
            self.module_info = "Editing Item Lists"
            self.module_state = self.rom_name

    def on_debugger_script_open(self, script_name: str):
        assert self.project is not None
        self.debugger_script_name = script_name.replace(self.project.get_project_file_manager().dir(), "")
        self._update_current_presence()

    def _update_current_presence(self):
        try:
            if self.current_presence == "main":
                self._update_presence(
                    state=self.module_state,
                    details=self.module_info,
                    start=self.start,
                    large_text=self.rom_name,
                )
            elif self.current_presence == "debugger":
                self._update_presence(
                    state=self.debugger_script_name,
                    details=("In the debugger" if self.debugger_script_name is None else "Editing script"),
                    start=self.start,
                    large_text=self.rom_name,
                    small_image="bug",
                )
            else:  # idle
                self._update_presence(state=None, details="Idle", start=None, large_text=self.rom_name)
        except BaseException as ex:
            logger.error("Updating the presence failed: ", exc_info=ex)

    def _update_presence(
        self,
        state,
        details,
        start,
        large_text,
        large_image="skytemple",
        small_image=None,
        small_text=None,
    ):
        if self.rpc.sock_writer is not None:
            self._schedule(
                self.rpc.update,
                state=state,
                details=details,
                start=start,
                large_image=large_image,
                large_text=large_text,
                small_image=small_image,
                small_text=small_text,
                buttons=[{"label": "Get SkyTemple", "url": "https://skytemple.org"}],
            )

    def _reset_playtime(self):
        self.start = int(time.time())

    @staticmethod
    def _schedule(f: Callable, *args, **kwargs):
        """
        Depending on whether f is a normal or a coroutine function,
        run it now or send it to the event loop to run soon.
        """
        if inspect.iscoroutinefunction(f):
            asyncio.create_task(f(*args, **kwargs))
        else:
            f(*args, **kwargs)
