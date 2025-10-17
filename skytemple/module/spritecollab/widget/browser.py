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
from __future__ import annotations
import asyncio
import platform
import webbrowser
from threading import Thread
from typing import Optional, TYPE_CHECKING, Any, cast
from collections.abc import Callable
from PIL import Image
from gi.repository import Gtk, GLib, GdkPixbuf
from skytemple.core.ui_utils import (
    assert_not_none,
    create_tree_view_column,
    data_dir,
    safe_destroy,
)
from skytemple_files.common.i18n_util import _, f
from skytemple_files.common.spritecollab.client import (
    DEFAULT_SERVER,
    MonsterFormInfoWithPortrait,
    SpriteCollabClient,
    MonsterFormDetails,
)
from skytemple_files.common.spritecollab.schema import Credit
from skytemple.controller.main import MainController
from skytemple.core.error_handler import display_error
from skytemple.core.list_icon_renderer import ListIconRenderer
from skytemple.init_locale import LocalePatchedGtkTemplate

if TYPE_CHECKING:
    from skytemple.module.spritecollab.module import SpritecollabModule
DEFAULT_SERVER_BROWSER = "https://sprites.pmdcollab.org/"
NOT_SC_SERVER = "https://nss.pmdcollab.org/graphql"
NOT_SC_SERVER_BROWSER = "https://nsc.pmdcollab.org/"


def loader(
    client: SpriteCollabClient,
    callback: Callable[[list[MonsterFormInfoWithPortrait]], Any],
    error_callback: Callable[[Exception], Any],
):
    asyncio.run(
        loader_impl(
            client,
            lambda x: GLib.idle_add(lambda: callback(x)),
            lambda x: GLib.idle_add(lambda: error_callback(x)),
        )
    )


async def loader_impl(
    client: SpriteCollabClient,
    callback: Callable[[list[MonsterFormInfoWithPortrait]], Any],
    error_callback: Callable[[Exception], Any],
):
    try:
        async with client as session:
            value = await session.list_monster_forms(True)
            callback(value)
    except Exception as error:
        error_callback(error)


def entry_loader(
    client: SpriteCollabClient,
    idx: int,
    form_paths: list[str],
    callback: Callable[[list[tuple[MonsterFormDetails, Image.Image]]], Any],
    error_callback: Callable[[Exception], Any],
):
    asyncio.run(
        entry_loader_impl(
            client,
            idx,
            form_paths,
            lambda x: GLib.idle_add(lambda: callback(x)),
            lambda x: GLib.idle_add(lambda: error_callback(x)),
        )
    )


async def entry_loader_impl(
    client: SpriteCollabClient,
    idx: int,
    form_paths: list[str],
    callback: Callable[[list[tuple[MonsterFormDetails, Image.Image]]], Any],
    error_callback: Callable[[Exception], Any],
):
    async with client as session:
        try:
            res = await session.monster_form_details([(idx, p) for p in form_paths])
            res.sort(key=lambda x: x.form_path)
            values: list[tuple[MonsterFormDetails, Image.Image]] = []
            for r in res:
                sheet = await r.fetch_portrait_sheet()
                values.append((r, sheet))
            callback(values)
        except Exception as error:
            error_callback(error)


import os


