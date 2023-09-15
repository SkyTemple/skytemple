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
from typing import Optional, Dict, List, Union

from gi.repository import Gtk
from skytemple.core.abstract_module import AbstractModule, DebuggingInfo
from skytemple.core.item_tree import ItemTree, ItemTreeEntryRef, ItemTreeEntry, RecursionType
from skytemple.core.model_context import ModelContext
from skytemple.core.module_controller import AbstractController
from skytemple.core.rom_project import RomProject, BinaryName
from skytemple.module.misc_graphics.controller.w16 import W16Controller
from skytemple.module.misc_graphics.controller.wte_wtu import WteWtuController
from skytemple.module.misc_graphics.controller.zmappat import ZMappaTController
from skytemple.module.misc_graphics.controller.font import FontController
from skytemple.module.misc_graphics.controller.graphic_font import GraphicFontController
from skytemple.module.misc_graphics.controller.chr import ChrController
from skytemple.module.misc_graphics.controller.cart_removed import CartRemovedController
from skytemple.module.misc_graphics.controller.main import MainController, MISC_GRAPHICS
from skytemple_files.common.types.file_types import FileType
from skytemple_files.container.dungeon_bin.model import DungeonBinPack
from skytemple_files.graphics.wte.model import Wte
from skytemple_files.graphics.wtu.model import Wtu
from skytemple_files.graphics.fonts import *
from skytemple_files.graphics.fonts.abstract import AbstractFont
from skytemple_files.graphics.fonts.font_dat.model import FontDat
from skytemple_files.graphics.fonts.font_sir0.model import FontSir0
from skytemple_files.graphics.fonts.banner_font.model import BannerFont
from skytemple_files.graphics.fonts.graphic_font.model import GraphicFont
from skytemple_files.graphics.chr.model import Chr
from skytemple_files.graphics.zmappat.model import ZMappaT
from skytemple_files.hardcoded.cart_removed import HardcodedCartRemoved

from PIL import Image

W16_FILE_EXT = 'w16'
WTE_FILE_EXT = 'wte'
WTU_FILE_EXT = 'wtu'
DAT_FILE_EXT = 'dat'
BIN_FILE_EXT = 'bin'
PAL_FILE_EXT = 'pal'
CHR_FILE_EXT = 'chr'
ZMAPPAT_FILE_EXT = 'zmappat'
CART_REMOVED_NAME = "cart_removed.at"
DUNGEON_BIN_PATH = 'DUNGEON/dungeon.bin'
VALID_FONT_DAT_FILES = {'FONT/kanji_rd.dat', 'FONT/unkno_rd.dat'}
VALID_GRAPHIC_FONT_FILES = {'FONT/staffont.dat', 'FONT/markfont.dat'}
VALID_FONT_SIR0_FILES = {'FONT/kanji.dat', 'FONT/kanji_b.dat', 'FONT/unknown.dat'}
VALID_BANNER_FONT_FILES = {"FONT/banner.bin", "FONT/banner_c.bin", "FONT/banner_s.bin"}
FONT_PAL_ASSOC = [("FONT/banner.bin","FONT/b_pal.bin"),
                  ("FONT/banner.bin","FONT/b_pal2.bin"),
                  ("FONT/banner_c.bin","FONT/b_pal_r.bin"),
                  ("FONT/banner_c.bin","FONT/b_pal_p.bin"),
                  ("FONT/banner_s.bin",None)]


class FontOpenSpec:
    def __init__(self, font_filename: str, pal_filename: Optional[str], font_type: FontType):
        self.font_filename = font_filename
        self.pal_filename = pal_filename
        self.font_type = font_type

    def get_row_name(self):
        if self.font_type == FontType.BANNER_FONT and self.pal_filename is not None:
            return self.font_filename + ':' + self.pal_filename
        else:
            return self.font_filename
        
class WteOpenSpec:
    def __init__(self, wte_filename: str, wtu_filename: Optional[str] = None, in_dungeon_bin=False):
        self.wte_filename = wte_filename
        self.wtu_filename = wtu_filename
        self.in_dungeon_bin = in_dungeon_bin


