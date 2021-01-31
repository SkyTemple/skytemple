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
import logging
import os
import sys
from typing import TYPE_CHECKING, Optional, Dict, List

from xml.etree.ElementTree import Element, ElementTree

from skytemple.core.message_dialog import SkyTempleMessageDialog
from skytemple_files.common.xml_util import prettify

import cairo

from skytemple.core.error_handler import display_error
from skytemple_files.graphics.fonts.abstract import AbstractFont

try:
    from PIL import Image
except:
    from pil import Image
from gi.repository import Gtk
from gi.repository.Gtk import ResponseType

from skytemple.controller.main import MainController
from skytemple.core.img_utils import pil_to_cairo_surface
from skytemple.core.module_controller import AbstractController
from skytemple_files.common.i18n_util import f, _

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from skytemple.module.misc_graphics.module import MiscGraphicsModule, FontOpenSpec


IMAGE_ZOOM = 2
COLUMN_TITLE = {"char": _("Char ID"), "width": _("Width"),
                "bprow": _("Bytes per row"), "cat": _("Category"), "padding": _("Padding")}
class FontController(AbstractController):
    def __init__(self, module: 'MiscGraphicsModule', item: 'FontOpenSpec'):
        self.module = module
        self.spec = item
        self.font: Optional[AbstractFont] = self.module.get_font(self.spec)
        
        self.builder = None

    def get_view(self) -> Gtk.Widget:
        self.builder = self._get_builder(__file__, 'font.glade')
        self._init_font()

        # Generate Automatically the columns since we don't know what properties we will be using
        self.entry_properties = self.font.get_entry_properties()
        tree_store = Gtk.ListStore(*([str]*len(self.entry_properties)))
        entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
        entry_tree.set_model(tree_store)
        self._column_mapping: List[Tuple[Gtk.CellRendererText, str]] = []
        for i, p in enumerate(self.entry_properties):
            renderer = Gtk.CellRendererText(editable=(p!="char"))
            renderer.connect("edited", self.on_row_value_changed)
            column = Gtk.TreeViewColumn(COLUMN_TITLE[p], renderer, text=i)
            self._column_mapping.append((renderer, p))
            entry_tree.append_column(column)
        
        self._switch_table()
        self.builder.connect_signals(self)
        self.builder.get_object('draw').connect('draw', self.draw)
        return self.builder.get_object('editor')

    def on_export_clicked(self, w: Gtk.MenuToolButton):
        dialog = Gtk.FileChooserNative.new(
            _("Export font in folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            '_Save', None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()

        if response == Gtk.ResponseType.ACCEPT:
            xml, tables = self.font.export_to_xml()
            with open(os.path.join(fn, f'char_tables.xml'), 'w') as f:
                f.write(prettify(xml))
            for i, table in tables.items():
                table.save(os.path.join(fn, f'table-{i}.png'))
            
    def on_import_clicked(self, w: Gtk.MenuToolButton):
        md = SkyTempleMessageDialog(
            MainController.window(),
            Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.INFO,
            Gtk.ButtonsType.OK,
            _("To import, select a folder containing all the files that were created when exporting the font.\n"
              "IMPORTANT: All image files must be indexed PNGs!\n"
              "For banner fonts, all images must have the same palette."),
            title=_("Import Font")
        )
        md.run()
        md.destroy()
        dialog = Gtk.FileChooserNative.new(
            _("Import font from folder..."),
            MainController.window(),
            Gtk.FileChooserAction.SELECT_FOLDER,
            None, None
        )

        response = dialog.run()
        fn = dialog.get_filename()
        dialog.destroy()
        
        if response == Gtk.ResponseType.ACCEPT:
            try:
                xml = ElementTree().parse(os.path.join(fn, f'char_tables.xml'))
                tables = dict()
                for i in range(256):
                    path = os.path.join(fn, f'table-{i}.png')
                    if os.path.exists(path):
                        tables[i] = Image.open(path, 'r')
                        
                self.font.import_from_xml(xml, tables)
                self.module.mark_font_as_modified(self.spec)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error importing font.")
                )
            self._init_font()
        
    def _init_font(self):
        # Init available tables
        self.tables = self.font.to_pil()
        
        cb_store: Gtk.ListStore = self.builder.get_object('table_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_table_select')
        self._fill_available_font_tables_into_store(cb_store)
        
        cb.set_active(0)

    def _add_property_row(self, store, entry):
        prop = entry.get_properties()
        row = [None]*len(self.entry_properties)
        for i, c in enumerate(self.entry_properties):
            if c in prop:
                row[i] = str(prop[c])
        store.append(row)
        
    def _switch_table(self):
        cb_store: Gtk.ListStore = self.builder.get_object('table_store')
        cb: Gtk.ComboBoxText = self.builder.get_object('cb_table_select')
        if cb.get_active_iter()!=None:
            v : int = cb_store[cb.get_active_iter()][0]
            self.entries = self.font.get_entries_from_table(v)
            
            entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
            store: Gtk.ListStore = entry_tree.get_model()
            store.clear()
            
            for e in self.entries:
                self._add_property_row(store, e)
            surface = self.tables[v].resize((self.tables[v].width*IMAGE_ZOOM, self.tables[v].height*IMAGE_ZOOM))
            self.surface = pil_to_cairo_surface(surface.convert('RGBA'))
            self.builder.get_object('draw').queue_draw()

    def on_entry_char_id_changed(self, widget):
        try:
            val = int(widget.get_text())
        except ValueError:
            val = -1
        
        if val<0:
            val = 0
            widget.set_text(str(val))
        elif val>=256:
            val=255
            widget.set_text(str(val))
        
    def on_btn_add_clicked(self, widget):
        dialog: Gtk.Dialog = self.builder.get_object('dialog_choose_char')

        self.builder.get_object('entry_char_id').set_text(str(0))
        self.builder.get_object('entry_char_id').set_increments(1,1)
        self.builder.get_object('entry_char_id').set_range(0, 255)
        
        dialog.set_attached_to(MainController.window())
        dialog.set_transient_for(MainController.window())

        resp = dialog.run()
        dialog.hide()
        if resp == ResponseType.OK:
            cb_store: Gtk.ListStore = self.builder.get_object('table_store')
            cb: Gtk.ComboBoxText = self.builder.get_object('cb_table_select')
            v : int = cb_store[cb.get_active_iter()][0]
            char = int(self.builder.get_object('entry_char_id').get_text())
            try:
                for e in self.entries:
                    if e.get_properties()["char"]==char:
                        raise ValueError(f(_("Character {char} already exists in the table!")))
                entry = self.font.create_entry_for_table(v)
                entry.set_properties({"char": char})
                self.entries.append(entry)
                
                entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
                store: Gtk.ListStore = entry_tree.get_model()
                self._add_property_row(store, entry)
                self.module.mark_font_as_modified(self.spec)
            except Exception as err:
                display_error(
                    sys.exc_info(),
                    str(err),
                    _("Error adding character.")
                )
    
    def on_btn_remove_clicked(self, widget):
        # Deletes all selected font entries
        # Allows multiple deletions
        entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
        active_rows : List[Gtk.TreePath] = entry_tree.get_selection().get_selected_rows()[1]
        store: Gtk.ListStore = entry_tree.get_model()
        for x in sorted(active_rows, key=lambda x:-x.get_indices()[0]):
            elt = self.entries[x.get_indices()[0]]
            self.font.delete_entry(elt)
            del self.entries[x.get_indices()[0]]
            del store[x.get_indices()[0]]
        self.module.mark_font_as_modified(self.spec)
        self.tables = self.font.to_pil()
        self._switch_table()

    def on_row_value_changed(self, widget, path, text):
        try:
            int(text)
        except ValueError:
            return
        entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
        store: Gtk.ListStore = entry_tree.get_model()
        for i, c in enumerate(self._column_mapping):
            if widget==c[0]:
                store[path][i] = text
                self.entries[int(path)].set_properties({c[1]: int(text)})
        self.module.mark_font_as_modified(self.spec)
        self.builder.get_object('draw').queue_draw()
        
    def on_entry_tree_selection_changed(self, *args):
        self.builder.get_object('draw').queue_draw()
        
    def on_font_table_changed(self, widget):
        self._switch_table()
    
    def _fill_available_font_tables_into_store(self, cb_store):
        # Init combobox
        cb_store.clear()
        for v in self.tables.keys():
            cb_store.append([v, f'Table {v}'])
    
    def draw(self, wdg, ctx: cairo.Context, *args):
        if self.surface:
            wdg.set_size_request(self.surface.get_width(), self.surface.get_height())
            ctx.fill()
            ctx.set_source_surface(self.surface, 0, 0)
            ctx.get_source().set_filter(cairo.Filter.NEAREST)
            ctx.paint()
            entry_tree: Gtk.TreeView = self.builder.get_object('entry_tree')
            active_rows : List[Gtk.TreePath] = entry_tree.get_selection().get_selected_rows()[1]
            for x in active_rows:
                prop = self.entries[x.get_indices()[0]].get_properties()
                if self.font.get_entry_image_size()>12:
                    ctx.set_line_width(4)
                    ctx.set_source_rgba(0,0,0, 1)
                    ctx.rectangle((prop["char"]%16)*self.font.get_entry_image_size()*IMAGE_ZOOM, \
                                  (prop["char"]//16)*self.font.get_entry_image_size()*IMAGE_ZOOM, prop["width"]*IMAGE_ZOOM, self.font.get_entry_image_size()*IMAGE_ZOOM)
                    ctx.stroke()
                ctx.set_line_width(2)
                if self.font.get_entry_image_size()>12:
                    ctx.set_source_rgba(1,1,1, 1)
                else:
                    ctx.set_source_rgba(1,0,0, 1)
                ctx.rectangle((prop["char"]%16)*self.font.get_entry_image_size()*IMAGE_ZOOM, \
                              (prop["char"]//16)*self.font.get_entry_image_size()*IMAGE_ZOOM, prop["width"]*IMAGE_ZOOM, self.font.get_entry_image_size()*IMAGE_ZOOM)
                ctx.stroke()
        return True
