"""Sprite renderer module. Allows rendering Sprites, and loads them asynchronously."""
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
import json
import logging
import os
import threading
from typing import TYPE_CHECKING, Tuple, Dict, List, Union

import cairo
try:
    from PIL import Image, ImageFilter
except ImportError:
    from pil import Image, ImageFilter
from gi.repository import Gdk, Gtk, GdkPixbuf

from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.model_context import ModelContext
from skytemple.core.ui_utils import data_dir
from skytemple_files.common.task_runner import AsyncTaskRunner
from skytemple_files.common.types.file_types import FileType
from skytemple_files.common.util import MONSTER_MD, MONSTER_BIN, open_utf8
from skytemple_files.container.bin_pack.model import BinPack
from skytemple_files.data.md.model import Md
from skytemple_files.graphics.wan_wat.model import Wan

if TYPE_CHECKING:
    from skytemple.core.rom_project import RomProject


SpriteAndOffsetAndDims = Tuple[cairo.ImageSurface, int, int, int, int]
ActorSpriteKey = Tuple[Union[str, int], int]
sprite_provider_lock = threading.Lock()
logger = logging.getLogger(__name__)

FALLBACK_STANDIN_ENTITIY = 1
STANDIN_ENTITIES_DEFAULT = {
    0: 1,
    1: 1,
    2: 4,
    3: 25,
    4: 7,
    10: 4,
    11: 7,
    12: 2,
    13: 5,
    14: 26,
    15: 8,
    22: 152,
    23: 155,
    24: 158,
    25: 280,
    26: 153,
    27: 156,
    28: 159,
    29: 271,
    30: 282,
    31: 283,
    32: 284,
    33: 285,
    34: 286,
    35: 287,
    36: 288,
    37: 422,
    38: 423,
    39: 424,
    40: 425,
    41: 426,
    42: 427,
    43: 428,
    44: 429,
    45: 430,
    46: 488,
    47: 488,
    48: 488,
    49: 488,
    50: 488,
    51: 488,
    52: 488,
    53: 488,
    54: 488,
    55: 488,
    56: 488,
    57: 488,
    58: 1,
    59: 4,
    60: 1,
    61: 4,
    62: 25,
    63: 7,
    64: 1,
    65: 4,
    66: 1,
    67: 4
}
FILE_NAME_STANDIN_SPRITES = '.standin_sprites.json'