@LocalePatchedGtkTemplate(filename=os.path.join(data_dir(), "widget", "spritecollab", "browser.ui"))
class StSpritecollabBrowserPage(Gtk.Window):
    __gtype_name__ = "StSpritecollabBrowserPage"
    module: SpritecollabModule
    item_data: None
    sc_store_switcher_combobox: Gtk.ListStore = cast(Gtk.ListStore, Gtk.Template.Child())
    sc_paned: Gtk.Paned = cast(Gtk.Paned, Gtk.Template.Child())
    sc_left: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    sc_infobar: Gtk.InfoBar = cast(Gtk.InfoBar, Gtk.Template.Child())
    sc_tree: Gtk.TreeView = cast(Gtk.TreeView, Gtk.Template.Child())
    sc_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    sc_page_welcome: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    sc_page_content: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    sc_content_stack: Gtk.Stack = cast(Gtk.Stack, Gtk.Template.Child())
    sc_content_switcher: Gtk.StackSidebar = cast(Gtk.StackSidebar, Gtk.Template.Child())
    sc_page_loader: Gtk.Box = cast(Gtk.Box, Gtk.Template.Child())
    sc_header: Gtk.HeaderBar = cast(Gtk.HeaderBar, Gtk.Template.Child())
    sc_search: Gtk.SearchEntry = cast(Gtk.SearchEntry, Gtk.Template.Child())
    sc_external: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    sc_settings: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    sc_help: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    sc_diag_settings: Gtk.Dialog = cast(Gtk.Dialog, Gtk.Template.Child())
    button1: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    button2: Gtk.Button = cast(Gtk.Button, Gtk.Template.Child())
    sc_diag_preset: Gtk.ComboBox = cast(Gtk.ComboBox, Gtk.Template.Child())
    sc_diag_server_url: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    sc_diag_browser_url: Gtk.Entry = cast(Gtk.Entry, Gtk.Template.Child())
    _instance = None

    def __init__(self, module: SpritecollabModule, item_data: None):
        super().__init__()
        self.module = module
        self.item_data = item_data
        self.was_realized = False
        self._search_text: str = ""
        self._spriteserver_url: str = DEFAULT_SERVER
        self._spritebrowser_url: str | None = DEFAULT_SERVER_BROWSER
        self._spriteclient: SpriteCollabClient | None = None
        self._disable_switch = True
        self._something_loading = False
        self.set_parent(MainController.window())
        self.resize(1100, 720)
        # Filtered, Name, ID, Display Label, Form Paths (List[str])
        self._store = Gtk.ListStore(bool, str, int, str, object)
        self._filter = self._store.filter_new()
        self.sc_tree.set_model(self._filter)
        self._filter.set_visible_column(0)
        self.sc_paned.set_position(200)
        self._icon_renderer = ListIconRenderer(3, False)
        self.sc_diag_settings.set_transient_for(self)
        self.sc_diag_settings.set_attached_to(self)
        self.reinit()

    @Gtk.Template.Callback()
    def on_self_destroy(self, *args):
        # Try to destroy all top-level widgets outside of the template to not leak memory.
        safe_destroy(self.sc_diag_settings)

    @classmethod
    def get_instance(cls, module):
        if cls._instance is None:
            cls._instance = cls(module, None)
        return cls._instance

    def reinit(self):
        self._disable_switch = True
        external_button = self.sc_external
        info_bar = self.sc_infobar
        stack = self.sc_stack
        search = self.sc_search
        if self._spritebrowser_url is not None:
            cast(Gtk.HeaderBar, self.get_titlebar()).set_subtitle(self._spritebrowser_url)
            external_button.set_sensitive(True)
        else:
            cast(Gtk.HeaderBar, self.get_titlebar()).set_subtitle(self._spriteserver_url)
            external_button.set_sensitive(False)
        self._store.clear()
        self._filter.refilter()
        search.set_text("")
        info_bar.set_revealed(True)
        stack.set_visible_child(self.sc_page_welcome)
        self._spriteclient = SpriteCollabClient(
            server_url=self._spriteserver_url, use_ssl=platform.system() != "Windows"
        )
        Thread(
            target=loader,
            args=(self._spriteclient, self.after_init, self.error_during_init),
            daemon=True,
        ).start()

    def after_init(self, monsters: list[MonsterFormInfoWithPortrait]):
        info_bar = self.sc_infobar
        monsters.sort(key=lambda m: m.monster_id)
        lists_form_paths: dict[int, list[str]] = {}
        for monster in monsters:
            if monster.monster_id not in lists_form_paths:
                lists_form_paths[monster.monster_id] = []
            lists_form_paths[monster.monster_id].append(monster.form_path)
            if monster.form_path == "" or monster.form_path == "0" or monster.form_path == "0000":
                self._store.append(
                    [
                        True,
                        monster.monster_name,
                        monster.monster_id,
                        f"{monster.monster_id:04}: {monster.monster_name}",
                        lists_form_paths[monster.monster_id],
                    ]
                )
        info_bar.set_revealed(False)
        self._disable_switch = False

    def error_during_init(self, error: Exception):
        info_bar = self.sc_infobar
        display_error(
            error,
            _("Failed loading list of Pokémon from the configured SpriteCollab server."),
            _("Error Updating Sprites"),
            window=self,
        )
        info_bar.set_revealed(False)

    @Gtk.Template.Callback()
    def on_sc_tree_selection_changed(self, selection: Gtk.TreeSelection):
        model, treeiter = selection.get_selected()
        if not self._disable_switch and treeiter is not None and (model is not None):
            self.load_entry(model[treeiter][2], model[treeiter][4])

    @Gtk.Template.Callback()
    def on_sc_settings_clicked(self, *args):
        diag = self.sc_diag_settings
        diag_preset = self.sc_diag_preset
        diag_server_url = self.sc_diag_server_url
        diag_browser_url = self.sc_diag_browser_url
        # Label, Custom select, preset server url, preset browser url
        model = cast(Optional[Gtk.ListStore], diag_preset.get_model())
        had_model = model is not None
        if not had_model:
            model = Gtk.ListStore(str, bool, str, str)
        assert model is not None
        model.clear()
        model.append(
            [
                f(_("SpriteCollab (SpriteBot, {DEFAULT_SERVER})")),
                False,
                DEFAULT_SERVER,
                DEFAULT_SERVER_BROWSER,
            ]
        )
        model.append(
            [
                f(_("NotSpriteCollab ({NOT_SC_SERVER})")),
                False,
                NOT_SC_SERVER,
                NOT_SC_SERVER_BROWSER,
            ]
        )
        model.append([_("Custom Server"), True, "", ""])
        if not had_model:
            diag_preset.set_model(model)
            renderer_text = Gtk.CellRendererText()
            diag_preset.pack_start(renderer_text, True)
            diag_preset.add_attribute(renderer_text, "text", 0)
        active_id = 2
        if self._spriteserver_url == DEFAULT_SERVER:
            active_id = 0
        elif self._spriteserver_url == NOT_SC_SERVER:
            active_id = 1
        diag_preset.set_active(active_id)
        answer = diag.run()
        diag.hide()
        if answer == Gtk.ResponseType.APPLY:
            self._spriteserver_url = diag_server_url.get_text()
            browser_text = diag_browser_url.get_text()
            self._spritebrowser_url = browser_text if browser_text != "" else None
            self.reinit()

    @Gtk.Template.Callback()
    def on_sc_help_clicked(self, *args):
        from skytemple.controller.main import SKYTEMPLE_WIKI_LINK

        webbrowser.open(f"{SKYTEMPLE_WIKI_LINK}/index.php/SkyTemple:UI-Link/skytemple-spritecollab-browser")

    @Gtk.Template.Callback()
    def on_sc_diag_preset_changed(self, w: Gtk.ComboBox, *args):
        diag_server_url = self.sc_diag_server_url
        diag_browser_url = self.sc_diag_browser_url
        model = w.get_model()
        treeiter = w.get_active_iter()
        if model is None or treeiter is None:
            return
        row = model[treeiter]
        if row is None:
            return
        diag_server_url.set_text(row[2])
        diag_browser_url.set_text(row[3])
        diag_server_url.set_sensitive(row[1])
        diag_browser_url.set_sensitive(row[1])

    @Gtk.Template.Callback()
    def on_sc_external_clicked(self, *args):
        if self._spritebrowser_url is not None:
            webbrowser.open_new_tab(self._spritebrowser_url)

    @Gtk.Template.Callback()
    def on_sc_search_search_changed(self, search: Gtk.SearchEntry):
        """Filter the main item view using the search field"""
        self._search_text = search.get_text().strip()
        if self._search_text == "":
            self._store.foreach(self._filter__reset_row, True)
        else:
            self.sc_tree.collapse_all()
            self._store.foreach(self._filter__reset_row, False)
            self._store.foreach(self._filter__show_matches)
            self._filter.foreach(self._filter__expand_all_visible)

    def _filter__reset_row(self, model, path, iter, make_visible):
        """Change the visibility of the given row"""
        self._store[iter][0] = make_visible

    def _filter__make_path_visible(self, model, iter):
        """Make a row and its ancestors visible"""
        while iter:
            self._store[iter][0] = True
            iter = model.iter_parent(iter)

    def _filter__make_subtree_visible(self, model, iter):
        """Make descendants of a row visible"""
        for i in range(model.iter_n_children(iter)):
            subtree = model.iter_nth_child(iter, i)
            if model[subtree][0]:
                # Subtree already visible
                continue
            self._store[subtree][0] = True
            self._filter__make_subtree_visible(model, subtree)

    def _filter__expand_all_visible(self, model: Gtk.TreeStore, path, iter):
        """
        This is super annoying. Because of the two different "views" on the model,
        we can't do this in show_matches, because we have to use the filter model here!
        """
        search_query = self._search_text.lower()
        text = model[iter][1].lower()
        if search_query in text:
            self.sc_tree.expand_to_path(path)

    def _filter__show_matches(self, model: Gtk.TreeStore, path, iter):
        search_query = self._search_text.lower()
        text = model[iter][1].lower()
        if search_query in text:
            # Propagate visibility change up
            self._filter__make_path_visible(model, iter)
            # Propagate visibility change down
            self._filter__make_subtree_visible(model, iter)

    def load_entry(self, idx: int, form_paths: list[str]):
        # sanity check:
        if self._something_loading:
            return
        self._something_loading = True
        stack = self.sc_stack
        stack.set_visible_child(self.sc_page_loader)
        self.sc_tree.set_sensitive(False)
        Thread(
            target=entry_loader,
            args=(
                self._spriteclient,
                idx,
                form_paths,
                self.after_load_entry,
                self.error_during_load_entry,
            ),
            daemon=True,
        ).start()

    def after_load_entry(self, details: list[tuple[MonsterFormDetails, Image.Image]]):
        try:
            if len(details) < 1:
                raise ValueError("Invalid result returned: No form.")
            stack = self.sc_stack
            switcher = self.sc_content_switcher
            content_stack = self.sc_content_stack
            content_stack.set_vhomogeneous(False)
            content_stack.set_hhomogeneous(False)
            self.clear_entries()
            for d in details:
                self.populate_form(*d)
            stack.set_visible_child(self.sc_page_content)
            content_stack.set_visible_child(content_stack.get_children()[0])
            # cool bug. first entry in sidebar does not autofocus.
            try:
                scrolled_window = cast(Gtk.ScrolledWindow, switcher.get_children()[0])
                viewport = cast(Gtk.Viewport, scrolled_window.get_children()[0])
                list_box = cast(Gtk.ListBox, viewport.get_children()[0])
                first_row = cast(Gtk.ListBoxRow, list_box.get_children()[0])
                list_box.select_row(first_row)
            except Exception:
                # this is not worth breaking over.
                pass
        except Exception as err:
            self.error_during_load_entry(err)
        self._something_loading = False
        self.sc_tree.set_sensitive(True)

    def error_during_load_entry(self, error: Exception):
        stack = self.sc_stack
        display_error(
            error,
            _("Failed loading this Pokémon."),
            _("Error Loading Pokémon"),
            window=self,
        )
        stack.set_visible_child(self.sc_page_welcome)
        self._something_loading = False
        self.sc_tree.set_sensitive(True)

    def clear_entries(self):
        stack = self.sc_content_stack
        for child in stack.get_children():
            stack.remove(child)

    def populate_form(self, form: MonsterFormDetails, portrait: Image.Image):
        assert self._spriteclient is not None
        stack = self.sc_content_stack
        form_name = form.full_form_name.replace(form.monster_name, "", 1).lstrip()
        if form_name == "":
            form_name = _("Normal")
        new_child: Gtk.Grid = Gtk.Grid.new()
        new_child.set_margin_start(10)
        new_child.set_margin_end(10)
        new_child.set_margin_top(10)
        new_child.set_margin_bottom(10)
        new_child.set_row_spacing(10)
        new_child.set_column_spacing(5)
        name_label: Gtk.Label = Gtk.Label.new("")
        name_label.set_markup(f'<span size="24pt">{form.full_form_name}</span>')
        name_label.set_hexpand(True)
        new_child.attach(name_label, 0, 0, 2, 1)
        # Portraits
        portraits_label: Gtk.Label = Gtk.Label.new("")
        portraits_label.set_markup(_("<b>Portraits:</b>"))
        portraits_label.set_hexpand(True)
        new_child.attach(portraits_label, 0, 1, 1, 1)
        portrait_data = portrait.convert("RGBA").tobytes()
        portrait_w, portrait_h = portrait.size
        pix = GdkPixbuf.Pixbuf.new_from_bytes(
            GLib.Bytes.new(portrait_data),
            GdkPixbuf.Colorspace.RGB,
            True,
            8,
            portrait_w,
            portrait_h,
            portrait_w * 4,
        )
        image: Gtk.Image = Gtk.Image.new_from_pixbuf(pix.copy())
        new_child.attach(image, 0, 2, 1, 1)
        portraits_button: Gtk.Button = Gtk.Button.new_with_label(_("Apply Portraits"))
        portraits_button.connect(
            "clicked",
            lambda *args: self.module.apply_portraits(self, portrait),
        )
        new_child.attach(portraits_button, 0, 3, 1, 1)
        # Sprites
        sprites_label: Gtk.Label = Gtk.Label.new("")
        sprites_label.set_markup(_("<b>Sprites:</b>"))
        sprites_label.set_hexpand(True)
        new_child.attach(sprites_label, 1, 1, 1, 1)
        sprite_forms_sw: Gtk.ScrolledWindow = Gtk.ScrolledWindow.new()
        sprite_forms_sw.set_max_content_height(400)
        sprite_forms_container: Gtk.TreeView = Gtk.TreeView.new()
        sprite_forms_store = Gtk.ListStore(str)
        sprite_forms_container.set_model(sprite_forms_store)
        renderer = Gtk.CellRendererText.new()
        sprite_forms_column: Gtk.TreeViewColumn = create_tree_view_column("", renderer, text=0)
        sprite_forms_container.append_column(sprite_forms_column)
        sprite_forms_container.set_headers_visible(False)
        for sprite in sorted(list(form.sprites.keys())):
            sprite_forms_store.append([sprite])
        for sprite, copy_of in form.sprites_copy_of.items():
            sprite_forms_store.append([f"{sprite} (copy of {copy_of})"])
        sprite_forms_sw.add(sprite_forms_container)
        new_child.attach(sprite_forms_sw, 1, 2, 1, 1)
        sprite_button: Gtk.Button = Gtk.Button.new_with_label(_("Apply Sprites"))
        sprite_button.connect(
            "clicked",
            lambda *args: self.module.apply_sprites(self, assert_not_none(self._spriteclient), form),
        )
        new_child.attach(sprite_button, 1, 3, 1, 1)
        credit_child: Gtk.Grid = Gtk.Grid.new()
        credit_child.set_margin_top(10)
        credit_child.set_margin_bottom(10)
        credit_child.set_row_spacing(10)
        credit_child.set_column_spacing(5)
        credit_child.set_hexpand(True)
        new_child.attach(credit_child, 0, 4, 2, 1)
        label: Gtk.Label = Gtk.Label.new("")
        label.set_markup(_("<b><i>Make sure to credit artists:</i></b>"))
        label.set_hexpand(True)
        credit_child.attach(label, 0, 0, 2, 1)
        # Portrait credits
        portrait_credits: Gtk.Label = Gtk.Label.new("")
        portrait_credits.set_markup(_("<b>Portrait Credits:</b>"))
        portrait_credits.set_hexpand(False)
        portrait_credits.set_halign(Gtk.Align.START)
        portrait_credits.set_valign(Gtk.Align.START)
        portrait_credits.set_justify(Gtk.Justification.LEFT)
        credit_child.attach(portrait_credits, 0, 1, 1, 1)
        portrait_credits_content: Gtk.TextView = Gtk.TextView.new()
        portrait_credits_content.get_buffer().set_text(self._credits(form.portrait_credits))
        portrait_credits_content.set_wrap_mode(Gtk.WrapMode.WORD)
        portrait_credits_content.set_hexpand(True)
        credit_child.attach(portrait_credits_content, 1, 1, 1, 1)
        # Sprite credits
        sprite_credits: Gtk.Label = Gtk.Label.new("")
        sprite_credits.set_markup(_("<b>Sprite Credits:</b>"))
        sprite_credits.set_hexpand(False)
        sprite_credits.set_valign(Gtk.Align.START)
        sprite_credits.set_halign(Gtk.Align.START)
        sprite_credits.set_justify(Gtk.Justification.LEFT)
        credit_child.attach(sprite_credits, 0, 2, 1, 1)
        sprite_credits_content: Gtk.TextView = Gtk.TextView.new()
        sprite_credits_content.get_buffer().set_text(self._credits(form.sprite_credits))
        sprite_credits_content.set_wrap_mode(Gtk.WrapMode.WORD)
        sprite_credits_content.set_hexpand(True)
        credit_child.attach(sprite_credits_content, 1, 2, 1, 1)
        # Button for details
        details_button: Gtk.Button = Gtk.Button.new_with_label(_("Open Details on Website..."))
        if self._spritebrowser_url is not None:
            details_button.connect(
                "clicked",
                lambda *args: webbrowser.open_new_tab(
                    f"{assert_not_none(self._spritebrowser_url).rstrip('/')}/#/{form.monster_id:04}"
                ),
            )
        else:
            details_button.set_sensitive(False)
        new_child.attach(details_button, 0, 5, 2, 1)
        new_child.show_all()
        stack.add_titled(new_child, form_name, form_name)

    @Gtk.Template.Callback()
    def gtk_widget_hide_on_delete(self, w: Gtk.Widget, *args):
        w.hide_on_delete()
        return True

    def _credits(self, credits: list[Credit]):
        crstr = ""
        for c in credits:
            crstr += parse_credit(c) + "\n"
        if crstr == "":
            crstr = "n/a"
        return crstr.rstrip()


def parse_credit(credit: Credit) -> str:
    artist_name = credit["id"]
    if credit["name"] is not None:
        artist_name = credit["name"]
    elif credit["discordHandle"] is not None:
        artist_name = credit["discordHandle"]
    link = ""
    if credit["contact"] is not None:
        link = f" ({credit['contact']})"
    return f"{artist_name}{link}"