class MiscGraphicsModule(AbstractModule):
    @classmethod
    def depends_on(cls):
        return []

    @classmethod
    def sort_order(cls):
        return 800

    def __init__(self, rom_project: RomProject):
        """Various misc. graphics formats."""
        self.project = rom_project
        self.list_of_w16s = self.project.get_files_with_ext(W16_FILE_EXT)
        self.list_of_wtes = self.project.get_files_with_ext(WTE_FILE_EXT)
        self.list_of_wtus = self.project.get_files_with_ext(WTU_FILE_EXT)
        self.list_of_font_dats = sorted(list(set(self.project.get_files_with_ext(DAT_FILE_EXT)) & VALID_FONT_DAT_FILES))
        self.list_of_font_sir0s = sorted(list(set(self.project.get_files_with_ext(DAT_FILE_EXT)) & VALID_FONT_SIR0_FILES))
        self.list_of_graphic_fonts = sorted(list(set(self.project.get_files_with_ext(DAT_FILE_EXT)) & VALID_GRAPHIC_FONT_FILES))
        self.list_of_bins = self.project.get_files_with_ext(BIN_FILE_EXT)
        self.list_of_pals = self.project.get_files_with_ext(PAL_FILE_EXT)
        self.list_of_chrs = self.project.get_files_with_ext(CHR_FILE_EXT)
        self.list_of_banner_fonts = sorted(list(set(self.list_of_bins) & VALID_BANNER_FONT_FILES))
        self.dungeon_bin_context: ModelContext[DungeonBinPack]
        self.list_of_wtes_dungeon_bin: List[Wte]
        self.list_of_wtus_dungeon_bin: List[Wtu]
        self.list_of_zmappats_dungeon_bin: List[ZMappaT]

        self._item_tree: ItemTree
        self._tree_level_iter: Dict[str, ItemTreeEntryRef] = {}
        self._tree_level_dungeon_iter: Dict[str, ItemTreeEntryRef] = {}

    def load_tree_items(self, item_tree: ItemTree):
        self.dungeon_bin_context = self.project.open_file_in_rom(
            DUNGEON_BIN_PATH, FileType.DUNGEON_BIN,
            static_data=self.project.get_rom_module().get_static_data(),
            threadsafe=True
        )
        with self.dungeon_bin_context as dungeon_bin:
            self.list_of_wtes_dungeon_bin = dungeon_bin.get_files_with_ext(WTE_FILE_EXT)
            self.list_of_wtus_dungeon_bin = dungeon_bin.get_files_with_ext(WTU_FILE_EXT)
            self.list_of_zmappats_dungeon_bin = dungeon_bin.get_files_with_ext(ZMAPPAT_FILE_EXT)

        root = item_tree.add_entry(None, ItemTreeEntry(
            icon='skytemple-e-graphics-symbolic',
            name=MISC_GRAPHICS,
            module=self,
            view_class=MainController,
            item_data=0
        ))
        self._item_tree = item_tree
        self._tree_level_iter = {}
        self._tree_level_dungeon_iter = {}

        # chr at the beginning:
        for i, name in enumerate(self.list_of_chrs):
            self._tree_level_iter[name] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=name,
                module=self,
                view_class=ChrController,
                item_data=name
            ))
        
        sorted_entries = {}
        for name in self.list_of_w16s:
            sorted_entries[name] = False
        for name in self.list_of_wtes:
            sorted_entries[name] = True
        sorted_entries = {k: v for k, v in sorted(sorted_entries.items(), key=lambda item: item[0])}

        for i, (name, is_wte) in enumerate(sorted_entries.items()):
            if not is_wte:
                self._tree_level_iter[name] = item_tree.add_entry(root, ItemTreeEntry(
                    icon='skytemple-e-graphics-symbolic',
                    name=name,
                    module=self,
                    view_class=W16Controller,
                    item_data=self.list_of_w16s.index(name)
                ))
            else:
                wtu_name = name[:-3] + WTU_FILE_EXT
                if wtu_name not in self.list_of_wtus:
                    wtu_name = None
                self._tree_level_iter[name] = item_tree.add_entry(root, ItemTreeEntry(
                    icon='skytemple-e-graphics-symbolic',
                    name=name,
                    module=self,
                    view_class=WteWtuController,
                    item_data=WteOpenSpec(
                        name, wtu_name, False
                    )
                ))

        # fonts at the end:
        for i, name in enumerate(self.list_of_font_dats):
            spec = FontOpenSpec(name, None, FontType.FONT_DAT)
            self._tree_level_iter[spec.get_row_name()] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=spec.get_row_name(),
                module=self,
                view_class=FontController,
                item_data=spec
            ))
        
        for i, name in enumerate(self.list_of_font_sir0s):
            spec = FontOpenSpec(name, None, FontType.FONT_SIR0)
            self._tree_level_iter[spec.get_row_name()] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=spec.get_row_name(),
                module=self,
                view_class=FontController,
                item_data=spec
            ))
        
        for i, name in enumerate(self.list_of_banner_fonts):
            for assoc in FONT_PAL_ASSOC:
                if name==assoc[0]:
                    none_assoc = False
                    pal_name = assoc[1]
                    if pal_name not in self.list_of_bins:
                        pal_name = None
                    if not none_assoc or pal_name!=None:
                        if pal_name==None:
                            none_assoc = True
                        spec = FontOpenSpec(name, pal_name, FontType.BANNER_FONT)
                        self._tree_level_iter[spec.get_row_name()] = item_tree.add_entry(root, ItemTreeEntry(
                            icon='skytemple-e-graphics-symbolic',
                            name=spec.get_row_name(),
                            module=self,
                            view_class=FontController,
                            item_data=spec
                        ))
            
        for i, name in enumerate(self.list_of_graphic_fonts):
            pal_name = name[:-3] + PAL_FILE_EXT
            if pal_name not in self.list_of_pals:
                pal_name = None
            spec = FontOpenSpec(name, pal_name, FontType.GRAPHIC_FONT)
            self._tree_level_iter[spec.get_row_name()] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name=spec.get_row_name(),
                module=self,
                view_class=GraphicFontController,
                item_data=spec
            ))
            
        # dungeon bin entries at the end:
        for i, name in enumerate(self.list_of_wtes_dungeon_bin):
            wtu_name = name[:-3] + WTU_FILE_EXT
            if name[:-3] + WTU_FILE_EXT not in self.list_of_wtus_dungeon_bin:
                wtu_name = None
            self._tree_level_dungeon_iter[name] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name='dungeon.bin:' + name,
                module=self,
                view_class=WteWtuController,
                item_data=WteOpenSpec(
                    name, wtu_name, True
                )
            ))
        # zmappat at the end:
        for i, name in enumerate(self.list_of_zmappats_dungeon_bin):
            self._tree_level_dungeon_iter[name] = item_tree.add_entry(root, ItemTreeEntry(
                icon='skytemple-e-graphics-symbolic',
                name='dungeon.bin:' + name,
                module=self,
                view_class=ZMappaTController,
                item_data=name
            ))
        
        # cart removed at the end:
        self._tree_level_iter[CART_REMOVED_NAME] = item_tree.add_entry(root, ItemTreeEntry(
            icon='skytemple-e-graphics-symbolic',
            name=CART_REMOVED_NAME,
            module=self,
            view_class=CartRemovedController,
            item_data=CART_REMOVED_NAME
        ))

    def mark_w16_as_modified(self, item_id):
        """Mark a specific w16 as modified"""
        w16_filename = self.list_of_w16s[item_id]
        self.project.mark_as_modified(w16_filename)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._tree_level_iter[w16_filename], RecursionType.UP)

    def get_w16(self, item_id):
        w16_filename = self.list_of_w16s[item_id]
        return self.project.open_file_in_rom(w16_filename, FileType.W16)

    def get_wte(self, fn) -> Wte:
        return self.project.open_file_in_rom(fn, FileType.WTE)

    def get_wtu(self, fn) -> Wtu:
        return self.project.open_file_in_rom(fn, FileType.WTU)

    def get_font(self, spec: FontOpenSpec) -> Optional[AbstractFont]:
        if spec.font_type == FontType.FONT_DAT:
            return self.project.open_file_in_rom(spec.font_filename, FileType.FONT_DAT)
        elif spec.font_type == FontType.FONT_SIR0:
            return self.project.open_file_in_rom(spec.font_filename, FileType.FONT_SIR0)
        elif spec.font_type == FontType.BANNER_FONT:
            font = self.project.open_file_in_rom(spec.font_filename, FileType.BANNER_FONT)
            if spec.pal_filename:
                font.set_palette(self.project.open_file_in_rom(spec.pal_filename, FileType.PAL))
            return font
        else:
            return None
    
    def get_graphic_font(self, spec: FontOpenSpec) -> Optional[GraphicFont]:
        if spec.font_type == FontType.GRAPHIC_FONT:
            font = self.project.open_file_in_rom(spec.font_filename, FileType.GRAPHIC_FONT)
            if spec.pal_filename:
                font.set_palette(self.project.open_file_in_rom(spec.pal_filename, FileType.PAL))
            return font
        else:
            return None

    def get_chr(self, fn: str) -> Chr:
        chr_file = self.project.open_file_in_rom(fn, FileType.CHR)
        if fn[:-4]+".pal" in self.list_of_pals:
            pal = self.project.open_file_in_rom(fn[:-4]+".pal", FileType.PAL)
            chr_file.set_palette(pal)
        return chr_file

    def get_cart_removed_data(self) -> Image.Image:
        arm9 = self.project.get_binary(BinaryName.ARM9)
        static_data = self.project.get_rom_module().get_static_data()
        return HardcodedCartRemoved.get_cart_removed_data(arm9, static_data)
    
    def set_cart_removed_data(self, img: Image.Image):
        """Sets cart removed data"""
        def update(arm9):
            static_data = self.project.get_rom_module().get_static_data()
            HardcodedCartRemoved.set_cart_removed_data(img, arm9, static_data)
        self.project.modify_binary(BinaryName.ARM9, update)

        self._item_tree.mark_as_modified(self._tree_level_iter[CART_REMOVED_NAME], RecursionType.UP)
        
    def get_dungeon_bin_file(self, fn):
        with self.dungeon_bin_context as dungeon_bin:
            return dungeon_bin.get(fn)

    def _mark_font_assoc_as_modified(self, name: str):
        """Marks the other instances as modified (the ones with a different palette) """
        for assoc in FONT_PAL_ASSOC:
            if name==assoc[0]:
                pal_name = assoc[1]
                if pal_name not in self.list_of_bins:
                    pal_name = None
                if pal_name is not None:
                    spec = FontOpenSpec(name, pal_name, FontType.BANNER_FONT)
                    self._item_tree.mark_as_modified(self._tree_level_iter[spec.get_row_name()], RecursionType.UP)
        
    def mark_font_as_modified(self, item: FontOpenSpec):
        """Mark a specific font as modified"""
        self.project.mark_as_modified(item.font_filename)
        if item.pal_filename:
            self.project.mark_as_modified(item.pal_filename)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._tree_level_iter[item.get_row_name()], RecursionType.UP)
        self._mark_font_assoc_as_modified(item.font_filename)
        
    def mark_zmappat_as_modified(self, zmappat, fn):
        with self.dungeon_bin_context as dungeon_bin:
            dungeon_bin.set(fn, zmappat)
        self.project.mark_as_modified(DUNGEON_BIN_PATH)
        # Mark as modified in tree
        self._item_tree.mark_as_modified(self._tree_level_dungeon_iter[fn], RecursionType.UP)
        
    def mark_chr_as_modified(self, fn):
        """Mark a specific chr as modified"""
        self.project.mark_as_modified(fn)
        if fn[:-4]+".pal" in self.list_of_pals:
             self.project.mark_as_modified(fn[:-4]+".pal")
        self._item_tree.mark_as_modified(self._tree_level_iter[fn], RecursionType.UP)
        
    def mark_wte_as_modified(self, item: WteOpenSpec, wte, wtu):
        if item.in_dungeon_bin:
            with self.dungeon_bin_context as dungeon_bin:
                dungeon_bin.set(item.wte_filename, wte)
                if item.wtu_filename:
                    dungeon_bin.set(item.wtu_filename, wtu)
            self.project.mark_as_modified(DUNGEON_BIN_PATH)
            # Mark as modified in tree
            self._item_tree.mark_as_modified(self._tree_level_dungeon_iter[item.wte_filename], RecursionType.UP)
        else:
            self.project.mark_as_modified(item.wte_filename)
            if item.wtu_filename:
                self.project.mark_as_modified(item.wtu_filename)
            # Mark as modified in tree
            self._item_tree.mark_as_modified(self._tree_level_iter[item.wte_filename], RecursionType.UP)

    def collect_debugging_info(self, open_view: Union[AbstractController, Gtk.Widget]) -> Optional[DebuggingInfo]:
        if isinstance(open_view, CartRemovedController):
            pass  # todo
        if isinstance(open_view, ChrController):
            pass  # todo
        if isinstance(open_view, FontController):
            pass  # todo
        if isinstance(open_view, GraphicFontController):
            pass  # todo
        if isinstance(open_view, W16Controller):
            pass  # todo
        if isinstance(open_view, WteWtuController):
            pass  # todo
        if isinstance(open_view, ZMappaTController):
            pass  # todo
        return None