class SpriteProvider:
    """
    SpriteProvider. This class renders sprites using Threads. If a Sprite is requested, a loading icon
    is returned instead, until it is loaded by the AsyncTaskRunner.
    """
    def __init__(self, project: 'RomProject'):
        self._project = project
        self._loader_surface_dims = None
        self._loader_surface = None

        self._loaded__monsters: Dict[ActorSpriteKey, SpriteAndOffsetAndDims] = {}
        self._loaded__monsters_outlines: Dict[ActorSpriteKey, SpriteAndOffsetAndDims] = {}
        self._loaded__actor_placeholders: Dict[ActorSpriteKey, SpriteAndOffsetAndDims] = {}
        self._loaded__objects: Dict[str, SpriteAndOffsetAndDims] = {}

        self._requests__monsters: List[ActorSpriteKey] = []
        self._requests__monsters_outlines: List[ActorSpriteKey] = []
        self._requests__actor_placeholders: List[ActorSpriteKey] = []
        self._requests__objects: List[str] = []

        self._monster_md: Md = self._project.open_file_in_rom(MONSTER_MD, FileType.MD, threadsafe=True)
        self._monster_bin: BinPack = self._project.open_file_in_rom(MONSTER_BIN, FileType.BIN_PACK, threadsafe=True)

        self._stripes = Image.open(os.path.join(data_dir(), 'stripes.png'))
        self._loaded_standins = None

        # init_loader MUST be called next!

    def init_loader(self, screen: Gdk.Screen):
        icon_theme: Gtk.IconTheme = Gtk.IconTheme.get_for_screen(screen)
        # Loader icon
        loader_icon: GdkPixbuf.Pixbuf = icon_theme.load_icon(
            'skytemple-image-loading-symbolic', 24, Gtk.IconLookupFlags.FORCE_SIZE
        ).copy()
        self._loader_surface_dims = loader_icon.get_width(), loader_icon.get_height()
        self._loader_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *self._loader_surface_dims)
        ctx = cairo.Context(self._loader_surface)
        Gdk.cairo_set_source_pixbuf(ctx, loader_icon, 0, 0)
        ctx.paint()
        # Error icon
        error_icon: GdkPixbuf.Pixbuf = icon_theme.load_icon(
            'skytemple-img-load-error-symbolic', 24, Gtk.IconLookupFlags.FORCE_SIZE
        ).copy()
        self._error_surface_dims = error_icon.get_width(), error_icon.get_height()
        self._error_surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, *self._error_surface_dims)
        ctx = cairo.Context(self._error_surface)
        Gdk.cairo_set_source_pixbuf(ctx, error_icon, 0, 0)
        ctx.paint()

    def reset(self):
        with sprite_provider_lock:
            self._loaded__monsters: Dict[int, cairo.Surface] = {}
            self._loaded__actor_placeholders: Dict[str, cairo.Surface] = {}
            self._loaded__objects: Dict[str, cairo.Surface] = {}

            self._requests__monsters: List[int] = []
            self._requests__actor_placeholders: List[str] = []
            self._requests__objects: List[str] = []

    def get_actor_placeholder(self, actor_id, direction_id: int, after_load_cb=lambda: None) -> SpriteAndOffsetAndDims:
        """
        Returns a placeholder sprite for the actor with the given index (in the actor table).
        As long as the sprite is being loaded, the loader sprite is returned instead.
        """
        with sprite_provider_lock:
            if (actor_id, direction_id) in self._loaded__actor_placeholders:
                return self._loaded__actor_placeholders[(actor_id, direction_id)]
            if (actor_id, direction_id) not in self._requests__actor_placeholders:
                self._requests__actor_placeholders.append((actor_id, direction_id))
                self._load_actor_placeholder(actor_id, direction_id, after_load_cb)
        return self.get_loader()

    def get_monster(self, md_index, direction_id: int, after_load_cb=lambda: None) -> SpriteAndOffsetAndDims:
        """
        Returns the sprite using the index from the monster.md.
        As long as the sprite is being loaded, the loader sprite is returned instead.
        """
        with sprite_provider_lock:
            if (md_index, direction_id) in self._loaded__monsters:
                return self._loaded__monsters[(md_index, direction_id)]
            if (md_index, direction_id) not in self._requests__monsters:
                self._requests__monsters.append((md_index, direction_id))
                self._load_monster(md_index, direction_id, after_load_cb)
        return self.get_loader()

    def get_monster_outline(self, md_index, direction_id: int, after_load_cb=lambda: None) -> SpriteAndOffsetAndDims:
        """
        Returns the outline of a sprite using the index from the monster.md.
        As long as the sprite is being loaded, the loader sprite is returned instead.
        """
        with sprite_provider_lock:
            if (md_index, direction_id) in self._loaded__monsters_outlines:
                return self._loaded__monsters_outlines[(md_index, direction_id)]
            if (md_index, direction_id) not in self._requests__monsters_outlines:
                self._requests__monsters_outlines.append((md_index, direction_id))
                self._load_monster_outline(md_index, direction_id, after_load_cb)
        return self.get_loader()

    def get_for_object(self, name, after_load_cb=lambda: None) -> SpriteAndOffsetAndDims:
        """
        Returns a named object sprite file from the GROUND directory.
        As long as the sprite is being loaded, the loader sprite is returned instead.
        """
        with sprite_provider_lock:
            if name in self._loaded__objects:
                return self._loaded__objects[name]
            if name not in self._requests__objects:
                self._requests__objects.append(name)
                self._load_object(name, after_load_cb)
        return self.get_loader()

    def _load_actor_placeholder(self, actor_id, direction_id: int, after_load_cb):
        AsyncTaskRunner.instance().run_task(self._load_actor_placeholder__impl(actor_id, direction_id, after_load_cb))

    async def _load_actor_placeholder__impl(self, actor_id, direction_id: int, after_load_cb):
        md_index = FALLBACK_STANDIN_ENTITIY
        if actor_id in self.get_standin_entities():
            md_index = self.get_standin_entities()[actor_id]
        try:
            sprite_img, cx, cy, w, h = self._retrieve_monster_sprite(md_index, direction_id)

            # Convert to outline + stripes
            alpha_sprite = sprite_img.getchannel('A')

            im_outline = sprite_img.filter(ImageFilter.FIND_EDGES)
            alpha_outline = im_outline.getchannel('A')

            out_sprite = Image.new('RGBA', im_outline.size)
            for i in range(0, out_sprite.width, self._stripes.width):
                for j in range(0, out_sprite.height, self._stripes.height):
                    out_sprite.paste(self._stripes, (i, j))

            im_outline = Image.new('RGBA', im_outline.size, color='white')
            out_sprite.paste(im_outline, (0, 0, im_outline.width, im_outline.height), alpha_outline)

            out_sprite.putalpha(alpha_sprite)
            # Make red transparent
            data = out_sprite.getdata()
            new_data = []
            for item in data:
                if item[0] > 200 and item[1] < 200 and item[2] < 200:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            out_sprite.putdata(new_data)

            # /

            surf = pil_to_cairo_surface(out_sprite)
            loaded = surf, cx, cy, w, h
        except BaseException:
            loaded = self.get_error()
        with sprite_provider_lock:
            self._loaded__actor_placeholders[(actor_id, direction_id)] = loaded
            self._requests__actor_placeholders.remove((actor_id, direction_id))
        after_load_cb()

    def _load_monster(self, md_index, direction_id: int, after_load_cb):
        AsyncTaskRunner.instance().run_task(self._load_monster__impl(md_index, direction_id, after_load_cb))

    async def _load_monster__impl(self, md_index, direction_id: int, after_load_cb):
        try:
            pil_img, cx, cy, w, h = self._retrieve_monster_sprite(md_index, direction_id)
            surf = pil_to_cairo_surface(pil_img)
            loaded = surf, cx, cy, w, h
        except BaseException:
            loaded = self.get_error()
        with sprite_provider_lock:
            self._loaded__monsters[(md_index, direction_id)] = loaded
            self._requests__monsters.remove((md_index, direction_id))
        after_load_cb()

    def _load_monster_outline(self, md_index, direction_id: int, after_load_cb):
        AsyncTaskRunner.instance().run_task(self._load_monster_outline__impl(md_index, direction_id, after_load_cb))

    async def _load_monster_outline__impl(self, md_index, direction_id: int, after_load_cb):
        try:
            sprite_img, cx, cy, w, h = self._retrieve_monster_sprite(md_index, direction_id)

            # Convert to outline + stripes

            im_outline = sprite_img.filter(ImageFilter.FIND_EDGES)
            alpha_outline = im_outline.getchannel('A')
            im_outline = Image.new('RGBA', im_outline.size, color='white')
            im_outline.putalpha(alpha_outline)

            # /

            surf = pil_to_cairo_surface(im_outline)
            loaded = surf, cx, cy, w, h
        except BaseException:
            loaded = self.get_error()
        with sprite_provider_lock:
            self._loaded__monsters_outlines[(md_index, direction_id)] = loaded
            self._requests__monsters_outlines.remove((md_index, direction_id))
        after_load_cb()

    def _retrieve_monster_sprite(self, md_index, direction_id: int) -> Tuple[Image.Image, int, int, int, int]:
        try:
            with self._monster_md as monster_md:
                actor_sprite_id = monster_md[md_index].sprite_index
            if actor_sprite_id < 0:
                raise ValueError("Invalid Sprite index")
            with self._monster_bin as monster_bin:
                sprite = self._load_sprite_from_bin_pack(monster_bin, actor_sprite_id)

                ani_group = sprite.get_animations_for_group(sprite.anim_groups[0])
                frame_id = direction_id - 1 if direction_id > 0 else 0
                mfg_id = ani_group[frame_id].frames[0].frame_id

                sprite_img, (cx, cy) = sprite.render_frame_group(sprite.frame_groups[mfg_id])
            return sprite_img, cx, cy, sprite_img.width, sprite_img.height
        except BaseException as e:
            # Error :(
            logger.warning(f"Error loading a monster sprite for {md_index}.", exc_info=e)
            raise RuntimeError(f"Error loading monster sprite for {md_index}") from e

    def _load_object(self, name, after_load_cb):
        AsyncTaskRunner.instance().run_task(self._load_object__impl(name, after_load_cb))

    async def _load_object__impl(self, name, after_load_cb):
        try:
            with self._load_sprite_from_rom(f'GROUND/{name}.wan') as sprite:
                ani_group = sprite.get_animations_for_group(sprite.anim_groups[0])
                frame_id = 0
                mfg_id = ani_group[frame_id].frames[0].frame_id

                sprite_img, (cx, cy) = sprite.render_frame_group(sprite.frame_groups[mfg_id])
            surf = pil_to_cairo_surface(sprite_img)
            with sprite_provider_lock:
                self._loaded__objects[name] = surf, cx, cy, sprite_img.width, sprite_img.height

        except BaseException as e:
            # Error :(
            logger.warning(f"Error loading an object sprite for {name}.", exc_info=e)
            with sprite_provider_lock:
                self._loaded__objects[name] = self.get_error()
        with sprite_provider_lock:
            self._requests__objects.remove(name)
        after_load_cb()

    def _load_sprite_from_bin_pack(self, bin_pack: BinPack, file_id) -> Wan:
        # TODO: Support of bin_pack item management via the RomProject instead?
        return FileType.WAN.deserialize(FileType.COMMON_AT.deserialize(bin_pack[file_id]).decompress())

    def _load_sprite_from_rom(self, path: str) -> ModelContext[Wan]:
        return self._project.open_file_in_rom(path, FileType.WAN, threadsafe=True)

    def get_loader(self) -> SpriteAndOffsetAndDims:
        """
        Returns the loader sprite. A "loading" icon with the size ~24x24px.
        """
        w, h = self._loader_surface_dims
        return self._loader_surface, int(w/2), h, w, h

    def get_error(self) -> SpriteAndOffsetAndDims:
        """
        Returns the error sprite. An "error" icon with the size ~24x24px.
        """
        w, h = self._error_surface_dims
        return self._error_surface, int(w/2), h, w, h

    def get_standin_entities(self):
        if not self._loaded_standins:
            self._loaded_standins = STANDIN_ENTITIES_DEFAULT
            p = self._standin_entities_filepath()
            if os.path.exists(p):
                with open_utf8(p, 'r') as f:
                    try:
                        self._loaded_standins = {int(k): v for k, v in json.load(f).items()}
                    except BaseException as err:
                        logger.error(f"Failed to load standin sprites from {p}, falling back to default: {err}.")
        return self._loaded_standins

    def set_standin_entities(self, mappings):
        with sprite_provider_lock:
            self._loaded__actor_placeholders = {}
        p = self._standin_entities_filepath()
        with open_utf8(p, 'w') as f:
            json.dump(mappings, f)
        self._loaded_standins = mappings

    def _standin_entities_filepath(self):
        return os.path.join(self._project.get_project_file_manager().dir(), FILE_NAME_STANDIN_SPRITES)
